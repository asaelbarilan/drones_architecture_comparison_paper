import struct

import pytest

from uavlab.plugins.inference import cpu_placement as placement

SECOND_CPU_MASK = 2


def test_cpu_set_parser_and_highest_class_selection():
    raw = bytearray(64)
    for offset, logical, level in ((0, 0, 1), (32, 1, 0)):
        struct.pack_into("<IIIHBBBBBB", raw, offset, 32, 0, logical, 0,
                         logical, 0, 0, 0, level, 0)
    rows = placement.parse_cpu_sets(raw)
    assert rows == [(0, 0, 1), (0, 1, 0)]
    assert placement.performance_mask(rows, 3) == 1


@pytest.mark.parametrize("raw", [b"x", bytes(8), struct.pack("<II", 32, 0)])
def test_malformed_topology_is_rejected(raw):
    with pytest.raises(ValueError):
        placement.parse_cpu_sets(raw)


def test_never_expands_inherited_affinity_or_assumes_processor_group():
    rows = [(0, 0, 1), (0, 1, 1), (0, 2, 0)]
    assert placement.performance_mask(rows, 6) == SECOND_CPU_MASK
    assert placement.performance_mask([(0, 0, 0), (0, 1, 0)], 2) == SECOND_CPU_MASK
    for invalid, mask in ((rows, 4), ([(1, 0, 1)], 1), ([], 1)):
        with pytest.raises(ValueError):
            placement.performance_mask(invalid, mask)


class FakeAffinity:
    def __init__(self):
        self.mask = 3
        self.history = []

    def get(self):
        return self.mask

    def set(self, mask):
        self.mask = mask
        self.history.append(mask)

    def topology(self):
        return [(0, 0, 1), (0, 1, 0)]


def test_restores_affinity_even_when_inference_fails(monkeypatch):
    monkeypatch.setattr(placement.sys, "platform", "win32")
    fake = FakeAffinity()
    with (pytest.raises(RuntimeError, match="inference"),
          placement.placed_cpu("performance", lambda: fake) as result):
        assert result["selected_mask"] == 1
        raise RuntimeError("inference failed")
    assert fake.history == [1, 3]


def test_default_does_not_touch_native_api_and_other_platforms_reject(monkeypatch):
    def forbidden():
        raise AssertionError("must not touch native API")

    with placement.placed_cpu(factory=forbidden) as result:
        assert result == {"policy": "inherit"}
    monkeypatch.setattr(placement.sys, "platform", "linux")
    with pytest.raises(ValueError), placement.placed_cpu("performance", forbidden):
        pass
