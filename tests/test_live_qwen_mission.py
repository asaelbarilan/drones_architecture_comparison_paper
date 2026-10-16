"""Mission preservation and measured completion, independent of model wording."""

import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import s_to_ns
from uavlab.live_qwen.mission_plan import accept_plan, parse_steps, validate_direction
from uavlab.live_qwen.prompts import monitor_context, role_request

state = scheduler_fixture


def ordered(state):
    steps = [dict(objective="Move forward two meters", target=[2, 0, 0, 0]),
             dict(objective="Turn right fifteen degrees", target=[0, 0, 0, 15])]
    accept_plan(state, dict(steps=steps), ORIGIN_NS)
    return state.steps


def test_replan_keeps_mission_and_step(state):
    scheduler, _ = state
    mission = scheduler.mission.instruction
    steps = ordered(scheduler)
    scheduler.replan("scene uncertainty", ORIGIN_NS)
    assert scheduler.steps == steps and scheduler.step_index == 0
    assert scheduler.plan == steps[0] and scheduler.mission.instruction == mission
    with pytest.raises(ValueError, match="cannot replace"):
        accept_plan(scheduler, dict(steps=steps[:1]), ORIGIN_NS)


def test_cannot_combine_steps_or_drop_heading(state):
    scheduler, _ = state
    ordered(scheduler)
    for target, terminal in (([2, 0, 0, 15], True), ([2, 0, 0, 0], True)):
        with pytest.raises(ValueError):
            scheduler.accept_goal(dict(kind="relative", target=target, terminal=terminal),
                                  observation(), ORIGIN_NS, ORIGIN_NS)


def test_step_advancement_requires_arrival_heading_and_settled(state):
    scheduler, _ = state
    steps = ordered(scheduler)
    scheduler.accept_goal(dict(kind="relative", target=steps[0]["target"], terminal=False),
                          observation(), ORIGIN_NS, ORIGIN_NS)
    for status, obs in (("continue", observation(0)), ("stop", observation(2, speed=.3)),
                        ("stop", observation(0)), ("stop", observation(2, yaw=.2))):
        scheduler.accept_monitor(dict(status=status, reason="test"), obs, ORIGIN_NS)
        assert scheduler.step_index == 0 and not scheduler.stopped
    scheduler.accept_monitor(dict(status="stop", reason="arrived"), observation(2), ORIGIN_NS)
    assert scheduler.step_index == 1 and scheduler.plan == steps[1]
    assert not scheduler.stopped


def test_hold_preserves_current_goal_and_waits(state):
    scheduler, _ = state
    ordered(scheduler)
    goal = scheduler.goal
    scheduler.accept_monitor(dict(status="hold", reason="uncertain"), observation(), ORIGIN_NS)
    scheduler.update(observation(), ORIGIN_NS, ORIGIN_NS+1, False)
    assert scheduler.goal is goal and scheduler.step_index == 0
    assert not scheduler.worker.calls
    assert scheduler.hold_until == ORIGIN_NS+s_to_ns(scheduler.settings["monitor_retry_s"])


def test_stationary_hold_mission_can_finish_without_actions(state):
    scheduler, rows = state
    accept_plan(scheduler, dict(steps=[dict(objective="Hold", target=[0, 0, 0, 0])]), ORIGIN_NS)
    scheduler.accept_goal(dict(kind="relative", target=[0, 0, 0, 0], terminal=True),
                          observation(), ORIGIN_NS, ORIGIN_NS)
    scheduler.accept_monitor(dict(status="stop", reason="stationary"), observation(), ORIGIN_NS)
    assert scheduler.stopped and not scheduler.worker.calls
    assert not any(row["kind"] == "action_consumed" for row in rows)


def test_step_changes_accumulate_without_repeating_motion(state):
    scheduler, _ = state
    ordered(scheduler)
    assert scheduler.steps[1]["target"] == [2, 0, 0, 15]
    value = validate_direction(scheduler, dict(kind="relative", target=[2, 0, 0, 0]))
    assert value["terminal"] is False
    scheduler.step_index = 1
    value = validate_direction(scheduler, dict(kind="relative", target=[2, 0, 0, 15]))
    assert value["terminal"] is True


@pytest.mark.parametrize("steps", [[], [dict(objective="hold", target=[float('nan'), 0, 0, 0])]])
def test_empty_or_nonfinite_plan_rejected(steps):
    with pytest.raises(ValueError):
        parse_steps(dict(steps=steps))


@pytest.mark.parametrize("pose,accepted", [
    ((1.51, .08, .19), True), ((1.49, 0, 0), False),
    ((2, .09, 0), False), ((2, 0, .21), False)])
def test_completion_respects_all_unchanged_tolerances(state, pose, accepted):
    scheduler, _ = state
    x, yaw, speed = pose
    obs = observation(x, yaw, speed)
    scheduler.accept_monitor(dict(status="stop", reason="test"), obs, ORIGIN_NS)
    assert scheduler.stopped is accepted
    context = monitor_context(scheduler, obs)
    assert context["position_error_m"] == abs(2-x)
    assert "remaining" not in context and "plan" not in context


def test_numeric_completion_is_not_blocked_by_model_arithmetic(state):
    scheduler, rows = state
    ordered(scheduler)
    scheduler.accept_goal(dict(kind="relative", target=[2, 0, 0, 0]),
                          observation(), ORIGIN_NS, ORIGIN_NS)
    scheduler.accept_monitor(dict(status="continue", reason="0.4 exceeds 0.5"),
                             observation(1.6), ORIGIN_NS)
    assert scheduler.step_index == 1 and not scheduler.stopped
    assert any(r["kind"] == "numeric_completion_override" for r in rows)


def test_safety_hold_still_vetoes_numeric_completion(state):
    scheduler, _ = state
    ordered(scheduler)
    scheduler.accept_monitor(dict(status="hold", reason="unsafe"), observation(2), ORIGIN_NS)
    assert scheduler.step_index == 0 and not scheduler.stopped


def test_direction_gets_only_current_target_not_old_step_history(state):
    scheduler, _ = state
    ordered(scheduler)
    scheduler.step_index = 1
    scheduler.plan = dict(scheduler.steps[1])
    prompt = role_request(scheduler, "direction", observation()).prompt
    assert '"authorized_target": [2, 0, 0, 15]' in prompt
    assert '"ordered_steps"' not in prompt and '"completed"' not in prompt
    assert scheduler.mission.instruction and scheduler.steps[1]["target"] == [2, 0, 0, 15]
