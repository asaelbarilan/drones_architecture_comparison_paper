"""The infrastructure gate refuses insufficient or unknown memory headroom."""

import pytest
from scripts.local_inference_resources import check_headroom


@pytest.mark.parametrize(
    "key", ["available_physical_gib", "available_commit_gib", "available_gpu_gib"]
)
@pytest.mark.parametrize("value", [None, 0, float("nan")])
def test_unknown_or_exhausted_resource_refuses_start(key, value):
    sample = dict(available_physical_gib=12, available_commit_gib=20, available_gpu_gib=7)
    sample[key] = value
    result = check_headroom(sample)
    assert not result["ready"]
    assert result["shortfalls"][0]["resource"] == key


def test_admission_distinguishes_before_and_after_loading():
    sample = dict(available_physical_gib=4, available_commit_gib=5, available_gpu_gib=1.5)
    assert not check_headroom(sample)["ready"]
    assert check_headroom(sample, loaded=True)["ready"]


def test_recorded_oom_resources_are_rejected_even_after_loading():
    sample = dict(
        available_physical_gib=713672 / 1024**2,
        available_commit_gib=815040 / 1024**2,
        available_gpu_gib=278 / 1024,
    )
    assert len(check_headroom(sample, loaded=True)["shortfalls"]) == 3
