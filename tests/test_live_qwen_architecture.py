"""D-160 paper architecture switches over the shared live scheduler (CPU only, no model)."""

import json
from pathlib import Path

import pytest

from tests.test_live_qwen import ORIGIN_NS, ManualWorker, observation
from uavlab.contracts import Vec3, s_to_ns
from uavlab.live_qwen.architecture import DEFAULTS, recovery_due, switches
from uavlab.live_qwen.goals import Goal, interpret_goal
from uavlab.live_qwen.planner_memory import remember
from uavlab.live_qwen.runner import mission_spec
from uavlab.live_qwen.scheduler import GoalScheduler

OUTSIDE_X = 100.0


def scheduler(instruction="Approach the red pillar and stop nearby.", **arch):
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    settings["architecture"] = arch
    case = dict(settings["missions"][0], instruction=instruction)
    return GoalScheduler(ManualWorker(), mission_spec(case, settings), settings, lambda row: None)


def test_defaults_reproduce_the_full_stack_and_unknown_switches_fail():
    assert switches({}) == DEFAULTS
    with pytest.raises(ValueError):
        switches(dict(architecture=dict(planner="maybe")))
    with pytest.raises(ValueError):
        switches(dict(architecture=dict(monitor="sometimes")))
    with pytest.raises(ValueError):
        switches(dict(architecture=dict(memory="yes")))


def test_instruction_source_commits_the_mission_without_a_planner_call():
    state = scheduler(goal_source="instruction")
    state.settings["goal_mode"] = "visual"
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    assert state.steps == [dict(objective=state.mission.instruction,
                                target=state.mission.instruction)]
    assert state.worker.calls[0].request.role == "direction"


def test_instruction_source_keeps_explicit_public_coordinates_as_world_step():
    state = scheduler("Fly to the world ENU coordinate (4, 2, 3) and stop.",
                      goal_source="instruction")
    state.settings["goal_mode"] = "numeric"
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    assert state.plan["target"] == dict(world_enu=[4.0, 2.0, 3.0])


def test_oracle_sets_the_privileged_goal_and_flies_without_cognition():
    state = scheduler(goal_source="oracle")
    state.settings.update(goal_mode="numeric", oracle_goal=[5.0, 0.0, 3.0])
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    assert state.goal.position == Vec3(x=5, y=0, z=3) and state.goal.terminal
    assert state.worker.calls[0].request.role == "pilot"


def test_oracle_stops_short_of_a_visual_goal():
    state = scheduler(goal_source="oracle")
    state.settings.update(goal_mode="numeric", oracle_goal=[6.0, 0.0, 1.0], oracle_visual=True)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    assert state.goal.position == Vec3(x=5, y=0, z=3)


def test_no_monitor_completes_numeric_arrival_directly():
    state = scheduler(goal_source="instruction", monitor="none")
    state.settings["goal_mode"] = "numeric"
    state.steps = [dict(objective="Move forward 2 meters.", target=[2, 0, 0, 0])]
    state.plan, state.origin, state.last_obs = dict(state.steps[0]), observation(), observation(2)
    state.goal = Goal(1, Vec3(x=2, y=0, z=3), 0, True, ORIGIN_NS+s_to_ns(45), 1)
    state.request_monitor("arrival", ORIGIN_NS)
    assert state.stopped and state.monitor_reason is None


def test_no_monitor_turns_near_grounding_into_a_fresh_stop_verification():
    state = scheduler(goal_source="instruction", monitor="none")
    state.settings["goal_mode"] = "visual"
    state.steps = [dict(objective="Approach", target="red pillar")]
    state.plan, state.origin, state.last_obs = dict(state.steps[0]), observation(), observation(2)
    state.goal = Goal(1, Vec3(x=2, y=0, z=3), 0, False, ORIGIN_NS+s_to_ns(45), 1)
    state.request_monitor("fresh object proximity; verify visual accomplishment", ORIGIN_NS)
    assert state.visual_stop_pending and state.goal is None and state.monitor_reason is None


@pytest.mark.parametrize("recovery,event", [("event", True), ("none", False)])
def test_recovery_switch_controls_the_planner_wakeup(recovery, event):
    state = scheduler(recovery=recovery)
    state.steps = [dict(objective="Approach", target="red pillar")]
    state.plan = dict(state.steps[0])
    state.request_planner("stalled_progress", ORIGIN_NS)
    assert bool(state.planner_event) is event


def test_periodic_recovery_is_due_after_its_interval():
    state = scheduler(recovery="periodic", recovery_interval_s=5)
    state.steps, state.last_recovery = [dict(objective="Approach", target="x")], ORIGIN_NS
    assert not recovery_due(state, ORIGIN_NS+s_to_ns(4))
    assert recovery_due(state, ORIGIN_NS+s_to_ns(5))


def test_memory_switch_keeps_no_event_history():
    state = scheduler(memory=False)
    remember(state, "target_observed", ORIGIN_NS)
    assert state.memory == []


@pytest.mark.parametrize("verifier", [True, False])
def test_verifier_switch_controls_the_envelope_check(verifier):
    state = scheduler(verifier=verifier)
    payload = dict(kind="world", target=dict(world_enu=[OUTSIDE_X, 0.0, 3.0]), terminal=True)
    if verifier:
        with pytest.raises(ValueError):
            interpret_goal(payload, observation(), observation(), state.settings)
    else:
        position, _, _ = interpret_goal(payload, observation(), observation(), state.settings)
        assert position.x == OUTSIDE_X
