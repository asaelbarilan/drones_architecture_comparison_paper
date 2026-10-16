"""A visual task cannot pass just because a model says stop at a local waypoint."""

import importlib
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from PIL import Image, ImageDraw


@pytest.mark.parametrize("distance,visible,stopped,expected", [
    (5, True, True, False), (1, False, True, False),
    (1, True, False, False), (1, True, True, True)])
def test_independent_object_score(monkeypatch, distance, visible, stopped, expected):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts/diagnostics"))
    score = importlib.import_module("run_qwen_visual_object").score
    settings = dict(audit_criteria=dict(near_object_m=1.5), stopped_mps=.2, max_tick_gap_s=.15)
    state = NS(stopped=stopped, failed=False, settings=settings)
    obs, evidence = NS(velocity=NS(norm=lambda: 0)), NS(events=[])
    status = NS(goal_visible=visible, distance_to_goal_m=distance, collided=False,
                out_of_bounds=False, collision_count=0)
    assert score(state, obs, evidence, [.05], status)["task_pass"] is expected


def test_pixel_audit_distinguishes_target_from_background(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts/diagnostics"))
    audit = importlib.import_module("audit_qwen_visual_object")
    image = Image.new("RGB", (10, 10), (100, 110, 100))
    ImageDraw.Draw(image).rectangle((2, 1, 5, 4), fill=(200, 40, 40))
    path = tmp_path / "frame.png"
    image.save(path)
    target = dict(u=400, v=300, travel_m=1, target_visible=True, box=[200, 100, 600, 500])
    correct = audit.check_pixels(path, target)
    assert correct["point_on_red"] and correct["box_iou"] == 1
    wrong = audit.check_pixels(path, dict(target, u=800, v=800))
    assert not wrong["point_on_red"]
