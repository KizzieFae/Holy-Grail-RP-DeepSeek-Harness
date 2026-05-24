# Prior-suite re-analysis validation (#246 vs #227 manual)

- **Passed:** True
- **Agreement rate:** 1.0 (25/25)
- **Mode:** mock, corpus_replay=True

## Summary metrics

{
  "observational_only": true,
  "runtime_allowlist": false,
  "continuity_authority": false,
  "runtime_gate": false,
  "purpose": "offline evaluation calibration \u2014 not canonical runtime truth",
  "schema_version": "participation_adjudication_summary.v1",
  "raw_deterministic_suspicion_count": 20,
  "adjudication_pending_count": 0,
  "adjudicated_total_count": 20,
  "adjudicated_failure_count": 3,
  "adjudicated_non_failure_count": 14,
  "ambiguous_or_unresolved_count": 3,
  "needs_human_review_count": 0,
  "human_reviewed_count": 0,
  "llm_reviewed_count": 0,
  "deterministic_policy_reviewed_count": 20,
  "validation_failure_metric": "adjudicated_failure_count"
}

## Priority cases 11 / 12 / 15

{
  "11": {
    "case_id": "11",
    "suspicion_id": "899:7:Willow_Reeves:P03",
    "deterministic_rubric": "C3_missed_covered_change",
    "manual_expected_outcome": "adjudicated_failure",
    "new_adjudication_outcome": "adjudicated_failure",
    "suspicion_emitted": true,
    "agreement": true,
    "mismatch_disposition": "agreement",
    "mismatch_reason": "Matches manual calibration anchor",
    "manual_case_class": "true_miss",
    "notes": "Garage + remote phone true miss"
  },
  "12": {
    "case_id": "12",
    "suspicion_id": "899:9:Willow_Reeves:P04",
    "deterministic_rubric": "C3_missed_covered_change",
    "manual_expected_outcome": "adjudicated_failure",
    "new_adjudication_outcome": "adjudicated_failure",
    "suspicion_emitted": true,
    "agreement": true,
    "mismatch_disposition": "agreement",
    "mismatch_reason": "Matches manual calibration anchor",
    "manual_case_class": "true_miss",
    "notes": "Key retrieval but continues leaving"
  },
  "15": {
    "case_id": "15",
    "suspicion_id": "902:7:Hannah_Lovelace:P03",
    "deterministic_rubric": "C3_missed_covered_change",
    "manual_expected_outcome": "adjudicated_failure",
    "new_adjudication_outcome": "adjudicated_failure",
    "suspicion_emitted": true,
    "agreement": true,
    "mismatch_disposition": "agreement",
    "mismatch_reason": "Matches manual calibration anchor",
    "manual_case_class": "true_miss",
    "notes": "Remote relocation true miss"
  }
}

## Mismatches

None.

## Full comparison

| Case | Rubric | Manual | New | Agree | Disposition |
|------|--------|--------|-----|-------|-------------|
| 01 | C2_correct_covered_change | no_suspicion_emitted | — | True | agreement |
| 02 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 03 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 04 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 05 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 06 | C2_correct_covered_change | no_suspicion_emitted | — | True | agreement |
| 07 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 08 | C1_correct_no_covered_change | no_suspicion_emitted | — | True | agreement |
| 09 | C1_correct_no_covered_change | no_suspicion_emitted | — | True | agreement |
| 10 | C1_correct_no_covered_change | no_suspicion_emitted | — | True | agreement |
| 11 | C3_missed_covered_change | adjudicated_failure | adjudicated_failure | True | agreement |
| 12 | C3_missed_covered_change | adjudicated_failure | adjudicated_failure | True | agreement |
| 13 | C3_missed_covered_change | ambiguous_or_unresolved | ambiguous_or_unresolved | True | agreement |
| 14 | C3_missed_covered_change | ambiguous_or_unresolved | ambiguous_or_unresolved | True | agreement |
| 15 | C3_missed_covered_change | adjudicated_failure | adjudicated_failure | True | agreement |
| 16 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 17 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 18 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 19 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 20 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 21 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 22 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 23 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
| 24 | C3_missed_covered_change | ambiguous_or_unresolved | ambiguous_or_unresolved | True | agreement |
| 25 | C3_missed_covered_change | adjudicated_non_failure | adjudicated_non_failure | True | agreement |
