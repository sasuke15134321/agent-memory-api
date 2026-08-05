"""
Usage Governance Local Integration v0.1 - Integration Tests
4 integration cases. No network, no database, no external dependencies.
"""
import copy
import pytest

from usage_governance_integration import evaluate_memory_usage_governance

# Shared fixtures
MEMORY_ID = "mem-001"
SUBJECT_ID = "user-abc"
AS_OF = "2026-08-05T00:00:00Z"
POLICY_VERSION = "usage-policy-v0.1"
LIFECYCLE_STATUS = "active"
PURPOSE_SCOPE = ["customer_support", "audit"]
REQUESTED_PURPOSE = "customer_support"
DECISION_ID = "decision-001"
DECISION_TYPE = "usage_eligibility"


def test_case1_allowed():
    purpose_scope = ["customer_support", "audit"]

    result = evaluate_memory_usage_governance(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record={"status": "not_revoked"},
        subject_id=SUBJECT_ID,
        current_subject_id=SUBJECT_ID,
        purpose_scope=purpose_scope,
        requested_purpose="customer_support",
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
        decision_id=DECISION_ID,
        decision_type=DECISION_TYPE,
    )

    rev = result["revocation_result"]
    elig = result["eligibility_result"]
    snap = result["evidence_snapshot"]
    rec = result["decision_record"]

    # Basic outcome
    assert rev.revocation_status == "not_revoked"
    assert elig.decision == "allowed"
    assert rec["final_decision"] == "allowed"

    # Snapshot consistency
    assert snap == rec["evidence_snapshot"]

    # memory_id consistency
    assert rev.memory_id == MEMORY_ID
    assert elig.memory_id == MEMORY_ID
    assert rec["subject"]["memory_id"] == MEMORY_ID

    # policy_version consistency
    assert elig.policy_version == POLICY_VERSION
    assert snap["policy_version"] == POLICY_VERSION
    assert rec["evidence_snapshot"]["policy_version"] == POLICY_VERSION

    # reason code preservation
    checks_by_type = {c["check_type"]: c for c in rec["checks"]}
    assert checks_by_type["revocation"]["reason_code"] == rev.reason_code
    assert checks_by_type["usage_eligibility"]["reason_code"] == elig.reason_code

    # final_decision preservation
    assert rec["final_decision"] == elig.decision

    # input immutability
    assert purpose_scope == ["customer_support", "audit"]


def test_case2_revoked():
    purpose_scope = ["customer_support"]

    result = evaluate_memory_usage_governance(
        memory_id=MEMORY_ID,
        as_of="2026-08-05T00:00:00Z",
        revocation_record={
            "status": "revoked",
            "effective_at": "2026-01-01T00:00:00Z",
            "reason_code": "CONSENT_WITHDRAWN",
        },
        subject_id=SUBJECT_ID,
        current_subject_id=SUBJECT_ID,
        purpose_scope=purpose_scope,
        requested_purpose="customer_support",
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
        decision_id=DECISION_ID,
        decision_type=DECISION_TYPE,
    )

    rev = result["revocation_result"]
    elig = result["eligibility_result"]
    snap = result["evidence_snapshot"]
    rec = result["decision_record"]

    assert rev.revocation_status == "revoked"
    assert elig.decision == "denied"
    assert elig.reason_code == "INFORMATION_REVOKED"
    assert rec["final_decision"] == "denied"

    # Snapshot consistency
    assert snap == rec["evidence_snapshot"]

    # memory_id consistency
    assert rev.memory_id == MEMORY_ID
    assert elig.memory_id == MEMORY_ID
    assert rec["subject"]["memory_id"] == MEMORY_ID

    # Both reason codes preserved in checks
    checks_by_type = {c["check_type"]: c for c in rec["checks"]}
    assert checks_by_type["revocation"]["reason_code"] == rev.reason_code
    assert checks_by_type["usage_eligibility"]["reason_code"] == "INFORMATION_REVOKED"

    # final_decision preservation (not re-calculated)
    assert rec["final_decision"] == elig.decision

    # input immutability
    assert purpose_scope == ["customer_support"]


def test_case3_revocation_unknown():
    purpose_scope = ["customer_support"]

    result = evaluate_memory_usage_governance(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=None,  # None → unknown
        subject_id=SUBJECT_ID,
        current_subject_id=SUBJECT_ID,
        purpose_scope=purpose_scope,
        requested_purpose="customer_support",
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
        decision_id=DECISION_ID,
        decision_type=DECISION_TYPE,
    )

    rev = result["revocation_result"]
    elig = result["eligibility_result"]
    snap = result["evidence_snapshot"]
    rec = result["decision_record"]

    assert rev.revocation_status == "unknown"
    assert elig.decision == "unknown"
    assert elig.reason_code == "REVOCATION_STATUS_UNAVAILABLE"
    assert rec["final_decision"] == "unknown"

    # Must not be promoted to allowed
    assert rec["final_decision"] != "allowed"

    # Snapshot consistency
    assert snap == rec["evidence_snapshot"]

    # memory_id consistency
    assert rev.memory_id == MEMORY_ID
    assert elig.memory_id == MEMORY_ID
    assert rec["subject"]["memory_id"] == MEMORY_ID

    # reason code preserved
    checks_by_type = {c["check_type"]: c for c in rec["checks"]}
    assert checks_by_type["usage_eligibility"]["reason_code"] == "REVOCATION_STATUS_UNAVAILABLE"

    # final_decision preservation
    assert rec["final_decision"] == elig.decision

    # input immutability
    assert purpose_scope == ["customer_support"]


def test_case4_purpose_mismatch():
    purpose_scope = ["audit"]

    result = evaluate_memory_usage_governance(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record={"status": "not_revoked"},
        subject_id=SUBJECT_ID,
        current_subject_id=SUBJECT_ID,
        purpose_scope=purpose_scope,
        requested_purpose="customer_support",  # not in scope
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
        decision_id=DECISION_ID,
        decision_type=DECISION_TYPE,
    )

    rev = result["revocation_result"]
    elig = result["eligibility_result"]
    snap = result["evidence_snapshot"]
    rec = result["decision_record"]

    assert rev.revocation_status == "not_revoked"
    assert elig.decision == "denied"
    assert elig.reason_code == "PURPOSE_SCOPE_MISMATCH"
    assert rec["final_decision"] == "denied"

    # Must not be promoted to allowed even though not_revoked
    assert rec["final_decision"] != "allowed"

    # Snapshot consistency
    assert snap == rec["evidence_snapshot"]

    # memory_id consistency
    assert rev.memory_id == MEMORY_ID
    assert elig.memory_id == MEMORY_ID
    assert rec["subject"]["memory_id"] == MEMORY_ID

    # policy_version consistency
    assert elig.policy_version == POLICY_VERSION
    assert snap["policy_version"] == POLICY_VERSION

    # reason code preserved
    checks_by_type = {c["check_type"]: c for c in rec["checks"]}
    assert checks_by_type["usage_eligibility"]["reason_code"] == "PURPOSE_SCOPE_MISMATCH"

    # final_decision preservation
    assert rec["final_decision"] == elig.decision

    # input immutability
    assert purpose_scope == ["audit"]
