## Summary

Institutional **deferred-signals / watchlist** for **Phase 0** simulation observations that are **architecturally interesting** but **below recurrence/severity thresholds** for standalone lifecycle issues. This issue **preserves** weak-signal findings from **#189** synthesis (sessions **678–688**) as a **recurrence reference** and **promotion trigger registry**. It is **not** a miscellaneous backlog, **not** a substitute for properly scoped work, and **does not** assert that every listed item is a product defect.

Parent context: **#176** (Phase 0 stabilization), **#184** (umbrella). **Director / attribution umbrella** [**#206**](https://github.com/KizzieFae/Holy_Grail_RP/issues/206) is **validated** and absorbed the standalone orchestration/director hygiene lane (child deliveries **#207**, **#210** C‑A, **#208**). **Residual items** tied to that lane appear below as **watchlist-tier readability/UX triggers** (not proof of reopened architecture instability). Still out of scope here: broad **continuity substrate corruption** (not reproduced in #189), **#188**.

## Type

`quality`

## Layer

`audit_simulation`

## Pattern status

`potential_pattern`

## Current status

`open`

## Evidence (mandatory)

- **Scenario ids:** Multiple Phase 0 audited scenarios under **#189** wide / stress classification (see **#189** synthesis comment); corpus **sessions `678`–`688`** (repo-relative audit roots: `autogen_rp/python/rp_app/data/rp_audits/session_<678–688>/`).
- **Audit session paths:** As above; specific exemplar sessions called out **per row** in the watchlist table.
- **Turn index:** `n/a` — issue-level registry; row-level pointers reference representative turns in linked audit JSON where applicable.

## Evidence (preferred)

Synthesis on **#189**: no committed **`continuity_state`** corruption pattern; **`has_bypass: false`** across **`678`–`688`** in observability extracts referenced there. Residual interest is **representation**, **prompt/accumulation hygiene**, **perception serialization**, **sparse presence metadata**, and **audit-vs-regression heuristic alignment** — not authoritative continuity truth errors.

## Expected behavior

Weak but **repeatable-looking** seams should have a **single low-noise home** with **explicit promotion rules**, so recurrence can be judged without **speculative child-issue sprawl**.

## Observed behavior

Clustered **non-blocking** observations from #189-class runs: occasional **serialization/presentation drift** in perception-related fields; **sparse `character_presence_status`** in some scenarios; **prompt/memory accumulation** pressure in long or multi-character runs; **audit interpretation heuristics** that can disagree with regression-style expectations without proving runtime bypass (**#189** evidence bundle).

## Deterministic reasoning

These items are recorded because they have **traceable audit anchors** and **layer ownership**, but **insufficient** cross-scenario recurrence or user impact to justify **independent** issues today. Promotion requires **thresholds** (below), not narrative alone.

## System impact

Primarily **operator interpretability** and **investigation efficiency** (when to open a **scoped** child issue). Not claimed as end-user outage.

## Constraints

- **Not** a dumping ground: new rows require **originating reference** + **layer** + **confidence class** + **threshold** + **promotion trigger**.
- **No** implied defect: rows are **observations** until promoted.
- **No** implementation work is authorized **from this issue alone**; promoted items spawn **separate** issues with normal **§D** evidence.
- **Orchestration/director seam** is **out of scope** for this watchlist (**reserved** for standalone filing).
- Do **not** reopen or broaden **#188** / **#189** from this registry without new evidence.

## Affected modules

Row-level. See **Architectural layer** column (perception, memory, prompt assembly, audit harness, grounding as applicable). Meta-registry: `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` (interpretation discipline); audit output under `autogen_rp/python/rp_app/data/rp_audits/`.

## Validation criteria

- **Promotion:** A child issue is justified when **any** row’s **Promotion trigger** fires; update row **Status** to **`promoted`** and link the **new issue** in a comment.
- **Retirement:** Move to **`retired`** when superseded by design, proven benign, or **explicitly** folded into another tracked issue (link).
- **Recurrence review:** On **major** audit methodology or **Phase 0** scenario batch reruns, comment with **pass/fail vs thresholds** for **`monitor`** rows (no code required).

## Documentation

- [ ] Documentation reviewed and updated where behavior or contracts changed (terminal closure only).

---

## Promotion and recurrence policy (governance)

**Confidence classes (per row)**

| Class | Meaning |
|-------|--------|
| **Observation** | Seen in trace; no stable signature yet. |
| **Possible pattern** | Two or more similar instances **or** one strong instance plus plausible code path. |
| **Confirmed pattern** | Same signature across **distinct** scenarios/sessions **or** explicit code/docs contradiction. |

**Default recurrence thresholds (any one can justify promotion)**

1. **Recurrence:** Same signature in **≥ 2** distinct audited sessions **or** **≥ 2** distinct scenario ids after #189 baseline.
2. **Severity / impact:** Material impact on **interpretability**, **safety-critical paths**, or **continuity authority** (with audit proof) — not mere noise.
3. **Deterministic proof:** Failing check, invariant break, or documented contract violation (**§E** `bug`/`design_gap` path).

**Promotion trigger (meta)**

File a **new** scoped issue when a row hits thresholds; **do not** expand this issue into implementation threads.

**Archival**

If no updates for **180 days** and all rows **`dormant`** or **`retired`**, owner may **`Current status: closed`** with pointer to **#176** / Phase 0 archive policy.

---

## Deferred observation inventory (seed from #189)

| ID | Observation (short) | Originating issue / corpus | Architectural layer | Current confidence | Recurrence threshold | Promotion trigger | Recommended future investigation type | Status |
|----|---------------------|----------------------------|------------------------|--------------------|----------------------|-------------------|----------------------------------------|--------|
| DS-01 | **Perception / audibility serialization drift** — serialized prompt/read-model slices occasionally misaligned with perception policy expectations in audit-facing paths. | **#189**; exemplar **`session_682`** (audit JSON under `rp_audits/session_682/`). | `perception` | Observation → **Possible pattern** (if second session matches) | Second distinct session with same field-level mismatch signature | User-visible leak OR **≥2** sessions with same drift signature | Targeted audit diff + perception gating review; then scoped issue if confirmed | **monitor** |
| DS-02 | **Sparse `character_presence_status`** — presence metadata thin/absent in some multi-character runs; complicates offline assertions. | **#189**; exemplar **`session_683`**. | `response_validation` / **`audit_simulation`** (instrumentation vs payload — split on repro) | Observation | Same sparsity pattern in **≥2** scenario families | Blocks regression heuristic or masks real presence bug | Trace field producer(s) + schema expectations; scoped issue with owner layer | **monitor** |
| DS-03 | **Prompt / accumulation hygiene** — long-run prompt sections show pressure (volume, duplication risk) without proving continuity corruption. | **#189**; exemplar **`session_680`**; long/multi-char stress family. | `memory` / `grounding` | Observation | **≥2** long sessions with same hygiene signature **or** measurable token budget issue | Operator-visible quality drop OR failing structured eval | Prompt assembly / merge caps review; separate issue per root cause | **dormant** |
| DS-04 | **Audit heuristic ambiguity** — classification or dashboard heuristics disagree with “green” regression-style expectations (false tension). | **#189**; exemplar sessions **`684`–`685`** (wide sweep). | `audit_simulation` | Observation | **≥2** sessions where same heuristic misfires | Mis-triage causing missed real defect OR sustained noise in ops | Heuristic calibration ticket or doc contract update | **monitor** |
| DS-05 | **Operational / cafeteria baseline variance** — low-amplitude variance in baseline 3-character operational scenarios; may be innocuous. | **#189**; **`session_688`** (operational baseline family). | `audit_simulation` **(metrics/artifact variance; not selection-path)** | Observation | Escalation only if same variance signature appears with **runtime** selection/eligibility failure evidence | Proven **next-actor** or eligibility bug **with audit trail** | If the failure is **orchestration/director seam**, open a **standalone** **`layer: orchestration`** issue — **not** an expansion of this row | **dormant** |



---

### Post-#206 umbrella — deferred UX signal (Director rationale wording / C-B disposition)

**Backlinks:** [**#206**](https://github.com/KizzieFae/Holy_Grail_RP/issues/206) (umbrella, `validated`), [**#207**](https://github.com/KizzieFae/Holy_Grail_RP/issues/207) (`director_model_reason`), [**#208**](https://github.com/KizzieFae/Holy_Grail_RP/issues/208) (episodic interpretation ladder), [**#210**](https://github.com/KizzieFae/Holy_Grail_RP/issues/210) (**C‑A** projection ownership; **C‑B deferred**).

**Observed:** In audited runs (see **#206** promotion thread; E-family sessions **690–693**), verbatim **`director_model_reason`** sometimes echoes **model-authored orchestration/policy tokens** (`low_pressure_turn_selection`, `action_responsibility`, …). This reflects **prompt/model phrasing**, not **`director_reason_projection`** corruption or semantic instability in merged **`reason`** post‑**C‑A**.

**Why `reason_segments[]` / #210 C‑B was not adopted:** Segments polish **merged operator `reason`**; they **do not remove** jargon the model writes into **`director_model_reason`**. Umbrella validation found **stable orchestration**, coherent attribution, and acceptable memory interpretation (**#208** ladder + tests) without **active** **`reason_segments[]`** work.

**Disposition:** **`reason_segments[]` / #210 C‑B** = **optional productization** — **no architectural mandate**. Do **not** reopen or broaden **#210** scope via this registry.

**Revisit / promotion triggers:** File a narrowly scoped ticket (**or** revisit **#210** C‑B only if warranted) when **any** holds: **(1)** sustained **audit skim cost** worsens materially vs post‑**C‑A** baseline, **(2)** **operator readability** regresses under **deterministic audit cites**, **(3)** **episodic quality** materially degrades because verbatim tier **systematically** carries policy jargon (**not** one-off stochastic runs). Prefer **prompt rubric**, **audit tooling**, episodic wording policy, **or** a minimal segments spike—smallest lever first.

---

### Post-#209 fold — session / audit trace UX (watchlist-only)

**Backlink:** [**#209**](https://github.com/KizzieFae/Holy_Grail_RP/issues/209) (**closed**) — folded into this registry; **not** active standalone roadmap.

**Concern preserved:** Reconstructing **`selector_decisions`** / operator-facing selector trace parity after **session load** vs persisted **`team_state.director_decisions`** payloads — **session-load / tooling UX**, not unresolved architecture fault.

**Evidence posture:** **[#206](https://github.com/KizzieFae/Holy_Grail_RP/issues/206)** broader validation (**E-family** / deterministic regressions) **did not** show **material usability pain** forcing active **#209** work.

**Revisit / promote triggers:** Only if **(1)** audit / session **navigation becomes difficult**, **(2)** **selector trace reconstruction** becomes **operationally expensive**, **(3)** **session replay / debugging degrades materially** (with **deterministic cites**). Prefer smallest **doc / tooling / UI** slice.

---


**Orchestration / director seam:** **Outside** this watchlist by charter. If selection/eligibility defects emerge, **open a dedicated issue** (likely **Layer `orchestration`**) per **§F**; do not attach them here.



---

### Post-#242 deferred watchpoints — prompt compression & runtime observation (DS-06)

**Backlinks:** [#242](https://github.com/KizzieFae/Holy_Grail_RP/issues/242) (`validated` — Waves 0–1–3–2 complete), [#240](https://github.com/KizzieFae/Holy_Grail_RP/issues/240) (topology validated), [#239](https://github.com/KizzieFae/Holy_Grail_RP/issues/239) (parent refinement).

**Disposition:** **Intentionally deferred** pending **real runtime evidence** — **not** unresolved bug, failed work, or dangling implementation debt.

| ID | Observation (short) | Layer | Confidence | Revisit / promotion trigger | Status |
|----|---------------------|-------|------------|----------------------------|--------|
| **DS-06** | **Wave 4+ behavioral compression** — further priorities 1–4 / OUTPUT RULES / semantic-cluster consolidation beyond Wave 2 bridge merge. | `prompt` / `memory` | Observation (deferred by consensus) | **(1)** Sustained token pressure blocks retrieval/memory expansion on production paths; **(2)** ≥2 long-session audits show measurable prompt-budget regression vs post-#242 headroom; **(3)** #230 productization demands additional mass reduction **with** audit proof | **deferred_intentional** |
| **DS-06a** | **Emotional-quality degradation watch** — conservative `no_covered_change` variance must not become emotional flattening or participation misclassification under merged calibration topology. | `prompt` / `audit_simulation` | Observation (baseline WARN accepted) | **(1)** Manual RP spot-check FAIL on emotional overlay lanes; **(2)** aggressive false `covered_change` spike vs #240 adjudication corpus; **(3)** semantic_eval omission > 0 on v1_next7 | **monitor** |
| **DS-06b** | **Retrieval / memory pressure revisit** — post-#242 headroom should be re-measured before substantive Phase 1 memory expansion ([#177](https://github.com/KizzieFae/Holy_Grail_RP/issues/177)). | `memory` / `grounding` | Observation | **(1)** #230 live re-validation on production topology; **(2)** long-session prompt growth re-exceeds budget after memory channel activation; **(3)** operator documents headroom insufficiency with audit cites | **monitor** |

**Long-form runtime observation criteria (non-gate):**

- Re-run fixed regression slice (cert + emotional + 3-char) on **production** topology after #230 merge — compare semantic_eval presence, profile_match, overlay F0, manual RP.
- Compare system prompt median size vs post-`0a53b28` manifest medians on same scenario ids.
- Wave 4+ work **must not** resume from this row alone — requires new scoped issue + normal §H consensus.

**Explicit framing:** Wave 4 deferment is **governance-approved scope boundary**, satisfied by #242 validated delivery. DS-06 rows are **watchlist anchors**, not Phase 1 blockers ([#184](https://github.com/KizzieFae/Holy_Grail_RP/issues/184) program authority).

---

## Governance / classification

- **Posture:** Phase **0** stabilization **governance** + **observability** (low noise).
- **Project:** **RP System Workflow** — **Priority `P3`** until recurrence forces triage.
- **Labels:** `improvement`, `type:quality`, `audit`, `monitor` (scope: surveillance registry).

## Next step

Owners: on each **Phase 0** batch review, skim **`monitor`** rows; update confidence **only** with audit cites; **promote** via child issues when thresholds hit.


