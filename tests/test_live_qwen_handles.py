"""D-168 handles H1 (typed task contract) and H2 (kind-aware executive), CPU only."""

import json
from pathlib import Path

import pytest

from tests.test_live_qwen import ORIGIN_NS, ManualWorker, observation
from uavlab.contracts import Vec3, s_to_ns
from uavlab.live_qwen.contract import parse_contract
from uavlab.live_qwen.executive import HOLD, adjust_visual, follow_done
from uavlab.live_qwen.goals import Goal
from uavlab.live_qwen.runner import mission_spec
from uavlab.live_qwen.scheduler import GoalScheduler

MISSION = ("If the left gap is clear fly through it, otherwise through the right gap. "
           "Then visit the red pillar.")
PROGRAM = dict(program=[
    dict(kind="condition", question="Is the left gap clear?",
         then=[dict(kind="pass", object="left gap")],
         **{"else": [dict(kind="pass", object="right gap")]}),
    dict(kind="visit", object="red pillar", near_m=2, dwell_s=0, stop=True)])
FAR_M, BAND = 9.0, (4, 6)
ALTITUDE_M = 3.2
HOVER_LIMIT_M = 1.15
OPENING_M, BEYOND_M = 3.0, 2.0
TYPED_START = "Write the mission as a small typed program"


def scheduler(contract="typed", executive="kinds"):
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    settings["architecture"] = dict(contract=contract, executive=executive)
    settings["goal_mode"] = "visual"
    case = dict(settings["missions"][0], instruction=MISSION)
    state = GoalScheduler(ManualWorker(), mission_spec(case, settings), settings, lambda row: None)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    return state


def answer(state, payload, at=1):
    state.worker.finish(payload)
    state.update(observation(), ORIGIN_NS+s_to_ns(at), ORIGIN_NS+s_to_ns(at), False)


def test_contract_rejects_structure_errors_but_repairs_small_ones():
    program, repairs = parse_contract(PROGRAM, MISSION)
    assert program[0]["kind"] == "condition" and repairs == []
    with pytest.raises(ValueError):
        parse_contract(dict(program=[dict(kind="teleport")]), MISSION)
    with pytest.raises(ValueError):  # the only step invents a coordinate: nothing left to run
        parse_contract(dict(program=[dict(kind="goto", world_enu=[1, 2, 3])]), MISSION)
    noisy = dict(program=[dict(PROGRAM["program"][0], stop=False),
                          dict(kind="follow", object="car", min_m=6, max_m=0, duration_s=10)])
    program, repairs = parse_contract(noisy, MISSION)
    assert "stop" not in program[0] and (program[1]["min_m"], program[1]["max_m"]) == (0.5, 6)
    assert any("dropped" in r for r in repairs) and any("clamped" in r for r in repairs)


def test_stated_hover_distance_and_altitude_reach_the_executable_visit():
    from uavlab.live_qwen.contract import executable

    node = parse_contract(dict(program=[dict(kind="visit", object="car", near_m=1,
                                             altitude_m=3.2)]),
                          "Hover above the car at 3.2 metres altitude.")[0][0]
    step = executable(node)
    assert step["standoff_m"] == 1.0 and step["altitude_m"] == ALTITUDE_M
    assert node["dwell_s"] == 0.0 and node["stop"] is False


def test_typed_planner_prompt_is_used_and_a_condition_asks_the_camera():
    state = scheduler()
    assert state.worker.calls[0].request.prompt.startswith(TYPED_START)
    answer(state, PROGRAM)
    request = state.worker.calls[-1].request
    assert request.role == "check" and len(request.images) == 1
    assert request.prompt.endswith("Is the left gap clear?")


def test_condition_answer_splices_the_chosen_branch():
    state = scheduler()
    answer(state, PROGRAM)
    answer(state, dict(answer="no", reason="a wall blocks the left gap"), at=2)
    assert [s["target"] for s in state.steps] == ["right gap", "red pillar"]
    assert state.plan["kind"] == "pass" and state.worker.calls[-1].request.role == "direction"


def test_without_the_executive_the_typed_contract_is_flattened_and_inert():
    state = scheduler(executive="basic")
    answer(state, PROGRAM)
    assert "kind" not in state.steps[0] and state.steps[0]["objective"].startswith("if Is the left")
    assert state.worker.calls[-1].request.role == "direction"


def test_pass_aims_beyond_the_opening_and_completes_on_arrival():
    state = scheduler()
    state.steps = [dict(kind="pass", objective="pass gap", target="gap"),
                   dict(kind="visit", objective="visit pillar", target="pillar", final=True)]
    state.plan = dict(state.steps[0])
    proposal = dict(target=dict(u=500, v=500, travel_m=1.0))
    travel = adjust_visual(state, proposal, OPENING_M, ORIGIN_NS)["target"]["travel_m"]
    assert travel == OPENING_M + BEYOND_M
    state.goal = Goal(2, Vec3(x=0, y=0, z=3), 0, False, ORIGIN_NS+s_to_ns(45), 1)
    state.continue_mission(observation(), ORIGIN_NS)
    assert state.step_index == 1 and state.plan["target"] == "pillar" and not state.stopped


def test_follow_keeps_its_band_and_ends_only_after_its_duration():
    state = scheduler()
    state.steps = [dict(kind="follow", objective="follow car", target="car", min_m=BAND[0],
                        max_m=BAND[1], duration_s=20)]
    state.plan = dict(state.steps[0])
    far = adjust_visual(state, dict(target=dict(u=500, v=500, travel_m=1.0)), FAR_M, ORIGIN_NS)
    assert far["target"]["travel_m"] == pytest.approx(FAR_M - BAND[0])
    near = dict(target=dict(u=500, v=500, travel_m=1.0))
    assert adjust_visual(state, near, BAND[0], ORIGIN_NS) is HOLD
    assert not follow_done(state, ORIGIN_NS+s_to_ns(19))
    assert follow_done(state, ORIGIN_NS+s_to_ns(20))


def test_altitude_critic_drops_a_limit_written_as_an_altitude():
    limited = "Fly to the red pillar through the passage. Stay below 7 metres."
    node, repairs = parse_contract(dict(program=[dict(kind="visit", object="red pillar",
                                                      altitude_m=7)]), limited)
    assert node[0]["altitude_m"] is None and any("altitude" in r for r in repairs)
    stated = "Hover above the car at 3.2 metres altitude."
    node, _ = parse_contract(dict(program=[dict(kind="visit", object="car", altitude_m=3.2)]),
                             stated)
    assert node[0]["altitude_m"] == ALTITUDE_M


def test_malformed_grounding_is_not_visible_only_with_the_executive():
    from uavlab.live_qwen.executive import tolerant_grounding

    bad = dict(target_visible=True, box=None)
    assert tolerant_grounding(scheduler(), bad, ORIGIN_NS) is None
    with pytest.raises(ValueError):
        tolerant_grounding(scheduler(executive="basic"), bad, ORIGIN_NS)


def test_typed_hover_uses_the_tighter_tolerance():
    from uavlab.live_qwen.contract import executable
    from uavlab.live_qwen.stop_rules import near_limit

    state = scheduler()
    node = parse_contract(dict(program=[dict(kind="visit", object="pillar", near_m=1)]),
                          MISSION)[0][0]
    state.plan = executable(node)
    assert near_limit(state) == pytest.approx(HOVER_LIMIT_M)


def test_h11_plan_check_moves_a_one_sided_final_stop_after_the_condition():
    from uavlab.live_qwen.plan_check import final_on_every_path

    stop = dict(kind="visit", object="red pillar", near_m=2, dwell_s=0, stop=True)
    route = dict(kind="search", object="another route around the wall")
    program = [dict(kind="pass", object="open passage"),
               dict(kind="condition", question="Is the passage still open?", then=[route],
                    **{"else": [stop]})]
    repairs = []
    fixed = final_on_every_path(program, repairs)
    assert fixed[-1] == stop and fixed[1]["else"] == [] and fixed[1]["then"] == [route]
    assert len(repairs) == 1
    both = [dict(kind="condition", question="Is A open?", then=[dict(stop, object="A")],
                 **{"else": [dict(stop, object="B")]})]
    assert final_on_every_path(both, []) == both  # each branch has its own destination
