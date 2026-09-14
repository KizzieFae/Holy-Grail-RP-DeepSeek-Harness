# Issue #201 — Package D Stage 2 Refinement Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating`  
**SHA:** `c751ea666f0cae6524698005aa5859721c2e9738` (pre-evidence-commit; see §22 for commit SHA after durability)  
**Prior tranche:** `governance/records/issue-201-package-d-stage2-tranche1-2026-09-14.md`

---

## 1. Current #201 state

| Field | Value |
|-------|-------|
| State | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| New ablations | **NOT executed** (refinement only) |

---

## 2. Evidence-durability commit / disposition

**Committed to repository (see §22 SHA):**

| Path | Role |
|------|------|
| `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` | Packages A–C |
| `governance/records/issue-201-package-d-stage1-2026-09-14.md` | Stage-1 blocker |
| `governance/records/issue-201-package-d-d0-baseline-2026-09-14.md` | D0 baseline |
| `governance/records/issue-201-package-d-stage2-tranche1-2026-09-14.md` | Tranche 1 |
| `governance/records/issue-201-package-d-stage2-refinement-2026-09-14.md` | This report |
| `governance/records/issue201-experiment-nomenclature-d01-d10.md` | D-01–D-10 canonical map |
| `governance/records/issue201-stage2-human-evaluator-worksheet.md` | Rubric + instructions |
| `governance/records/issue201-stage2-human-evaluator-scoring-sheet.md` | Full blind scoring sheet |
| `governance/records/issue201-stage2-governance-blind-transport.md` | Governance AI transport guide |
| `v2/rp_runtime/scripts/issue201-package-d-{d0-baseline,stage1,stage2-tranche1}.mjs` | Investigation harnesses |
| `tools/investigation/forensic_exp2_arkham_r2.py` | EXP-2 forensic helper |
| `v2/rp_runtime/src/plugins/hg-phase-executors/character-phase.mjs` | `skipCharacterKnowledgeCognition` hook |
| `v2/rp_runtime/src/plugins/hg-round-orchestrator/service.mjs` | Pass-through for EXP-3 |

**Gitignored (retained locally):** `data/investigation_runs/issue201-d0-baseline-*`, `issue201-package-d-stage2-*` — paths cited in records.

**Deleted:** `_backfill_meta.py` (staging utility).

---

## 3–5. EXP-2 Arkham r2 forensic timeline and divergence

**Session:** `hg-session-a92735ee-709d-4d00-a79a-7b41f0ee8652` (original failed sample)

| Stage | State |
|-------|-------|
| PVR / decomposition | Success |
| Storyteller + plot preamble | Success (EXP-2 does not skip preamble) |
| Director decision | **Accepted** — `next_actor: Harley Quinn` (QA **disabled** — no `director_semantic_qa` inference) |
| Character orientation | Inference ran; finalize **`schema_mismatch`** (`accepted: false`) — cognition continued |
| Character move ×3 | All **`semantic_rejected_hard`** (R14, R16, R02b — Harley not entitled to Player-private perception units) |
| Character semantic eval | Functioning; exhausted retry budget |
| Commit | **Never reached** — `character_failure` |
| Narrator / post-commit | **Not reached** (`incomplete_post_commit_graph`) |
| Presentation | **0 bytes** |

**Exact divergence point:** Character phase — first Harley `character_move` semantic evaluation hard-reject after Director selected Harley. Round terminated after 3 move attempts without a second Director cycle (contrast EXP-2 Arkham r1 success path: Harley failures then **second Director turn → Poison Ivy → accepted move**).

**Tool:** `tools/investigation/forensic_exp2_arkham_r2.py`

---

## 6. Causal classification (original failed sample)

### **Likely unrelated / transient contamination**

**Required causal chain for Director-QA attribution (NOT met):**

1. Director QA disabled →  
2. Director QA would have rejected/changed Harley selection →  
3. Without that change, downstream failure occurs →  
4. Failure would not occur with QA enabled.

**Evidence against Director-QA causality:**

- EXP-2 Arkham **r1** succeeded with **same** `directorSemanticQaEnabled: false` (no QA inferences in either run).
- Failure occurred at **Character semantic evaluation**, not Director QA stage.
- Director structural validation **accepted** Harley selection in failed run.
- EXP-2 r1 forensic record shows **same first-actor Harley selection** then recovery via Ivy on a later Director turn.

**Evidence for transient/stochastic path:**

- Failure mode = semantic budget exhaustion on a high-risk actor (Harley) with perception-boundary violations — a mode **Character semantic eval is designed to catch**.
- r1 demonstrated recovery without Director QA when routing reached Ivy.

---

## 7–9. Authorized confirmation / replacement run

Per Task B (**unrelated/transient**): **replacement matched Arkham EXP-2 samples** executed (full EXP-2 refresh 2026-09-14).

| Case | Wall (s) | Inferences | Committed |
|------|----------|------------|-----------|
| EXP-2 arkham-r1 (replacement) | 311.0 | 85 | **yes** |
| EXP-2 arkham-r2 (replacement) | 336.9 | 93 | **yes** |

Original contaminated r2 **superseded** for architectural comparison; retained in session evidence for forensics only.

### Updated EXP-2 classification: **inconclusive**

Director QA removal is **not demonstrated** as the cause of the original Arkham failure. With replacement data, EXP-2 Arkham is **4/4 committed** (both reps) under QA-off. **Cannot** conclude QA is necessary from this tranche; **cannot** conclude QA is removable without further designed tests.

### Updated architectural-work accounting (EXP-2, post-replacement Arkham)

| Metric | vs D0 Arkham mean |
|--------|-------------------|
| `director_semantic_qa` | **0** (removed by design) |
| Inference count | ~85–93 vs ~86 D0 (no clear savings) |
| Librarian mediation | 6–9 vs 2–10 D0 (fan-out noise) |

---

## 10–13. Human blind evaluation transport

| Artifact | Path |
|----------|------|
| Primary worksheet | `governance/records/issue201-stage2-human-evaluator-worksheet.md` |
| Full scoring sheet (A–P) | `governance/records/issue201-stage2-human-evaluator-scoring-sheet.md` |
| Machine blind packet (refreshed) | `data/investigation_runs/.../outputs/issue201-stage2-human-blind-eval-packet.json` |
| Governance transport guide | `governance/records/issue201-stage2-governance-blind-transport.md` |

**Answer key concealed:** `issue201-stage2-human-blind-eval-answer-key.json` — **not** in evaluator or Governance transport bundles.

**Human scoring instructions:** 11 dimensions, 1–5; use scenario briefings (Arkham vs Ayame); no architecture/latency/inference data; primary evaluator = project user; Governance second pass optional after primary lock.

**Status:** Ready for user scoring; **not yet scored.**

---

## 14–15. Canonical D-01–D-10 mapping and corrections

See `governance/records/issue201-experiment-nomenclature-d01-d10.md`.

**Key correction:** Stage-1 EXP-3 label (Storyteller-only) **superseded** by Governance Stage-2 EXP-3 = **D-03** orientation bypass. **D-10** = post-commit join / `skipLibrarianProposalGeneration` — same experiment, not a rename conflict.

---

## 16–19. EXP-3 topology decomposition and updated interpretation

### Node/edge decomposition under `skipCharacterKnowledgeCognition`

| Component | D0 (control) | EXP-3 |
|-----------|--------------|-------|
| **1. Orientation LLM inference** | 1–2× `character_orientation` | **0** — removed |
| **2. Librarian mediation (orientation path)** | 1–10× tied to KAR from orientation | **Reduced variably** (2–13×) — not fully removed; other lanes remain |
| **3. Manifest/context assembly** | `prepareCharacterOrientationContext` + `prepareCharacterContext` | **Retained** — authoritative manifest still assembled for Character Move |
| **4. Downstream Character Move inputs** | manifest + `librarian_bundle` from orientation | manifest **without** orientation bundle (`librarian_bundle` null) |
| **5. Routing/coordination** | Full character prep subgraph | **Retained** — projection lifecycle, semantic eval, director loop unchanged |

### Work actually removed

- Orientation LLM call(s) and orientation finalize acceptance path when skipped  
- Orientation-derived KAR and orientation-mediated librarian bundle attachment

### Work remaining solely due to old orientation topology

- `prepareCharacterOrientationContext` domain round-trip (if still invoked elsewhere in graph — **not** invoked when cognition skipped)  
- Character prep orchestration spans, projection lifecycle, character semantic evaluation, multi-inference librarian fan-out from **other** lanes (storyteller, narrator env, etc.)

### Updated EXP-3 interpretation (**inconclusive**, architecturally informative)

- **Orientation LLM:** Removed cleanly (count = 0); 4/4 commits prove path viability.  
- **Orientation subsystem / information train:** Librarian fan-out and wall time **not** cleanly reduced — marginal LLM cost is **small vs coordination noise**.  
- **Do not collapse** "orientation inference" and "orientation topology" into one conclusion.

**Answer (Task F):** If orientation LLM were permanently eliminated while supplying authoritative inputs directly to Character Move, **remaining synchronous work** would include: character projection lifecycle, `prepareCharacterContext` assembly, character move + semantic eval retries, director/narrator stacks, and **non-orientation** librarian mediation — unless topology is redesigned to shed those edges.

---

## 20. Updated EXP-1 interpretation (no production implementation)

Governance alignment: **strong candidate for conditional/tiered use**, not always-on. Evidence unchanged: 4/4 commit, ~9–15 inference reduction, low confound. **No** complexity-gated production behavior authorized.

---

## 21. World-state observations

No material change from tranche-1 observe-only assertions. Player promotion / portal authority still not auto-verified.

---

## 22. Repository evidence commit SHA

*Populated after `git commit` in this session — see session comment.*

---

## 23. Artifact cleanup

- Staging scripts deleted  
- Blind packet refreshed after EXP-2 replacement (no empty sample in new packet)  
- Scoring sheet may be regenerated from refreshed packet if labels shifted

---

## 24. Recommended next architectural challenge (ranked)

1. **Human blind eval completion** (primary user + optional Governance)  
2. **D-10** post-commit join (`skipLibrarianProposalGeneration`) — after quality signal from blind eval  
3. **Designed Director-QA test** (if Governance wants causal QA proof — requires isolated design, not repetition alone)  
4. **Fair orientation bundle-preservation variant** (if Governance authorizes)  
5. **D-04 env cognition tiering**

---

## 25. Questions for Governance

1. Accept **inconclusive** EXP-2 classification after replacement 4/4 Arkham commits?  
2. Authorize **human scoring** as gate before next tranche?  
3. Require **dedicated Director-QA causal experiment** (QA on vs off paired with actor-selection capture) or accept inconclusive?  
4. Approve **D-10** as next tranche candidate after blind eval?  
5. Update #201 Issue body execution snapshot with refinement SHA/paths?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** EXP-2 forensic trace, replacement runs, blind eval transport, nomenclature reconciliation, EXP-3 topology analysis, evidence durability commit  
**Not executed:** New ablations, E–G synthesis, production tiering
