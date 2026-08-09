"""
Conflict Evidence Builder Tests v0.1
5 tests. No network, no database, no external dependencies.
"""
import pytest

from conflict_evidence_builder import build_conflict_evidence

RULE_1_MSG = "Inconsistent atom results: allowed eligibility requires not_revoked revocation status"
RULE_2_MSG = "Inconsistent atom results: revoked memory requires denied/INFORMATION_REVOKED eligibility"


def test_case_a_revoked_allowed():
    evidence = build_conflict_evidence(
        attempted_decision_id="decision-attempt-001",
        memory_id="mem-001",
        left_check_type="revocation",
        left_result="revoked",
        right_check_type="usage_eligibility",
        right_result="allowed",
        right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        consistency_rule=RULE_1_MSG,
        assembly_outcome="rejected",
        decision_record_generated=False,
    )

    assert evidence["attempted_decision_id"] == "decision-attempt-001"
    assert evidence["memory_id"] == "mem-001"
    assert evidence["left_check_type"] == "revocation"
    assert evidence["left_result"] == "revoked"
    assert evidence["right_check_type"] == "usage_eligibility"
    assert evidence["right_result"] == "allowed"
    assert evidence["right_reason_code"] == "ELIGIBILITY_REQUIREMENTS_SATISFIED"
    assert evidence["consistency_rule"] == RULE_1_MSG
    assert evidence["assembly_outcome"] == "rejected"
    assert evidence["decision_record_generated"] is False
    assert "final_decision" not in evidence
    assert len(evidence) == 10


def test_case_b_unknown_allowed():
    # Rule 1 fires before Rule 3 — unknown + allowed uses Rule 1 consistency_rule
    evidence = build_conflict_evidence(
        attempted_decision_id="decision-attempt-001",
        memory_id="mem-002",
        left_check_type="revocation",
        left_result="unknown",
        right_check_type="usage_eligibility",
        right_result="allowed",
        right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        consistency_rule=RULE_1_MSG,
        assembly_outcome="rejected",
        decision_record_generated=False,
    )

    assert evidence["attempted_decision_id"] == "decision-attempt-001"
    assert evidence["left_result"] == "unknown"
    assert evidence["right_result"] == "allowed"
    assert evidence["consistency_rule"] == RULE_1_MSG
    assert evidence["assembly_outcome"] == "rejected"
    assert evidence["decision_record_generated"] is False
    assert "final_decision" not in evidence
    assert len(evidence) == 10


def test_case_c_revoked_denied_purpose_mismatch():
    evidence = build_conflict_evidence(
        attempted_decision_id="decision-attempt-001",
        memory_id="mem-003",
        left_check_type="revocation",
        left_result="revoked",
        right_check_type="usage_eligibility",
        right_result="denied",
        right_reason_code="PURPOSE_SCOPE_MISMATCH",
        consistency_rule=RULE_2_MSG,
        assembly_outcome="rejected",
        decision_record_generated=False,
    )

    assert evidence["attempted_decision_id"] == "decision-attempt-001"
    assert evidence["left_result"] == "revoked"
    assert evidence["right_result"] == "denied"
    assert evidence["right_reason_code"] == "PURPOSE_SCOPE_MISMATCH"
    assert evidence["consistency_rule"] == RULE_2_MSG
    assert evidence["assembly_outcome"] == "rejected"
    assert evidence["decision_record_generated"] is False
    assert "final_decision" not in evidence
    assert len(evidence) == 10


def test_missing_empty_required_field_rejected():
    with pytest.raises(ValueError, match="attempted_decision_id"):
        build_conflict_evidence(
            attempted_decision_id=None,
            memory_id="mem-001",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="rejected",
            decision_record_generated=False,
        )

    with pytest.raises(ValueError, match="attempted_decision_id"):
        build_conflict_evidence(
            attempted_decision_id="",
            memory_id="mem-001",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="rejected",
            decision_record_generated=False,
        )

    with pytest.raises(ValueError, match="attempted_decision_id"):
        build_conflict_evidence(
            attempted_decision_id="   ",
            memory_id="mem-001",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="rejected",
            decision_record_generated=False,
        )

    with pytest.raises(ValueError, match="memory_id"):
        build_conflict_evidence(
            attempted_decision_id="decision-attempt-001",
            memory_id="",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="rejected",
            decision_record_generated=False,
        )

    with pytest.raises(ValueError, match="assembly_outcome"):
        build_conflict_evidence(
            attempted_decision_id="decision-attempt-001",
            memory_id="mem-001",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="   ",
            decision_record_generated=False,
        )

    with pytest.raises(ValueError, match="decision_record_generated"):
        build_conflict_evidence(
            attempted_decision_id="decision-attempt-001",
            memory_id="mem-001",
            left_check_type="revocation",
            left_result="revoked",
            right_check_type="usage_eligibility",
            right_result="allowed",
            right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
            consistency_rule=RULE_1_MSG,
            assembly_outcome="rejected",
            decision_record_generated="false",
        )


def test_deterministic_output_and_input_unchanged():
    kwargs = dict(
        attempted_decision_id="decision-attempt-001",
        memory_id="mem-001",
        left_check_type="revocation",
        left_result="revoked",
        right_check_type="usage_eligibility",
        right_result="allowed",
        right_reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        consistency_rule=RULE_1_MSG,
        assembly_outcome="rejected",
        decision_record_generated=False,
    )

    result_1 = build_conflict_evidence(**kwargs)
    result_2 = build_conflict_evidence(**kwargs)

    assert result_1 == result_2
    assert result_1["attempted_decision_id"] == "decision-attempt-001"
    assert result_2["attempted_decision_id"] == "decision-attempt-001"

    # Input strings are unchanged
    assert kwargs["attempted_decision_id"] == "decision-attempt-001"
    assert kwargs["memory_id"] == "mem-001"
    assert kwargs["left_result"] == "revoked"
    assert kwargs["right_result"] == "allowed"
    assert kwargs["assembly_outcome"] == "rejected"
    assert kwargs["decision_record_generated"] is False
