"""
Revocation Atom v0.1
Pure function. Local Prototype Only.
No DB, no network, no file access, no current time.
"""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RevocationResult:
    memory_id: str
    revocation_status: str  # revoked | not_revoked | unknown
    effective_at: Optional[str] = None
    reason_code: Optional[str] = None


_UNKNOWN = "unknown"
_REVOKED = "revoked"
_NOT_REVOKED = "not_revoked"
_UNAVAILABLE = "REVOCATION_STATUS_UNAVAILABLE"


def check_revocation_status(
    memory_id: str,
    as_of: str,
    revocation_record: Optional[dict] = None,
) -> RevocationResult:
    # Case 4: record missing
    if not revocation_record:
        return RevocationResult(
            memory_id=memory_id,
            revocation_status=_UNKNOWN,
            reason_code=_UNAVAILABLE,
        )

    status = revocation_record.get("status")

    # Case 4: status is None or "unknown"
    if status is None or status == _UNKNOWN:
        return RevocationResult(
            memory_id=memory_id,
            revocation_status=_UNKNOWN,
            reason_code=_UNAVAILABLE,
        )

    # Case 3: explicit not_revoked
    if status == _NOT_REVOKED:
        return RevocationResult(
            memory_id=memory_id,
            revocation_status=_NOT_REVOKED,
            reason_code="NO_ACTIVE_REVOCATION",
        )

    # Case 1 / Case 2: status == "revoked"
    if status == _REVOKED:
        effective_at = revocation_record.get("effective_at")
        reason_code = revocation_record.get("reason_code")

        if not effective_at:
            return RevocationResult(
                memory_id=memory_id,
                revocation_status=_UNKNOWN,
                reason_code=_UNAVAILABLE,
            )

        try:
            effective_dt = datetime.fromisoformat(effective_at)
            as_of_dt = datetime.fromisoformat(as_of)
        except (ValueError, TypeError):
            return RevocationResult(
                memory_id=memory_id,
                revocation_status=_UNKNOWN,
                reason_code=_UNAVAILABLE,
            )

        # Case 1: effective_at <= as_of
        if effective_dt <= as_of_dt:
            return RevocationResult(
                memory_id=memory_id,
                revocation_status=_REVOKED,
                effective_at=effective_at,
                reason_code=reason_code,
            )

        # Case 2: effective_at > as_of (not yet effective)
        return RevocationResult(
            memory_id=memory_id,
            revocation_status=_NOT_REVOKED,
            effective_at=effective_at,
            reason_code="REVOCATION_NOT_YET_EFFECTIVE",
        )

    # Case 5: undefined status (pending, inactive, invalid, etc.)
    return RevocationResult(
        memory_id=memory_id,
        revocation_status=_UNKNOWN,
        reason_code=_UNAVAILABLE,
    )
