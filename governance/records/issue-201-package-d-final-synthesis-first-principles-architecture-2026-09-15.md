# Issue #201 — Package D Final Synthesis & First-Principles Architecture Assessment

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  
**Status:** Final architectural assessment — **NOT implementation**

**Evidence anchors:**

| Anchor | SHA / record |
|--------|----------------|
| Packages A–C inventory | `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` |
| D0 baseline | `governance/records/issue-201-package-d-d0-baseline-2026-09-14.md` |
| Stage-2 / D-06 Director QA | `governance/records/issue-201-package-d-stage2-synthesis-2026-09-14.md` |
| Stage-3 Plot preamble | `governance/records/issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` |
| D-01-L Storyteller preamble | `5d15936` — `issue-201-package-d-d01l-primary-decode-synthesis-2026-09-14.md` |
| D-10 post-commit Storyteller | `d30f4b3` chain — `issue-201-package-d-d10-primary-decode-synthesis-2026-09-15.md` |
| D-04R env cognition | `b88333b` — `issue-201-package-d-d07-d04r-targeted-evidence-design-2026-09-15.md` |
| D-07 Narrator QA | `d30f4b3` — `issue-201-package-d-d07-blind-decode-synthesis-2026-09-15.md` |
| LLM coverage audit | `5ad7129` — `issue-201-runtime-llm-call-coverage-audit-2026-09-15.md` |
| Control substrate | `c751ea6` |

**Governance adjudications carried forward:**

- `director_semantic_qa`: **remove/consolidate** (D-06)
- `narrator_semantic_qa`: **remove/consolidate** always-on separate LLM (D-07)
- `storyteller_orientation` / `storyteller_assessment`: **remove/consolidate** synchronous preamble (D-01-L)
- `storyteller_post_commit_issue_pressure`: **remove/consolidate** (D-10)
- `plot_cognition_*`: **retain function**; topology open (Stage-3, D-01, D-10)
- `narrator_environment_cognition`: **retain function**; **redesign/tier mechanism** (D-04R)
- `character_move`, `narrator_presentation`, `director_turn`: **retain** as core endpoints
- `character_semantic_evaluation`: **retain function**; mechanism may consolidate (correctness B-evidence)
- `character_orientation`, `librarian_mediation`: **conditional**; evidence incomplete

---

## 1. Executive answer

**If Holy Grail were designed today from first principles, we would deliberately rebuild:**

1. **A deterministic Continuity / perception / knowledge substrate** — authoritative state, entitlement, scenario authority, durable facts, audit, retrieval indexing, selective projection.
2. **One primary RP/agentic cognition layer** — Character agency (structured move) + Narrator rendering + Director turn selection as the **small set of creative endpoints** that directly produce player-visible decisions and prose.
3. **One persistent narrative-planning cognition** — Plot cognition (user-remembered Scribe responsibility), operating **off the synchronous critical path** by default, event- or complexity-triggered, writing advisory narrative state consumed by Character/Director.
4. **Deterministic validation and objective gates** — move validation, PVR, perceptual boundaries, scenario/spatial contracts, structural presentation checks, player-authorship rules.
5. **Narrow, failure-triggered semantic repair** — not an every-turn LLM-checks-LLM topology.

**We would not rebuild:**

- Synchronous Storyteller preamble (orientation + assessment) on every turn.
- Post-commit Storyteller issue-pressure as a separate always-on LLM producer parallel to Plot.
- Always-on Director semantic QA and Narrator semantic QA as separate inference kinds.
- Always-on Narrator environment cognition (~2.1×/turn with 44% no-demonstrated-obligation).
- Default always-on Librarian LLM mediation on every orientation/env/ST lane.
- The full ~26-kind synchronous LLM stack as the default turn path.

**Recommended target architecture:** **A2** — *Primary RP intelligence + persistent narrative cognition (Plot/Scribe lane) on deterministic state/retrieval infrastructure* — with a **tiered simple/complex turn path**, not a single expensive topology for every beat.

**Confidence:** High on removals/consolidations listed above; medium on exact compact topology and tiering triggers; low on optimal Character-orientation and Librarian mediation shape without redesign validation.

---

## 2. Governing question

> **If Holy Grail were designed today from first principles, which RP-turn components would we deliberately build again?**

Not: “How can the current architecture be made faster?”

---

## 3. Method

- Package A–C: architecture inventory, coordination edges, baseline models (A0–A4).
- Package D: causal ablations (D-01, D-01-L, D-03, D-06, D-10, D-07), blind semantic evaluation, objective correctness, cost forensics (#194, D0, D-04R).
- Runtime LLM catalog coverage audit (26 production kinds).
- Governance blind-score lock → decode discipline for all experiments.
- Supporting-cognition pruning principle applied throughout.
- No additional live experiments (Governance: Package D complete).

---

## 4. Evidence hierarchy

Applied in order:

1. Causal ablation / intervention  
2. Blind semantic evaluation  
3. Objective correctness  
4. Downstream consumption forensics  
5. Runtime cost / accounting  
6. Validated contracts / tests  
7. Historical Issue rationale  
8. Architectural inference  

Historical rationale and passing tests **do not** override negative causal/blind evidence for **marginal** synchronous value.

---

## 5. Required RP outcomes (mechanism-independent)

| Outcome | Must preserve | Primary mechanism in candidate arch |
|---------|---------------|-------------------------------------|
| Excellent player-visible RP | Yes | Character + Narrator endpoints |
| Character fidelity & agency | Yes | Character move + orientation (conditional) |
| Scenario authority | Yes | Continuity + deterministic validators |
| Private knowledge / no omniscience | Yes | PVR + perception projection + entitlement |
| Perceptual boundaries | Yes | PVR + Host filters |
| Persistent continuity & consequences | Yes | Continuity commits + durable derived state |
| Unresolved narrative pressure | Yes | Plot overlay (+ optional derived pressure store) |
| Multi-character / separated locations | Yes | Director + per-character manifests |
| Long-session robustness | Yes | Continuity + retrieval, not full-context LLM |
| Massive lore scalability | Yes | Retrieval/indexing + selective projection |
| Deterministic correctness where possible | Yes | Validators, contracts, Host authority |
| Semantic judgment where necessary | Conditional | Repair-only / uncertainty-triggered |
| Forensic auditability | Yes | Execution evidence + Continuity audit |
| Acceptable latency/cost | Yes | Tiered topology |

---

## 6. Current architecture inventory (A4)

**Synchronous path (Package B):** ~40+ nodes N-00–N-72 from player submit to visible presentation, including deterministic gates and parallel post-commit join.

**Coordination edges:** 19 documented edges E-01–E-19 (ingress → PVR → preamble → Director → Character chain → commit → post-commit parallel → presentation).

**Production LLM kinds:** **26** unique (`llm-call-catalog.mjs`, audit `5ad7129`).

**Typical F06-class turn:** 38+ LLM inferences, ~157–224s player-visible; post-commit narrator lane binding (#194).

---

## 7. Runtime LLM-call coverage (summary)

| Disposition bucket | Count (approx.) |
|--------------------|----------------:|
| COVERED — retain core endpoint | 6 |
| COVERED — remove/consolidate | **6** (ST preamble ×2, ST post-commit, Director QA, Narrator QA, combined preamble ablation) |
| COVERED — function necessary / mechanism unresolved | 6 |
| UNCOVERED — low decision value | 8 |
| Synthesis-critical (pre-D-07) | **0 remaining** |

**7 kinds directly causally challenged** by #201; all adjudicated or carried as qualified uncertainty.

---

## 8. Cost / latency architecture

- **Binding costs:** preamble stack (~52s serial F06), Character orientation (~17.6s), PVR decomposition waste on simple turns (#194 ~41.5s), narrator env cognition (~55.7s F06), librarian mediation fan-out (2–10×/run D0).
- **QA layers:** small per-call wall but add synchronous depth and stiffness risk.
- **Post-commit parallel:** ST pressure + Plot + Narrator lane compete; join barriers add coordination tax (E-13).
- **Observation:** Cost often scales weakly with decision complexity (env cognition on knock-only turn; decomposition invalid PVR).

**Conclusion:** Latency is a **topology problem**, not only a model-speed problem. Removing/consolidating layers with negative blind evidence is the first architectural lever; tiering is the second.

---

## 9. Coordination-edge analysis

**Necessary infrastructure edges:** E-04, E-07, E-09–E-12, E-16 (with deterministic checks).

**High-loss / bureaucracy risk:**

- E-06 Librarian bundle summarization (repeated reinterpretation)
- E-05 Storyteller advisory bind (largely remove with preamble)
- E-17 scene pressures stale-risk (post-commit ST candidate removed)
- E-18 Plot projection advisory (simplify)
- E-15 env cognition → Narrator when obligation low

**Pattern:** Many edges exist to **feed the next LLM**, not to establish authoritative fact.

---

## 10. Main-agent value assessment

### Player

**Outcome needed:** tier-1 player authority, visibility routing, asymmetric perception.  
**Not proven:** full LLM decomposition on every non-uniform post.  
**Disposition:** **Input-processing boundary + conditional cognition** — retain triage; tier decomposition; strengthen uniform shortcut (#197).

### Character

**Outcome needed:** independent agency, voice, structured commits.  
**Proven:** `character_move` endpoint.  
**Not proven:** entire pre-move chain (orientation + mediation + plot epistemic eval) on every turn.  
**Disposition:** **Retain move**; **conditional** orientation/mediation; **challenge** plot epistemic eval chain (N-46).

### Director

**Outcome needed:** turn selection among eligible actors.  
**Proven:** `director_turn` produces decisions.  
**Not proven:** `director_semantic_qa` marginal value (D-06: blind +0.12 vs D0).  
**Disposition:** **Retain Director decision**; **remove** always-on semantic QA; strengthen deterministic eligibility/policy.

### Narrator

**Outcome needed:** player-visible prose grounded in committed state.  
**Proven:** `narrator_presentation` endpoint.  
**D-07:** remove always-on `narrator_semantic_qa`.  
**D-04R:** tier `narrator_environment_cognition`.  
**Disposition:** **Retain presentation**; **consolidate** validation/repair; **redesign** env cognition trigger.

### Continuity

**Outcome needed:** authoritative commits, knowledge boundaries, durable state.  
**Disposition:** **Deterministic** — not an LLM agent. Core substrate.

### Plot (narrative planning)

**Outcome needed:** persistent unresolved pressure, goals, cross-turn planning.  
**Proven:** Stage-3 Plot ON vs OFF ~**+0.239** descriptive; D-10 both arms retained Plot.  
**Disposition:** **Retain function**; simplify supporting calls (init/update retain; epistemic eval/advisory generation → future validation targets).

### Storyteller (legacy round-local)

**Preamble (D-01-L):** control 4.575 vs ablated 4.525 (Δ **+0.05**); Arkham favors ablation.  
**Post-commit (D-10):** control 4.40 vs ablated 4.63 (Δ **−0.23**); durable overlays confirmed but **no demonstrated RP benefit**.  
**Disposition:** **Do not rebuild** synchronous preamble or current post-commit ST LLM path. Absorb narrative-planning function in **Plot**; absorb durable pressure needs in Plot + Continuity derived state if still required.

### Librarian / Retrieval

**Outcome needed:** selective relevant facts at scale.  
**Not proven:** LLM mediation every retrieval trigger.  
**Disposition:** **Rebuild simplified** — retrieval/indexing/projection as infrastructure; **conditional** LLM mediation/summarization.

### Validators / checkers

**Disposition:** **Retain deterministic**; **remove** default LLM→LLM→repair pattern (Director QA + Narrator QA evidence). **Retain** character semantic eval function with topology open. **Contract-correction** kinds: low decision value; fold into retry policy where needed.

---

## 11. Supporting-cognition assessment

**Principle applied:** Supporting cognition earns no presumption; must serve a demonstrated endpoint or independent responsibility.

| Supporting call | Parent endpoint | Evidence | Disposition |
|-----------------|-----------------|----------|-------------|
| Director QA | Director | D-06 negative | **Remove** |
| Narrator QA | Narrator | D-07 negative | **Remove** always-on |
| ST preamble | Round advisory | D-01-L weak | **Remove** sync path |
| ST post-commit | Narrative pressure | D-10 negative | **Remove** |
| Character orientation | Character move | D-03 mixed | **Conditional** |
| Librarian mediation | Multiple | Fan-out cost; partial D-03 | **Conditional / simplify** |
| Plot epistemic eval | Plot projection | Low cost; low decision value | **Do not rebuild** by default |
| Env cognition | Narrator | D-04R 44% no obligation | **Tier / conditional** |
| Contract corrections | Various | Retry-only | **Consolidate** |

---

## 12. Checker / QA assessment

**Evidence against default topology:**

> LLM generates → separate LLM reviewer → repair

- Director QA (D-06): no blind harm when removed; slight improvement.
- Narrator QA (D-07): ablated **4.39** vs control **4.34**; Sample **E** spatial defect **with QA on** and QA **passed**.

**Conclusion:** Do **not** rebuild always-on semantic second opinions on Director/Narrator. Preserve **protected outcomes** via:

- deterministic validation (spatial/scenario, player-authorship, move legality),
- stronger generation contracts,
- **narrow semantic repair on failure signals**.

Character semantic evaluation **retains function** (#193/#200) — topology may still consolidate later.

---

## 13. Retrieval / Librarian assessment

**Need:** massive lore, selective context, private knowledge at scale.  
**Does not require:** 2–10 LLM `librarian_mediation` calls per turn (D0).  
**Candidate:** deterministic retrieval + ranking + projection; LLM summarization only when retrieval set exceeds budget or ambiguity requires it.  
**Disposition:** **Rebuild simplified** retrieval plane; **move** LLM mediation off default path.

---

## 14. Continuity / state assessment

**Indispensable (deterministic):** commits, scenario authority, entitlement, durable records, stale-pressure protection, audit.  
**Not indispensable as LLM:** any “Continuity agent.”  
**Disposition:** **Retain and strengthen** as authoritative substrate; narrative cognition reads/writes **through** Host gates.

---

## 15. Perception / knowledge assessment

**Need:** PVR, triage, uniform path, perceptual visibility on presentations (#200).  
**Need ≠** always-on `player_decomposition` LLM on simple uniform-eligible posts.  
**Disposition:** **Retain** triage + uniform verification; **tier** decomposition; **deterministic** projection where possible.

---

## 16. Plot / narrative-planning assessment

**Retain:** `plot_cognition_init`, `plot_cognition_update` function — persistent overlay, pressures, goals.  
**Challenge:** epistemic eval + advisory generation + contract corrections — **supporting bureaucracy** under Plot.  
**Lineage (qualified):** Plot is the persistent narrative-planning branch of Storyteller/Scribe intent; not identical to post-commit ST overlays.  
**Disposition:** **Retain function / consolidate topology** — primary Scribe-like role in candidate architecture.

---

## 17. Storyteller assessment

| Mechanism | Blind evidence | Disposition |
|-----------|----------------|-------------|
| Preamble orientation/assessment | Δ +0.05 overall; Arkham −0.25 | **Move off critical path / do not rebuild** |
| Post-commit issue pressure | Δ −0.23; overlays exist but no RP gain | **Do not rebuild**; Plot + Continuity suffice for pressure function |

Post-commit ST **can** create distinct durable overlays (D-10 causal-gap resolved); evidence did **not** show paying for that cognition improved RP.

---

## 18. Environment-cognition conclusion

**D-04R:** 109 invocations; ~2.13/turn; 19% high-value; 37% enrichment; **44% `baseline_sufficient`**.  
**#194:** ~55.7s / ~11.5k reasoning for narrow B2 need on knock turn.  
**Disposition:** **Retain capability; redesign trigger** — complexity-, obligation-, or retrieval-triggered; not always-on. **Do not invent unsupported production gate** in this synthesis.

---

## 19. Information-bureaucracy conclusion

> **Has Holy Grail accumulated information-processing bureaucracy that no longer proportionately improves RP?**

**Yes — materially.**

Evidence: 26 LLM kinds; repeated summarization (Librarian, ST assessment, Plot projection eval); dual narrative-pressure producers (Plot + post-commit ST); dual QA layer; preamble stack; env cognition on low-obligation beats; contract-correction proliferation.

**Necessary infrastructure:** Continuity, PVR routing, commit validation, retrieval/indexing, audit.  
**Unnecessary cognitive handoffs:** many synchronous “interpret previous LLM output for next LLM” stages.

**Risk:** correctness machinery competes with creative attention → stiffness, latency, failure surface (blind: over-composed Ivy, invented env detail, Sample E spatial slip uncaught by QA).

---

## 20. Architecture ladder A0–A4

| Tier | Description | RP quality | Agency | Knowledge | Continuity | Scale | Audit | Latency | Complexity |
|------|-------------|------------|--------|-----------|------------|-------|-------|---------|------------|
| **A0** Monolithic | 1 LLM does all | Good short; drifts long | Weak multi-actor | Poor | Poor | Poor | Poor | Low call count; context blow-up | Lowest code; highest hidden risk |
| **A1** Mono + substrate | 1 creative + deterministic state/PVR/retrieval/validation | Good | Moderate | **Strong** | **Strong** | **Strong** | **Strong** | Better than A4 if one call | Medium |
| **A2** Primary + Scribe/Plot | A1 + persistent narrative cognition (off CP default) | **Best fit to evidence** | **Strong** | **Strong** | **Strong** | **Strong** | **Strong** | **Much better than A4** | Medium-high |
| **A3** Compact multi-agent | Small conditional specialist set | Plausible | Strong | Strong | Strong | Strong | Strong | Better than A4 | High |
| **A4** Current Holy Grail | ~26 LLM kinds, ~40 nodes | Demonstrated capable; stiff/slow | Demonstrated | Demonstrated (with bugs fixed) | Demonstrated | Designed for; costly | **Excellent** | **Poor** (#194, D0) | **Very high** |

**Recommendation:** Target **A2** with A1 substrate; borrow **A3** only for **conditional** triggers (complex beat), not as default.

---

## 21. Cognitive-call frontier

| Frontier | What it buys in A4 | Evidence |
|----------|-------------------|----------|
| **~1** primary creative | Prose + reaction | Janitor baseline lesson |
| **~2** (+ narrative planner) | Cross-turn pressure, goals | Plot +0.239 |
| **~4** (+ Director + dual QA) | Selection + checking | QA layers **not** justified |
| **~8+** (+ preamble ST, orientation, mediation) | Advisory stacks | D-01-L, D-03 weak/mixed |
| **~26** current | Checking, summarizing, repairing prior cognitions | Bureaucracy; marginal blind gains |

**Pattern:** Steps above ~2–3 mostly add **checking, summarizing, reinterpreting, repairing** — not new player-visible capabilities.

---

## 22. Two-model / Scribe hypothesis evaluation

**Hypothesis:**

1. **Primary RP / Agentic Intelligence** — Character, Narrator, local Director decisions, prose, immediate scene continuation.  
2. **Persistent Scribe / Narrative Intelligence** — Plot cognition: pressures, goals, long-horizon planning, delayed consequences.  
3. **Deterministic substrate** — Continuity, PVR, retrieval, validation, audit.

**Verdict:** **Explains Package D evidence better than A4.**

| Evidence | Fit |
|----------|-----|
| Plot retained (Stage-3) | Scribe lane justified |
| ST preamble removed (D-01-L) | Round-local ST not justified |
| ST post-commit removed (D-10) | Duplicate pressure producer not justified |
| QA removed (D-06, D-07) | Not part of either model |
| Env cognition tiered (D-04R) | Supporting machinery under Narrator, not separate agent |

**Scribe need not be synchronous every turn** — post-commit, scene-boundary, complexity-triggered, advisory consumption.

**Multi-character scenes:** may require **multiple Character move cognitions** per round, not multiple “agents” in the architectural sense — still within primary RP layer.

---

## 23. Simple vs complex turn topology

### Simple beat (knock, look, short line, single clear actor)

**Always:** Continuity, PVR triage/uniform path, Director if needed, Character OR Narrator endpoint, deterministic validation, audit.  
**Default OFF:** ST preamble, post-commit ST, Director QA, Narrator QA, env cognition, orientation, librarian mediation, plot epistemic eval, decomposition if uniform-eligible.

### Complex beat (multi-actor, private agendas, retrieval-heavy, unresolved pressures, state-changing)

**Add conditionally:** Plot update/resume, orientation, retrieval mediation (possibly LLM), env obligation resolution, character semantic eval, narrow semantic repair on failure.

**No exact thresholds stated** — redesign validation must calibrate.

---

## 24. Massive-knowledge scalability

**Requirement:** novels, lore, histories, entities, relationships, locations, private knowledge, selective retrieval.

**Path:** **sophisticated deterministic/retrieval infrastructure + small cognitive topology** — not feeding everything to one model (A0 failure) and not LLM-mediate-everything (A4 failure).

- Index + query + entitlement filter + projection templates  
- LLM sees **bounded, pre-selected** context packages  
- Narrative planner maintains **compressed** pressure/goals overlay, not full lore in prompt

---

## 25. Protected-capability challenge

| Capability | Preserved by |
|------------|--------------|
| Independent Character agency | `character_move` + commit |
| Multiple NPCs | Director + per-character turns |
| Private knowledge | PVR + entitlement + Continuity |
| Perceptual separation | Perception filter + PVR |
| Closed doors / secrets | Scenario authority + projection |
| Persistent object state | Continuity commits |
| Delayed consequences | Plot overlay + durable Continuity |
| Unresolved conflict | Plot pressures |
| Long sessions | Continuity + retrieval not full-context |
| Character drift | Persistent character cards + move validation |
| Lore retrieval | Retrieval plane |
| Environmental grounding | Conditional env resolution + Narrator contract |
| Player authorship | Deterministic authorship rules + repair |
| Malformed output | Structural validation + contract correction (consolidated) |
| Hallucinated state | Host validators + semantic eval on move (retained) |
| Audit reconstruction | Execution evidence + Continuity audit |

**Gap requiring validation:** optimal **spatial/scenario** checker caught Sample E — proposed as **deterministic** addition, not Narrator QA.

---

## 26. Component disposition matrix

| Component | Value demonstrated | Evidence | Disposition | Destination in candidate | Confidence |
|-----------|-------------------|----------|-------------|--------------------------|------------|
| Continuity / Host kernel | High | Architecture, #200 | **Deterministic** | Substrate | High |
| PVR triage/uniform | High | #121, #197 | **Retain** | Substrate | High |
| Player decomposition | Conditional | #194 waste cases | **Conditional** | Tier on simple beat | Medium |
| Director turn | High | Core path | **Retain** | Primary RP | High |
| Director semantic QA | Low marginal | D-06 | **Do not rebuild** | Deterministic Director policy | High |
| Character move | High | Core | **Retain** | Primary RP | High |
| Character semantic eval | High correctness | #193, #200 | **Retain function** | Validation/repair | High |
| Character orientation | Mixed | D-03 | **Conditional** | Complex beat only | Medium |
| Librarian mediation | Partial | Cost, D-03 | **Rebuild simplified** | Retrieval-triggered | Medium |
| Plot init/update | High | Stage-3, D-10 | **Retain function** | Scribe/Plot lane | High |
| Plot epistemic eval / advisory gen | Low | Coverage audit | **Do not rebuild** default | Cut or fold | Medium |
| ST preamble | Low | D-01-L | **Do not rebuild** | Remove | High |
| ST post-commit pressure | Low RP | D-10 | **Do not rebuild** | Plot/Continuity | High |
| Narrator presentation | High | Core | **Retain** | Primary RP | High |
| Narrator env cognition | Mixed | D-04R | **Conditional** | Obligation-triggered | Medium |
| Narrator semantic QA | Low | D-07 | **Do not rebuild** always-on | Deterministic + repair | High |
| Opening / segmentation | Low decision | Coverage | **Conditional** | Init only | Low |
| Contract-correction kinds | Low | Audit | **Consolidate** | Shared retry | Medium |

---

## 27. Historical architecture debt

**Pattern:** Each failure mode added an LLM layer — semantic QA after QA failures, Storyteller after drift, Plot after Scribe intent, mediation after knowledge gaps, env cognition after grounding bugs, contract correction after parse failures.

**Test:** With today’s Continuity, PVR, Host authority, and Plot overlay, **many would be solved deterministically or conditionally**, not by another always-on inference.

---

## 28. Evidence gaps / uncertainty

- Character orientation: when exactly required vs redundant  
- Librarian mediation: deterministic replacement ceiling  
- Plot supporting chain simplification without pressure loss  
- Env cognition: exact trigger design  
- Character semantic eval: fold into move contract vs separate call  
- Multi-character rounds: optimal Director+Character call pattern  
- Contract-correction consolidation behavior under redesign  

**None block first-principles direction.**

---

## 29. Recommended redesign direction

**Adopt A2:** Primary RP cognition (Character, Narrator, Director) + Plot/Scribe persistent narrative cognition + deterministic Continuity/PVR/retrieval/validation substrate.

**Remove from default synchronous path:** ST preamble, post-commit ST LLM, Director QA, Narrator QA, always-on env cognition, default librarian LLM mediation, plot epistemic eval chain.

**Validate before build:** tier triggers, spatial/scenario deterministic checks, retrieval-only paths, post-commit Plot scheduling.

---

## 30. What we would deliberately rebuild

1. Continuity authoritative substrate  
2. PVR + perceptual visibility + entitlement  
3. Character structured move + commit gate  
4. Narrator presentation  
5. Director turn selection  
6. Plot persistent overlay (init/update)  
7. Execution evidence / audit  
8. Retrieval/indexing infrastructure (expanded)  
9. Deterministic validation suite (expanded)  
10. Failure-triggered semantic repair (narrow)

---

## 31. What we would not rebuild

1. Synchronous Storyteller preamble (orientation + assessment) every turn  
2. Post-commit Storyteller issue-pressure LLM (`storyteller_post_commit_issue_pressure`)  
3. Always-on `director_semantic_qa`  
4. Always-on `narrator_semantic_qa`  
5. Always-on `narrator_environment_cognition`  
6. Default always-on `librarian_mediation` on every KAR lane  
7. Plot epistemic eval + character advisory generation as default sync chain  
8. Per-kind contract-correction LLM rows as architecture  
9. A4 as the **default** turn topology for simple beats  

---

## 32. What redesign validation must prove

1. **Simple-beat path** meets latency budget without quality regression (knock, mess-hall opener class).  
2. **Complex-beat path** preserves Arkham-scale multi-actor quality (Plot + conditional orientation/retrieval).  
3. **Spatial/scenario deterministic checks** catch Sample-E-class defects without Narrator QA.  
4. **Plot-only narrative pressure** suffices after post-commit ST removal (longitudinal).  
5. **Tiered env cognition** matches obligation rate (reduce 44% no-obligation calls).  
6. **Retrieval-first Librarian** matches mediation quality on lore-heavy scenarios.  
7. **Character semantic eval** still blocks #200-class leaks if topology changes.  
8. **No blind regression** vs D-07 ablated arm on matched scenarios.

---

## 33. Proposed next governance phase

| Phase | Action |
|-------|--------|
| **G1** | Governance + user **accept/reject** this synthesis (no implementation) |
| **G2** | Authorize **redesign specification** Issue(s) — topology doc, tier rules, migration boundaries — still not production mutation |
| **G3** | **Prototype / shadow** simple-beat path on F06 + Arkham fixtures |
| **G4** | Longitudinal validation of Plot-only pressure vs removed post-commit ST |
| **G5** | Transition #201 from `investigating` to `validated` or split into implementation-track Issues |

**Do not:** close #201, implement removals, or create remediation Issues without G1 acceptance.

---

## Governance decisions required

1. **Accept** this Package D final synthesis as the authoritative #201 architectural assessment.  
2. **Confirm** adjudications: Narrator QA, Director QA, ST preamble, post-commit ST → remove/consolidate; Plot → retain function; env cognition → tier.  
3. **Accept** recommended target **A2** (or direct Governance to alternate A1/A3).  
4. **Authorize** next phase: redesign specification only (G2), not implementation.  
5. **Decline** further Package D live experimentation.  
6. Keep #201 **`investigating`** until Governance accepts synthesis and sets transition (G1).

---

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**

**No production mutation. No implementation Issues created.**
