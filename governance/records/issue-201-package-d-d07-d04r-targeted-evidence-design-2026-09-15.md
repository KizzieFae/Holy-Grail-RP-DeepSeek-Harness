# Issue #201 — Final Targeted Evidence Design & Narrator Environment Utilization Report

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**Bootstrap profile:** Full  
**Status:** D-07 design for Governance review — **execution NOT authorized**; D-04R read-only analysis **complete**

**Evidence anchors:**

| Anchor | SHA / path |
|--------|------------|
| Runtime LLM coverage audit (accepted) | `5ad7129` — `governance/records/issue-201-runtime-llm-call-coverage-audit-2026-09-15.md` |
| D-10 primary decode | `64dff5f` |
| D-06 / EXP-2 (Director QA) | Stage-2 synthesis |
| D-01-L decode | `5d15936` |
| D-10 execution evidence | `data/investigation_runs/issue201-package-d-d10-2026-09-15T01-20-29-181Z/` |
| D0 baseline | `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/` |
| #194 env cognition (F06) | `governance/records/issue-194-investigation-2026-09-14.md` |
| Control substrate | `c751ea6` |

---

## 1. Activation / state / weights

| Field | Value |
|-------|-------|
| Issue | OPEN / `investigating` |
| Project #10 | In Progress / Investigating / **P1** |
| Runtime LLM coverage audit | **Accepted** (`5ad7129`) |
| Production inference kinds | **26** |
| Directly causally challenged by #201 | **7** |
| Synthesis-critical uncovered (pre-gate) | **2** (`narrator_semantic_qa`, `narrator_environment_cognition`) |
| Final synthesis | **Paused** — do not begin until D-07 completes or Governance explicitly waives |
| Production remediation | **NOT authorized** |
| Governance recommendation accepted | **B** — small targeted evidence gap |
| D-07 | **Design complete** — live execution **NOT authorized** |
| D-04R | **Complete** (read-only, existing evidence) |

---

## 2. D-07 exact causal question

### Primary

> **Does a separate Narrator semantic-QA LLM call materially improve player-visible RP quality or prevent meaningful correctness failures compared with Narrator output without that QA call?**

### Secondary

> **When Narrator semantic QA intervenes, does it actually cause a better final presentation?**

Architectural framing (not to be decided before scoring):

> Does Holy Grail need separate LLM cognition whose primary job is to semantically double-check another principal LLM's output — specifically on the Narrator presentation path, symmetric to the Director QA case already challenged in D-06?

**Required causal trace (per turn, where evidence permits):**

```text
Narrator candidate
  → deterministic presentation validation
  → semantic QA (control arm only)
  → accept / reject / correction decision
  → any retry / repair / fallback
  → final visible presentation
```

---

## 3. D-07 intervention / hook feasibility and blast radius

### Hook located and verified

| Item | Detail |
|------|--------|
| **Flag** | `roundOptions.narratorSemanticQaEnabled` |
| **Default** | `true` (`options.narratorSemanticQaEnabled !== false`) |
| **Orchestrator wiring** | `v2/rp_runtime/src/plugins/hg-round-orchestrator/service.mjs` L615 |
| **Phase gate** | `v2/rp_runtime/src/plugins/hg-phase-executors/narrator-phase.mjs` L555–577 — when `false`, accepts presentation immediately after deterministic validation passes |
| **Precedent** | Mirror of `directorSemanticQaEnabled: false` (EXP-2 / D-06) |
| **Test coverage** | `narrator-semantic-qa-orchestration.test.mjs` (enabled/disabled paths); `narrator-semantic-qa-live.test.mjs`; `narrator-last-attempt-summary.test.mjs` |

### Blast radius (narrow)

| Subsystem | Control arm | Ablated arm | Changed? |
|-----------|-------------|-------------|----------|
| `narrator_environment_cognition` | runs | runs | **No** |
| `narrator_presentation` | runs | runs | **No** |
| Deterministic presentation validation / fidelity retry | runs | runs | **No** |
| `librarian_mediation` (narrator-lane) | runs when env cognition triggers | same | **No** |
| Plot cognition | runs | runs | **No** |
| Character orientation / move / semantic eval | runs | runs | **No** |
| Director decision | runs | runs | **No** |
| PVR / player decomposition | runs | runs | **No** |
| `narrator_semantic_qa` inference | **runs** | **skipped** | **Yes — intended** |
| QA-driven regen / soft-hard reject / player-authorship repair gate | active | **bypassed** | **Yes — intended** |
| QA infra-fail → terminal fallback path | active | **bypassed** | **Yes — intended** |

**Not changed:** env cognition, presentation generation, structural contracts, Host B2 authority, normal narrator fidelity retries **except** those caused specifically by semantic QA policy.

### Verdict

**Proceed — existing production hook is sufficiently isolated.** No production code change required for D-07 execution. Harness-only alias `skipNarratorSemanticQa` (documentation mapping to `narratorSemanticQaEnabled: false`) optional; not implemented.

**If hook semantics change at execution time** (e.g., QA bypass no longer skips only `narrator_semantic_qa`): **STOP** and report blast-radius drift.

---

## 4. Proposed experimental topology

### Rationale for baseline selection

Reuse the **post-D-01-L / post-D-10 lean characterized stack** rather than full A4 incumbent:

- ST preamble already causally weak (D-01-L) — re-enabling adds cost and confound.
- Post-commit ST already remove/consolidate candidate (D-10) — retaining it adds overlay noise unrelated to Narrator QA.
- Director QA already remove/consolidate candidate (D-06) — retaining it leaves asymmetric LLM-checks-LLM topology on the Director arm.

This isolates the **remaining symmetric semantic-QA case** (Narrator) without re-litigating settled layers.

### Topology table (both arms unless noted)

| Layer | Setting | Rationale |
|-------|---------|-----------|
| Storyteller preamble | **OFF** (`skipStorytellerCognition: true`) | D-01-L verdict; avoids preamble confound |
| Storyteller post-commit issue-pressure | **OFF** (`skipLibrarianProposalGeneration: true`) | D-10 ablated topology; avoids duplicate narrative-pressure producer |
| Plot cognition | **ON** | Stage-3 retain; persistent narrative cognition retained |
| Director QA | **OFF** (`directorSemanticQaEnabled: false`) | D-06 verdict; symmetric QA test focuses on Narrator only |
| Character orientation | **ON** (default) | Not under test; preserves multi-character stress |
| Narrator environment cognition | **ON** | Preserved — not ablated in D-07 |
| Narrator semantic QA | **ON (control) / OFF (ablated)** | **Only intended causal difference** |
| Librarian mediation | **Normal** (orientation + narrator-env lanes when triggered) | Not bypassed — high blast radius if removed |
| PVR / deterministic validation | **Normal** | Required correctness substrate |

### Arms

```javascript
// Control
{
  skipStorytellerCognition: true,
  skipLibrarianProposalGeneration: true,
  directorSemanticQaEnabled: false,
  narratorSemanticQaEnabled: true,  // default — may omit
}

// Ablated
{
  skipStorytellerCognition: true,
  skipLibrarianProposalGeneration: true,
  directorSemanticQaEnabled: false,
  narratorSemanticQaEnabled: false,
}
```

### Governance amendment option (not recommended default)

**D-10-control-equivalent baseline** (post-commit ST **ON** on both arms): use only if Governance requires "production-like except preamble." Adds ~16 post-commit inferences per 14-turn equivalent and reintroduces pressure-overlay confound. **Not recommended** for the Narrator-QA architectural question.

---

## 5. Proposed scenarios / sample

### Default tranche (Governance-proposed minimum)

| Scenario | Role | Control reps | Ablated reps | Turns / rep | Total runs |
|----------|------|-------------:|-------------:|------------:|-----------:|
| Arkham mess hall stress (primary) | Multi-character institutional stress | 2 | 2 | **1** | 4 |
| Ayame household entry (contrast) | Constrained domestic / threshold | 2 | 2 | **1** | 4 |
| **Total** | | | | | **8** |

**Player policies:** Reuse frozen D0 opener stimuli and character assignments (same as EXP-2 / D0):

- Arkham: `mess_hall_magpie` opener + Magpie watch/murmur stimulus
- Ayame: F06 knock + house-number check stimulus

**Determinism:** Fixed scenario IDs, role assignments, opener preferences, and player posts — no predicate branching required for single-turn design.

### Why single-turn (not longitudinal)

| Factor | Implication |
|--------|-------------|
| D-06 precedent | EXP-2 used 1 turn / run; blind causal gate proven |
| Intervention rarity in short samples | D0 + Stage-2: **28/28** narrator QA outcomes = `pass` (0 regen) |
| D-10 longitudinal supplement | Control archive: **9/64** non-pass QA interventions — use for §8 forensics without extra live cost |
| Cost | 8 runs ≈ EXP-2 scale; 5-turn replication would ~4× Arkham cost |

### Intervention-forensics supplement (authorized read-only)

Mine **D-10 control-arm** execution evidence (`64` narrator presentations) for QA intervention-value analysis (§8). Does not replace D-07 causal ablation.

### Prospective expansion triggers (max +1 rep / scenario / arm)

1. Contradictory blind outcomes between replications (Arkham or Ayame)
2. Intervention-specific correctness failure pattern on ablated arm
3. Generic runtime contamination (character_failure) without replacement success
4. Hook blast-radius drift at preflight

**Do not expand** into per-contract-correction ablations, env-cognition live ablation, or 26-call matrix.

---

## 6. Objective correctness endpoints

Score **before** blind semantic evaluation. Separate **objective correctness** from **subjective RP quality**.

### Automated harness checks (per run)

| Check | Source / method |
|-------|-----------------|
| Round commit success | `submitUserTurn` terminal state |
| PVR validation status | Harness report (`validation_status`) |
| Knowledge / perception boundary | Existing D0 harness checks; flag invalid PVR |
| Unsupported environmental invention | Host B2 authority outcome vs presentation claims (where indexed) |
| Contradiction of committed Character move | Structured move vs presentation (director-selected character lane) |
| Scenario-authority violations | Opening / scenario contract flags |
| Impossible spatial claims | Forensic flags from narrator fidelity validation class |
| Unauthorized state mutation | No abort / no continuity write errors |
| Missing required presentation | `presentation_rendered` / empty presentation guard |
| Deterministic narrator contract failures | `validation_class` ≠ accepted; fidelity retry exhausted |
| Player-authorship violations | QA `player_authorship_fail_closed` on control; ablated arm must not **increase** authorship defects |

### Per-turn forensic fields (non-blind sidecar)

- `validation_class`, `validation_reason`
- `semantic_qa.policy_action` (control)
- `retry_decision`, `attempt_index`
- `rejected_presentation_text` vs final `presentation_text`
- `environment_cognition` summary (unchanged between arms)

### Correctness verdict rules (per run)

| Outcome | Rule |
|---------|------|
| **Clean** | Committed + no objective check failures |
| **Degraded non-blocking** | Committed with soft fidelity flags but visible presentation |
| **Blocking failure** | No commit OR hard contract failure with material player-visible defect |

**Blind rubric must not substitute for this layer.**

---

## 7. Blind semantic rubric

### Primary endpoint

**Reuse Stage-2 / D0 per-turn 11-dimension rubric** (`issue201-stage2-human-evaluator-worksheet.md`) — proven for Package D single-turn causal comparisons.

| # | Dimension | Maps to user-requested judges |
|---|-----------|------------------------------|
| 1 | Character fidelity | coherence (partial) |
| 2 | Distinctiveness | naturalness (partial) |
| 3 | Initiative | scene progression |
| 4 | Responsiveness | responsiveness |
| 5 | Dramatic progression | scene progression |
| 6 | Coherence | coherence |
| 7 | Prose quality | prose quality |
| 8 | Repetitiveness (5=low) | repetition/stiffness |
| 9 | Stiffness (5=natural) | naturalness |
| 10 | Unnecessary exposition (5=lean) | unsupported invention (proxy) |
| 11 | Emotional/narrative continuity | continuity |

### Narrator-specific adjunct (optional Governance overlay)

If Governance requires explicit Narrator-QA dimensions, add **two** sequence-agnostic per-sample fields (do not replace the 11):

| Adjunct | Scale |
|---------|-------|
| **Environmental grounding** | 1–5 |
| **Overall RP usefulness** | 1–5 |

**Evaluation unit:** one player-visible presentation per run (8 samples).  
**Packet schema:** `issue201_blind_eval_packet_v1` (same family as D0 / Stage-2).  
**Answer key:** concealed until Governance locks scores (`issue201-d07-blind-eval-answer-key.json`).

---

## 8. QA intervention-value capture plan

### On control arm (new D-07 runs + D-10 archive)

| # | Field |
|---|-------|
| 1 | QA call count |
| 2 | QA accept count (`pass`, `accept_with_residuals`) |
| 3 | QA reject count (`hard_regen`, `soft_regen`, `player_authorship_fail_closed`) |
| 4 | QA correction/retry count (narrator regen attempts triggered by QA) |
| 5 | Reason/category (`policy_action`, findings[]) |
| 6 | Pre-QA narrator candidate (`candidate_presentation_text` / `rejected_presentation_text`) |
| 7 | Post-QA / final presentation |
| 8 | Objective defect corrected? (manual adjudication against §6) |
| 9 | Subjective quality issue corrected? (optional bounded review of paired texts — **not** blind RP score) |
| 10 | Degradation introduced? (final worse than pre-QA on objective checks) |
| 11 | Added inference / token / wall cost per QA event |

**Key metric:** `consequential_benefit_rate` = interventions where final output is objectively or blind-better vs counterfactual pre-QA text / ablated arm matched turn.

### Existing forensic baseline (D-10 control archive)

| Metric | D0 + Stage-2 (28 pres.) | D-10 control (64 pres.) |
|--------|--------------------------:|------------------------:|
| QA invocations | 28 | 64 |
| `pass` | 28 (100%) | 54 (84.4%) |
| `soft_regen` | 0 | 5 |
| `hard_regen` | 0 | 3 |
| `accept_with_residuals` | 0 | 1 |
| `player_authorship_fail_closed` | 0 | 1 |
| **Non-pass interventions** | **0** | **9 (14.1%)** |

**Interpretation:** Single-turn samples under-power intervention observation; D-10 archive is **required** for secondary architectural question unless D-07 adopts multi-turn replication.

---

## 9. Prospective D-07 classification rules

Define **before execution**; do not pre-select outcome.

### Separate QA justified

Requires **all**:

- Ablated arm shows **≥1** objective correctness regression vs control **or**
- Blind overall mean Δ ≥ **0.20** favoring control **with** scenario-consistent direction (both Arkham reps or explicit Governance adjudication) **and**
- ≥1 control intervention demonstrably corrected objective defect **or** blind-visible quality defect

### Function necessary, topology unresolved

- Control interventions catch **≥2** meaningful issues (objective or bounded text review) across pooled control evidence **but**
- Ablated blind quality within **Δ ≤ 0.15** and no systematic objective regression  
→ semantic checking may be necessary; separate always-on call not proven.

### Remove / consolidate

- Objective correctness matched (no systematic ablated regression)
- Blind overall Δ ≤ **0.15** (negligible band per D-01-L / D-10 precedent)
- QA intervention rate **< 5%** **or** interventions lack demonstrated consequential benefit (benefit rate < 50% on adjudicated sample)
- Analogous to D-06 Director QA disposition

### Inconclusive

- Contradictory replication (control better on one Arkham rep, ablated on other, no objective anchor)
- Zero QA interventions on control **and** no D-10 archive supplement used
- Hook blast-radius drift
- Generic runtime contamination > 25% runs requiring replacement

**Between-arm comparison required** — control quality in isolation is not sufficient.

---

## 10. D-07 confounds and stop conditions

| Confound | Mitigation |
|----------|------------|
| Director QA asymmetry | **OFF on both arms** (D-06 settled) |
| ST preamble / post-commit noise | **OFF on both arms** (D-01-L / D-10) |
| Librarian mediation fan-out variance | Pair by scenario; report fan-out; do not blind-score |
| Character semantic-eval hard reject | Exclude contaminated runs; classify per Stage-2 forensic rules |
| Path fan-out / latency noise | Report separately; not blind endpoint |
| Single-turn under-sampling QA interventions | D-10 archive supplement mandatory for §8 |
| Player-authorship repair only on control | Compare objective authorship checks on both arms |

### Stop conditions (do not continue tranche)

1. `narratorSemanticQaEnabled: false` suppresses more than `narrator_semantic_qa` (preflight regression failure)
2. **≥2** ablated-arm objective correctness failures with shared pattern plausibly QA-preventable **and** control arm clean → early signal (report, await Governance)
3. Intervention-specific infrastructure failure pattern on control only

---

## 11. D-04R evidence corpus

Read-only analysis — **no new live RP**.

| Source | Use |
|--------|-----|
| **D0** (`issue201-d0-baseline-2026-09-14.md` + evidence root) | Per-run env/QA timing; contractual baseline |
| **Stage 2** (EXP-1..3 tranche) | Env invocation density across variants; QA pass-heavy |
| **D-01-L** | Longitudinal topology context (env cognition on both arms) |
| **D-10** execution | Largest narrator presentation + QA intervention sample |
| **#194** F06 session | Canonical disproportionate-cost case (55.7s / 11.5k reasoning tokens) |
| **#49** forensic record | Env cognition architecture, B2 authority, consumption contract |
| **#136** prompt corpus | Obligation/resolution schema |
| **#151 / #131** (historical) | Sufficiency gate; projection dedup did not remove F06 cost |
| **Runtime traces** | Pooled execution-evidence index parse (D0 + Stage-2 + D-10) |

---

## 12. Environment-cognition invocation / utilization findings

### Pooled invocation statistics (execution evidence)

| Corpus | Sessions / turns | Env invocations | Invocations / narrator turn | `baseline_sufficient: true` |
|--------|-----------------:|----------------:|----------------------------:|------------------------------:|
| D0 | 4 runs | 9 | ~2.25 | 4 / 9 (44%) |
| Stage-2 | 15 narrator turns | 34 | ~2.27 | 12 / 34 (35%) |
| D-10 | 32 narrator turns | 66 | ~2.06 | 32 / 66 (48%) |
| **Pooled** | **51 turns** | **109** | **~2.13** | **48 / 109 (44%)** |

**Pattern:** Env cognition fires **multiple times per narrator turn** (~2.1×) when active — consistent with retry / multi-resolution loops, not a single-shot gate.

### Resolution output shape (pooled)

| Metric | Value |
|--------|------:|
| Invocations with `resolutions[]` | 61 / 109 (56%) |
| Mean resolutions when non-empty | ~3.0 |
| `baseline_sufficient` without resolutions | 48 |

**Finding:** Nearly half of invocations declare existing context **sufficient** — the call ran but declared **no unique obligation** in output.

---

## 13. Environment obligation classifications

Classification applied to pooled env-cognition outputs (where JSON parseable). Categories per Governance brief:

| Class | Definition | Pooled count | Share |
|-------|------------|-------------:|------:|
| **High-value obligation** | Non-baseline; resolutions include correctness-critical env facts (B2 / contradiction avoidance) | 21 | 19% |
| **Useful enrichment** | Non-baseline; ≥3 resolutions or multi-fact grounding without proven correctness criticality | 40 | 37% |
| **Low-value / simple beat** | Non-baseline; 1–2 resolutions on low-complexity turns (inferred) | 0 | 0% |
| **No demonstrated obligation** | `baseline_sufficient: true` or no resolutions | 48 | 44% |

### Scenario contrast

| Scenario | Env invocations (D0) | Wall-time signal (D0 report) | #194 F06 |
|----------|---------------------:|-----------------------------:|---------|
| Arkham | 3 + 3 per run | 42–73s summed per run | — |
| Ayame | 1 + 2 per run | 3–27s summed per run | **55.7s single call** |

**Ayame paradox:** Simple opening turn can still trigger **disproportionate** env cognition cost (#194) while pooled corpus shows **high `baseline_sufficient` rate** on later turns — complexity-insensitive triggering is plausible; **not causally proven** without ablation.

---

## 14. Environment downstream-consumption findings

### Trace model

```text
narrator_environment_cognition
  → resolutions / B2 proposals
  → librarian_mediation (when obligated)
  → narrator manifest lanes
  → narrator_presentation
  → player-visible text
```

### Evidence-backed consumption checks

| Question | Finding |
|----------|---------|
| Supplies information unavailable elsewhere? | **Sometimes** — B2 `house_number` on F06 not in player text alone (#194) |
| Narrator actually uses it? | **Partial** — F06 presentation adds `"brass"` beyond env output; D0 Ayame knock reflected in door/entry prose |
| Prevented known failure? | **Not demonstrated** in pooled #201 evidence (no A/B without env cognition) |
| Deterministic retrieval/projection sufficient? | **Plausible for subset** — `baseline_sufficient` 44%; Host `EnvironmentalCurrentView` projection exists (#49) |
| LLM needed to reason? | **Unresolved** — F06 shows heavy reasoning for narrow need; many invocations may be replaceable by projection + retrieval |
| Simple turn unnecessary? | **Supported observational** for F06 + high `baseline_sufficient` rate; not causal |

### D0 consumption spot-check

- 4/4 narrator turns with env cognition linked `environment_cognition` evidence on `narrator_presentation` decision patch
- 1/4 shows explicit house-number / entrance lexical overlap between env output and presentation (Ayame-class)

**Do not infer consumption from invocation alone** — linkage proves orchestration attachment, not unique semantic necessity.

---

## 15. Environment cost evidence

### Wall-time (D0 report — authoritative for #201 live path)

| Run | Env count | Env wall (ms, summed) | QA count | QA wall (ms) |
|-----|----------:|----------------------:|---------:|-------------:|
| arkham-r1 | 3 | 73,287 | 2 | 3,238 |
| arkham-r2 | 3 | 42,216 | 2 | 3,101 |
| ayame-r1 | 1 | 3,116 | 1 | 1,233 |
| ayame-r2 | 2 | 26,883 | 1 | 1,282 |

### #194 F06 (single indexed call)

| Metric | Value |
|--------|------:|
| Wall | 55,728 ms |
| Reasoning tokens | 11,454 |
| Total tokens | 24,841 |
| Post-commit narrator lane | 78,156 ms (env ≈ 71% of lane) |

### Proportionate critical-path role

- Binds **post-commit narrator lane** on env-heavy turns (#194 proven for F06)
- **Not** a reliable fraction across pooled #201 turns — Arkham D0 42–73s vs Ayame 3–27s shows high variance
- **Do not manufacture** causal latency savings from observational timing alone

### Skip-hook audit

**No production `skipNarratorEnvironmentCognition` hook found.** Live env ablation would require new hook — **not proposed or authorized** under Recommendation B.

---

## 16. Environment tiering conclusion

| Tiering hypothesis | Evidence status |
|--------------------|-----------------|
| Always-on | **Unproven and expensive** — 44% no-demonstrated-obligation invocations; F06 disproportionate cost |
| Complexity-triggered | **Plausible, not proven** — F06 vs pooled `baseline_sufficient` pattern |
| Missing-detail-triggered | **Plausible** — aligns with B2 house-number case |
| Retrieval-triggered | **Plausible** — Host projection + librarian mediation exist (#49) |
| Scene-boundary only | **Insufficient evidence** |
| Conditional repair | **Insufficient evidence** |
| Folded into narrator presentation | **Mechanism unresolved** |
| Remove entirely | **Not supported** — 19% high-value obligation + #49 correctness architecture |

**Governance-safe statement:**

> Always-on env cognition is **unproven as cost-efficient** and **frequently reports baseline sufficient**, but the function is **not disproven** — tiering remains **qualified uncertainty** carryable into synthesis. **No gating rule should be claimed** without causal ablation (optional future work; not part of Recommendation B).

---

## 17. Updated 26-kind coverage status

### `narrator_semantic_qa`

| Field | Status |
|-------|--------|
| Pre-gate | UNCOVERED — synthesis-critical |
| Post-D-04R | **Unchanged** — awaits D-07 causal ablation |
| Disposition | Pending D-07 |

### `narrator_environment_cognition`

| Field | Updated status |
|-------|----------------|
| Pre-gate | UNCOVERED — synthesis-critical |
| Post-D-04R | **UNCOVERED — synthesis-critical (cost/tiering refined)** |
| Evidence added | Obligation mix (44% no demonstrated obligation); pooled 109 invocations; F06 disproportionate cost reaffirmed; consumption partially traced |
| Disposition | **Function necessary / mechanism unresolved (tiering candidate)** — stronger than "unknown," weaker than causal retain/remove |
| Live ablation required for synthesis? | **Optional** — synthesis may proceed with qualified tiering uncertainty if D-07 completes |

### Coverage matrix delta

Only `narrator_environment_cognition` narrative classification refined; counts unchanged:

| Bucket | Count |
|--------|------:|
| COVERED — retain | 6 |
| COVERED — remove/consolidate | 4 |
| COVERED — function necessary, mechanism unresolved | 6 (+ refined env cognition write-up) |
| UNCOVERED — low decision value | 8 |
| UNCOVERED — synthesis-critical | **1 pending D-07** (`narrator_semantic_qa`); env cognition synthesis-critical for **tiering** not removal |
| INAPPLICABLE | 2 |

---

## 18. Additional synthesis-critical unknowns (besides Narrator QA)

| Unknown | Blocks synthesis? | Notes |
|---------|-------------------|-------|
| **`narrator_semantic_qa` marginal value** | **Yes — primary gate** | D-07 proposed |
| **Env cognition tiering / always-on** | **Partial** | D-04R narrows; causal ablation optional |
| Librarian mediation fan-out | No | Unlikely to flip A0/A4 alone |
| Character orientation topology | No | D-03 conditional retain |
| Character semantic-eval vs stronger contract | No | Correctness retain |
| Plot epistemic / advisory chain | No | Low decision value per audit |
| Per-contract-correction kinds | No | Bundled low value |

**Answer:** **One** causal synthesis-critical gap remains for the **LLM-checks-LLM QA topology** (`narrator_semantic_qa`). Env cognition is synthesis-critical for **cost architecture** but D-04R supplies sufficient read-only characterization to carry qualified uncertainty if Governance accepts.

---

## 19. Durable record / commit / Issue comment

| Artifact | Path |
|----------|------|
| This report | `governance/records/issue-201-package-d-d07-d04r-targeted-evidence-design-2026-09-15.md` |
| Proposed harness (future) | `v2/rp_runtime/scripts/issue201-package-d-d07-narrator-qa.mjs` (not created) |
| Coverage audit (prior) | `governance/records/issue-201-runtime-llm-call-coverage-audit-2026-09-15.md` |

**Synthesis status:** **Still paused.**  
**D-07 execution:** **NOT authorized.**

---

## 20. Exact Governance decisions required

1. **Accept D-04R** read-only environment-cognition utilization analysis as Package D evidence.
2. **Review / challenge / agree** D-07 experimental design:
   - Hook: `narratorSemanticQaEnabled: false`
   - Topology: lean post-D-01-L / post-D-10 stack (§4)
   - Sample: 8 single-turn runs (2×2 per scenario)
   - Endpoints: §6 objective + §7 blind rubric
   - Classification rules: §9
3. **Authorize or amend** D-07 live execution (separate step from design acceptance).
4. **Decline or defer** live env-cognition ablation (no hook exists; not recommended).
5. **Confirm** final synthesis remains deferred until D-07 decode **or** explicit Governance waiver of Narrator QA causal gap.
6. Keep #201 **`investigating`** — In Progress / Investigating / **P1**.

**Do not execute D-07 in this step.**

---

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
