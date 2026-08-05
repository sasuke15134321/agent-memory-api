"""
Usage Eligibility Atom v0.1
Pure deterministic function. Local Prototype Only.
Not integrated into API endpoints or database.
"""
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class EligibilityResult:
    decision: str  # allowed | denied | unknown
    reason_code: str
    memory_id: str
    policy_version: str


def evaluate_usage_eligibility(
    memory_id: Optional[str],
    subject_id: Optional[str],
    current_subject_id: Optional[str],
    purpose_scope: Optional[List[str]],
    requested_purpose: Optional[str],
    lifecycle_status: Optional[str],
    revocation_status: Optional[str],
    policy_version: Optional[str],
    requesting_agent_id: Optional[str] = None,  # Optional, not used in v0.1 judgment
) -> EligibilityResult:
    # Step 1: Required field existence
    required_fields = [
        memory_id, subject_id, current_subject_id, purpose_scope,
        requested_purpose, lifecycle_status, revocation_status, policy_version,
    ]
    if not all(f is not None and f != [] and f != "" for f in required_fields):
        return EligibilityResult(
            decision="unknown",
            reason_code="MISSING_REQUIRED_FIELD",
            memory_id=memory_id or "",
            policy_version=policy_version or "",
        )

    # Step 2: Subject match
    if current_subject_id != subject_id:
        return EligibilityResult(
            decision="denied",
            reason_code="SUBJECT_SCOPE_MISMATCH",
            memory_id=memory_id,
            policy_version=policy_version,
        )

    # Step 3: Lifecycle status — only "active" is permitted
    if lifecycle_status != "active":
        return EligibilityResult(
            decision="denied",
            reason_code="INFORMATION_NOT_ACTIVE",
            memory_id=memory_id,
            policy_version=policy_version,
        )

    # Step 4: Revocation status
    if revocation_status == "revoked":
        return EligibilityResult(
            decision="denied",
            reason_code="INFORMATION_REVOKED",
            memory_id=memory_id,
            policy_version=policy_version,
        )

    if revocation_status != "not_revoked":
        return EligibilityResult(
            decision="unknown",
            reason_code="REVOCATION_STATUS_UNAVAILABLE",
            memory_id=memory_id,
            policy_version=policy_version,
        )

    # Step 5: Purpose scope
    if requested_purpose not in purpose_scope:
        return EligibilityResult(
            decision="denied",
            reason_code="PURPOSE_SCOPE_MISMATCH",
            memory_id=memory_id,
            policy_version=policy_version,
        )

    # Step 6: All conditions satisfied
    return EligibilityResult(
        decision="allowed",
        reason_code="ELIGIBILITY_REQUIREMENTS_SATISFIED",
        memory_id=memory_id,
        policy_version=policy_version,
    )


# --- Shadow Adapter (read-only, local only) ---


@dataclass
class MemoryRecord:
    memory_id: str
    agent_id: str


@dataclass
class RequestContext:
    current_subject_id: Optional[str]
    requested_purpose: Optional[str]
    requesting_agent_id: Optional[str] = None


@dataclass
class PolicySnapshot:
    policy_version: Optional[str]
    purpose_scope: Optional[List[str]]


@dataclass
class LifecycleSnapshot:
    subject_id: Optional[str]
    lifecycle_status: Optional[str]
    revocation_status: Optional[str]


def build_eligibility_input(
    memory_record: MemoryRecord,
    request_context: RequestContext,
    policy_snapshot: PolicySnapshot,
    lifecycle_snapshot: LifecycleSnapshot,
) -> EligibilityResult:
    return evaluate_usage_eligibility(
        memory_id=memory_record.memory_id,
        subject_id=lifecycle_snapshot.subject_id,
        current_subject_id=request_context.current_subject_id,
        purpose_scope=policy_snapshot.purpose_scope,
        requested_purpose=request_context.requested_purpose,
        lifecycle_status=lifecycle_snapshot.lifecycle_status,
        revocation_status=lifecycle_snapshot.revocation_status,
        policy_version=policy_snapshot.policy_version,
        requesting_agent_id=request_context.requesting_agent_id,
    )
