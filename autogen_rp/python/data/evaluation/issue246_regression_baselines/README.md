# Issue #246 regression baselines

Frozen adjudication summary anchors for `adjudication_corpus_cohesion_v1.json`.

**Operator discipline:** calibration outcomes are **not** canonical runtime truth. See `AUDIT_DOCUMENTATION.md` (*Participation suspicion adjudication — #246*).

Regenerate corpus: `python scripts/build_issue246_corpus.py`

Run regression: `python scripts/run_issue246_corpus_regression.py --eval`

Expected v1 anchors: cases 11/12/15 → `adjudicated_failure`; topology FPs → `adjudicated_non_failure`.
