"""
Evidence Snapshot Builder v0.1 - Local Tests
No network, no database, no external dependencies.
"""
import pytest

from evidence_snapshot_builder import build_evidence_snapshot


def test_case1_normal_snapshot():
    result = build_evidence_snapshot("active", ["customer_support"], "usage-policy-v0.1")
    assert result == {
        "lifecycle_status": "active",
        "purpose_scope": ["customer_support"],
        "policy_version": "usage-policy-v0.1",
    }


def test_case2_inactive_retained():
    result = build_evidence_snapshot("inactive", ["audit"], "usage-policy-v0.2")
    assert result["lifecycle_status"] == "inactive"


def test_case3_purpose_scope_immutability():
    original = ["customer_support"]
    result = build_evidence_snapshot("active", original, "usage-policy-v0.1")
    result["purpose_scope"].append("MUTATED")
    assert original == ["customer_support"]
    assert result["purpose_scope"] is not original


def test_case4_empty_purpose_scope_raises():
    with pytest.raises(ValueError):
        build_evidence_snapshot("active", [], "usage-policy-v0.1")
