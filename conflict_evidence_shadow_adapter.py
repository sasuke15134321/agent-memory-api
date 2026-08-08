"""
Conflict Evidence Shadow Adapter v0.1
Local Shadow Prototype Only.
No DB, no network, no file access, no logging, no persistence.

Responsibility:
  - Call assemble_decision_record() with existing Results
  - On normal return: pass decision record through unchanged
  - On ValueError (semantic conflict): use existing Results to build Conflict Evidence
  - Does NOT re-judge conflict conditions independently
  - Does NOT parse ValueError message to determine which rule fired
  - Trusts ValueError as the Detection Signal from Assembler
"""
from typing import List

from decision_record_assembler import assemble_decision_record
from conflict_evidence_builder import build_conflict_evidence
from revocation_engine import RevocationResult
from eligibility_engine import EligibilityResult


def assemble_with_conflict_evidence(
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
    """
    Returns one of:
      {"outcome": "decision_record", "record": <dict>}
      {"outcome": "conflict_evidence", "evidence": <dict>}

    Conflict Evidence path is entered only when Assembler raises ValueError.
    Shadow Caller does not re-judge; ValueError is the Detection Signal.
    consistency_rule = str(exc): human-readable error text, not a stable rule ID.
    """
    try:
        record = assemble_decision_record(
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
        return {"outcome": "decision_record", "record": record}
    except ValueError as exc:
        # Detection Signal: Assembler raised ValueError.
        # Shadow Caller does not inspect exc to re-determine which rule fired.
        # str(exc) is reused as consistency_rule — human-readable, not stable rule ID.
        evidence = build_conflict_evidence(
            memory_id=revocation_result.memory_id,
            left_check_type="revocation",
            left_result=revocation_result.revocation_status,
            right_check_type="usage_eligibility",
            right_result=eligibility_result.decision,
            right_reason_code=eligibility_result.reason_code,
            consistency_rule=str(exc),
            assembly_outcome="rejected",
            decision_record_generated=False,
        )
        return {"outcome": "conflict_evidence", "evidence": evidence}
