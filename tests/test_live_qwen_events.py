import json

import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import s_to_ns
from uavlab.live_qwen.mission_plan import accept_plan
from uavlab.live_qwen.planner_memory import MEMORY_LIMIT, accept_recovery, planner_context, remember
from uavlab.live_qwen.prompts import monitor_context, role_request

state = scheduler_fixture


def visual(state):
    scheduler, _ = state
    scheduler.settings["goal_mode"] = "visual"
    accept_plan(scheduler, dict(steps=[dict(objective="Approach and stop", target="red pillar")]),
                ORIGIN_NS)
    return scheduler


def test_waypoint_arrival_refreshes_grounding_without_planner_or_monitor(state):
    scheduler = visual(state)
    scheduler.check_events(observation(2), ORIGIN_NS+s_to_ns(3))
    assert scheduler.goal is None and scheduler.monitor_reason is None
    assert scheduler.next_role(observation(2), False) == "direction"
    assert scheduler.step_index == 0 and scheduler.plan["target"] == "red pillar"
    assert not scheduler.planner_event


def test_target_loss_wakes_planner_once_with_original_goal_and_memory(state):
    scheduler = visual(state)
    scheduler.goal = None
    for offset in (0, 3):
        scheduler.accept_goal(dict(target_visible=False, box=None), observation(),
                              ORIGIN_NS, ORIGIN_NS+s_to_ns(offset))
    assert scheduler.next_role(observation(), False) == "planner"
    context = planner_context(scheduler)
    assert context["original_mission"] == scheduler.mission.instruction
    assert context["committed_steps"] == scheduler.steps
    assert sum(e["event"] == "target_lost" for e in scheduler.memory) == 1
    prompt = role_request(scheduler, "planner", observation()).prompt
    assert '"trigger": "target_lost"' in prompt and '"target": "red pillar"' in prompt


@pytest.mark.parametrize("action", ["retry_current", "refresh_view", "hold"])
def test_planner_recovery_retains_steps_and_original_goal(state, action):
    scheduler = visual(state)
    before = json.dumps(scheduler.steps)
    scheduler.request_planner("stalled_progress", ORIGIN_NS)
    accept_recovery(scheduler, dict(action=action, reason="recover same target"), ORIGIN_NS)
    assert json.dumps(scheduler.steps) == before and scheduler.step_index == 0
    assert scheduler.plan["target"] == "red pillar" and not scheduler.stopped
    assert scheduler.planner_event is None
    assert (scheduler.hold_until > ORIGIN_NS) is (action == "hold")


def test_recovery_cannot_skip_or_complete_mission(state):
    scheduler = visual(state)
    scheduler.request_planner("target_lost", ORIGIN_NS)
    with pytest.raises(ValueError):
        accept_recovery(scheduler, dict(action="complete", reason="pretend done"), ORIGIN_NS)
    assert scheduler.step_index == 0 and not scheduler.stopped


@pytest.mark.parametrize("distance,fresh,near", [(4.0, True, False), (1.0, True, True),
                                               (None, True, False), (1.0, False, False)])
def test_monitor_distinguishes_waypoint_from_object(state, distance, fresh, near):
    scheduler = visual(state)
    obs = observation(2)
    scheduler.visual_source = obs
    scheduler.visual_evidence = dict(range_m=distance,
                                    expires_ns=ORIGIN_NS+s_to_ns(1 if fresh else -1))
    context = monitor_context(scheduler, obs)
    assert context["waypoint_reached"] is True
    assert context["object_near"] is near
    assert context["object_evidence_fresh"] is fresh
    assert "position_and_heading_acceptable" not in context


def test_memory_bounded_but_committed_plan_is_not_evicted(state):
    scheduler = visual(state)
    for seq in range(MEMORY_LIMIT*2):
        remember(scheduler, "observation", ORIGIN_NS+seq)
    assert len(scheduler.memory) == MEMORY_LIMIT
    assert planner_context(scheduler)["committed_steps"] == scheduler.steps
