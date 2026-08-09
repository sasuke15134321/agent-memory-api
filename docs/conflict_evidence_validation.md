# Conflict Evidence Validation

**Type:** Public Validation Note
**Repository:** sasuke15134321/agent-memory-api
**Verified Commit:** `e24c3161fcfe122556e4345728521454d462a56e`

---

## Problem

In agent governance, independent judgment results can be semantically contradictory.
A revocation check and an eligibility check may produce results that cannot be consistently assembled.

Examples used in existing tests:

```
revoked + allowed
unknown + allowed
revoked + denied with non-INFORMATION_REVOKED reason
```

---

## Existing Fail-safe

`decision_record_assembler.py` owns Semantic Consistency Check.

On contradiction:

```
ValueError raised
→ Decision Record not generated
```

**Conflict Evidence does not re-evaluate or override this check.**
The assembler's rejection stands.

---

## Conflict Evidence Responsibility

```
Assembler               → semantic conflict detection, raises ValueError
Conflict Evidence Builder → structured evidence assembly
Shadow Adapter          → connects detection signal and results
```

Two distinctions to keep clear:

```
Conflict Evidence   ≠ Decision Record
assembly rejected   ≠ final decision denied
```

---

## Shadow Path

```
RevocationResult + EligibilityResult
           ↓
 Decision Record Assembler
           ↓
    ┌──────┴──────┐
 consistent    conflict
     ↓              ↓
 Decision        ValueError
 Record              ↓
               Shadow Adapter
                    ↓
            Conflict Evidence
```

---

## Evidence Fields

Current Local Prototype Contract — 9 fields:

```
memory_id
left_check_type
left_result
right_check_type
right_result
right_reason_code
consistency_rule
assembly_outcome
decision_record_generated
```

This is a **Local Prototype Contract**.
It is **not** a Public API Schema or Canonical Cross-system Schema.

---

## Validation Results

```
Conflict Evidence Builder Tests:        5 / 5
Decision Record Assembler Tests:        7 / 7
Conflict Evidence Shadow Adapter Tests: 4 / 4

Combined Relevant Tests:               16 / 16
```

---

## GitHub Remote Verification

Verified commit: `e24c3161fcfe122556e4345728521454d462a56e`

Three-way SHA match confirmed:

```
Local HEAD = origin/main after fetch = remote server refs/heads/main
```

Published files in this commit:

```
conflict_evidence_builder.py
conflict_evidence_shadow_adapter.py
test_conflict_evidence_builder.py
test_conflict_evidence_shadow_adapter.py
```

---

## What This Does NOT Prove

```
No Render deployment         No endpoint integration
No database integration      No evidence persistence
No production traffic        No live verification
No operational evidence      No authentication solution
No Governance Singularity validation
```

---

## Design Direction

This prototype explores one small part of external execution assurance:
preserving evidence when governance results cannot be consistently assembled.

Future observation areas include input integrity and intent fidelity.
