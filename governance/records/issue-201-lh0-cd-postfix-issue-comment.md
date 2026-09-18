## LH-0 C/D post-fix verification + LH-B consumption investigation (2026-09-15)

**Candidate:** `b14ba60468eca29de4e7a148379c64e588660d1b`

### Part A — C/D post-fix (authorized single run each)
- **Run:** `data/investigation_runs/issue201-lh0-cd-postfix-2026-09-15T21-51-52-447Z`
- **LH-C:** `LH0-LIVE-lh_c-1789509112453` — 6/6 turns; post-commit OK; **D/E/F/G/H fail**
- **LH-D:** `LH0-LIVE-lh_d-1789509555185` — 6/6 turns; post-commit OK; **D/E/F/G/H fail**
- Post-commit `inference_kind` defect: **fixed** (no 0-turn abort)
- Remaining seam: LH-0 finalized projection built in transport but **not merged into Character manifest** for C/D (manifest has `scene_pressures` only; `received_obligation_ids` empty). LH-B contrast: same obligations appear as `active_constraints` in Character manifest.
- **LH-1A ready:** false (both arms)
- **K6:** detected; does not block C/D execution

### Part B — LH-B consumption (read-only)
- Corrective LH-B proves A–D through T4–6 receipt, but **E/F/H not proven**
- Primary causes: **B1** (ID-only obligation content, no narrative semantics) + **B5** (no durable obligation-reference evidence contract). **B3/B7** contribute (fixture forks exist but obligations don't encode fork semantics; receipt precedes activation).
- T5 guest-policy stimulus: Character deflects without answering — cannot attribute to cognition vs missing semantics without counterfactual arm.

**Record:** `governance/records/issue-201-lh0-cd-postfix-b-investigation-2026-09-15.md`

**Governance needed:** bounded C/D manifest-merge remediation (+ one verification) and/or LH-B representation+instrumentation before further live proof. LH-0 incomplete; LH-1A not authorized.
