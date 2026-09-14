# Issue #201 — Packages A–C Investigation Record

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` (Packages A–C complete; Package D proposed only)  
**Assigned / effective weight:** `full` / `full`  
**Bootstrap profile:** Full  
**Investigation SHA:** `43db105401769750980bdc214666424fa11985cb`  
**Primary evidence session:** `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311`  
**Historical comparison session:** `hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40`  
**Scenario (primary):** `ayame_household_entry_evaluation`  
**Stress benchmark candidate (Package D):** `arkham_asylum_mess_hall_arena` (+ `arkham_multi_character_stress` harness scenarios)

---

## 1. Activation synchronization evidence

### Full bootstrap reads completed

| Profile requirement | Path | Status |
|---------------------|------|--------|
| AGENTS.md | `AGENTS.md` | read |
| Issue workflow §B/§D/§H | `governance/sources/issue-tracking-workflow.md` | read (§B.3, §H) |
| GitHub execution policy | `governance/execution/github-issues.md` | read |
| Project behavior | `governance/sources/project-behavior-holy-grail.md` | read |
| Cursor workflow layer | `governance/execution/cursor-workflow-layer.md` | read |
| Workflow weights | `governance/sources/workflow-weights.md` | read |
| PRD | `governance/sources/holy-grail-prd.md` | read |
| Architecture overview | `governance/sources/architecture-overview.md` | read |
| Implementation architecture | `docs/architecture.md` | referenced |
| Module index | `MODULE_INDEX.md` | referenced |
| RP runtime layout | `v2/README.md` | referenced |

### Issue body reconciliation

- Preserved binding user sequencing decision (create #199/#200/#201 → remediate → assess → redesign only after consensus).
- Recorded prerequisite gate **satisfied** 2026-09-14 (#199 PR #202; #200 PR #203).
- Updated `Current status:` → `investigating`.
- Updated Execution snapshot, anchor, Next step, Validation criterion 5, Related work.

### Post-transition metadata (§B.2)

```
gh issue view 201 --repo KizzieFae/Holy-Grail-RP-DeepSeek-Harness --json number,state,labels,projectItems
→ OPEN, labels=[enhancement, type:design_gap], projectItems Status=In Progress

gh project item-list 10 --owner KizzieFae --jq '.items[] | select(.content.number==201) | {status, workflow, priority}'
→ status=In Progress, workflow=Investigating, priority=P1
```

**§B.3 alignment:** `Current status: investigating` ↔ Project **In Progress** / **Investigating** — **pass**.  
**Priority (material):** P1 unchanged; assessment authorized within correctness-first phase sequence.

---

## 2. Repository / evidence anchor

| Anchor | Value |
|--------|-------|
| Investigation commit | `43db105401769750980bdc214666424fa11985cb` |
| Source-session SHA | `09f39295cfc6d6aa62367c65d9e09cdbc89b24b0` |
| Post-#199 merge | `d40d8c6f95e6aca75ba4ea88cca9a0665be06557` |
| Post-#200 merge | `4b322f2bea2b5879a2569c77b162ee982244e5a8` |
| LLM catalog authority | `v2/rp_runtime/src/application/llm-call-catalog.mjs` |
| Latency reconstruction | `tools/investigation/reconstruct_round_latency.py` |
| Forensic navigator | `tools/investigation/trace_turn_forensics.py` |
| #136 assessment | `governance/records/issue-136-llm-inference-contract-assessment.md` |
| #194 decision-value | `governance/records/issue-194-investigation-2026-09-14.md` |
| Execution evidence layout | `docs/rp-data-layout.md` §Execution evidence |

---

## 3. Package A — Requirements / outcomes model

### Required outcomes (mechanism-independent)

| Outcome | Why indispensable | Current typical mechanism(s) | Mechanism optional? |
|---------|-------------------|------------------------------|---------------------|
| **Character fidelity** | Product core; NPCs must remain themselves across turns | Character manifest, orientation, semantic eval, scene grounding | **Partially** — fidelity enforcement need not equal dedicated Character LLM chain |
| **Independent character agency** | Multi-NPC scenes require non-Player initiative | Director selection + Character generation + participation policy | **Partially** — monolith could generate all NPCs but isolation weakens |
| **Knowledge / privacy boundaries** | Prevent cross-character leaks (#112, #38, #199) | PVR, perceptual projection, Librarian mediation, entitlement filters | **Unlikely fully optional** — requires structured entitlement even if not multi-agent |
| **Perception boundaries** | Characters see only what entitled (#155, #199) | `perception_audibility_visibility.py`, `character_perceptual_inventory.py` | **Structured machinery required**; LLM perception optional |
| **Authoritative continuity / world state** | Single committed truth (#100, PRD) | `ContinuityManager.process_turn`, commit transaction | **State machinery required**; Continuity LLM cognition not proven necessary |
| **Coherent progression** | Scenes must advance without contradiction | Director, issue pressure, plot cognition, Storyteller advisory | **Partially** — progression could be simpler with fewer advisory layers |
| **High-quality narrative presentation** | Operator-facing prose quality | Narrator render + env cognition + semantic QA | **Partially** — quality may not require separate Narrator + env cognition + QA stack |
| **User responsiveness** | Live play tolerance (~30–60s historical; F06 ~157–224s) | Entire synchronous stack | **Outcome demands fewer critical-path inferences** — mechanism TBD |
| **Long-session stability** | Resumable scenes, no drift accumulation | Continuity persistence, invalidation, pressure freshness (#200) | **State + invalidation required** |
| **Auditability / forensic reconstruction** | Program and session audits | `execution_evidence/`, trace emitters, session records | **Instrumentation required**; extent on critical path TBD |
| **Deterministic legality** | Objective rules must not be LLM-guessable | `response_validation_*.py`, Host `validate_*` | **Required** — validators may be deterministic without semantic QA |
| **Scalable knowledge retrieval / context assembly** | Future novel-scale corpora (#31, #50, PRD Layer 1–2) | Retrieval façade, Librarian S2a, Packaging `prepare_*` | **Knowledge-system complexity likely grows**; **cognition-topology complexity need not** |
| **Credible large-world support** | Assimilated novels, many characters, deep history | Authored index, story knowledge JSONL, future graph/vector | **Ingestion + retrieval + entitlement scale** — separate from agent count |

### Governing complementary questions (Governance framing)

1. **Top-down (#201 charter):** Which components would we deliberately build again?  
2. **Bottom-up (Governance addendum):** What observable capability disappears if we remove each node/edge?  
3. **Synthesis:** What is the least complex cognitive architecture preserving required outcomes, excellent RP, and credible massive-knowledge path?

### Marginal-value principle

Historical existence ≠ justification. Cost ≠ uselessness. Each synchronous inference/edge must demonstrate **marginal system value** — a materially different downstream decision, state, context, or visible result.

---

## 4. Package A — Architecture hypotheses A0–A4

*No winner selected. Evidence requirements noted per topology.*

### A0 — Monolithic RP (single creative LLM)

| Dimension | Assessment |
|-----------|------------|
| **Topology** | One model receives bounded context and emits full round output (NPC moves + narration + implicit state). |
| **Strengths (known class)** | Simple coordination; low handoff loss; strong immediate prose when context fits; lowest inference count. |
| **Weaknesses (known class)** | Context/attention competition as history grows; weak private-knowledge separation; cross-character leakage; character drift; difficult forensic attribution. |
| **Holy Grail fit** | **Insufficient alone** for knowledge boundaries, deterministic legality, and audit reconstruction without substantial non-LLM infrastructure wrapped around it. |
| **Evidence to distinguish** | Multi-character private-knowledge stress (Arkham mess hall); long-session drift; entitlement violation rate vs A1+. |

### A1 — Monolithic creative + structured knowledge/state infrastructure

| Dimension | Assessment |
|-----------|------------|
| **Topology** | One primary generative model; deterministic machinery for state, entitlement, perception, retrieval, selective context assembly. |
| **Strengths** | Preserves RP fluency while addressing #112-class leaks and #100 continuity authority; aligns with PRD Layers 1–2 feeding one executor. |
| **Weaknesses** | Single model still bears all creative + epistemic load; may struggle multi-NPC differentiation; context window becomes bottleneck at novel scale. |
| **Holy Grail fit** | **Plausible target** if marginal value of separate Character/Director/Narrator cognition is low in ablation. |
| **Evidence to distinguish** | Ablation: remove Director/Character/Narrator separation but keep PVR + Continuity + Retrieval + validators. |

### A2 — Creative model + consolidated supervisory cognition

| Dimension | Assessment |
|-----------|------------|
| **Topology** | One RP generator + one additional model for consolidated planning/checking/state-oriented duties (merged Director + partial Storyteller + selective QA). |
| **Strengths** | Reduces agent count vs A4; centralizes progression/planning; may cut preamble stack duplication. |
| **Weaknesses** | Supervisor may become prompt-bloat sink (#136 risk); harder to enforce role-private generation; checker/generator coupling. |
| **Holy Grail fit** | **Conditional** — attractive if Storyteller + Director + partial semantic QA overlap is confirmed duplicative. |
| **Evidence to distinguish** | Combine Director + Storyteller assessment + plot init into one call on simple turns; measure correctness + latency. |

### A3 — Compact specialized multi-agent

| Dimension | Assessment |
|-----------|------------|
| **Topology** | Small fixed role set (e.g., 3–4): **Planner/Selector**, **Actor**, **Renderer**, plus deterministic **Authority** layer — boundaries derived from requirements not historical names. |
| **Strengths** | Preserves separation of selection / in-character generation / presentation; fewer edges than A4. |
| **Weaknesses** | Still multi-handoff; role boundaries may not match Holy Grail's issue/continuity model without redesign. |
| **Holy Grail fit** | **Candidate moderate redesign** axis for deliverable §19. |
| **Evidence to distinguish** | Map current nodes onto 3-role compact model; identify orphaned inferences. |

### A4 — Current Holy Grail (distributed inference architecture)

| Dimension | Assessment |
|-----------|------------|
| **Topology** | ~25 primary LLM call kinds (`llm-call-catalog.mjs`); 5+ named agents; parallel post-commit fan-out; deepest Character chain. |
| **Strengths** | Strong documented boundaries (#33, #100, #136); extensive validation surround; rich forensic evidence; proven correctness fixes (#199, #200). |
| **Weaknesses** | F06: 38/38 successful inferences, ~157–224s player-visible; stiffness; semantic violations before fixes; high coordination cost. |
| **Holy Grail fit** | **Default incumbent** — must earn retention per component, not assume. |
| **Evidence to distinguish** | Package D ablations removing/combining each major lane. |

---

## 5. Package B — Node inventory (synchronous path)

**Scope:** Player submit → player-visible presentation. Includes deterministic nodes when they decide, derive, filter, or mutate state on the critical path.

### Phase 0 — Ingress

| ID | Node | Location | Sync/CP | LLM | Authority | Preliminary marginal-value hypothesis |
|----|------|----------|---------|-----|-----------|--------------------------------------|
| N-00 | Streamlit submit | `v2/ui/streamlit_app.py` | sync | no | derived | Required ingress — neutral |
| N-01 | App server `/api/turns/submit` | `app-server.mjs` | sync | no | derived | Required API — neutral |
| N-02 | Round concurrency guard | `hg-application-client.mjs` | sync | no | deterministic | Prevents corrupt parallel ops — **high safety value** |
| N-03 | Forced-speaker detection | `detect-forced-speaker.mjs` | sync | no | deterministic | Routes participation bypass — **conditional value** |

### Phase 1 — Player PVR (pre-round)

| ID | Node | Location | Sync/CP | LLM | Measured cost (F06 evidence) | Preliminary hypothesis |
|----|------|----------|---------|-----|------------------------------|------------------------|
| N-10 | Player visibility triage | `player-visibility-triage-phase.mjs` | **CP** | yes | ~0.7s (#194) | **Supporting** — cheap router; retain |
| N-11 | Uniform eligibility verification | `player-uniform-eligibility-verification.mjs` | CP | yes | small (#197) | **Necessary guard** on uniform path — retain |
| N-12 | Uniform projection shortcut | `player-uniform-projection.mjs` | CP | no | negligible | **High value** — avoids decomposition |
| N-13 | Player decomposition (PVR) | `player-decomposition-phase.mjs` | **CP** | yes | ~41.5s wasted on knock-only (#194) | **Conditional** — required for asymmetric visibility; cost/regression needs tiering |
| N-14 | PVR normalize/validate | Host `player_decomposition_context.py`, domain validators | CP | no | in decomposition | **Required** if N-13 runs |
| N-15 | `record_user_turn` | Host `kernel.record_user_turn` | **CP** | no | persist | **Indispensable** — tier-1 player authority |
| N-16 | Scene-pressure freshness note | `continuity_scene_pressure_projection.py` | CP | no | negligible | **High correctness value** (#200) |

### Phase 2 — Round bootstrap

| ID | Node | Location | Sync/CP | LLM | Preliminary hypothesis |
|----|------|----------|---------|-----|------------------------|
| N-20 | Runtime provenance sync | `hg-application-client.mjs` | sync | no | **Audit value** — retain |
| N-21 | `startRound` | Host `kernel.startRound` | CP | no | **Required** |
| N-22 | Execution span / graph coordinator | `execution-span-tracker.mjs`, `round-orchestration-span-coordinator.mjs` | parallel instrumentation | no | **Observability** — off-CP overhead TBD |

### Phase 3 — Round preamble

| ID | Node | Location | Sync/CP | LLM | Measured (F06 #194) | Preliminary hypothesis |
|----|------|----------|---------|-----|---------------------|------------------------|
| N-30 | Storyteller orientation | `storyteller-cognition-substrate.mjs` | **CP serial** | yes | ~2.8s | **Conditional** — defer on simple turns? |
| N-31 | Librarian mediation @storyteller | `librarian-mediation-substrate.mjs` | CP serial | yes | ~23.3s | **Worthwhile refinement** — cost high on T1 |
| N-32 | Storyteller assessment | `storyteller-cognition-substrate.mjs` | CP serial | yes | ~15.2s | **Conditional** — advisory; tier by complexity |
| N-33 | Plot cognition init | `plot-cognition-orchestration.mjs` | CP serial | yes | ~10.5s | **Conditional** — opening-turn cost (#194 deferral candidate) |
| N-34 | Plot cognition update (resume) | `plot-cognition-orchestration.mjs` | CP | yes | varies | **Conditional** — cross-commit advisory value unproven at scale |

### Phase 4 — Character-turn loop (per iteration)

| ID | Node | Location | Sync/CP | LLM | Measured | Preliminary hypothesis |
|----|------|----------|---------|-----|----------|------------------------|
| N-40 | Eligible actors | Host `getEligibleActors` | CP | no | small | **Required** |
| N-41 | Participation decision | Host `getParticipationDecision` | CP | no | small | **Required** — may bypass Director |
| N-42 | Director turn | `director-phase.mjs` | CP | yes | ~1.9–3.3s | **Decision-producing** — core selection |
| N-43 | Director semantic QA | `director-semantic-qa.mjs` | CP | yes | ~1.2s | **Validation** — unique safety TBD in ablation |
| N-44 | Character orientation | `character-cognition-substrate.mjs` | CP | yes | ~17.6s | **Supporting** — high cost; marginal prose value unproven |
| N-45 | Librarian mediation @character | `librarian-mediation-substrate.mjs` | CP | yes | bundled in prep | **Conditional** — knowledge boundary aid |
| N-46 | Plot epistemic eval + advisory regen | `plot-cognition-character-projection.mjs` | CP | yes | ~5.5s (×4) | **Low-evidence advisory** — ablation candidate |
| N-47 | Character move | `character-phase.mjs` | CP | yes | ~4.3s | **Decision-producing** — core output |
| N-48 | `validate_move` | Host `kernel.validate_move` | CP | no | small | **Indispensable** deterministic gate |
| N-49 | Character semantic evaluation | `character-semantic-evaluation.mjs` | CP | yes | ~1.3s | **Necessary guard** — demonstrated #199/#193 |
| N-50 | `commit_move` → `process_turn` | `commit_move_transaction.py` | **CP** | no | small | **Indispensable** authority |
| N-51 | Storyteller advisory invalidation | `commit_move_transaction.py` Phase F | CP | no | small | **Required** for Model A hygiene |
| N-52 | Post-commit join coordinator | `post-commit-span-coordinator.mjs` | CP join | no | join overhead | **Coordination tax** |

### Phase 4.9 — Post-commit parallel fan-out

| ID | Node | Location | Sync/CP | LLM | Measured | Preliminary hypothesis |
|----|------|----------|---------|-----|----------|------------------------|
| N-60 | Storyteller post-commit issue pressure | `librarian-proposal-orchestration.mjs` | parallel (joined) | yes | ~4.7s | **Observational** — narrow S4 input |
| N-61 | Plot cognition post-commit | `plot-cognition-orchestration.mjs` | parallel | yes | varies | **Conditional** advisory |
| N-62 | Narrator environment cognition | `narrator-environment-cognition-substrate.mjs` | **CP tail** | yes | **~55.7s** (#194) | **Disproportionate** on simple beats — tiering candidate |
| N-63 | Librarian mediation @narrator | `librarian-mediation-substrate.mjs` | CP tail | yes | ~7.1s | **Supporting** |
| N-64 | Narrator presentation | `narrator-phase.mjs` | CP tail | yes | ~9.0s | **Decision-producing** visible prose |
| N-65 | Narrator semantic QA | `narrator-semantic-qa.mjs` | CP tail | yes | ~1.1s | **Validation** — fidelity guard |
| N-66 | S4 proposal finalize/apply | Host `finalize_librarian_proposals` | parallel | mixed | small | **Derived-state seam** — correctness (#200) vs complexity |

### Phase 5 — Presentation persistence

| ID | Node | Location | Sync/CP | LLM | Preliminary hypothesis |
|----|------|----------|---------|-----|------------------------|
| N-70 | `record_presentation` | Host `kernel.record_presentation` | CP | no | **Required** — PVR on visible output |
| N-71 | Transcript refresh | `hg-application-client.mjs` | CP | no | **Required** for UI |
| N-72 | Perceptual visibility on presentation | `perceptual_visibility_service.py` | CP | no | **Required** boundary enforcement |

**F06 repeat session (Issue body):** R1 **156.8s**, R2 **192.6s** wall; **38/38** inferences success, zero retries. Historical F06 knock-only turn **~224s** (#194).

**Primary runtime LLM inventory:** 25 entries in `PRIMARY_RUNTIME_CATALOG` (+ contract-correction variants).

---

## 6. Package B — Coordination edge inventory

| Edge ID | From → To | Payload / transformation | Authority class | Loss risk | Preliminary hypothesis |
|---------|-----------|--------------------------|-----------------|-----------|------------------------|
| E-01 | Player text → triage | raw post → route decision | derived | low | retain |
| E-02 | Triage → decomposition OR uniform | routing | deterministic | low | retain |
| E-03 | Decomposition → `record_user_turn` | semantic units + entitlement | **authoritative** | medium — retry waste | refine tiering |
| E-04 | `record_user_turn` → round start | tier-1 player_fact | **authoritative** | low | indispensable |
| E-05 | Storyteller bind → preamble consumers | advisory package | suggestive | medium — stale if not invalidated | retain with invalidation |
| E-06 | Librarian bundle → Storyteller/Character/Narrator | mediated knowledge | derived | **high** — summarization loss | core #33 seam |
| E-07 | Director decision → Character prep | next_actor, constraints | mixed | medium | core orchestration |
| E-08 | Perception filter → Character trigger | entitled observables only | derived | **high** — #200 class drops | structural risk |
| E-09 | Character move → validate_move | proposed JSON | derived | low if contract tight | indispensable |
| E-10 | validate → semantic eval | normalized + authority refs | derived | low | indispensable |
| E-11 | semantic eval → commit | pass/reject | deterministic gate | low | indispensable |
| E-12 | commit → Continuity | validated_move + director_decision | **authoritative** | low | indispensable |
| E-13 | commit → post-commit parallel | domain_commit_id, turn index | authoritative | join blocking | **coordination cost** |
| E-14 | Character structured move → Narrator | committed beats | authoritative | medium — spec-renderer risk | quality concern |
| E-15 | Env cognition → Narrator | B2 proposals | derived | medium | cost/value mismatch on simple turns |
| E-16 | Narrator prose → presentation record | visible text + PVR | derived→authoritative | low | indispensable |
| E-17 | Scene pressures → Character manifest | advisory overlays | derived | **high stale risk** — #200 | freshness fix helps; promotion gap remains |
| E-18 | Plot projection → Character | advisory overlay | derived | medium | ablation candidate |
| E-19 | Execution evidence → forensic tools | attempt JSON | observational | none | retain for assessment |

### Information-train preliminary traces (F06 facts)

| Fact | Authoritative source | Transformations observed | Failure mode |
|------|---------------------|--------------------------|--------------|
| **Knock / steeled herself** | Player post; PVR marked internal/private correctly | Character move invented "strain tells" (#199) | Private → false observable |
| **Wipe feet** | PVR `observable_event`; Player post | Director claimed compliance; Character re-commanded mat (#200) | Authoritative observable dropped in Character projection |
| **Scenario premise** | Authored scenario template | Character used premise as perceptual evidence (#199) | Knowledge → false observable |
| **Env grounding (house number)** | Player glance action | Env cognition ~56s for narrow B2 (#194) | Disproportionate cost; modest value |
| **Continuity / issue pressure** | Librarian B2 overlay | Stale `semantic_unmet_condition` after Player tier-1 (#200) | Derived pressure contradicted world truth |
| **Plot guidance** | Plot cognition overlay | Character prep receives advisory | Value vs cost unproven on simple turns |

---

## 7. Package C — Historical justification ledger

*Chain-of-custody from governance records; historical reason ≠ continuing necessity.*

| Component | Originating driver | Introducing Issues/PRs | Failure prevented | Current justification |
|-----------|-------------------|------------------------|-------------------|----------------------|
| **PVR stack** | Knowledge leaks; 0/18 usable PVR (#112 audit) | #112→PR126; #121 uniform; #197 verification | Cross-character player leaks | **Strong, refined** — always-on full decomp rejected |
| **Director** | PRD turn selection | #23, #26 semantic QA | Wrong actor; prompt-as-fix anti-pattern | **Strong** |
| **Character chain** | PRD structured moves | #136, #19, #38, #199 | Invalid moves; invented facts | **Strong** — deepest chain; cost questioned |
| **Narrator** | Prose render ≠ truth | #24, #27, #49 env cognition | Dialogue invention; env fabrication | **Strong role** — env cognition cost questioned |
| **Storyteller** | #33 decomposition | #32, #164 producer realignment | Monolithic prompt knowledge | **Strong advisory** — preamble cost on simple turns |
| **Librarian** | #33 mediation | #34, #100, #39 | Ungoverned retrieval; uncontrolled S4 | **Strong with seam debt** |
| **Continuity** | PRD truth engine | #55 commit txn, #100 seams | Prompt-as-truth | **Foundational** |
| **Validators / semantic QA** | PRD validation layer | #19, #26, #27, #193, #200 | Semantic illegality after structural pass | **Strong** — independent value demonstrated |
| **Plot cognition** | #48 persistent advisory | #58–#64 | Round-local plot loss | **Moderate-strong** — newer; latency questions |
| **Env cognition** | #49 narrator env obligations | #49, #151, #194 | Ungoverned worldbuilding | **Strong post-remediation** — tiering needed |
| **Scene Grounding** | PRD §5.8 settled facts | #127 | Re-litigating logistics | **Strong** — read-only MVP |
| **Retrieval** | #31 hard access | S0+S1, #50 story knowledge | Vector-as-truth | **Strong assistive layer** |

### Superseded / weakened justifications

- **Always-on full PVR:** rejected (#112).
- **Librarian as routine post-commit semantic producer for broad kinds:** superseded by #164 (narrow `issue_tension_pressure` only).
- **Forward-only R16 (#193):** generalized bidirectionally for objective regression (#200) — partial supersession of narrow rule.
- **Perception widening as #200 fix:** rejected; stale derived state was root cause.

### Duplication signals (#136, #194)

- DSH `live-inference-prompts.mjs` vs Host `inference_instruction` — instruction duplication risk.
- Stacked advisories (Storyteller + plot + scene digests + Librarian) compete with transcript in Character/Director manifests.
- Generation → checker → retry patterns on Player PVR and Narrator env cognition amplify cost without demonstrated marginal value on simple turns.

---

## 8. Major-agent falsifiable hypotheses

| Agent | Hypothesis | Falsified if | Package D experiment sketch |
|-------|------------|--------------|----------------------------|
| **Character** | Dedicated character cognition improves fidelity/agency/knowledge adherence vs consolidated generation | Ablated topology matches contractual + quality metrics | Combine orientation+move; remove orientation on simple turns |
| **Director** | Separate selection authority improves legality/progression vs embedded selection | Monolith+validators matches actor selection quality | Bypass Director when participation policy deterministic |
| **Narrator** | Separate rendering improves prose/grounding/perspective vs inline generation | Character-only output matches narrative quality rubric | Skip Narrator; render from structured move only |
| **Storyteller** | Story-level advisory improves long-horizon drama beyond simpler topology | No quality delta over 10+ turns without Storyteller preamble | Remove preamble stack on tier-1 turns |
| **Librarian** | Semantic mediation adds value beyond Retrieval+deterministic assembly | Raw retrieval+entitlement filters match consumption correctness | Bypass S2a; structured retrieval only |
| **Continuity (state)** | Authoritative state machinery is indispensable | N/A — expected retained | Not ablated |
| **Continuity (LLM)** | Any Continuity-associated LLM cognition is indispensable | Deterministic rules cover same legality | Identify any Continuity LLM calls (currently minimal on hot path) |
| **Validators** | Independent semantic QA provides unique safety vs better generator contracts | Earlier deterministic authority prevents same violations | Remove semantic eval; strengthen contracts |

---

## 9. Checker / validator preliminary analysis

| Pattern | Instances | Unique safety demonstrated? | Earlier deterministic alternative? | Duplication? | Preliminary class |
|---------|-----------|----------------------------|-----------------------------------|--------------|-------------------|
| Structural move validate | `validate_move`, `validate_director_decision` | yes — schema/legality | partial | no | **necessary guard** |
| Character semantic eval | R02b, R16, player_fact rules | yes — #199, #193, #200 | hard for all semantic cases | overlaps with validate | **necessary guard** |
| Director semantic QA | selection defensibility | partial | participation policy sometimes bypasses | low | **conditional** |
| Narrator semantic QA | F1/F2 fidelity | yes — prose invention | render contract tightening possible | low | **worthwhile refinement** |
| PVR substantive coverage checker | decomposition retry | prevents bad units | triage/uniform path avoids | triggers retry waste | **expensive narrow** on simple turns |
| Contract correction (×6 kinds) | parse recovery | yes — availability | stricter schemas | per-call overhead | **defensive** |
| Inverse R16 (#200) | objective regression | yes — demonstrated | world-state promotion could reduce | extends #193 | **necessary guard** until promotion exists |

---

## 10. Knowledge-system vs cognition-topology analysis

| Dimension | Knowledge-system complexity | Cognition-topology complexity |
|-----------|----------------------------|------------------------------|
| **Scales with corpus size** | ingestion, indexing, entitlement graph, scoped retrieval, evidence budgets (#50, #51) | not inherently — unless each turn spawns many LLM mediators |
| **Holy Grail current state** | authored snapshot + compiled index + story JSONL; vector/graph deferred | ~25 LLM kinds, 5+ agents, 3+ mediation calls per turn |
| **Future novel-scale requirement** | needs robust ingestion, scoped retrieval, entitlement-safe assembly, rebuildable indexes | needs **bounded** context assembly — not necessarily more agents |
| **Risk of conflation** | adding Librarian/Storyteller/Plot layers to compensate for weak retrieval | reducing retrieval investment because agents "handle" knowledge in prompts |
| **Assessment implication** | invest in Packaging + Retrieval + entitlement as first-class | ablate cognition layers while holding knowledge-system constant |

---

## 11. Evidence gaps and uncertainties

| Gap | Impact | Proposed resolution |
|-----|--------|-------------------|
| No causal ablation data | Cannot confirm marginal value rankings | Package D (authorized separately) |
| Quality metrics subjective | Cannot rank prose improvements deterministically | Semantic rubric + blind human eval in Package D |
| Post-#199/#200 corpus on `main` | Assessment quality may improve vs source session | Re-run F06 characterization on `4b322f2`+ before final synthesis |
| Portal desync (#200 deferred) | World-state promotion gap confounds consumption analysis | Include in #201 assessment; not fixed |
| `trace_turn_forensics` pressure gaps (#200 F5/F9) | Harder to audit handoff failures | Instrumentation recommendation in final synthesis |
| Arkham stress recency | Multi-character stress scenarios exist but may need refresh on current `main` | Validate harness before Package D |
| Instruction duplication (#136) | Unknown cost/quality impact | Prompt corpus diff + ablation |

---

## 12. Proposed Package D — causal ablation campaign (NOT EXECUTED)

### Stress benchmark primary

**`arkham_asylum_mess_hall_arena`** — 3+ characters, distinct agendas, low privacy, perceptual boundaries, staff authority margin, public volatility vectors (`data/scene_templates/arkham_asylum_mess_hall_arena.json`). Supported by `arkham_multi_character_stress` harness scenarios (`tools/maintenance/issue88_tranche1_prepare.py`).

**Secondary controlled scenarios:** `ayame_household_entry_evaluation` (F06 regression isolation); `arkham_asylum_cell_intake` (dyadic tension).

### Tier-1 experiments (highest information gain)

| Exp ID | Element under test | Control | Variant | Correctness measures | Quality measures | Latency | If control wins | If variant wins |
|--------|-------------------|---------|---------|---------------------|------------------|---------|-----------------|-----------------|
| D-01 | Storyteller preamble stack (N-30–32, N-31) | full preamble | skip on tier-1/simple turn detector | knowledge violations, progression errors | dramatic progression rubric | wall, inference count | preamble justified | defer/slim preamble |
| D-02 | Plot cognition init (N-33) | init on opening | skip init turn 1 | plot thread continuity | scene coherence | wall | init unnecessary early | retain init |
| D-03 | Character orientation (N-44) | full orientation | move-only | R02b/R16 passes, fidelity | character voice rubric | wall | orientation redundant | retain |
| D-04 | Narrator env cognition (N-62) | full env cog | template baseline only (#49 B1) | env grounding errors | prose grounding | wall, reasoning tokens | env cog overkill simple beats | retain tiered cog |
| D-05 | Librarian S2a @character (N-45) | mediated bundle | retrieval+deterministic assembly | leak rate, entitlement | knowledge use quality | wall | mediation redundant | retain |
| D-06 | Director semantic QA (N-43) | QA on | QA off | invalid selections | pacing | wall | QA redundant | retain |
| D-07 | Character semantic eval (N-49) | eval on | eval off + stronger contracts | #199/#200 class violations | stiffness | wall | contracts sufficient | retain eval |
| D-08 | Combined compact topology | A4 full | A3 3-role compact | full contractual matrix | RP quality bundle | wall, tokens | **major redesign warranted** | incremental tweaks |
| D-09 | Player PVR full path (N-13) | decomposition | uniform+verify only on eligible | leak rate | n/a | wall | tiering works | retain full PVR |
| D-10 | Post-commit parallel join (N-52–66) | sync join all | narrator-only critical; defer plot/S4 | pressure freshness, presentation | prose latency | tail wall | parallel fan-out excessive | retain |

**Confounders:** model/version drift; scenario-specific beats; temperature; effective config epoch; post-#199/#200 fixes changing baseline.

**Authorization:** Governance must approve campaign before any live inference spend.

---

## 13. Creative-quality evaluation framework (proposed)

### Objective / contractual (deterministic or rule-based)

- knowledge boundary violations (entitlement cross-check)
- perception violations (unsupported observables)
- continuity contradictions (committed state vs output)
- player action regression (inverse R16 class)
- missed required responses
- retry/failure counts
- wall latency, token totals, inference count per operation
- forensic completeness (evidence artifacts present)

### Semantic RP quality (non-deterministic; labeled as such)

| Dimension | Description | Measurement approach |
|-----------|-------------|-------------------|
| Character fidelity | Voice, goals, boundaries | blind rubric 1–5 |
| Distinctiveness | separable voices multi-NPC | pairwise comparison |
| Initiative | unprompted dramatic action | rubric + exemplar anchors |
| Responsiveness | reacts to Player facts | fact-consistency checklist |
| Dramatic progression | tension/movement | Storyteller-agnostic rubric |
| Scene coherence | spatial/temporal clarity | error tagging |
| Prose quality | naturalness, rhythm | blind rubric |
| Repetitiveness | loop/stiffness (#201 concern) | n-gram + rubric |
| Stiffness / exposition | spec-renderer vs scene | comparative annotation |
| Emotional continuity | carryover across turns | session-level rubric |

---

## 14. Complexity-frontier measurement structure (not populated)

Compare viable points on complexity axis:

**1 call → 2 calls → compact multi-agent (A3) → richer multi-agent (A4 current)**

| Metric | 1-call | 2-call | compact | current |
|--------|--------|--------|---------|---------|
| RP quality (semantic bundle) | TBD | TBD | TBD | baseline |
| Correctness (contractual) | TBD | TBD | TBD | baseline |
| Knowledge isolation | TBD | TBD | TBD | baseline |
| Long-context robustness | TBD | TBD | TBD | baseline |
| Latency (p50/p95) | TBD | TBD | TBD | 157–224s F06 |
| Tokens / inference count | TBD | TBD | TBD | 38/round F06 |
| Auditability | TBD | TBD | TBD | strong |
| Knowledge scalability | TBD | TBD | TBD | moderate |
| Implementation complexity | low | low-med | med | high |

Population awaits Package D + synthesis packages.

---

## 15. Mapping to #201 deliverable sections 1–23

| § | Deliverable | Packages A–C status |
|---|-------------|---------------------|
| 1 | End-to-end architecture map | **Partially satisfied** — §5–6 node/edge inventory |
| 2 | Critical-path map | **Partially satisfied** — F06 #194 wall segments + §5 CP flags |
| 3 | Complete inference inventory | **Satisfied** — `llm-call-catalog.mjs` + §5 |
| 4 | Component value ledger | **Partially supported** — preliminary hypotheses only |
| 5 | Checker/correction ledger | **Partially supported** — §9 |
| 6 | Information-handoff map | **Partially supported** — §6 traces |
| 7 | Historical rationale per layer | **Satisfied** — §7 |
| 8 | Measured latency contribution | **Partially supported** — F06/#194; per-node on key stages |
| 9 | Demonstrated correctness contribution | **Partially supported** — #199/#200 fixes; not per-component causal |
| 10 | Demonstrated quality contribution | **Gap** — stiffness observed; not causally attributed |
| 11 | Failure modes per layer | **Partially supported** — §6, §7 |
| 12 | Duplication/redundancy | **Partially supported** — §7, #136 signals |
| 13 | Creative-freedom findings | **Gap** — hypothesis only (spec-renderer risk) |
| 14 | Decision-value ranking | **Partially supported** — #194 table extended in §5 |
| 15 | Components clearly justified | **Premature** — state machinery, PVR (conditional), validators |
| 16 | Conditional components | **Partially supported** — preamble, plot, orientation, env cog |
| 17 | Insufficient justification | **Premature** — candidates flagged, not concluded |
| 18 | Candidate simplifications | **Partially supported** — tiering, deferral, compact topology |
| 19 | Target architectures A0–A4 comparison | **Partially supported** — §4; awaits D metrics |
| 20 | Risk/tradeoff analysis | **Awaiting synthesis** |
| 21 | Expected latency ranges | **Awaiting D** |
| 22 | Validation strategy | **Partially supported** — §13–14 |
| 23 | Remediation program | **Not authorized** — post-consensus only |

---

## 16. Durable record location / investigation artifact disposition

| Artifact | Location | Status |
|----------|----------|--------|
| Packages A–C investigation (this record) | `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` | **committed candidate** (repo working tree) |
| Issue body (authoritative workflow state) | GitHub #201 body | updated activation 2026-09-14 |
| Activation body staging file | `governance/records/_issue-201-body-activation.md` | disposable staging — delete after verification |
| Execution evidence (read-only) | `data/execution_evidence/hg-session-*` | not mutated |
| Package D results | not created | awaits authorization |

---

## 17. Questions for Governance before Package D

1. **Approve Package D live ablation campaign** with proposed experiment set (§12) — or subset?
2. **Re-baseline F06** on post-#200 `main` (`4b322f2+`) before ablations, or use historical sessions only?
3. **Primary stress scenario:** confirm `arkham_asylum_mess_hall_arena` + harness `arkham_multi_character_stress` vs alternative?
4. **Human quality eval:** authorize blind rubric sessions for semantic dimensions (§13)?
5. **Tiering policy:** may Package D include complexity-sensitive gating (skip preamble/env cog on tier-1) as variants, or only removal ablations?
6. **World-state promotion gap** (deferred from #200): assess within #201 synthesis or file separate Issue before D?
7. **Disposition authority:** may investigation proceed to Packages E–G (synthesis) after D without new Governance gate?

---

## 18. Session boundary

**Stage:** `investigating` — Packages A–C complete; Package D proposed only.  
**Completed:** Full bootstrap; activation sync; requirements model; hypotheses A0–A4; node/edge inventory; historical ledger; agent hypotheses; checker analysis; information-train traces; knowledge/cognition split; D proposal; quality framework; complexity structure; §1–23 mapping.  
**Not done:** Package D execution; consensus; any production change.  
**Next:** Governance review of this record + Package D authorization decision.
