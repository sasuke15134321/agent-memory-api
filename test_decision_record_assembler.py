"""
Decision Record Assembler v0.1 - Local Tests
No network, no database, no external dependencies.
"""
import copy
import pytest

from revocation_engine import RevocationResult
from eligibility_engine import EligibilityResult
from decision_record_assembler import assemble_decision_record

MEMORY_ID = "mem_abc123"
AS_OF = "2026-08-05T05:00:00Z"
POLICY_VERSION = "usage-policy-v0.1"


def _make_revocation(
    revocation_status: str,
    reason_code: str,
    memory_id: str = MEMORY_ID,
) -> RevocationResult:
    return RevocationResult(
        memory_id=memory_id,
        revocation_status=revocation_status,
        reason_code=reason_code,
    )


def _make_eligibility(
    decision: str,
    reason_code: str,
    memory_id: str = MEMORY_ID,
) -> EligibilityResult:
    return EligibilityResult(
        decision=decision,
        reason_code=reason_code,
        memory_id=memory_id,
        policy_version=POLICY_VERSION,
    )


def test_case1_allowed():
    """Case 1: not_revoked + allowed → final_decision = allowed"""
    rev = _make_revocation("not_revoked", "NO_ACTIVE_REVOCATION")
    elig = _make_eligibility("allowed", "ELIGIBILITY_REQUIREMENTS_SATISFIED")
    purpose_scope = ["customer_support"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    record = assemble_decision_record(
        decision_id="dec_A_001",
        decision_type="memory_usage_eligibility",
        revocation_result=rev,
        eligibility_result=elig,
        subject_id="customer_001",
        current_subject_id="customer_001",
        requested_purpose="customer_support",
        as_of=AS_OF,
        lifecycle_status="active",
        purpose_scope=purpose_scope,
    )

    assert record["final_decision"] == "allowed"
    assert record["final_reason_code"] == "ELIGIBILITY_REQUIREMENTS_SATISFIED"
    assert record["checks"][0]["check_type"] == "revocation"
    assert record["checks"][0]["result"] == "not_revoked"
    assert record["checks"][1]["check_type"] == "usage_eligibility"
    assert record["checks"][1]["result"] == "allowed"

    # immutability
    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before
    record["evidence_snapshot"]["purpose_scope"].append("MUTATED")
    assert purpose_scope == purpose_before


def test_case2_revoked():
    """Case 2: revoked + denied/INFORMATION_REVOKED → both reason codes preserved"""
    rev = _make_revocation("revoked", "CUSTOMER_CORRECTION")
    elig = _make_eligibility("denied", "INFORMATION_REVOKED")
    purpose_scope = ["customer_support"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    record = assemble_decision_record(
        decision_id="dec_B_001",
        decision_type="memory_usage_eligibility",
        revocation_result=rev,
        eligibility_result=elig,
        subject_id="customer_001",
        current_subject_id="customer_001",
        requested_purpose="customer_support",
        as_of=AS_OF,
        lifecycle_status="active",
        purpose_scope=purpose_scope,
    )

    assert record["final_decision"] == "denied"
    assert record["final_reason_code"] == "INFORMATION_REVOKED"
    assert record["checks"][0]["check_type"] == "revocation"
    assert record["checks"][0]["result"] == "revoked"
    assert record["checks"][0]["reason_code"] == "CUSTOMER_CORRECTION"
    assert record["checks"][1]["check_type"] == "usage_eligibility"
    assert record["checks"][1]["reason_code"] == "INFORMATION_REVOKED"

    # immutability
    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before


def test_case3_unknown():
    """Case 3: unknown + unknown → final_decision = unknown (must not become allowed)"""
    rev = _make_revocation("unknown", "REVOCATION_STATUS_UNAVAILABLE")
    elig = _make_eligibility("unknown", "REVOCATION_STATUS_UNAVAILABLE")
    purpose_scope = ["customer_support"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    record = assemble_decision_record(
        decision_id="dec_C_001",
        decision_type="memory_usage_eligibility",
        revocation_result=rev,
        eligibility_result=elig,
        subject_id="customer_001",
        current_subject_id="customer_001",
        requested_purpose="customer_support",
        as_of=AS_OF,
        lifecycle_status="active",
        purpose_scope=purpose_scope,
    )

    assert record["final_decision"] == "unknown"
    assert record["final_decision"] != "allowed"

    # immutability
    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before


def test_case5_revoked_allowed_contradiction():
    """Case 5: revoked + allowed → ValueError, no record generated"""
    rev = _make_revocation("revoked", "CUSTOMER_CORRECTION")
    elig = _make_eligibility("allowed", "ELIGIBILITY_REQUIREMENTS_SATISFIED")
    purpose_scope = ["customer_support"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    with pytest.raises(ValueError):
        assemble_decision_record(
            decision_id="dec_E_001",
            decision_type="memory_usage_eligibility",
            revocation_result=rev,
            eligibility_result=elig,
            subject_id="customer_001",
            current_subject_id="customer_001",
            requested_purpose="customer_support",
            as_of=AS_OF,
            lifecycle_status="active",
            purpose_scope=purpose_scope,
        )

    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before


def test_case6_unknown_allowed_contradiction():
    """Case 6: unknown + allowed → ValueError, no record generated"""
    rev = _make_revocation("unknown", "REVOCATION_STATUS_UNAVAILABLE")
    elig = _make_eligibility("allowed", "ELIGIBILITY_REQUIREMENTS_SATISFIED")
    purpose_scope = ["customer_support"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    with pytest.raises(ValueError):
        assemble_decision_record(
            decision_id="dec_F_001",
            decision_type="memory_usage_eligibility",
            revocation_result=rev,
            eligibility_result=elig,
            subject_id="customer_001",
            current_subject_id="customer_001",
            requested_purpose="customer_support",
            as_of=AS_OF,
            lifecycle_status="active",
            purpose_scope=purpose_scope,
        )

    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before


def test_case7_revoked_denied_wrong_reason_contradiction():
    """Case 7: revoked + denied/PURPOSE_SCOPE_MISMATCH → ValueError, no record generated"""
    rev = _make_revocation("revoked", "CUSTOMER_CORRECTION")
    elig = _make_eligibility("denied", "PURPOSE_SCOPE_MISMATCH")
    purpose_scope = ["marketing"]

    rev_before = copy.deepcopy(rev)
    elig_before = copy.deepcopy(elig)
    purpose_before = copy.deepcopy(purpose_scope)

    with pytest.raises(ValueError):
        assemble_decision_record(
            decision_id="dec_G_001",
            decision_type="memory_usage_eligibility",
            revocation_result=rev,
            eligibility_result=elig,
            subject_id="customer_001",
            current_subject_id="customer_001",
            requested_purpose="marketing",
            as_of=AS_OF,
            lifecycle_status="active",
            purpose_scope=purpose_scope,
        )

    assert rev == rev_before
    assert elig == elig_before
    assert purpose_scope == purpose_before


def test_case4_memory_id_mismatch():
    """Case 4: revocation memory_id != eligibility memory_id → assembly fails"""
    rev = _make_revocation("not_revoked", "NO_ACTIVE_REVOCATION", memory_id="mem_X")
    elig = _make_eligibility("allowed", "ELIGIBILITY_REQUIREMENTS_SATISFIED", memory_id="mem_Y")

    with pytest.raises(ValueError, match="memory_id mismatch"):
        assemble_decision_record(
            decision_id="dec_D_001",
            decision_type="memory_usage_eligibility",
            revocation_result=rev,
            eligibility_result=elig,
            subject_id="customer_001",
            current_subject_id="customer_001",
            requested_purpose="customer_support",
            as_of=AS_OF,
            lifecycle_status="active",
            purpose_scope=["customer_support"],
        )
