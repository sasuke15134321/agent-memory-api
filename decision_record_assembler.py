"""
Decision Record Assembler v0.1
Pure function. Local Prototype Only.
No DB, no network, no file access, no current time.
"""
import copy
from typing import List

from revocation_engine import RevocationResult
from eligibility_engine import EligibilityResult


def assemble_decision_record(
    decision_id: str,
    decision_type: str,
    revocation_result: RevocationResult,
    eligibility_result: EligibilityResult,
    subject_id: str,
    current_subject_id: str,
    requested_purpose: str,
    as_of: str,
    lifecycle_status: str,
    purpose_scope: List[str],
) -> dict:
    # Required field check — no partial record
    required = {
        "decision_id": decision_id,
        "decision_type": decision_type,
        "subject_id": subject_id,
        "current_subject_id": current_subject_id,
        "requested_purpose": requested_purpose,
        "as_of": as_of,
        "lifecycle_status": lifecycle_status,
        "purpose_scope": purpose_scope,
    }
    missing = [k for k, v in required.items() if v is None or v == "" or v == []]
    if missing:
        raise ValueError(
            f"Decision Record assembly failed: missing required fields: {missing}"
        )

    # memory_id consistency — refuse to guess; Assembly fails if mismatch
    if revocation_result.memory_id != eligibility_result.memory_id:
        raise ValueError(
            f"Decision Record assembly failed: memory_id mismatch: "
            f"revocation={revocation_result.memory_id!r} "
            f"!= eligibility={eligibility_result.memory_id!r}"
        )

    # Cross-result semantic consistency — not a re-judgment; checks that results can coexist
    if eligibility_result.decision == "allowed" and revocation_result.revocation_status != "not_revoked":
        raise ValueError(
            "Inconsistent atom results: allowed eligibility requires not_revoked revocation status"
        )
    if revocation_result.revocation_status == "revoked":
        if eligibility_result.decision != "denied" or eligibility_result.reason_code != "INFORMATION_REVOKED":
            raise ValueError(
                "Inconsistent atom results: revoked memory requires denied/INFORMATION_REVOKED eligibility"
            )
    if revocation_result.revocation_status == "unknown":
        if eligibility_result.decision != "unknown" or eligibility_result.reason_code != "REVOCATION_STATUS_UNAVAILABLE":
            raise ValueError(
                "Inconsistent atom results: unknown revocation status requires unknown/REVOCATION_STATUS_UNAVAILABLE eligibility"
            )

    # policy_version source of truth: eligibility_result
    return {
        "decision_id": decision_id,
        "decision_type": decision_type,
        "subject": {
            "memory_id": eligibility_result.memory_id,
            "subject_id": subject_id,
        },
        "request_context": {
            "current_subject_id": current_subject_id,
            "requested_purpose": requested_purpose,
            "as_of": as_of,
        },
        "evidence_snapshot": {
            "lifecycle_status": lifecycle_status,
            "purpose_scope": copy.deepcopy(purpose_scope),
            "policy_version": eligibility_result.policy_version,
        },
        "checks": [
            {
                "check_type": "revocation",
                "result": revocation_result.revocation_status,
                "reason_code": revocation_result.reason_code,
            },
            {
                "check_type": "usage_eligibility",
                "result": eligibility_result.decision,
                "reason_code": eligibility_result.reason_code,
            },
        ],
        # Final Decision Semantic Owner: Usage Eligibility — no re-judgment here
        "final_decision": eligibility_result.decision,
        "final_reason_code": eligibility_result.reason_code,
    }
