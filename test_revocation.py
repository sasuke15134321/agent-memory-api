"""
Revocation Atom v0.1 - Local Tests
No network, no database, no external dependencies.
"""
import copy
from revocation_engine import check_revocation_status
from eligibility_engine import evaluate_usage_eligibility

MEMORY_ID = "mem_abc123"
AS_OF = "2026-08-04T07:00:00Z"


def test_case1_effective_revocation():
    """Case 1: effective_at <= as_of → revoked"""
    record = {
        "status": "revoked",
        "effective_at": "2026-08-04T06:00:00Z",
        "reason_code": "CUSTOMER_CORRECTION",
    }
    record_before = copy.deepcopy(record)

    r = check_revocation_status(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=record,
    )

    assert r.revocation_status == "revoked"
    assert r.memory_id == MEMORY_ID
    assert record == record_before  # input not mutated


def test_case2_future_revocation():
    """Case 2: effective_at > as_of → not yet effective"""
    record = {
        "status": "revoked",
        "effective_at": "2026-08-05T00:00:00Z",
        "reason_code": "SCHEDULED_DELETION",
    }
    record_before = copy.deepcopy(record)

    r = check_revocation_status(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=record,
    )

    assert r.revocation_status == "not_revoked"
    assert r.reason_code == "REVOCATION_NOT_YET_EFFECTIVE"
    assert r.memory_id == MEMORY_ID
    assert record == record_before  # input not mutated


def test_case3_explicit_not_revoked():
    """Case 3: explicit not_revoked"""
    record = {"status": "not_revoked"}
    record_before = copy.deepcopy(record)

    r = check_revocation_status(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=record,
    )

    assert r.revocation_status == "not_revoked"
    assert r.reason_code == "NO_ACTIVE_REVOCATION"
    assert r.memory_id == MEMORY_ID
    assert record == record_before  # input not mutated


def test_case4_missing_or_unknown():
    """Case 4: revocation_record missing → unknown"""
    r_none = check_revocation_status(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=None,
    )
    assert r_none.revocation_status == "unknown"
    assert r_none.reason_code == "REVOCATION_STATUS_UNAVAILABLE"
    assert r_none.memory_id == MEMORY_ID

    record_unknown = {"status": "unknown"}
    record_before = copy.deepcopy(record_unknown)

    r_unknown = check_revocation_status(
        memory_id=MEMORY_ID,
        as_of=AS_OF,
        revocation_record=record_unknown,
    )
    assert r_unknown.revocation_status == "unknown"
    assert r_unknown.reason_code == "REVOCATION_STATUS_UNAVAILABLE"
    assert r_unknown.memory_id == MEMORY_ID
    assert record_unknown == record_before  # input not mutated


def test_case5_undefined_status():
    """Case 5: undefined status → unknown (must not become not_revoked)"""
    for undefined_status in ("pending", "inactive", "invalid"):
        record = {"status": undefined_status}
        record_before = copy.deepcopy(record)

        r = check_revocation_status(
            memory_id=MEMORY_ID,
            as_of=AS_OF,
            revocation_record=record,
        )

        assert r.revocation_status == "unknown", f"status={undefined_status} must not become not_revoked"
        assert r.reason_code == "REVOCATION_STATUS_UNAVAILABLE"
        assert r.memory_id == MEMORY_ID
        assert record == record_before  # input not mutated


# --- Usage Eligibility connection boundary check ---

def _eligibility_from_revocation_status(revocation_status: str) -> str:
    r = evaluate_usage_eligibility(
        memory_id="mem_boundary",
        subject_id="customer-x",
        current_subject_id="customer-x",
        purpose_scope=["customer_support"],
        requested_purpose="customer_support",
        lifecycle_status="active",
        revocation_status=revocation_status,
        policy_version="usage-policy-v0.1",
    )
    return r.decision


def test_boundary_revoked_to_eligibility_denied():
    assert _eligibility_from_revocation_status("revoked") == "denied"


def test_boundary_not_revoked_to_eligibility_proceeds():
    assert _eligibility_from_revocation_status("not_revoked") == "allowed"


def test_boundary_unknown_to_eligibility_unknown():
    assert _eligibility_from_revocation_status("unknown") == "unknown"
