"""
Conflict Evidence Shadow Adapter Tests v0.1
4 tests. No network, no database, no external dependencies.
"""
import pytest

from conflict_evidence_shadow_adapter import assemble_with_conflict_evidence
from revocation_engine import RevocationResult
from eligibility_engine import EligibilityResult

RULE_1_MSG = "Inconsistent atom results: allowed eligibility requires not_revoked revocation status"
RULE_2_MSG = "Inconsistent atom results: revoked memory requires denied/INFORMATION_REVOKED eligibility"

_COMMON_KWARGS = dict(
    decision_id="dec-test",
    decision_type="usage",
    subject_id="sub-001",
    current_subject_id="sub-001",
    requested_purpose="research",
    as_of="2024-01-01T00:00:00",
    lifecycle_status="active",
    purpose_scope=["research"],
)


def test_case_a_revoked_allowed_produces_conflict_evidence():
    """Case A: revoked + allowed → Rule 1 ValueError → conflict_evidence"""
    rev = RevocationResult(memory_id="mem-001", revocation_status="revoked")
    elig = EligibilityResult(
        decision="allowed",
        reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        memory_id="mem-001",
        policy_version="v1",
    )
    result = assemble_with_conflict_evidence(
        revocation_result=rev,
        eligibility_result=elig,
        **_COMMON_KWARGS,
    )

    assert result["outcome"] == "conflict_evidence"
    ev = result["evidence"]
    assert ev["memory_id"] == "mem-001"
    assert ev["left_check_type"] == "revocation"
    assert ev["left_result"] == "revoked"
    assert ev["right_check_type"] == "usage_eligibility"
    assert ev["right_result"] == "allowed"
    assert ev["right_reason_code"] == "ELIGIBILITY_REQUIREMENTS_SATISFIED"
    assert ev["consistency_rule"] == RULE_1_MSG
    assert ev["assembly_outcome"] == "rejected"
    assert ev["decision_record_generated"] is False
    assert ev["attempted_decision_id"] == "dec-test"
    assert len(ev) == 10
    assert "final_decision" not in ev


def test_case_b_unknown_allowed_fires_rule_1():
    """Case B: unknown + allowed → Rule 1 fires first (not Rule 3) → conflict_evidence"""
    rev = RevocationResult(memory_id="mem-002", revocation_status="unknown")
    elig = EligibilityResult(
        decision="allowed",
        reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        memory_id="mem-002",
        policy_version="v1",
    )
    result = assemble_with_conflict_evidence(
        revocation_result=rev,
        eligibility_result=elig,
        **_COMMON_KWARGS,
    )

    assert result["outcome"] == "conflict_evidence"
    ev = result["evidence"]
    assert ev["left_result"] == "unknown"
    assert ev["right_result"] == "allowed"
    assert ev["consistency_rule"] == RULE_1_MSG
    assert ev["assembly_outcome"] == "rejected"
    assert ev["decision_record_generated"] is False
    assert ev["attempted_decision_id"] == "dec-test"
    assert len(ev) == 10
    assert "final_decision" not in ev


def test_case_c_revoked_denied_purpose_mismatch_fires_rule_2():
    """Case C: revoked + denied/PURPOSE_SCOPE_MISMATCH → Rule 2 ValueError → conflict_evidence"""
    rev = RevocationResult(memory_id="mem-003", revocation_status="revoked")
    elig = EligibilityResult(
        decision="denied",
        reason_code="PURPOSE_SCOPE_MISMATCH",
        memory_id="mem-003",
        policy_version="v1",
    )
    result = assemble_with_conflict_evidence(
        revocation_result=rev,
        eligibility_result=elig,
        **_COMMON_KWARGS,
    )

    assert result["outcome"] == "conflict_evidence"
    ev = result["evidence"]
    assert ev["left_result"] == "revoked"
    assert ev["right_result"] == "denied"
    assert ev["right_reason_code"] == "PURPOSE_SCOPE_MISMATCH"
    assert ev["consistency_rule"] == RULE_2_MSG
    assert ev["assembly_outcome"] == "rejected"
    assert ev["decision_record_generated"] is False
    assert ev["attempted_decision_id"] == "dec-test"
    assert len(ev) == 10
    assert "final_decision" not in ev


def test_normal_case_not_revoked_allowed_returns_decision_record():
    """Normal: not_revoked + allowed → consistent → decision_record, no conflict_evidence"""
    rev = RevocationResult(
        memory_id="mem-004",
        revocation_status="not_revoked",
        reason_code="NO_ACTIVE_REVOCATION",
    )
    elig = EligibilityResult(
        decision="allowed",
        reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        memory_id="mem-004",
        policy_version="v1",
    )
    result = assemble_with_conflict_evidence(
        revocation_result=rev,
        eligibility_result=elig,
        **_COMMON_KWARGS,
    )

    assert result["outcome"] == "decision_record"
    assert "record" in result
    assert "evidence" not in result
    record = result["record"]
    assert record["final_decision"] == "allowed"
    assert record["decision_id"] == "dec-test"
