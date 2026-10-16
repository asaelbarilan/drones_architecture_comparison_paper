import pytest

from uavlab.plugins.inference import cpu_qos as qos


class FakeQoS:
    def __init__(self, rejected=False):
        self.value = dict(control=4, state=4)
        self.history = []
        self.rejected = rejected

    def get(self):
        return dict(self.value)

    def set(self, value):
        self.history.append(value)
        if not self.rejected:
            self.value = dict(value)


def test_execution_hint_preserves_unrelated_timer_policy():
    original = dict(control=4, state=4)
    assert qos.latency_state(original) == dict(control=5, state=4)
    assert qos.latency_state(dict(control=5, state=5)) == dict(control=5, state=4)
    assert original == dict(control=4, state=4)


@pytest.mark.parametrize("fail", [False, True])
def test_current_process_hint_restored_on_success_and_failure(monkeypatch, fail):
    monkeypatch.setattr(qos.sys, "platform", "win32")
    fake = FakeQoS()
    try:
        with qos.execution_qos("latency", lambda: fake) as selected:
            assert selected["selected"] == dict(control=5, state=4)
            if fail:
                raise RuntimeError("inference")
    except RuntimeError as exc:
        assert str(exc) == "inference"
    assert fake.value == dict(control=4, state=4)
    assert fake.history == [dict(control=5, state=4), dict(control=4, state=4)]


def test_unapplied_policy_is_not_reported_ready(monkeypatch):
    monkeypatch.setattr(qos.sys, "platform", "win32")
    fake = FakeQoS(rejected=True)
    with (pytest.raises(RuntimeError, match="did not apply"),
          qos.execution_qos("latency", lambda: fake)):
        pytest.fail("unapplied scheduling hint must fail")
    assert fake.history[-1] == dict(control=4, state=4)


def test_default_never_calls_native_api_and_other_os_rejected(monkeypatch):
    def forbidden():
        pytest.fail("native API not permitted")

    with qos.execution_qos(factory=forbidden) as result:
        assert result == dict(policy="inherit")
    monkeypatch.setattr(qos.sys, "platform", "linux")
    with pytest.raises(ValueError), qos.execution_qos("latency", forbidden):
        pass
