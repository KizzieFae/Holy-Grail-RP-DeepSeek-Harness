# Issue #201 — G3 A2 Prototype & Shadow Validation Proposal

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Execution stage:** `consensus_reached` — In Progress / Awaiting Consensus / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  
**G2 specification:** `d769a43` — `issue-201-g2-a2-redesign-specification-2026-09-15.md`  
**Status:** Proposal only — **NOT executable prototype; NOT production mutation**

---

## 1. Executive summary

G3 will build the **smallest non-production vertical slice** capable of falsifying the A2 thesis:

> A substantially smaller cognition topology can preserve Holy Grail's protected capabilities.

The prototype tests three falsification questions (**F1** simple-beat, **F2** complex multi-character, **F3** persistent narrative) using **harness-only orchestration** that cannot activate from production defaults.

**Recommended isolation:** parallel experimental orchestrator module + dedicated harness scripts, reusing Domain Host substrate and Package D evidence patterns. **Do not** modify `HgRoundOrchestrator` control path for G3-A.

**Estimated execution scope (post-authorization):** ~8–12 new files, ~1 scene-template extension, ~1 domain validator module, 0 production entry-point changes.

---

## 2. G3 purpose and non-goals

### Purpose

Falsify A2 core thesis via shadow comparison against accepted lean A4 baselines on frozen stimuli.

### NOT in G3 proposal scope

- Full A2 implementation
- Production rollout
- Complete Librarian redesign
- Sophisticated obligation router (LLM or otherwise)
- Massive-retrieval campaign (deferred to G3-E unless nearly free)

### NOT authorized by this document

- Executable prototype code
- Live G3 runs
- Production/runtime mutation

---

## 3. Falsification questions (F1–F3)

### F1 — Simple-beat sufficiency

**Question:** Can an F06-like turn run the G2 minimal simple path while preserving RP quality, fidelity, authorship, PVR, grounding, Continuity, and auditability — **without** ST, Director QA, Narrator QA, default env cognition, orientation LLM, default librarian mediation, or **synchronous** Plot?

**Minimum-path proof.** Primary comparison: A2 prototype vs D-07 ablated lean arm (accepted substrate).

### F2 — Complex multi-character sufficiency

**Question:** Can the same architecture expand for Arkham stress while preserving independent agency, per-character entitlement, private knowledge, agendas, selection, commit consistency, Narrator rendering, spatial correctness, and forensic causality — **without** recreating the fixed A4 stack?

**Complexity-escalation proof.** Comparison: A2 complex path vs lean A4 Arkham baseline (D-07 topology + Package D evidence).

### F3 — Persistent narrative sufficiency

**Question:** Can Plot/Scribe (post-commit async) preserve unresolved pressure, delayed consequences, trajectory, agenda interaction, and multi-turn progression — **without** ST preamble or post-commit ST cognition?

**Longitudinal proof.** Comparison: A2 Plot post-commit vs accepted D-10 ablated (ST post-commit OFF, Plot ON) and D-01-L lean sequences.

---

## 4. Prototype isolation boundary

### Recommended mechanism (evidence-based)

**Three-layer isolation:**

| Layer | Mechanism | Evidence |
|-------|-----------|----------|
| **Entry** | Harness-only scripts; no `HolyGrailApplicationClient.submitUserTurn` default path for A2 arm | Package D pattern (`issue201-package-d-d07-narrator-qa.mjs` calls `orchestrator.runRound` directly) |
| **Orchestration** | New module `a2-beat-orchestration.mjs` — **not** imported by `bootstrap.mjs` or production mount | Issue #136 gate pattern (`run-issue136-g3-only.mjs` — isolated runner) |
| **Runtime** | `startHarnessRuntime` + temp `HG_DATA_DIR` / `HG_SESSIONS_DIR` per run | `scenario-harness/harness-runtime.mjs` |

### Production-safety proof

1. **No production import chain:** `a2-beat-orchestration.mjs` imported only from `issue201-g3-*.mjs` scripts.
2. **No feature flag on default path:** unlike Package D ablations (which reuse `HgRoundOrchestrator`), A2 prototype uses a **separate orchestrator** — production `runRound` unchanged.
3. **Experimental labeling:** all evidence JSON uses `schema: issue201_g3_a2_*`, `architecture_arm: a2_prototype`, `experimental_sha` pinning (D-07 preflight pattern).
4. **State isolation:** harness temp data dirs; no writes to operator production session stores.
5. **Removability:** delete `a2-*` modules + `issue201-g3-*` scripts without touching `hg-round-orchestrator/service.mjs`.

### Alternative considered and rejected for G3-A

| Alternative | Rejection reason |
|-------------|------------------|
| Lean `roundOptions` only on `HgRoundOrchestrator` | Proves ablation, not A2 topology (commit/presentation boundary, obligation routing, async Plot placement) |
| Production feature flag `a2ModeEnabled` | Risk of accidental activation; couples prototype to production orchestrator |
| UI toggle | Out of scope; violates isolation |

**G3-B onward:** lean `roundOptions` arm remains the **A4 comparison baseline**; A2 arm uses experimental orchestrator.

---

## 5. Reused deterministic components

| Component | Reuse path | G3 role |
|-----------|------------|---------|
| Continuity / Host kernel | `v2/domain/modules/continuity_manager.py`, Domain API session/round/commit | Authoritative commits unchanged |
| PVR triage | `player-visibility-triage-phase.mjs` | Simple path: uniform-eligible skip decomposition |
| Player decomposition | `player-decomposition-phase.mjs` | Complex path only when uniform fails |
| Eligibility / participation | Domain `getEligibleActors`, `getParticipationDecision` | Deterministic Director on simple beats |
| Character move validation | Domain `response_validation*` | Retain |
| Character semantic eval | `character-semantic-evaluation.mjs` | Retain on complex; optional on simple (G3 open) |
| Player authorship | `player_authorship_authority.py` | Deterministic gate |
| PVR validation | `perceptual_visibility_validation.py` | Entitlement checks |
| Execution evidence | harness `executionEvidence` root | Full forensic chain |
| Model bindings | existing DeepSeek inference substrate | Same models for comparability |
| Scene templates | `ayame_household_entry_evaluation`, `arkham_asylum_mess_hall_arena` | Frozen stimuli |
| Plot cognition | `plot-cognition-orchestration.mjs` | F3: post-commit async only |
| Retrieval index | `data/retrieval/compiled/operational_pilot_v3.json` | Pass-through when obligation absent |
| Blind eval rubric | `issue201-stage2-human-evaluator-worksheet.md` | Concealed architecture labels |

---

## 6. Unavoidable A4 coupling

Even the A2 prototype **must** traverse:

| Coupling | Why | Mitigation |
|----------|-----|------------|
| Domain Host session/scene APIs | Authoritative state | Reuse; no fork |
| Continuity commit gate | Invariant §6 G2 | All proposals through Host |
| PVR ingress | Protected outcome | Reuse triage; tier decomposition |
| Eligibility engine | Turn structure | Deterministic bypass of Director LLM when single eligible |
| Execution evidence | Falsification audit | Mandatory logging |
| Scene template + opener binding | Fixture comparability | Same templates as Package D |
| Character semantic eval (complex) | #193/#200 protection | Retain unless F1 evidence allows simple-beat skip |

**Architectural evidence if coupling blocks isolation:** document as A4 orchestration debt in G3-A report.

---

## 7. F1 — Minimal simple-turn prototype flow

**Fixture:** `ayame_controlled` — F06 knock stimulus (D-07 `SCENARIOS.ayame_controlled`).

```text
1. [HARNESS] startHarnessRuntime → temp data dir
2. [HARNESS] createSession + load ayame template + opener
3. [DET]  runPlayerPvrAndRecord (triage; uniform path → skip decomposition)
4. [DET]  recordUserTurn
5. [DET]  api.startRound
6. [DET]  getEligibleActors → expect single eligible NPC
7. [DET]  participation decision → deterministic select (no Director LLM)
8. [DET]  build entitled ActorContextPackage (scene card only; no orientation LLM)
9. [COG]  Character move inference (1 call)
10. [DET] move validation (schema + authorship + entitlement)
11. [DET] Host commit
12. [COG] Narrator presentation inference (1 call) — separate from step 9 in G3-A
13. [DET] presentation validation (no state delta; + spatial validator when implemented)
14. [DET] audit / execution evidence finalize
15. [PLAYER VISIBLE] — critical path ends
16. [COG] Plot update — post-commit async (off critical path; F3 may measure separately)
```

**Skipped:** ST, Director QA, Narrator QA, env cognition, orientation LLM, librarian mediation, sync Plot, decomposition (if uniform).

### Character + Narrator coalescence (G3-A decision)

**G3-A retains two physical calls** (Character move, then Narrator presentation) to prove commit boundary without confound.

**G3-B optional substage:** test staged single-call coalescence only if F1 two-call path passes objective gates. Coalescence requires enforced `proposed_move → validate → commit → presentation` staging per G2 §12.

---

## 8. F2 — Minimal complex-turn prototype flow

**Fixture:** `arkham_stress` — frozen D-07 opener + player post.

```text
1–5.  Same harness/PVR ingress as F1
6. [DET] getEligibleActors → multiple eligible (Harley, Ivy, Magpie, …)
7. [COG] Director inference — ONLY if deterministic policy cannot select
       (G3 will record whether Arkham stimulus actually requires Director LLM)
8. [DET] For each entitled autonomous actor selected this beat:
         build isolated ActorContextPackage (no cross-actor private fields)
9. [COG] N Character move cognitions (parallel where safe)
10. [DET] Per-move validation → ordered/batched commit per Host rules
11. [COG] Narrator presentation (1 call from CommittedEventManifest)
12. [DET] presentation validation + spatial validator
13. [DET] audit
14. [COG] Plot post-commit async
```

### Character agency / isolation design

| Mechanism | Implementation |
|-----------|----------------|
| Package isolation | Separate `ActorContextPackage` per `character_id`; manifest hash logged |
| Leakage proof | Objective check: no private fact from actor A's entitlement in actor B's inference input manifest |
| Parallel moves | `Promise.all` on independent Character calls when no commit ordering conflict |
| Conflict resolution | Host commit ordering + Director turn structure; no extra "coordinator LLM" |
| Narrator hidden cognition | Narrator input = `CommittedEventManifest` + player-visible projection only; **no** raw Character reasoning traces |

### Director invocation design

| Signal | Arkham stimulus expectation | Action |
|--------|----------------------------|--------|
| Single eligible | Unlikely on stress opener | Deterministic select |
| Multiple eligible, clear priority | TBD in G3-A trace | May skip Director LLM |
| Ambiguous spotlight | Possible | Director LLM authorized |

**G3 records actual Director necessity** — do not assume.

---

## 9. F3 — Plot/Scribe longitudinal flow

**Reuse:** `runPostCommitPlotCognitionLifecycle` from `plot-cognition-orchestration.mjs`.

**Prototype placement:**

```text
… player-visible presentation complete (F1/F2 critical path end)
→ [async] runPostCommitPlotCognitionLifecycle
→ overlay write (advisory) with freshness marker
→ next turn: Character/Director read overlay as advisory input only
```

**Sequences:** reuse D-10 / D-01-L player policy JSON pattern (`issue201-d10-policies/`, 4-turn sequences).

**F3 tests:**

| Test | Evidence |
|------|----------|
| Overlay freshness | `as_of_turn` / stale flags in continuity forensics |
| Subsequent-turn consumption | Plot advisory present in Character context manifest |
| Delayed consequence | Overlay queue entries across turns |
| Pressure progression | Overlay diff turn-over-turn |
| Longitudinal RP value | Blind sequence scoring (D-10 packet schema) |

**Do not recreate Storyteller.** No second narrative LLM for comparison.

**Comparison arm:** D-10 ablated topology (ST post-commit OFF, Plot ON) — accepted evidence; rerun only if substrate SHA mismatch.

---

## 10. Spatial validator proposal (Sample E class)

### Defect class

Magpie described at **the table** vs briefing placing her **across the room / another table** (D-07 Sample E; QA passed).

### Existing contracts (insufficient alone)

| Contract | Path | Gap |
|----------|------|-----|
| Spatial move shape | `continuity_mutation_pipeline_validate.py` | Moves only, not presentation |
| Zone/portal perception | `perceptual_scene_context.py` | Arkham mess hall template lacks `perceptual_scene_context` |
| PVR validation | `perceptual_visibility_validation.py` | Entitlement, not scenario placement |
| D-07 objectiveChecks | harness | No spatial/scenario check |

### Proposed extension (smallest generalized)

**New:** `scenario_spatial_validator.py` (domain module)

**Inputs (authoritative, not hard-coded to Arkham):**

- Scene template `perceptual_scene_context` (zones, anchors, role placements)
- Session role assignments / opener briefing facts
- Committed character locations (Continuity)
- Narrator presentation claims tagged by entity/location (structured extraction or contract fields)

**Rules (deterministic):**

- Entity referenced in presentation must not contradict assigned zone/location facts
- Cross-zone proximity claims ("at the table with X") require co-location facts
- Scenario briefing facts are authoritative for initial placement until commit changes them

**Fixture prerequisite:** extend `arkham_asylum_mess_hall_arena.json` with `perceptual_scene_context` encoding table placements (Harley/Ivy shared table; Magpie separate).

**Test plan:**

- Unit tests with synthetic contradictions (not only Arkham)
- Negative control: valid co-location passes
- G3 objective gate: Sample E class presentation **must fail** validator

**Residual semantic boundary:** figurative language ("at the heart of the trouble") may require declared non-literal tag or human blind review — document false-positive policy in G3-B.

---

## 11. Retrieval-first handling (G3 scope)

**First slice:** scenarios do **not** meaningfully stress massive retrieval.

| Path | Behavior |
|------|----------|
| No retrieval obligation | Scene card + opener only; **no** librarian mediation |
| Indexed fact needed later | Log `mediation_would_be_required` if deterministic retrieval empty |
| Do not fake success | Explicit omission manifest in context package |

**Massive-retrieval validation:** defer to **G3-E** unless G3-A substrate work makes it nearly free.

---

## 12. Obligation routing (prototype)

**No sophisticated router.** Harness-local explicit dispatch:

| Scenario key | Obligations asserted | Routing |
|--------------|---------------------|---------|
| `ayame_controlled` | single actor, uniform PVR, no retrieval, no env, no sync plot | F1 simple path |
| `arkham_stress` | multi actor, entitlement divergence, spatial, possible Director | F2 complex path |

**Per-signal handling (deterministic, experimental):**

| Signal | Detection | Authorizes |
|--------|-----------|------------|
| Actor multiplicity | `eligibleActors.length > 1` | Multi Character path |
| Entitlement divergence | distinct private-knowledge hashes per actor | Isolated packages |
| Retrieval obligation | context manifest gap flag | Index query (no mediation) |
| Environmental obligation | **off** in G3-A/B unless manifest gap detected | Log only in first slice |
| Plot obligation | **off** sync in G3-A/B | Post-commit async only |
| State-mutation risk | move classifier | Expanded validators |
| Repair requirement | validation failure | Single repair call max |

**Prohibited:** LLM decides whether to invoke more LLMs.

---

## 13. Comparison baselines

### G3-B Simple beat (F1)

| Arm | Topology | Source |
|-----|----------|--------|
| **A2 prototype** | `a2-beat-orchestration` simple path | New |
| **A4 lean** | D-07 ablated: `LEAN_BASE` + `narratorSemanticQaEnabled: false` | Accepted `d30f4b3` |
| **Optional rerun** | Same arms at current SHA | Only if substrate drift |

**Reuse D-07 blind scores** for A4 lean arm if SHA-compatible; rerun A2 arm only.

### G3-C Complex beat (F2)

| Arm | Topology |
|-----|----------|
| **A2 prototype** | Complex path + spatial validator |
| **A4 lean** | D-07 ablated on `arkham_stress` |

### G3-D Longitudinal (F3)

| Arm | Topology |
|-----|----------|
| **A2 prototype** | F1/F2 + post-commit Plot async |
| **Accepted evidence** | D-10 ablated (ST post-commit OFF); D-01-L lean |

Rerun baseline only for causal comparability at execution SHA.

---

## 14. Blind semantic evaluation

- Reuse `issue201_blind_eval_packet_v1` / sequence packet schemas
- Architecture labels concealed (A/B/C…); answer key separate file
- Governance lock → decode discipline (Package D precedent)
- Rubric: `issue201-stage2-human-evaluator-worksheet.md` (11 dimensions)
- **Not** sole quality gate — objective correctness parallel

---

## 15. Objective correctness gates

| Gate | Pass criteria | F1 | F2 | F3 |
|------|---------------|----|----|-----|
| PVR valid | `validation_status === 'valid'` | ✓ | ✓ | ✓ |
| Round committed | `roundResult.committed` | ✓ | ✓ | ✓ |
| Presentation non-empty | length > 0 | ✓ | ✓ | ✓ |
| Player authorship | no `authorship_fail_closed` | ✓ | ✓ | ✓ |
| Entitlement leak | no cross-actor private fields in manifests | — | ✓ | ✓ |
| Spatial/scenario | `scenario_spatial_validator` pass | ✓ | ✓ | — |
| Move consistency | validated move matches commit | ✓ | ✓ | ✓ |
| Narrator authority | no state delta in presentation | ✓ | ✓ | ✓ |
| Plot advisory boundary | overlay writes advisory-only | — | — | ✓ |
| Malformed output | schema validation pass | ✓ | ✓ | ✓ |

**Blocking failures:** committed, authorship, entitlement leak, spatial validator fail (once implemented).

---

## 16. Efficiency accounting

Per run, capture in `issue201-g3-efficiency.json`:

| Metric | Source |
|--------|--------|
| Player-visible critical-path wall time | harness timestamps: ingress → presentation |
| Total operation wall time | including async Plot |
| LLM call count by `inference_kind` | execution evidence |
| Input/output/reasoning tokens | inference records |
| Retry/repair count | attempt traces |
| Coordination handoffs | manifest: projection → cognition → commit → presentation |

**Not sole success criterion.**

---

## 17. Information-bureaucracy accounting

Per LLM call, log `decision_value_record`:

```json
{
  "inference_kind": "...",
  "unique_information": "...",
  "consumer": "...",
  "downstream_decision": "...",
  "deterministic_alternative_existed": true|false,
  "mandatory": true|false,
  "obligation_trigger": "..."
}
```

Enables **decision value per inference** comparison vs A4 lean manifests.

---

## 18. Experimental stages (bounded campaign)

| Stage | Goal | Quality conclusion? |
|-------|------|---------------------|
| **G3-A** | Substrate + orchestration proof; wiring; objective gates pass once | No |
| **G3-B** | F1 simple-beat A2 vs A4 lean + blind eval | Yes (F1) |
| **G3-C** | F2 Arkham complex + entitlement leak checks + blind eval | Yes (F2) |
| **G3-D** | F3 longitudinal Plot sequences + blind eval | Yes (F3) |
| **G3-E** | Optional massive-retrieval (only if core survives) | Deferred |

**Order:** G3-A → G3-B → G3-C → G3-D → (optional) G3-E.

---

## 19. Stop / escalation rules

### Stop conditions (do not proceed to next stage)

| Condition | Classification |
|-----------|----------------|
| Cannot reuse Host without duplicating authoritative state | **Specification flaw** or **prototype bug** — escalate |
| Simple path loses objective correctness | **Prototype bug** first; if architectural, **A2 falsification** |
| Entitlement leak in Character packages | **Prototype bug** until proven systemic → **A2 falsification** |
| Commit/presentation boundary unenforceable | **A2 falsification** for coalescence; revert to two-call |
| Plot overlay writes authoritative state | **Prototype bug** (invariant violation) |
| Blind quality material degradation vs lean A4 | **A2 falsification** or topology gap — Governance review |
| Complex path needs ~A4 call count to pass gates | **A2 falsification** |
| Audit chain less reconstructable than A4 lean | **Specification flaw** |

### Material topology expansion

Any add of: always-on QA, sync Plot, env cognition, librarian mediation, ST paths → **STOP → Governance** (no silent rescue).

### Failure classification guide

| Symptom | Likely class |
|---------|--------------|
| Harness wiring / import error | Prototype bug |
| Wrong manifest assembly | Prototype bug |
| Validator too strict / false positive | Prototype bug → refine validator |
| Consistent quality loss with clean objectives | A2 falsification |
| Missing capability in G2 spec | Specification flaw |

---

## 20. Proposed prototype files / surfaces

| File | Purpose |
|------|---------|
| `v2/rp_runtime/src/lib/a2-beat-orchestration.mjs` | Experimental A2 turn orchestrator |
| `v2/rp_runtime/src/lib/a2-obligation-dispatch.mjs` | Harness-local obligation signals |
| `v2/rp_runtime/src/lib/a2-decision-value-logger.mjs` | Bureaucracy accounting |
| `v2/rp_runtime/scripts/lib/issue201-g3-scenarios.mjs` | Frozen scenario definitions |
| `v2/rp_runtime/scripts/lib/issue201-g3-objective-checks.mjs` | Extended correctness gates |
| `v2/rp_runtime/scripts/issue201-g3-a2-shadow-validation.mjs` | Main harness entry |
| `v2/rp_runtime/scripts/run-issue201-g3-only.mjs` | Thin gate runner (optional) |
| `v2/domain/modules/scenario_spatial_validator.py` | Sample E class protection |
| `v2/domain/tests/test_scenario_spatial_validator.py` | Unit tests |
| `data/scene_templates/arkham_asylum_mess_hall_arena.json` | Add `perceptual_scene_context` |
| `governance/records/issue201-g3-*-report.md` | Per-stage execution reports |
| `data/investigation_runs/issue201-g3-a2-<timestamp>/` | Evidence output |

**Production files NOT modified in G3-A:** `hg-round-orchestrator/service.mjs`, `bootstrap.mjs`, `hg-application-client.mjs`.

---

## 21. Expected mutation scope (post-execution authorization)

| Category | Files | Production path impact |
|----------|-------|------------------------|
| New experimental modules | 3–4 | None |
| New harness scripts | 3–4 | None |
| New domain validator | 1 + tests | Host validation hook (behind explicit call from A2 orchestrator + tests) |
| Scene template extension | 1 | Fixture only; improves spatial facts |
| Governance records | per stage | None |

**Proposed Host hook:** spatial validator invoked from A2 orchestrator presentation validation step — **not** wired into production Narrator path until separate Governance authorization.

---

## 22. A2 falsification criteria (G3 operationalized)

Reject or substantially revise A2 if:

- F1 blind quality < D-07 ablated arm on matched Ayame stimuli
- F2 entitlement leak or agency collapse vs Arkham lean baseline
- F3 longitudinal blind < D-10 ablated with Plot-only pressure
- Spatial validator cannot catch Sample E class even with template facts
- Simple path call reduction < 50% vs A4 lean **without** objective gate pass
- Complex path requires re-adding ≥3 always-on A4 cognition classes to pass gates

---

## 23. Unresolved decisions requiring Governance (pre-execution)

| # | Decision | Default recommendation |
|---|----------|------------------------|
| G3-1 | Authorize G3-A implementation (wiring only, no live quality conclusion) | Yes |
| G3-2 | Two-call vs coalesced simple beat in G3-A | Two-call first |
| G3-3 | Character semantic eval on F1 simple path | Off initially; add if leak detected |
| G3-4 | Rerun D-07 lean baseline at execution SHA | Only if substrate drift |
| G3-5 | Spatial validator Host hook scope | A2 orchestrator only until proven |
| G3-6 | G3-D sequence length (4-turn D-10 parity) | 4 turns |

---

## 24. Recommended Governance decision (G3 execution gate)

**Authorize G3-A only:** prototype substrate/orchestration implementation + spatial validator module + unit tests — **no live comparison runs** until G3-A objective wiring verified.

Upon G3-A pass report, **separately authorize G3-B** live F1 comparison.

---

## 25. Evidence anchors

| Anchor | Reference |
|--------|-----------|
| G2 specification | `d769a43` |
| G1 acceptance | `issue-201-g1-acceptance-phase-transition-2026-09-15.md` |
| D-07 lean baseline | `d30f4b3`, `issue201-package-d-d07-narrator-qa.mjs` |
| D-10 longitudinal | `issue201-package-d-d10-post-commit.mjs` |
| Sample E adjudication | `issue-201-package-d-d07-blind-decode-synthesis-2026-09-15.md` §13 |
| Harness runtime | `scenario-harness/harness-runtime.mjs` |
| Blind rubric | `issue201-stage2-human-evaluator-worksheet.md` |

---

**No executable prototype code written. No production mutation. Issue remains `consensus_reached`.**
