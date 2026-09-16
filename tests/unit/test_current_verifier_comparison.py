"""Experimental controls for the prepared C2/C3 verifier comparison."""

from uavlab.core.compose import load_architecture


def test_current_c2_c3_differ_only_in_verifier_and_identity():
    a = load_architecture("c2_spf_qwen4_current_dev").model_dump(mode="json")
    b = load_architecture("c3_spf_qwen4_current_dev").model_dump(mode="json")
    assert a["verifier"] is None
    assert b["verifier"]["name"] == "semantic_geometric"
    for d in [a, b]:
        for k in ["id", "name", "description", "family", "profile_of", "verifier"]:
            d.pop(k)
    assert a == b


def test_comparators_preserve_c5_flight_stack_and_local_checkpoint():
    c5 = load_architecture("c5_target_commitment_off_qwen4_dev")
    for name in ["c2_spf_qwen4_current_dev", "c3_spf_qwen4_current_dev"]:
        candidate = load_architecture(name)
        for key in ["planner", "controller", "perception", "inference", "staleness"]:
            assert getattr(candidate, key) == getattr(c5, key)
        assert candidate.policy.params["self_terminate"] is True
        assert candidate.monitor is None
        assert not candidate.allow_privileged_observations
