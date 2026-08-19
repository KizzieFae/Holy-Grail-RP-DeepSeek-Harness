# Issue #240 — Frozen Willow Adjudication Corpus (v1)

**Purpose:** Evaluation-only calibration benchmark. Not runtime authority. Not continuity authority.

**Artifact:** `adjudication_corpus_willow_v1.json`

**Source:** Applied actor-targeted Willow overlays from semantic_eval era sessions 825–847.

**Rebuild:**
```bash
cd autogen_rp/python
python scripts/_issue240_build_adjudication_corpus.py
```

**Pre-triage:** `clear_covered_change` | `clear_no_covered_change` | `ambiguous`

**Human review:** Cases with `needs_human_review: true` only.
