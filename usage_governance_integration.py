"""
Usage Governance Local Integration v0.1
Pure orchestrator: connects Revocation, Eligibility, Evidence Snapshot, Decision Record.
No new policy logic. No I/O. No side effects.
"""
from typing import List, Optional

from revocation_engine import check_revocation_status
from eligibility_engine import evaluate_usage_eligibility
from evidence_snapshot_builder import build_evidence_snapshot
from decision_record_assembler import assemble_decision_record


def evaluate_memory_usage_governance(
    memory_id: str,
    as_of: str,
    revocation_record: Optional[dict],
    subject_id: str,
    current_subject_id: str,
    purpose_scope: List[str],
    requested_purpose: str,
    lifecycle_status: str,
    policy_version: str,
    decision_id: str,
    decision_type: str,
    requesting_agent_id: Optional[str] = None,
) -> dict:
    revocation_result = check_revocation_status(
        memory_id=memory_id,
        as_of=as_of,
        revocation_record=revocation_record,
    )

    eligibility_result = evaluate_usage_eligibility(
        memory_id=memory_id,
        subject_id=subject_id,
        current_subject_id=current_subject_id,
        purpose_scope=purpose_scope,
        requested_purpose=requested_purpose,
        lifecycle_status=lifecycle_status,
        revocation_status=revocation_result.revocation_status,
        policy_version=policy_version,
        requesting_agent_id=requesting_agent_id,
    )

    evidence_snapshot = build_evidence_snapshot(
        lifecycle_status=lifecycle_status,
        purpose_scope=purpose_scope,
        policy_version=eligibility_result.policy_version,
    )

    decision_record = assemble_decision_record(
        decision_id=decision_id,
        decision_type=decision_type,
        revocation_result=revocation_result,
        eligibility_result=eligibility_result,
        subject_id=subject_id,
        current_subject_id=current_subject_id,
        requested_purpose=requested_purpose,
        as_of=as_of,
        lifecycle_status=lifecycle_status,
        purpose_scope=purpose_scope,
    )

    if evidence_snapshot != decision_record["evidence_snapshot"]:
        raise ValueError(
            f"Snapshot mismatch: builder={evidence_snapshot!r}, "
            f"record={decision_record['evidence_snapshot']!r}"
        )

    return {
        "revocation_result": revocation_result,
        "eligibility_result": eligibility_result,
        "evidence_snapshot": evidence_snapshot,
        "decision_record": decision_record,
    }
