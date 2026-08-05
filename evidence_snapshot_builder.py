"""
Evidence Snapshot Builder v0.1
Pure function. Local Prototype Only.
No DB, no network, no external state, no current time.
"""
import copy
from typing import List


def build_evidence_snapshot(
    lifecycle_status: str,
    purpose_scope: List[str],
    policy_version: str,
) -> dict:
    if not lifecycle_status:
        raise ValueError("evidence_snapshot build failed: lifecycle_status is required")
    if not purpose_scope:
        raise ValueError("evidence_snapshot build failed: purpose_scope is required and must not be empty")
    if not policy_version:
        raise ValueError("evidence_snapshot build failed: policy_version is required")

    return {
        "lifecycle_status": lifecycle_status,
        "purpose_scope": copy.deepcopy(purpose_scope),
        "policy_version": policy_version,
    }
