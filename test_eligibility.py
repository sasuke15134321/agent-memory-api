"""
Usage Eligibility Atom v0.1 - Local Tests
No network, no database, no external dependencies.
"""
from eligibility_engine import (
    evaluate_usage_eligibility,
    MemoryRecord,
    RequestContext,
    PolicySnapshot,
    LifecycleSnapshot,
    build_eligibility_input,
)

POLICY_VERSION = "usage-policy-v0.1"
BASE = dict(
    memory_id="mem_test_001",
    subject_id="customer-123",
    current_subject_id="customer-123",
    purpose_scope=["customer_support", "order_status"],
    requested_purpose="customer_support",
    lifecycle_status="active",
    revocation_status="not_revoked",
    policy_version=POLICY_VERSION,
)


def test_allowed():
    r = evaluate_usage_eligibility(**BASE)
    assert r.decision == "allowed"
    assert r.reason_code == "ELIGIBILITY_REQUIREMENTS_SATISFIED"


def test_purpose_mismatch():
    r = evaluate_usage_eligibility(**{**BASE, "requested_purpose": "payment_decision"})
    assert r.decision == "denied"
    assert r.reason_code == "PURPOSE_SCOPE_MISMATCH"


def test_subject_mismatch():
    r = evaluate_usage_eligibility(**{**BASE, "current_subject_id": "customer-999"})
    assert r.decision == "denied"
    assert r.reason_code == "SUBJECT_SCOPE_MISMATCH"


def test_inactive():
    r = evaluate_usage_eligibility(**{**BASE, "lifecycle_status": "expired"})
    assert r.decision == "denied"
    assert r.reason_code == "INFORMATION_NOT_ACTIVE"


def test_revoked():
    r = evaluate_usage_eligibility(**{**BASE, "revocation_status": "revoked"})
    assert r.decision == "denied"
    assert r.reason_code == "INFORMATION_REVOKED"


def test_unknown_revocation_status():
    r = evaluate_usage_eligibility(**{**BASE, "revocation_status": "unknown"})
    assert r.decision == "unknown"
    assert r.reason_code == "REVOCATION_STATUS_UNAVAILABLE"


def test_undefined_revocation_status():
    r = evaluate_usage_eligibility(**{**BASE, "revocation_status": "pending"})
    assert r.decision == "unknown"
    assert r.reason_code == "REVOCATION_STATUS_UNAVAILABLE"


def test_missing_required_field():
    r = evaluate_usage_eligibility(**{**BASE, "memory_id": None})
    assert r.decision == "unknown"
    assert r.reason_code == "MISSING_REQUIRED_FIELD"


# --- Shadow Adapter tests (max 3) ---

def test_shadow_adapter_allowed_full_snapshots():
    mem = MemoryRecord(memory_id="mem_abc123", agent_id="memory-writer-agent")
    mem_id_before = mem.memory_id
    agent_id_before = mem.agent_id

    req = RequestContext(
        current_subject_id="customer-123",
        requested_purpose="customer_support",
        requesting_agent_id="support-agent-7f3a",
    )
    pol = PolicySnapshot(
        policy_version="usage-policy-v0.1",
        purpose_scope=["customer_support", "order_status"],
    )
    lc = LifecycleSnapshot(
        subject_id="customer-123",
        lifecycle_status="active",
        revocation_status="not_revoked",
    )

    r = build_eligibility_input(mem, req, pol, lc)

    assert r.decision == "allowed"
    assert r.reason_code == "ELIGIBILITY_REQUIREMENTS_SATISFIED"
    # Memory object must not be mutated
    assert mem.memory_id == mem_id_before
    assert mem.agent_id == agent_id_before


def test_shadow_adapter_purpose_mismatch():
    mem = MemoryRecord(memory_id="mem_abc123", agent_id="memory-writer-agent")
    req = RequestContext(
        current_subject_id="customer-123",
        requested_purpose="payment_decision",
    )
    pol = PolicySnapshot(
        policy_version="usage-policy-v0.1",
        purpose_scope=["customer_support", "order_status"],
    )
    lc = LifecycleSnapshot(
        subject_id="customer-123",
        lifecycle_status="active",
        revocation_status="not_revoked",
    )

    r = build_eligibility_input(mem, req, pol, lc)

    assert r.decision == "denied"
    assert r.reason_code == "PURPOSE_SCOPE_MISMATCH"


def test_shadow_adapter_missing_external_state():
    mem = MemoryRecord(memory_id="mem_abc123", agent_id="memory-writer-agent")
    req = RequestContext(
        current_subject_id="customer-123",
        requested_purpose="customer_support",
    )
    pol = PolicySnapshot(
        policy_version="usage-policy-v0.1",
        purpose_scope=["customer_support", "order_status"],
    )
    # revocation_status is missing (None)
    lc = LifecycleSnapshot(
        subject_id="customer-123",
        lifecycle_status="active",
        revocation_status=None,
    )

    r = build_eligibility_input(mem, req, pol, lc)

    assert r.decision == "unknown"
    assert r.reason_code == "MISSING_REQUIRED_FIELD"
