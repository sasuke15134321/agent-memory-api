"""
Conflict Evidence Builder v0.1
Pure function. Local Prototype Only.
No DB, no network, no file access, no current time, no UUID generation.
"""


def build_conflict_evidence(
    attempted_decision_id: str,
    memory_id: str,
    left_check_type: str,
    left_result: str,
    right_check_type: str,
    right_result: str,
    right_reason_code: str,
    consistency_rule: str,
    assembly_outcome: str,
    decision_record_generated: bool,
) -> dict:
    # Structural validation only — not semantic correctness
    required_strings = {
        "attempted_decision_id": attempted_decision_id,
        "memory_id": memory_id,
        "left_check_type": left_check_type,
        "left_result": left_result,
        "right_check_type": right_check_type,
        "right_result": right_result,
        "right_reason_code": right_reason_code,
        "consistency_rule": consistency_rule,
        "assembly_outcome": assembly_outcome,
    }
    for field_name, value in required_strings.items():
        if value is None or not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Conflict Evidence build failed: {field_name!r} must be a non-empty string"
            )

    if not isinstance(decision_record_generated, bool):
        raise ValueError(
            "Conflict Evidence build failed: 'decision_record_generated' must be a bool"
        )

    return {
        "attempted_decision_id": attempted_decision_id,
        "memory_id": memory_id,
        "left_check_type": left_check_type,
        "left_result": left_result,
        "right_check_type": right_check_type,
        "right_result": right_result,
        "right_reason_code": right_reason_code,
        "consistency_rule": consistency_rule,
        "assembly_outcome": assembly_outcome,
        "decision_record_generated": decision_record_generated,
    }
