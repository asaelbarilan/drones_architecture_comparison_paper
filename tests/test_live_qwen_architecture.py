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


def skill_agent(instruction="Approach the red pillar and stop nearby."):
    state = scheduler(instruction, goal_source="skills", monitor="none", recovery="none",
                      memory=False)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    return state


def turn(state, skill, **args):
    state.worker.finish(dict(skill=skill, args=args, reason="test"))
    state.update(observation(), ORIGIN_NS+s_to_ns(1), ORIGIN_NS+s_to_ns(1), False)


def test_skill_agent_asks_a_text_only_skill_turn_first():
    state = skill_agent()
    request = state.worker.calls[0].request
    assert request.role == "planner" and request.images == ()
    assert '"mission": "Approach the red pillar and stop nearby."' in request.prompt


def test_goto_skill_becomes_one_numeric_goal_relative_to_current_pose():
    state = skill_agent()
    turn(state, "goto", forward_m=3)
    assert state.goal.position == Vec3(x=3, y=0, z=3) and state.settings["goal_mode"] == "numeric"
    assert state.worker.calls[-1].request.role == "pilot"


def test_approach_skill_uses_the_shared_grounding_role():
    state = skill_agent()
    turn(state, "approach", object="red pillar")
    assert state.plan["target"] == "red pillar" and state.settings["goal_mode"] == "visual"
    assert state.worker.calls[-1].request.role == "direction"


def test_failed_approach_returns_control_and_history_to_the_agent():
    state = skill_agent()
    turn(state, "approach", object="red pillar")
    state.request_planner("target_lost", ORIGIN_NS+s_to_ns(2))
    assert state.plan is None and state.skill is None
    assert state.skill_history[-1]["result"] == "target_lost"


def test_hover_waits_then_hands_back_and_done_stops():
    state = skill_agent()
    turn(state, "hover", seconds=2)
    assert state.skill["skill"] == "hover"
    state.update(observation(), ORIGIN_NS+s_to_ns(4), ORIGIN_NS+s_to_ns(4), False)
    assert state.skill_history[-1]["result"] == "hovered"
    turn(state, "done")
    assert state.stopped


def test_unknown_skill_is_a_contract_failure_not_an_action():
    state = skill_agent()
    turn(state, "teleport")
    assert state.failures == 1 and state.goal is None


def native_vla():
    state = scheduler(goal_source="vla_native", monitor="none", recovery="none", memory=False,
                      verifier=False)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    return state


def test_native_vla_first_asks_the_vla_for_its_own_line_with_image():
    state = native_vla()
    request = state.worker.calls[0].request
    assert request.role == "vla_line" and len(request.images) == 1
    assert json.loads(request.prompt) == dict(instruction=state.mission.instruction,
                                              state=[0.0, 0.0, 0.0, 0.0])


def test_native_vla_line_becomes_the_goal_and_the_vla_flies_it():
    state = native_vla()
    state.worker.finish(dict(box=None, left=[4.0, 0.0, 0.0, 0.0], said="Left +04.0"))
    state.update(observation(), ORIGIN_NS+s_to_ns(1), ORIGIN_NS+s_to_ns(1), False)
    assert state.goal.position == Vec3(x=4, y=0, z=3) and state.goal.terminal
    assert state.worker.calls[-1].request.role == "pilot"


def test_native_vla_without_a_line_is_a_contract_failure():
    state = native_vla()
    state.worker.finish(dict(box=None, left=None, said="nonsense"))
    state.update(observation(), ORIGIN_NS+s_to_ns(1), ORIGIN_NS+s_to_ns(1), False)
    assert state.failures == 1 and state.goal is None
