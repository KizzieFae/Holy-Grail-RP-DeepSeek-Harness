# RP App Audit System Documentation

This document describes the audit logging system for the RP app, enabling scene analysis and bot behavior debugging.

## Overview

The audit system captures every bot interaction during roleplay scenes, creating both granular per-bot logs and
session-level summaries. It is designed to support both prose review and architecture-level debugging.

This allows for:

- Complete scene reconstruction
- Per-character contribution analysis
- Director decision tracking
- Spotlight (turn distribution) analysis
- Bot behavior debugging
- Continuity-state and issue-lifecycle analysis
- State-change and consequence tracking
- Summary-block visibility and retrieval analysis

### Layers of truth in audits

Audit artifacts observe **different layers**: per-bot prompts and **parsed** model outputs; **continuity commits** and **`_narrative.json`** (orchestration-enriched trace); Director **decision** JSON; Narrator render path. Do not treat the **character’s parsed move** as the full source of structured scene truth. Fields such as **`issue_updates`**, scene-level **`tension_shift`**, and **`consequences`** in the **session narrative** reflect **continuity classification and orchestration history**, not a requirement that the character model emit them on every move.

Audit JSON is **not self-consuming**: it records observations for **interpretation** before scheduling work. Deterministic audit blocks and LLM-assisted validation logs are **advisory** unless explicitly documented as a runtime gate; they **do not** by themselves change continuity, progression, or rendered output. See [Audit interpretation and issue tracking](#audit-interpretation-and-issue-tracking).

### Offline evaluation layer (Issue #66 — v1)

**Purpose:** Offline-only mechanism that reads existing audit artifacts and emits **structured judgments**. It does **not** define a detection layer, quality gate, or runtime authority.

**Scope:** Implemented in `scene_eval_v1.py` (`run_scene_eval_v1`). **Fixed predicates only**; logic is **deterministic** and **artifact-driven** (character `*_full.json` via `load_character_audit_rows`, optional `structured_eval` JSON).

**Critical constraints:** Judgments are **descriptive**, not pass/fail or system verdicts. They **must not** infer narrative or continuity correctness. They **must not** consume CA1–CA7 derived fields, Audit v2 heuristic bundles, narrator/prose heuristic audits, or LLM-generated audit layers. The layer **must not** modify runtime behavior, prompts, audit writers, or continuity state.

**Interpretation:** `fired` means the predicate’s observable condition held — **not** failure. `clear` means that condition was not observed — **not** success or health. `inconclusive` means inputs were insufficient or out of scope for that predicate.

Normative applicability, authority, inventory, and examples for operators and tooling are defined under **[Audit signal applicability (contract)](#audit-signal-applicability-contract)** below (**GitHub #59**).

### Audit signal applicability (contract)

This section is the **repo-authoritative** contract for: (1) **authority** — whether any audit signal may influence runtime; (2) **classification** — the three applicability classes; (3) **granularity** — Option B (one class per inventory row); (4) **inventory** — every classified signal; (5) **worked examples**; (6) **runtime use allowlist** (empty by default).

#### Authority rules

##### A. Definitions

**Authoritative narrative truth**  
Committed scene, issue, knowledge, and consequence state owned by **`ContinuityManager`** and any subsystem explicitly designated continuity-authoritative in **Holy Grail PRD** and **`autogen_rp/python/rp_app/ARCHITECTURE.md`**. Continuity is not overridden, repaired, or inferred into truth by audit heuristics.

**Observational audit layer**  
Subsystems whose **primary purpose** is to record, summarize, or score scene and model artifacts **for operators, tooling, and post-hoc analysis**, including: Character Audit v1, Narrator / prose heuristic audits, Audit v2 deterministic and LLM-assisted audit bundles, support manifests, Issue #29 harness metadata, and analogous fields under per-turn `metadata`, **`_audit_summary.json`**, **`structured_eval`**, and **`_narrative.json`**, **when** those fields are interpretive or diagnostic (see **Runtime outcome records** below for exclusions).

**Runtime authority**  
Subsystems that **may** accept, reject, retry, reorder, or mutate committed narrative state on the live or headless **scene turn path**, including (illustrative, not exhaustive): structured move and Director JSON validation (`response_validation_*`, `semantic_validation` where applicable), progression enforcement (`progression_enforcement.py`), binding-contradiction retry paths, continuity `process_turn`, and any mechanism **explicitly documented** as blocking or mutating that path.

**Audit signal (subject of the three-class system)**  
A **named** observational output that is **listed in the [Audit signal applicability inventory](#audit-signal-applicability-inventory)**. Each inventory row has a stable **Signal id** and exactly one applicability class.

**Runtime outcome record**  
Values logged in audit JSON that **only mirror** a decision already taken by **runtime authority** (e.g. `stage`, validation rejection reason, progression retry flags, binding retry metadata on a committed path). These records are **not** audit signals under this contract: they inherit **authority from the runtime subsystem** that produced them, not from the three-class taxonomy. Do not assign them **always-on / conditional / heuristic**; interpret them via the owning runtime docs.

##### B. Absolute prohibition (default)

**No audit signal, as defined above, may be read as an input to any runtime authority decision** — including accept/reject/retry of a move, Director `next_actor` resolution, continuity commits or rollbacks, progression Q1–Q4, or injection/removal of prompt text — **unless** that signal’s id appears on the **[Runtime use allowlist](#runtime-use-allowlist)**.

This is a **hard prohibition**. There is **no** implied exception for “always-on” quality signals, high-severity Audit v2 tri-states, or future dashboards.

##### C. Positive exception mechanism (closed list, future-proof)

The only way any listed audit signal may influence runtime is for its **Signal id** to be added to **[Runtime use allowlist](#runtime-use-allowlist)**, where each entry states **all** of:

1. **Signal id** (must match the inventory).  
2. **Runtime subsystem** (exact module or documented seam name).  
3. **Effect** (e.g. “hard fail character turn”, “advisory prefix only”, “metrics only”).  
4. **Authoritative doc anchor** (PRD section or `ARCHITECTURE.md` / governance pointer) that explicitly authorizes that coupling.

**Amendment rule:** Adding or removing an allowlist entry requires **(i)** an explicit edit to this document and **(ii)** a tracked GitHub Issue recording engineering and product rationale. Silent or ad-hoc coupling is **out of contract**.

##### D. Non-contradiction with “always-on”

**Always-on** (classification below) governs **whether absence or default state is diagnostically meaningful when reading audit artifacts**. It does **not** grant authority to drive runtime. **Always-on ≠ runtime gate.**

##### E. Alignment summary

| Layer | Role |
|--------|------|
| **Continuity / runtime authorities** | Sole sources of committed truth and of accept/reject/retry on the turn path. |
| **Audit signals (inventory)** | Observational; inform **human** triage and **offline** tooling only, subject to class rules and the allowlist. |
| **Runtime outcome records** | Factual log of what runtime already did; not classified by the three applicability classes. |

#### Classification contract (three classes)

##### 1. Always-on

**Definition:** For every turn or artifact of the declared **in-scope** type, the signal is **expected** to carry a defined evaluation or explicit **sentinel**; **absence** or **violation of the expected shape** is **meaningful** for audit diagnosis (logging defect, pipeline bug, or unexpected omission).

**Operator behavior:** If in-scope and missing or malformed, **investigate the audit/logging path or configuration** before treating the finding as story quality. Do **not** treat as a continuity defect without continuity evidence.

**Runtime:** **Prohibited** from driving runtime unless the Signal id is on **[Runtime use allowlist](#runtime-use-allowlist)**. Always-on does **not** imply a production gate.

##### 2. Conditional

**Definition:** The signal is defined only when a **documented predicate** on session configuration, harness mode, feature flags, or upstream state is **true**. When the predicate is **false**, the signal is **out of scope**; absence is **neutral** (not pass, not fail, not evidence of a “clean scene”).

**Operator behavior:** Before interpreting value or silence, **evaluate the predicate**. Do not compute corpus-wide false-positive rates for the signal without conditioning on the predicate.

**Runtime:** **Prohibited** from driving runtime unless the Signal id is on **[Runtime use allowlist](#runtime-use-allowlist)**.

##### 3. Heuristic / advisory

**Definition:** A deterministic or model-assisted **proxy** for narrative or presentation quality; **not** semantic truth; **not** continuity-competitive.

**Operator behavior:** **Corroborate** with `_narrative.json`, continuity slices, prompts, or other runtime evidence before attributing bugs to a layer. **Never** sole proof of continuity or orchestration failure.

**Runtime:** **Prohibited** from driving runtime unless the Signal id is on **[Runtime use allowlist](#runtime-use-allowlist)**.

##### Mutual exclusion (contract logic)

At **inventory granularity (Option B)**, each **Signal id** has exactly **one** of: **always-on** | **conditional** | **heuristic / advisory**. The classes differ by **silence semantics** and interpretability, **not** by runtime power (runtime coupling is **uniformly forbidden** except entries on the allowlist).

#### Classification granularity (Option B)

1. **Unit of classification** — Exactly **one** applicability class is assigned to **each row** in the **[Audit signal applicability inventory](#audit-signal-applicability-inventory)**. A row’s **Signal id** is the finest granularity at which classification applies.

2. **Composite and nested fields** — If a published signal aggregates sub-scores or nested JSON, the **whole named signal** receives **one** class. Internal leaves are **not** separately classified unless promoted to their **own** inventory row in a future doc amendment.

3. **Deterministic assignment** — For every Signal id in the inventory, its class is **fixed in the table**. If emitted behavior or interpretation rules change, update the **inventory row** (and surrounding contract text) in the **same** change set as the behavior or analysis change.

4. **Character Audit v1** — One inventory row per **`metadata.character_audit_v1.derived`** key used as a quality signal, using the stable ids below. The **`observed`** envelope is a **single** inventory row (context for CA dimensions, not continuity truth).

5. **Audit v2** — One inventory row per **check_id** emitted in deterministic bundles (`audit_v2_escalation_policy.CHECK_TO_DIMENSION` and `audit_v2_deterministic` builders).

6. **Signals not in the inventory** — Must not support **strong** conclusions about system or narrative correctness until added and classified (prevents silent scope creep).

#### Key interpretation rule

A signal that does not fire is not evidence of correctness or failure **unless** it is defined as **always-on** for that inventory row (subject to any **predicate** for conditional rows).

#### Interpretation discipline (critical)

No **audit signal** may be interpreted using TP/FP or severity language until its **Signal id** has been located in the inventory and its **class** and **predicate** (if any) applied.

#### Evaluation guidance

When analyzing audit output:

1. Resolve **Signal id** → inventory row.  
2. If the row is **conditional**, evaluate the **predicate**; if false, stop — silence is neutral.  
3. If **always-on**, treat in-scope absence or malformed shape as an **audit-path** problem.  
4. If **heuristic / advisory**, require **corroboration** before filing runtime **Layer** issues.  
5. For **runtime outcome records**, use runtime documentation — not this three-class system.

Failure to apply this distinction can result in mis-scoped issues, misleading dashboards, and incorrect attribution of continuity bugs to observational heuristics.

### Audit signal applicability inventory

**Excluded from this table:** **Runtime outcome records** (see **Authority rules**). Examples: `stage: validation_progression_retry`, validation reason strings, successful `turn_execution_metadata` fields that mirror retry state — interpret via **`ARCHITECTURE.md`** and validation docs, not applicability class.

| Signal id | Description | Class | Predicate (conditional only) | Silence semantics |
|-----------|-------------|-------|-------------------------------|-------------------|
| `cav1.schema_version` | `metadata.character_audit_v1.schema_version` when the v1 block is written | always-on | `metadata.character_audit_v1` object is present on the character audit row | When the predicate holds, missing `schema_version` indicates a serialization / contract defect in the audit path. When the v1 block is absent entirely, evaluate **`cav1.block`** first (conditional). |
| `cav1.block` | Entire `metadata.character_audit_v1` advisory bundle | conditional | Per-turn character audit logging is enabled **and** the character turn produced a logged `*_full.json` / `*_light.json` row where v1 is attached | When audit logging is off or the row type omits v1, absence is **neutral**. When the predicate holds, absence of the block is an audit-path defect. |
| `cav1.observed` | `metadata.character_audit_v1.observed` (Director excerpt, digests, tails; pre-continuity context) | heuristic / advisory | Same as `cav1.block` | Silence or empty excerpts are common on short prompts or redacted paths; interpret only in context of **`cav1.block`** and continuity. |
| `cav1.derived.motivation_action_alignment` | CA1 — lexical / structural alignment (`character_audits_v1`) | heuristic / advisory | Same as `cav1.block` | High scores do not prove coherence; low scores do not prove continuity bugs. Audit v2 scored row uses **`excluded_deprecated`** (**#42**). |
| `cav1.derived.dialogue_action_consistency` | CA2 — lexical / structural consistency | heuristic / advisory | Same as `cav1.block` | Same as CA1. **`excluded_deprecated`** in Audit v2. |
| `cav1.derived.issue_engagement` | CA3 — move-level issue linkage proxy | heuristic / advisory | Same as `cav1.block` | `possibly_passive` means weak **move-level** linkage, not “no story engagement.” |
| `cav1.derived.repetition_vs_prior_self` | CA4 — repetition vs prior self | heuristic / advisory | Same as `cav1.block` | Silence uncommon when block present; interpret with tail windows in `observed`. |
| `cav1.derived.scene_plausibility_flags` | CA5 — plausibility flags | heuristic / advisory | Same as `cav1.block` | Advisory only; corroborate with scene state. |
| `cav1.derived.pressure_director` | CA6 — Director pressure snapshot | heuristic / advisory | Same as `cav1.block` | Reflects decision excerpt, not full orchestration truth. |
| `cav1.derived.pressure_move` | CA7 — declared pressure fields on move | heuristic / advisory | Same as `cav1.block` | `none` / weak readings reflect optional move fields, not absence of continuity pressure. |
| `av2.check.char_ca1_motivation_action` | Audit v2 scored row for CA1 | heuristic / advisory | `metadata.audit_v2` present with character deterministic bundle | Tri-state is **`excluded_deprecated`** — not a pass; does not aggregate into intra-move dimension (**#13**, **#42**). |
| `av2.check.char_ca2_dialogue_action` | Audit v2 scored row for CA2 | heuristic / advisory | Same as `av2.check.char_ca1_motivation_action` | Same as CA1 row. |
| `av2.check.char_ca4_repetition` | Audit v2 CA4 repetition band | heuristic / advisory | Same as `av2.check.char_ca1_motivation_action` | `fail` / `border` / `pass` are heuristic bands; corroborate with narrative. |
| `av2.check.char_ca7_declared_fields` | Audit v2 CA7 declared fields | heuristic / advisory | Same as `av2.check.char_ca1_motivation_action` | Border/fail still advisory vs continuity. |
| `av2.check.nar_strict_action_overlap` | Narrator strict action overlap | heuristic / advisory | `metadata.audit_v2_narrator` (or narrator bundle path used for prose) present | Absent when narrator v2 not built; neutral. |
| `av2.check.nar_v1_action_passes_bar` | Narrator v1 action `passes_bar` rollup | heuristic / advisory | Same as `av2.check.nar_strict_action_overlap` | Heuristic narrator output check. |
| `av2.check.nar_environment_cue` | Environment cue presence in render | heuristic / advisory | Same as `av2.check.nar_strict_action_overlap` | Conditional on Director/environment context; `environment_event` absent → check often inert (see payload). |
| `av2.check.nar_scope_proxy` | Legacy scope proxy (non-gating) | heuristic / advisory | Same as `av2.check.nar_strict_action_overlap` | Escalation always **`pass`** for this check id (**#9**, **#41**); raw noise expected. |
| `av2.check.prose_readability` | Prose readability proxy | heuristic / advisory | Prose bundle present in v2 path | High false-positive rate possible; not narrator correctness. |
| `av2.check.prose_redundancy` | Prose redundancy Jaccard | heuristic / advisory | Same as `av2.check.prose_readability` | `prior_turns_used == 0` → scored **`pass`** path per policy; interpret with `limitations`. |
| `av2.check.prose_dialogue_integration` | Prose dialogue integration proxy | heuristic / advisory | Same as `av2.check.prose_readability` | Advisory only. |
| `av2.check.prose_attribution` | Prose attribution proxy | heuristic / advisory | Same as `av2.check.prose_readability` | Pronoun-led false negatives common (**#10** class noise). |
| `av2.check.prose_tone` | Prose local tone proxy | heuristic / advisory | Same as `av2.check.prose_readability` | Lexical heuristic only. |
| `av2.llm_character` | LLM-assisted character audit v2 layer (when enabled) | conditional | LLM audit enabled for the run/build path | When disabled, absence is **neutral**. When enabled but missing where expected, investigate harness. |
| `av2.llm_narrator` | LLM-assisted narrator audit v2 layer | conditional | Same as `av2.llm_character` | Same silence semantics. |
| `av2.llm_prose` | LLM-assisted prose audit v2 layer | conditional | Same as `av2.llm_character` | Same silence semantics. |
| `metadata.progression_advisory` | Stall / progression advisory snapshot (not continuity truth) | heuristic / advisory | Progression advisory MVP active for session | When feature off, absence is **neutral**. |
| `metadata.anti_regression_advisory` | Anti-regression advisory snapshot | heuristic / advisory | Anti-regression path armed / used for session | When inactive, absence is **neutral**. |
| `metadata.retrieval_summary` | Retrieved bundle summary (counts/refs) | conditional | Authored retrieval or merged episodic path produced a summary for the character turn | When retrieval OFF and no merge, absence is **neutral**. |
| `metadata.scene_grounding` / `scene_grounding_summary` | Grounding observability snapshot | conditional | Scene grounding MVP produced facts for projection | When no promoted facts, absence or empty snapshot is **neutral**. |
| `metadata.support_manifest` | Support manifest `support_manifest.v1` | conditional | Character `*_full.json` audit path attached manifest (`audit_support_manifest`) | Per **Support Manifest** section: absent on Director/Narrator rows by design — **neutral**. |
| `audit.retrieval_session` | `_audit_summary.json` top-level `retrieval_session` | conditional | Headless simulation completed with post-merge summary refresh | Streamlit path may omit (**documented elsewhere**); absence then **neutral**, not a defect. |
| `audit.effective_user_trigger` | Top-level `effective_user_trigger` on **full** per-turn rows | conditional | Headless harness used per-turn user trigger schedule **or** tooling expects harness field | Light audits omit by design; absence **neutral** for light rows. |
| `structured_eval.bundle` | Headless `structured_eval` / metrics JSON (scenario id, metrics, `retrieval_session`, verdict flags when set) | conditional | Run requested metrics output (`--metrics-out` or suite aggregation) | Absent file or block means no metrics artifact — **neutral** for audit quality of the scene itself. |

### Worked examples

#### Example A — Always-on (`cav1.schema_version`)

**Artifact:** `round_001/*_turn03_Celina_full.json` (character), `metadata.character_audit_v1` present.

**Expectation:** `schema_version` is a non-empty string (current v1 schema).

**If missing:** Treat as **audit serialization / contract failure** (logging pipeline), not as evidence Celina “broke” continuity. Open an **audit_simulation** or infrastructure issue with the file path and writer version.

#### Example B — Conditional (`audit.effective_user_trigger`)

**Artifact:** Same `*_full.json` row from a headless run using **`--user-trigger-schedule`**.

**Predicate:** Full audit row + harness supplied an override line for this orchestration turn.

**If key absent:** First confirm **`light` vs `full`** serialization (light omits the field by contract). Then confirm the schedule JSON and CLI actually targeted this turn index. If predicate true and full row still lacks the field, treat as **harness / writer** issue — **not** evidence the model ignored the user line in continuity.

#### Example C — Heuristic / advisory (`cav1.derived.motivation_action_alignment` + `av2.check.char_ca1_motivation_action`)

**Artifact:** `metadata.character_audit_v1.derived.motivation_action_alignment` shows weak overlap; Audit v2 row `check_id: "char_ca1_motivation_action"` has `result: "excluded_deprecated"`.

**Interpretation:** The move may still be **semantically** coherent (subtext, indirect motivation). Do **not** infer a **response_validation** or **continuity_state** bug from CA1 alone. Read **`_narrative.json`** for the same turn; if continuity and narrative agree, file **quality** / calibration under **audit_simulation** if the metric is misleading — not a runtime regression without independent runtime evidence.

### Runtime use allowlist

**Status:** **Empty** — no inventory Signal id is currently authorized to drive **runtime authority** decisions.

**How entries are added** — See **Authority rules → C. Positive exception mechanism**. Each new row must list Signal id, runtime subsystem, effect, and PRD/`ARCHITECTURE`/governance anchor, and must be paired with a tracked GitHub Issue.

**How entries are removed** — Same process in reverse: doc edit + issue note so downstream tooling does not rely on stale coupling.

### Progression advisory (MVP) in audits

When enabled, Director turn metadata may include a **`progression_advisory`** object (not continuity truth): **`stall_score`**, **`progression_pressure`** (`low` / `medium` / `high`), template-sourced **`recommended_channels`**, human-readable **`note`**, **`stall_components`** (booleans: same phase, high tension, issue stability, exact structural repetition), and related fields consistent with `progression_advisory.py`. Logs may also record when advisory text is injected into prompts or when beat-shift eligibility is influenced by the unified **`stall_score`** threshold.

### Anti-regression advisory (MVP) in audits

Director turn metadata may include **`anti_regression_advisory`**: **`active`** (whether the ANTI-REGRESSION Director prefix was injected this call), **`ping_pong_detected`**, **`post_break_window_active`**, **`low_player_agency`**, **`ping_pong_actors`** (the two alternating `next_actor` ids when detected), and **`ticks_after_decrement`** (remaining post-break window ticks after this Director step). This mirrors orchestration cache fields from `anti_regression_advisory.py` and is not continuity truth. Application logs under **`rp_app.anti_regression_advisory`** record injection and post-break arming when enabled.

**Character** and **Narrator** per-turn audit metadata also include **`progression_advisory`** and **`anti_regression_advisory`** snapshots read from orchestration cache at log time (same fields as above, where present). That lets you correlate each rendered beat with stall pressure, ping-pong flags, and post-break window state without relying on Director JSON alone.

### Progression enforcement and `consequences` in audits

When progression enforcement is on, a character failure log may show **`validation_progression_retry`**: the move passed parse/presence checks but **Q1–Q4** in **`progression_enforcement.py`** failed after continuity **`process_turn`**, so continuity was rolled back and the turn retried. **Q1–Q4 logic is unchanged;** they consume **`turn_metadata_by_index[*]["consequences"]`** and related continuity outputs.

Structured **`consequences`** (and the enriched narrative mirror of them) are emitted by **`continuity_consequence_classifier.py`** via **`ContinuityManager._classify_turn_consequences`**. **Fixes for false retries** from empty or overly thin consequence lists are **continuity-side classification** improvements—**not** enforcement weakening. **`REPOSITIONING`** uses bounded movement/locus/transition rules and excludes **negated `turn`** phrasing as locomotion; **`REFUSAL`** / stance uses deterministic intent-aligned rules; **legacy** dialogue markers **`no` / `not`** match as **standalone words** only (word boundaries), not substrings inside words like "nothing" or "know". **Multi-tag** categories per turn remain supported (per-category dedupe only). See **`ARCHITECTURE.md`** (*Progression enforcement vs continuity classification*).

**`exit` in audits vs on-stage roster:** Event-facing lines and **`recent_delta`** are aligned with **effective** **`present_characters`** when a classified exit does not remove the actor (see **`ARCHITECTURE.md`** — *Exit narrative vs effective on-stage presence*). The **`exit`** string may still appear in **`consequences` / tags** in **`turn_metadata`** for those turns. Interpret **physical presence** from **`SceneState`** (e.g. **`present_characters`**), not from **`exit`** alone.

### Scene Grounding (MVP) in audits

Audits may record a compact **`scene_grounding`** snapshot (or **`scene_grounding_summary`**) per relevant turn: **active fact count**, **categories** present, **`fact_id`** list or hashed fingerprint of `(category, key)` pairs, and optionally the **exact `value_summary` lines** injected into prompts. This is **observability** for the prompt projection — **not** continuity truth (continuity remains authoritative; facts are derived).

**What to verify in audits**

- After a turn where continuity established a settled logistic (e.g. bunk assignment), the next turn’s **Director/character** audit payload should show the **SETTLED SCENE FACTS** block (or metadata proving injection).
- **No drift** between **continuity event** and **grounding** for the same key: if promotion rules fired, `source.ref` should tie to the continuity artifact.
- **Cap behavior:** fact count ≤ configured maximum; pruning should be visible if many keys compete.
- **Scene end:** grounding snapshot should be **empty** or **absent** on the next scene’s first turn after grounding state clears.

**BINDING CONSTRAINTS in audits**

Character `*_full.json` system prompts may include the heading `## **BINDING CONSTRAINTS (HIGH PRIORITY)**` when the active grounding state contains facts in the binding allowlist. Light audits and failure logging may surface `has_binding_constraints`, `scene_binding_constraints_section`, or related promoted fields (see `turn_runner_audit.py`, `audit_logger_serialization.py`). Use these to confirm injection on binding-stress scenarios without reading the entire system message.

**Binding sleeping-surface contradiction enforcement (runtime validation)**

When a move contradicts a **promoted** `assignment:sleeping_surface` binding, the first failed attempt may be logged with **`stage: validation_binding_retry`** and reason prefix **`[BINDING_SLEEPING_SURFACE]`** (see `turn_runner_turn.py`, `response_validation_binding_sleeping_surface.py`). The retry attempt’s system prompt may include a short **`[BINDING_RETRY]`** note. **`turn_execution_metadata`** can include **`binding_retry_triggered`**, **`binding_retry_reason`**, and related fields on successful turns after a retry.

**Do not conflate** with **`[REGISTRY_SLOT] sleeping_surface_assignment: invalid_surface_id`**, which fires when **`scene_state_updates.sleeping_surface_assignment`** uses a **surface id** not allowed by the registry/template contract (`response_validation_registry_slots.py`, `resolved_outcome_registry.py`). That path has **no** binding-contradiction retry; it is ordinary validation failure. Repeated `invalid_surface_id` churn in long runs is tracked separately (**GitHub #31**; see **`ARCHITECTURE.md`** — Scene Grounding binding enforcement note).

Automated coverage for the **contradiction** path: `autogen_rp/python/tests/test_response_validation_binding_sleeping_surface.py`.

**EVIDENCE & AUTHORITY DISCIPLINE**

Character `*_full.json` prompts include a fixed **`EVIDENCE & AUTHORITY DISCIPLINE (HIGH PRIORITY)`** section immediately before **`OUTPUT RULES:`** when using the current `prompt_builders.build_character_turn_prompt` template. It is not continuity-derived; presence is **always** expected for character turns (verify with a string search on `*_full.json`).

**Cast / others roster (character prompt):** In `*_full.json`, the acting character should **not** appear under **`OTHER PRESENT CHARACTERS`**, and **`CAST ROLE MAP`** should **not** list the same person twice under different id vs display spellings. Live and reconstruction use the same display-name resolver (`get_character_display_name_fn`) for this assembly path.

**Recorded check (2026-04-07):** Post–**#24** validation wave used headless audits **`session_388`–`session_393`** with mandatory first/last/actor-switch sampling on character `*_full.json` prompts — **no** self-in-others or id/display duplicate **CAST ROLE MAP** findings. Structured metrics: `autogen_rp/python/validation_runs/plan_execution/*.json`. Narrative cross-check for exit vs on-stage presence on **`long_session`** (session **393**). See **`SCENARIO_VALIDATION_FRAMEWORK.md`** for the full scenario list and phase outcomes.

### Episodic memory (Phase 3.2) in audits

Continuity-backed episodic recall is **off by default**. It is merged into the character system prompt under **RETRIEVED REFERENCE MATERIAL (NON-AUTHORITATIVE)** when enabled.

**Enable for Streamlit or any process:** set environment variable `RP_EPISODIC_MEMORY` to `1`, `true`, or `yes` (case-insensitive). See `episodic_memory_prompt.py`.

**Headless simulation CLI:** `python scripts/run_scene_simulation_llm.py ... --episodic-memory` (sets the env var and `prepare_headless_session(..., enable_episodic_memory=True)`). Use `--audit` to write `*_full.json` under `rp_app/data/rp_audits/`.

**Verify in artifacts:** search character `*_full.json` for `RETRIEVED REFERENCE MATERIAL` and `episodic:` (source_kind lines). **Visibility** uses exact string match on the turn-runner character key (`next_actor`); headless seed issues use **agent keys** from character cards so participants align with that key.

**Logs:** at INFO, logger `rp_app.episodic_prompt` emits one line per character turn when the episodic merge path runs (`pool_len`, `selected_len`, `bundle_items`). Logger `rp_app.retrieved_context` logs when the post-merge bundle is non-empty (`log_retrieval_if_active`).

### Effective user trigger (headless simulation harness)

**Field:** Top-level **`effective_user_trigger`** on **full** per-turn audit records (Director, character, narrator success paths, and turn failure entries where the harness supplies it). It records the **simulated user trigger string actually used for that orchestration turn** in the production prompts for that beat (Director selection, character generation, narrator render path for that turn).

**Interpretation:** Compare this field to **`by_orchestration_turn`** / CLI **`--trigger`** / scenario defaults when debugging “wrong user framing” in **headless** runs. Rules and JSON shape are documented in [SCENARIO_VALIDATION_FRAMEWORK.md](../../../SCENARIO_VALIDATION_FRAMEWORK.md) (**Per-turn user trigger schedule**). The schedule file is **harness input only**—it is not written into continuity or scenario files.

**Light vs full:** **`effective_user_trigger`** appears in **full** audit serialization (`entry_to_full_dict`). **Light** audit rows do **not** include it; use **`*_full.json`** when you need the per-turn line.

**Triage:** If the key is absent from on-disk `*_full.json` for a run that used `--user-trigger-schedule`, confirm turn-level behavior with **`_round_index.json`**, **`structured_eval`**, or metrics before assuming continuity/runtime failure—artifact layout or writer path may not expose the field in every session.

### Authored index retrieval (standard evaluation mode — Phase 4A)

**Activation:** **`RP_RETRIEVED_CONTEXT_INDEX`** only (path to compiled JSON, or unset / empty = OFF). Optional CLI: `scripts/run_scene_simulation_llm.py --retrieved-context-index [PATH]` (see [SCENARIO_VALIDATION_FRAMEWORK.md](../../../SCENARIO_VALIDATION_FRAMEWORK.md) from repository root).

**Accepted baseline** (content, not audit-specific): character **`lore_facts`**; template **`role_slots`** + refined **`premise`**; retrieval remains **non-authoritative** (same prompt contract as Phase 2). **Historical pilot** artifacts and the **rejected situational template-row cap** are documented in `data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md` — that file is the **runbook + manifest map**; day-to-day validation workflow is **standard**, not pilot-only.

**Per-turn (character `*_full.json` / light):** `metadata` may include **`retrieval_summary`**: `retrieved_block_present`, `retrieved_item_count`, `retrieved_char_count`, `retrieved_source_refs` (capped list). **No** full retrieved text is stored. Populated from the **`RetrievedContextBundle`** at prompt build time (`app_turn_prompting` → `turn_runner_audit`).

**Session summary (`_audit_summary.json`):** Top-level **`retrieval_session`** (same shape as structured_eval: mode, path, `retrieval_verified_active`, fingerprint) is **merged after headless simulation** completes (`headless_scene_simulation.run_headless_llm_scene`). **Streamlit** refresh of `_audit_summary.json` does **not** currently add this block — for run-level retrieval metadata in the UI path, rely on **per-turn** `retrieval_summary` and logs, or run the **headless** scenario with `--audit`.

**Strict verification (headless only):** If retrieval is **ON** and the continuity scene has **`scene_template_id`**, the headless run **raises** if no character turn had a non-empty retrieved bundle (guards silent misconfiguration).

### Support Manifest (`metadata.support_manifest`)

#### Purpose

The support manifest provides **observability into prompt support**: what material was available to the character model via the bounded prompt assembly path (summaries, retrieval refs, binding section text, and the full system prompt as an opaque envelope). It allows you to determine:

- what information was available to the model at a given turn, and
- when previously available information is no longer present (by comparing manifests across turns).

This exists to resolve ambiguity between:

- **model failure** (the model had the signal but did not use it well), and
- **context / support loss** (the signal was no longer in prompt support for that turn).

The manifest is **not** continuity truth; compare to continuity and narrative layers separately when diagnosing persistence.

#### Scope

- Present only on **character `*_full.json` audit entries** (`metadata.support_manifest`).
- **Not** present on Director or Narrator full entries (unchanged metadata shape for those bots).
- **Audit-only:** it does **not** affect runtime, does **not** modify prompts, and does **not** interact with continuity authority. It is derived in the audit layer from the same `prompt_layer_audit` payload and `task_prompt` string already logged for the character turn.

#### Schema

- **`schema_version`:** `"support_manifest.v1"`
- **`units`:** array of objects; each object has:
  - **`type`** — closed enum (string)
  - **`id`** — deterministic string identifier for that unit within the manifest
  - **`content_fp`** — `sha256:` followed by 64 lowercase hex digits (fingerprint of the canonical payload for that unit)

**Valid `type` values (closed set):**

| `type` | Role |
|--------|------|
| `summary_block_selected` | A summary block id that was selected for this prompt |
| `summary_block_excluded` | A summary block id that was available but not selected |
| `retrieval_source_ref` | One retrieved source ref line (position in the capped ref list matters for `id`) |
| `retrieval_aggregate` | Single aggregate over retrieval summary fields (`retr:agg:v1`) |
| `binding_constraints_section` | Binding constraints section text (`bind:v1`) |
| `prompt_envelope` | Entire character system prompt as one opaque unit (`prompt:envelope:character:v1`) |

Implementation: `audit_support_manifest.py`; attached in `turn_runner_audit.log_character_turn_audit`.

#### Determinism guarantees

- Structured unit payloads use **canonical JSON:** `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`, then **UTF-8** encoding, then **SHA-256** → `content_fp`.
- **`prompt_envelope`** hashes **raw UTF-8 bytes** of `task_prompt` (no JSON wrapper).
- **`units`** are sorted by **`(type, id)`** lexicographically before persistence.

**Guarantee:** identical `prompt_layer_audit` + `task_prompt` inputs → identical manifest.

#### How to use (critical)

##### Step 1 — Locate divergence

Find the first turn where behavior deviates from expectation (continuity vs output vs scene contract).

##### Step 2 — Compare manifests

Compare **`metadata.support_manifest`** for the **current** turn vs the **previous** character turn (same character when isolating per-actor support). Conceptually classify each `(type, id)` key:

- **`support_absent`** — present at *t−1*, missing at *t*
- **`support_new`** — present at *t*, missing at *t−1*
- **`support_changed`** — same `(type, id)` but different `content_fp`

Use the **`diff_support_manifests(previous, current)`** helper in `audit_support_manifest.py` for a deterministic diff shape (`support_absent`, `support_new`, `support_changed`). **Note:** the diff is **not** written into audit JSON by default; compute it offline or in tooling.

##### Step 3 — Classify

- **Case A — Support lost:** a unit (or envelope fingerprint) was present at *t−1* and is **absent** or **changed** in a way that removes signal at *t* → treat as a **system-side / support-path** hypothesis (retrieval, summarization window, binding text, or other content reflected in structured units or the envelope). Narrowing *which* subsystem requires other audit fields (e.g. `retrieval_summary`, `summary_blocks`, continuity), not the manifest alone.
- **Case B — Support retained:** relevant units still present with stable fingerprints but behavior is wrong → lean toward **model or orchestration** (selection, validation, parsing) rather than “forgotten in prompt.”

#### Limitations (important)

- **Grounding, dialogue history, and structured moves are not separate unit types in v1.** They are represented only through **`prompt_envelope`** (hash of the full system prompt). You can detect **that** support changed turn-over-turn, but **not** which internal subsection changed without reading the full prompts in `input_messages` or other audit fields.
- **No automatic diff persistence:** manifests are stored per turn; the diff helper exists but outputs are **not** stored in artifacts unless a future harness adds that (out of scope for v1).
- Manifests reflect **prompt inputs only**, not internal model reasoning or hidden chain-of-thought.

#### When to use

**Use** when:

- investigating “memory loss” or “forgetting” in long sessions,
- diagnosing long-session instability tied to bounded context,
- validating retrieval or summary **presence in prompt support**,
- distinguishing **system/support** hypotheses from **model** hypotheses.

**Do not use** for:

- narrative quality evaluation,
- subjective coherence judgments,
- treating the manifest as authoritative continuity state.

### Offline fact tracking (`fact_spec.v1`, GitHub #58)

**Purpose:** Deterministic **post-processing** over an existing character audit session (`*_full.json` only). Emits **`failure_classification`** in {`support_loss`, `utilization_failure`, `indeterminate`} plus turn anchors **`T_intro`**, **`T_support_last`**, **`T_divergence`**, **`support_state_at_divergence`**, and **`fact_spec_sha256`** for reproducibility.

**Authority:** **Observational / offline only.** This tool is **not** an audit signal row in the applicability inventory; it **does not** write into live audit JSON and **must not** feed **runtime authority** (same hard prohibition as **[Audit signal applicability (contract)](#audit-signal-applicability-contract)**). It consumes **conditional** inventory-class inputs (`metadata.support_manifest` when present) and prompt/output literals under operator-defined rules.

**Implementation:** `audit_fact_tracking.py` — **`analyze_fact_tracking`** (core), shared post-run **`run_fact_track_postprocess`** (writes companion file + returns result dict including `companion_artifact_path`; GitHub **#62**). **CLIs:** `python scripts/run_audit_fact_track.py --session-dir <path> --fact-spec <path.json>` (stdout JSON only). After audited headless simulation, `scripts/run_scene_simulation_llm.py` may take **`--fact-spec`** (requires **`--audit`**) and optionally **`--fact-track-out <path>`** to write the same companion JSON (default filename under the session directory). Orchestrators that do not use that script should call **`run_fact_track_postprocess`** directly. **v1:** companion only — **not** merged into `_audit_summary.json` in v1.

#### `fact_spec.v1` (minimal rule kinds)

Top-level fields:

| Field | Required | Description |
|--------|----------|-------------|
| `schema_version` | yes | Must be `fact_spec.v1`. |
| `probe_id` | yes | Stable string id for the probe (logged in output). |
| `actor_scope` | no | `{"kind": "all_characters"}` (default) or `{"kind": "character_name", "name": "<bot_name>"}` to restrict rows. |
| `establishment_rule` | yes | First matching character row is **`T_intro`**. |
| `support_predicate` | yes | Evaluated on every character row from **`T_intro`** through **`T_divergence`** (inclusive). |
| `behavior_rule` | yes | **Satisfied** rows are “behavior OK”; the first later row where the rule is **not** satisfied is **`T_divergence`**. |

Each rule is an object:

- **`kind`:** `prompt_literals_all` — all `literals` appear as substrings in the character system prompt (`input_messages[0].content`).
- **`kind`:** `parsed_output_literals_all` — all `literals` appear in `dialogue` + `action` (parsed move).

**Classification (deterministic):**

1. If there is no establishment row → `indeterminate` (`no_establishment`).
2. If no later behavior failure → `indeterminate` (`no_divergence`).
3. Otherwise at **`T_divergence`**: if **any** row in **[`T_intro`, `T_divergence`]** fails `support_predicate`, or consecutive character rows show a **non-`prompt_envelope`** `diff_support_manifests` change on the path (Issue #29 family) → **`support_loss`**.
4. Else if `support_predicate` holds on the full interval and at divergence → **`utilization_failure`**.
5. Else → **`indeterminate`** (`ambiguous_support_at_divergence`).

**Alignment with #59:** Interpret `support_manifest` and other inputs only per **inventory class and predicates**; tool output remains **offline** and is not on the **Runtime use allowlist**.

## Issue #70 — Engineering-role taxonomy (Tier 1 kernel)

This section is the **canonical Tier 1 kernel registry** for GitHub **Issue #70**: a small, curated set of **fully qualified surface instances** (`surface_id`) so operators do not conflate observability, guardrails, rollups, and offline detectors. **Normative Issue #59 rules** (applicability classes, inventory, allowlist) are **orthogonal** to **`engineering_role`** here: interpret both when both apply. **Outcome records** are audit mirrors of runtime authority; they are **not** #59 inventory signals—**omit `engineering_role` and `applicability_class`** for those rows (do not set them to `null`). A **`detector`** surface is **offline-first**, uses explicit **`predicate_id`** + **`judgment_schema`**, emits structured judgments, is **advisory** unless separately allowlisted under #59, and is **not** LLM-only at the core. **Runtime enforcement** (validation, progression Q1–Q4 gate, semantic overrides) is **`guardrail`**, never **`detector`**. Full methodology for evaluating signals lives under **Issue #71**; the offline evaluation layer specification lives under **Issue #66**.

In the registry table, **`surface_kind: signal`** applies only to surfaces that correspond to **Issue #59** audit signal applicability **inventory** rows (stable Signal ids)—not to arbitrary `metadata.*` fields or other audit keys unless they are explicitly inventory-listed.

### Tier 1 kernel registry

| surface_id | layer | scope | surface_kind | engineering_role | authority_posture | applicability_class | judgment_semantics | mirror_of | predicate_id | judgment_schema | notes |
|------------|-------|-------|--------------|------------------|-------------------|---------------------|-------------------|-----------|--------------|-----------------|-------|
| `runtime.progression_advisory` | runtime | production, headless | subsystem | guardrail | advisory | — | none | — | — | — | `progression_advisory.py`; stall score and prompt/Director advisory; pairs with beat-shift threshold. |
| `audit.metadata.progression_advisory` | audit | production, headless | signal | telemetry | observational | heuristic_advisory | proxy_score | — | — | — | #59 inventory `metadata.progression_advisory`; logged snapshot. **Derived from** `runtime.progression_advisory`. |
| `runtime.anti_regression_advisory` | runtime | production, headless | subsystem | guardrail | advisory | — | none | — | — | — | `anti_regression_advisory.py`; Director ANTI-REGRESSION prefix path. |
| `audit.metadata.anti_regression_advisory` | audit | production, headless | signal | telemetry | observational | heuristic_advisory | proxy_score | — | — | — | #59 inventory `metadata.anti_regression_advisory`; logged snapshot. **Derived from** `runtime.anti_regression_advisory`. |
| `runtime.progression_enforcement` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | `progression_enforcement.py`; Q1–Q4 after `process_turn`; rollback/retry—not a detector. |
| `runtime.response_validation.binding_sleeping_surface` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | `response_validation_binding_sleeping_surface.py`; binding contradiction retry path. |
| `runtime.response_validation.duplicate_dialogue` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | `response_validation_content.py` duplicate detection; duplicate retry path in `turn_runner_turn.py`. |
| `runtime.semantic_validation.presence_override` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | `semantic_validation.should_override_presence_rejection`; may clear presence rejection. |
| `runtime.semantic_validation.gated_alignment` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | `apply_gated_addressee_alignment_under_progression_enforcement` (`app_turn_director.py`). |
| `runtime.semantic_validation.narrator_fallback` | runtime | production, headless | subsystem | guardrail | runtime_authoritative | — | enforcement_decision | — | — | — | Narrator semantic review / fallback render path (`turn_runner_turn.py`). |
| `artifact.structured_eval.bundle` | artifact | headless | artifact | aggregation | observational | not_applicable | derived_metric + human_annotation | — | — | — | `progression_run_metrics.build_structured_eval_payload`; metrics bundle; optional human `verdict` / `failure_classification`. |
| `artifact._audit_summary` | artifact | production, headless | artifact | aggregation | observational | not_applicable | derived_metric | — | — | — | `_audit_summary.json` session rollup (`audit_logger_summary_report.py` stack). |
| `offline_job.audit_fact_tracking` | offline_job | offline_tooling | subsystem | detector | advisory | not_applicable | structured_judgment | — | `audit_fact_tracking.analyze.v1` | `audit_fact_tracking.v1` | `audit_fact_tracking.analyze_fact_tracking` / `run_fact_track_postprocess`; companion JSON; GitHub #62. |
| `audit.outcome_record.stage.validation_progression_retry` | audit | production, headless | outcome_record | | observational | | none | `runtime.progression_enforcement` | — | — | Logged `stage` mirror; **omit** `engineering_role` and `applicability_class`. |
| `audit.outcome_record.stage.validation_binding_retry` | audit | production, headless | outcome_record | | observational | | none | `runtime.response_validation.binding_sleeping_surface` | — | — | Logged `stage` mirror; **omit** `engineering_role` and `applicability_class`. |
| `audit.outcome_record.stage.validation_duplicate_retry` | audit | production, headless | outcome_record | | observational | | none | `runtime.response_validation.duplicate_dialogue` | — | — | Logged `stage` mirror; **omit** `engineering_role` and `applicability_class`. |

**Table conventions:** `—` means the field does not apply. For **`outcome_record`** rows, **`engineering_role`** and **`applicability_class`** are intentionally **blank** (omitted from the registry row, not `null`).

### Interpretation rules (summary)

- **Fully qualified `surface_id` only** — bare names (e.g. `progression_advisory` alone) are not sufficient for classification.
- **`signal` = #59 inventory only** — `surface_kind: signal` is for applicability-inventory Signal ids, not for every audit `metadata` field.
- **`outcome_record` is not a signal** — not governed by #59 silence semantics; do not assign inventory applicability classes to outcome rows.
- **`detector` is strict** — requires declared **`predicate_id`** and **`judgment_schema`**, offline-first default, structured judgments, not LLM-only core; see **Issue #66**.
- **Runtime enforcement ≠ `detector`** — validation, progression enforcement, and effective semantic paths are **`guardrail`** even when they emit reasons.
- **`derived_metric` / aggregation ≠ `detector`** — rollups and replay metrics are not detectors unless they meet the detector contract.
- **Audit JSON ≠ the runtime subsystem** — `audit.*` rows describe representations; behavior lives under `runtime.*` or `offline_job.*`.
- **#59 `applicability_class` is orthogonal to `engineering_role`** — always resolve inventory class and engineering role independently when both apply.

## Issue #29 Investigation Tooling

This section documents **headless harnesses**, **deterministic audit analysis**, and **optional AI-assisted interpretation** introduced or formalized during **Issue #29** (long-session “forgetting” triage). It complements **§D / §F** discipline in **`governance/rp-app/issue-tracking-workflow.md`**: machine-visible audit signals support **Type** / **Layer** hypotheses; advisory AI labels do **not** replace them.

### 1. Long-run harness

**CLI flag:** `--issue29-long-run-harness` on `scripts/run_scene_simulation_llm.py`.

**Eligibility:** **Headless only.** Scenario id must start with **`investigate_i29_`**. The suite driver **`scripts/run_issue29_suite.py`** passes this flag for packaged Issue #29 scenarios. Streamlit and normal production sessions do **not** set `issue29_long_run_harness`.

**Session flags:** Enabling the harness sets Streamlit session state **`issue29_long_run_harness`** and **forces** **`headless_ignore_director_end_round`** for that run (`prepare_headless_session` in `headless_scene_simulation.py`).

**Behavior (orchestration survivability):**

- **Ignores Director `end_round` termination** — When `ignore_director_end_round` is active, `turn_runner.py` clears **`end_round`** on the Director decision so the round loop can continue past a Director-chosen scene end while the investigation still needs more character turns.
- **Continues scene execution beyond normal stopping conditions** — Together with synthetic availability (below), the harness reduces **premature round exit** that would truncate long-horizon persistence / recall measurements.
- **Fills missing `next_actor` when necessary** — After clearing `end_round`, if `next_actor` is empty but **`available_actors`** is non-empty, the runner sets **`next_actor`** to the first available actor. When the harness is on and the Director returns an empty `next_actor` without `end_round`, the runner also picks **`available_actors[0]`**. If the **filtered** availability pool would otherwise be **empty**, `headless_scene_simulation.py` wraps **`get_available_actors`** so a **deterministic single-actor pool** is injected (order: **`issue29_last_successful_actor`**, then tail of **`issue29_actors_used_this_round_tail`**, then first participant key). This **does not** mutate continuity, retrieval bundles, or prompt builders.
- **Tracks last successful turn for continuity of the harness** — After each successful character turn, session state **`issue29_last_successful_actor`** is updated; the tail of actors used in the round is kept in **`issue29_actors_used_this_round_tail`** for fallback selection.

**Purpose:**

- Enable **long-horizon persistence and recall** testing without losing the run to Director **`end_round`** or empty availability pools.
- Prevent **premature scene termination** from **invalidating** Issue #29-style durability results.

**Constraints:**

- **Diagnostic / investigation use only** — Output is **not** a statement about correct scene ending, transitions, or on-stage presence under production rules.
- **Do not** use for **standard** scenario validation, production simulations, or operator-facing “normal” runs unless explicitly scoped as harness work.

**Run metadata:** Headless **`structured_eval`** JSON may include **`issue29_long_run_harness: true`**. Suite aggregate JSON under `autogen_rp/python/runs/` records the same per scenario row (`progression_run_metrics.py`).

### 2. Support manifest tracking (Issue #29 machine lane)

**Presence in audits:** Character **`*_full.json`** entries include **`metadata.support_manifest`** when audit logging is enabled (schema and diff helpers: **`audit_support_manifest.py`**, **`turn_runner_audit.py`**). See **Support Manifest (`metadata.support_manifest`)** under **Overview** above for the full v1 schema and comparison steps.

**Role across turns:** Comparing manifests (or using **`diff_support_manifests`** offline) detects **when structured prompt support changes** between consecutive character rows—supporting hypotheses about **support loss** vs **support retained**.

**Distinction used in Issue #29 tooling (`issue29_investigation.py`):**

- **`support_manifest_diff_non_envelope`** — Returned as **`T_sup`** reason when the manifest diff shows **absent**, **new**, or **changed** units involving any **`type` other than `prompt_envelope`**. That flags **structural** support changes in the **typed units** (summaries, retrieval refs, binding section, etc.), not merely a hash drift of the opaque full-system **`prompt_envelope`**.
- **Literal anchor disappearance (token-level)** — Detected separately when a scenario **anchor token** appears in the prior character system prompt (`input_messages[0].content`) but **not** in the current one (**`token_dropped_consecutive`** in **`compute_t_sup`**). Issue #29 long-session investigation **did not** treat **literal anchor drop-out** as the primary explanation where **`T_beh`** still showed anchors present; classify outcomes with both **manifest** and **prompt text** evidence.

**`T_sup` (support / prompt-side event):** First index after the established baseline where **`compute_t_sup`** reports **token drop** across consecutive character rows, **missing manifest**, or **`support_manifest_diff_non_envelope`**. This marks a **machine-visible change in what was assembled into the prompt** (or loss of manifest integrity)—**not** by itself “bad output.”

**Non-equivalence:** **`T_sup`** **does not** imply **behavioral failure**. Support can change or be noisily classified while the model still behaves acceptably; conversely, **`T_beh`** can show failure while support is **stable** (selection / salience — see **Workflow integration (machine vs AI)** below). Always pair **`T_sup`** / **`T_beh`** with **`context_snapshot`**, continuity, and narrative layers.

### 3. AI-assisted causal analysis (advisory layer)

**Purpose:** When **machine-layer** audit evidence (presence, absence, timing, diffs) is **necessary but not sufficient** to explain *why* output diverged, an **optional** AI-assisted pass can propose a **primary causal narrative** (e.g. competing dialogue pressure vs low salience of a token). This is **interpretation**, not a new runtime gate.

**Inputs (typical bundle):**

- **`input_messages[0].content`** — Character system prompt as logged.
- **`parsed_output`** — Validated structured move (dialogue / action fields used by Issue #29 probes).
- **Audit metadata** — Including **`T_beh`** location, anchor / probe tokens, **`metadata.support_manifest`**, **`effective_user_trigger`**, and related rows from the same session.

**Output:** A **single primary-cause classification** label chosen from the **advisory taxonomy** below, plus short **human-readable rationale** tied to quoted spans where possible.

**Classification system (advisory only):**

| Label | Meaning (high level) |
|-------|----------------------|
| **`LOW_SALIENCE`** | Required material was present but **underweighted** vs other prompt content; weak coupling between instruction and generation. |
| **`COMPETING_SIGNAL_OVERRIDE`** | **In-scene** dialogue, immediacy, or character intent **dominated** over **explicit anchor / recall** reuse. |
| **`TASK_MISALIGNMENT`** | Model behavior **does not match** the stated task framing or probe despite readable instructions. |
| **`INTERPRETATION_DRIFT`** | Model **reframes** or **misreads** constraints while surface text still contains anchors. |
| **`GENERATION_DRIFT`** | **Stylistic / lexical** choices (paraphrase, omission) that drop required literals without a clear competing narrative signal. |

**Constraints:**

- **Advisory only** — Does **not** override **machine-layer** conclusions (e.g. **`T_sup`** / **`T_beh`**, manifest diffs, continuity commits).
- **Not sole validation** — Do **not** file **`bug`** / **`quality`** / **`design_gap`** issues from AI labels alone; align with **`governance/rp-app/issue-tracking-workflow.md` §D** evidence and **deterministic reasoning**.

### 4. Workflow integration (machine vs AI)

**Machine layer** (`issue29_investigation.py`, manifest diffs, harness metrics):

- Detects **presence**, **absence**, **timing**, and **structured support change** in audit JSON.
- Emits **`T_sup`** and **`T_beh`** (and related flags) for deterministic triage.

**AI layer** (advisory causal pass):

- Explains **prioritization and behavior** when outputs ignore **present** support—e.g. **`COMPETING_SIGNAL_OVERRIDE`** vs **`LOW_SALIENCE`**.

**Together:** Use the machine layer to **distinguish persistence / support-loss failures** from **selection / utilization failures** (context **present** at **`T_beh`** but **not** reflected in the move). That split matches **GitHub Issue #29** disposition: **not** a memory-loss **bug** where anchors remain in prompt and continuity; **quality / design_gap** discussion when **utilization** is unreliable under competing narrative pressure (see **`governance/rp-app/issue-tracking-workflow.md`** **§E** / **§F**).

## Audit interpretation and issue tracking

### Audit pipeline

**Simulation → Audit → Interpretation → Issue detection → Classification → Tracking → Fix → Re-test.**

Headless or in-app runs with audit logging produce artifacts under `rp_app/data/rp_audits/`. **Interpretation** (human and/or AI-assisted) compares layers—`_audit_summary.json`, `_narrative.json`, granular `*_full.json`—before filing work. After a fix, **re-run the same or equivalent scenarios** with audit enabled and confirm the reported pattern is resolved without regressions on adjacent signals.

### Roles

**AI-assisted (agents / tooling):**

- Run simulations (e.g. `--audit`, headless CLI).
- Generate and refresh audit artifacts.
- Interpret outputs: reconcile narrative trace, continuity fields, progression retries, narrator/character audit blocks.
- Propose **candidate issues** with mandatory evidence and a primary **Layer** (see `governance/rp-app/issue-tracking-workflow.md`).

**Human:**

- Approve or reject filing or scope of an issue.
- Assign priority.
- Steer validation and implementation.

### When to file a GitHub Issue

File when **Pattern status** and **Type** are assigned per `governance/rp-app/issue-tracking-workflow.md` **§I** and **§E**, mandatory evidence (**§D**) is complete, and work should outlive the session. **Pattern status** and **audit-only** discipline are defined there (single instance, escalation, audit-only notes).

### Type and Layer (GitHub body)

- **Type** — `bug` | `quality` | `design_gap` with **PRD/architecture as authority** (`governance/rp-app/issue-tracking-workflow.md` **§E**). Labels alone are not enough.
- **Layer** — Exactly one primary **Layer** from `governance/rp-app/issue-tracking-workflow.md` **§F** (snake_case). Use **orchestration** vs **response_validation** per the explicit boundary in **§F**.
- **Pattern status** — `single_instance` | `potential_pattern` | `confirmed_pattern` (**§I**).
- **Current status** — Workflow line and allowed transitions: `governance/rp-app/issue-tracking-workflow.md` **§H**.

### Tracking policy

- **GitHub Issues** are the system of record (`governance/rp-app/issue-tracking-workflow.md`, Issue Tracking §A).
- **bug** → implement after **`consensus_reached`**, then validate with audited re-runs; cite PRD/architecture clause in the issue.
- **quality** → calibration or UX; do not file as **bug** without an explicit spec violation.
- **design_gap** → spec or design completion; may pair with **`DESIGN_GAP`** title prefix.

### Evidence requirements

Align with `governance/rp-app/issue-tracking-workflow.md` **§D**:

- **Scenario id**, **audit session path**, **turn index** (or `n/a` with reason) — mandatory.
- Prefer structured move excerpt, consequence output, continuity snapshot excerpt.
- Concrete **observed** fields/values and **deterministic reasoning** tying them to **Layer** and **Type**.

### Validation loop (post-fix)

1. Re-run the **same** or agreed regression scenario with audit logging.
2. Verify the issue’s **signature** no longer appears (or meets agreed reduction).
3. Spot-check related dimensions (e.g. **continuity_state**, **progression**, **rendering**, **response_validation**) for regressions—use **Layer** names from **§F** when recording notes.

### Audit outputs vs runtime

- Artifacts are **observational**; they **require interpretation** into filed issues and validation criteria.
- **Character Audit v1**, **Narrator Audit v1**, and **Audit v2** deterministic bundles (when present on character/narrator turn metadata) are **logging-only** and **advisory**: they **do not** alter model output, continuity commits, or gate acceptance unless a separate documented mechanism says otherwise.
- **LLM validation** steps reflected in audit JSON (e.g. narrator semantic validation) are **advisory** relative to the render path unless explicitly defined as blocking.

### Audit v2 (deterministic, advisory)

Per-turn logs may include **`audit_v2`** (character) and narrator-side **`audit_v2_narrator`** metadata with extra deterministic checks. Same non-mutating contract as v1 add-ons. Read **`pass` / `fail` / `border`**, documented non-tri-state values (below), and **`limitations`** together when interpreting logs; assign a GitHub issue **Layer** from `governance/rp-app/issue-tracking-workflow.md` **§F** (e.g. **audit_simulation** for harness/log shape issues; **rendering** or **response_validation** when separate runtime evidence shows a defect outside the audit heuristic). For **`nar_scope_proxy`**, the scored **`result`** is always **`pass`** for escalation purposes while raw scope metrics remain in the payload (**GitHub #9**, removal **#41**).

For **`char_ca1_motivation_action`** and **`char_ca2_dialogue_action`** (Character Audit v1 **CA1 / CA2**, deprecated for escalation after corpus evaluation — **GitHub #13** / **#42**), the scored **`result`** is **`excluded_deprecated`**: raw payloads remain on the check row for observability, but these checks **do not** participate in dimension aggregation, escalation **`reasons`**, or **`qualified`**. They are **not** a successful **`pass`**. When no other checks contribute to **`character_intra_move_coherence`**, that dimension’s aggregate is **`not_applicable`** (not an empty-success **`pass`**). See **`intra_move_summary.pattern`** = **`intra_move_not_applicable`** and the human-readable explanation on character deterministic bundles.

### Audit signal limitations

Many dimensions are **heuristic**: token overlap, substring scope proxies, short-window attribution tests, etc. They may be **conservative** by design and produce **high false-positive** rates on otherwise healthy runs.

Examples from baseline audits:

- **Prose attribution** / attribution proxies — pronoun-led or implicit attribution often fails fixed-window name tests.
- **CA1 (`char_ca1_motivation_action`)** — low lexical overlap between motivation text and action/dialogue on coherent, subtext-heavy moves. **Audit v2 escalation:** excluded (**`excluded_deprecated`**); see Audit v2 paragraph above (**#42**).

**CA1 / CA2 vs Audit v2 post–#42:** Those checks **do not** produce intra-move **`fail`** or **`border`** escalation outcomes in **Audit v2**; **`character_intra_move_coherence`** is **`not_applicable`** when only those inputs would apply. **Character Audit v1** `derived` CA1/CA2 fields remain for **raw observability** and are separate from **Audit v2** escalation **`reasons`** / **`qualified`**.

Except for that CA1/CA2 **Audit v2** intra path (retired per **#42**, above), treat chronic **`fail`** on these as **quality**-class signals or **design_gap** discussions for metrics unless **independent runtime evidence** shows incorrect behavior attributable to a concrete **Layer**. They **should not** alone trigger “fix the narrator/character” work without that evidence.

### GitHub issue usage (this repo)

- **Labels** (**§C**): **mandatory** on create for tracked issues (`bug`, `improvement`, `research`, `tech-debt`, `blocked`, `validation`, `docs`, `needs-reproduction`, `documentation`, `infrastructure`, `type:*`, … per **§C**). Labels do **not** replace **Type** or **Layer** in the body. **Projects:** **§B.1**–**§B.3** (**RP System Workflow**, **Status**, **Workflow**); **§B.2** verification.
- **Issue body:** `governance/rp-app/issue-tracking-workflow.md` **§D** (canonical contract). **Layer** definitions and tie-breaks: **§F**. **Title** prefixes **`[BUG]`** | **`[QUALITY]`** | **`[DESIGN_GAP]`**: **§G**.
- **Documentation** before terminal closure: checklist in **§D**; update architecture/audit/operator docs when behavior or contracts change.
- **Root template:** `.github/ISSUE_TEMPLATE/holy_grail_rp.yml` (repository git root) mirrors **§D** fields for the web UI.

## Directory Structure

All audit files are stored in:
```
rp_app/data/rp_audits/
```

Organised by session number first, then round number:
```
rp_audits/
└── session_{###}/                   # 3-digit session number
    ├── _manifest.json                # Scene cast and metadata
    ├── _round_index.json             # Round -> ordered turn mapping
    ├── _narrative.json               # Story trace + turn-level continuity facts
    ├── _audit_summary.json           # Session-level audit dashboard
    ├── round_001/
    │   ├── {owner}_session{###}_round001_turn01_director_full.json
    │   ├── {owner}_session{###}_round001_turn01_director_light.json
    │   ├── {owner}_session{###}_round001_turn01_{character}_full.json
    │   ├── {owner}_session{###}_round001_turn01_{character}_light.json
    │   ├── {owner}_session{###}_round001_turn01_narrator_full.json
    │   ├── {owner}_session{###}_round001_turn01_narrator_light.json
    │   ├── {owner}_session{###}_round001_turn02_director_full.json
    │   └── ...
    └── round_{###}/
```

## Key Files

### 1. `_manifest.json`
**Purpose**: Scene overview and cast list

**Created**: Once, when scene starts

**Contents**:
```json
{
  "session_number": 42,
  "timestamp": "2026-03-14T12:45:30Z",
  "cast": ["Ayame", "Celina", "Kizzie"],
  "user_name": "Player",
  "opening_description": "Rain had been falling...",
  "total_characters": 3,
  "scene_template": {
    "template_id": "household_entry_evaluation",
    "premise": "A host evaluates a newcomer while a guard remains present.",
    "role_assignments": {
      "Ayame": "host",
      "Celina": "applicant",
      "Kizzie": "guard"
    },
    "character_presence_constraints": {
      "Ayame": "must_remain",
      "Celina": "must_remain",
      "Kizzie": "must_remain"
    },
    "character_authority_labels": {
      "Ayame": "high",
      "Celina": "low",
      "Kizzie": "medium"
    }
  }
}
```

### 2. `_round_index.json`
**Purpose**: Maps each round to its ordered turns

**Created**: Updated after each turn

**Contents**:
```json
{
  "rounds": [
    {
      "round_number": 1,
      "turns": [
        {
          "turn_number": 1,
          "acting_character": "Ayame",
          "director_reason": "Ayame was directly addressed and had narrative momentum.",
          "acting_role": "host",
          "presence_constraint": "must_remain",
          "authority_label": "high",
          "continuity_event_type": "decision",
          "state_change_count": 1,
          "issue_update_count": 1,
          "presence_change_count": 0,
          "timestamp": "2026-03-14T12:45:45Z"
        },
        {
          "turn_number": 2,
          "acting_character": "Celina",
          "director_reason": "Celina's reaction would heighten the tension.",
          "acting_role": "applicant",
          "presence_constraint": "must_remain",
          "authority_label": "low",
          "timestamp": "2026-03-14T12:46:10Z"
        }
      ]
    }
  ]
}
```

### 3. `_narrative.json`
**Purpose**: Human-readable story trace with per-turn continuity and orchestration facts

**Created**: Updated after each turn

**Contents**:
```json
{
  "session_owner": "Ayame",
  "session_number": 42,
  "created_at": "2026-03-14T12:45:30Z",
  "last_updated": "2026-03-14T12:52:15Z",
  "total_rounds": 6,

  "scene_template": {
    "template_id": "household_entry_evaluation",
    "premise": "A host evaluates a newcomer while a guard remains present.",
    "role_assignments": {
      "Ayame": "host",
      "Celina": "applicant",
      "Kizzie": "guard"
    },
    "character_presence_constraints": {
      "Ayame": "must_remain",
      "Celina": "must_remain",
      "Kizzie": "must_remain"
    },
    "character_authority_labels": {
      "Ayame": "high",
      "Celina": "low",
      "Kizzie": "medium"
    }
  },
  
  "complete_narrative": "Rain had been falling steadily...\n\nAyame eased herself back...\n\nCelina crossed to the cabinet...",
  
  "turns": [
    {
      "round": 1,
      "turn": 1,
      "character": "Ayame",
      "character_role": "host",
      "character_presence_constraint": "must_remain",
      "character_authority_label": "high",
      "director_reason": "Ayame was directly addressed and had narrative momentum.",
      "environment_event": "",
      "tension_shift": "escalate",
      "character_action": "eased back onto the couch, movements deliberately slow",
      "character_dialogue": "As you command. Stitches and a tetanus shot...",
      "character_motivation": {
        "goal": "maintain psychological dominance",
        "tactic": "comply superficially while maintaining control",
        "emotional_driver": "amused confidence",
        "risk_level": "low"
      },
      "rendered_output": "Ayame eased herself back onto the couch...",
      "continuity_event_type": "decision",
      "continuity_event_summary": "Ayame refused the current demand, request, or proposed course of action.",
      "continuity_event_significance": "pivotal",
      "continuity_related_issue_ids": ["issue_1"],
      "state_changes": [
        "Ayame refused the current demand, request, or proposed course of action."
      ],
      "actionable_implications": [
        "The cast must respond to the refusal or choose a different course."
      ],
      "scene_recent_delta": "Ayame refused the current demand, request, or proposed course of action.",
      "scene_phase": "rising",
      "current_tension_level": "moderate",
      "active_issue_ids_after": ["issue_1"],
      "present_characters_after": ["Ayame", "Celina", "Kizzie"],
      "absent_but_relevant_after": [],
      "issue_updates": [
        {
          "issue_id": "issue_1",
          "description": "The current proposed course of action. Required next move: The cast must respond to the refusal or choose a different course.",
          "status": "escalating",
          "status_reason": "Ayame refused the current demand, request, or proposed course of action. escalated the plan execution; The cast must respond to the refusal or choose a different course.",
          "pressure_kind": "plan_execution",
          "blocked_what": "The current proposed course of action",
          "required_next_step": "The cast must respond to the refusal or choose a different course."
        }
      ],
      "presence_changes": [],
      "timestamp": "2026-03-14T12:46:00Z"
    }
  ],
  
  "character_stats": {
    "Ayame": {
      "turns": 3,
      "dialogue_count": 3,
      "total_response_length": 342,
      "avg_response_length": 114,
      "spotlight_percentage": 50.0
    },
    "Celina": {
      "turns": 3,
      "dialogue_count": 2,
      "total_response_length": 298,
      "avg_response_length": 99,
      "spotlight_percentage": 50.0
    }
  }
}
```

### 4. `_audit_summary.json` ⭐ PRIMARY AUDIT DASHBOARD
**Purpose**: Session-level audit dashboard aligned with the current continuity/orchestration architecture

**Created**: Refreshed during audited scene flow

**Highlights**:
- `overview`: rounds, turns, update timestamp
- `continuity_overview`: state-change coverage, issue updates, presence transitions, low-change turns
- `scene_template.role_coverage`: role/presence/authority coverage across the cast
- `round_summaries`: one compact entry per round, including continuity movement and summary-block use
- `summary_block_visibility`: raw prompt-visibility metrics
- `summary_block_quality`: availability/injection/fallback rates
- `issue_categories` / `heuristic_issue_categories`: confirmed and text-derived pressure buckets
- `regression_checks`: session-level pass/fail indicators
- **`retrieval_session`** (when present): run-level authored-retrieval observability — **typically after headless simulation** with `--audit` (see *Authored index retrieval* above). Omitted when the session never ran through that merge step (e.g. Streamlit-only audits).

### 5. Granular Bot Logs
**Naming**: `{owner}_session{###}_round{###}_turn{##}_{bot}_{level}.json`

**Examples**:
- `ayame_session042_round001_turn01_director_full.json`
- `ayame_session042_round001_turn01_ayame_full.json`
- `ayame_session042_round001_turn01_narrator_full.json`
- `ayame_session042_round001_turn02_director_light.json`
- `ayame_session042_round001_turn02_celina_light.json`
- `ayame_session042_round001_turn02_narrator_light.json`

**Two Levels**:
- `_full.json`: Complete prompt, raw response, parsed output, context snapshot
- `_light.json`: Message summaries, previews, metadata (smaller, faster to scan)

When scene templates are active, the granular `_full.json` logs also include `context_snapshot.scene_template`
with the template ID, premise, role assignments, presence constraints, and authority labels that were active
for that turn.

## How to Audit a Scene

### Quick Scene Read
1. Navigate to `rp_audits/session_{###}/`
2. Open `_audit_summary.json`
3. Check `overview`, `continuity_overview`, `issue_categories`, and `recent_rounds`
4. Open `_narrative.json` for the prose story and turn-by-turn trace
5. Use `_round_index.json` if you need the per-turn order and continuity counts within a round

### Analyze Character Contributions
1. Open `_narrative.json`
2. Review `turns[]` array
3. Each turn shows:
   - Who acted (`character`)
   - Why they were chosen (`director_reason`)
   - What they did (`character_action`)
   - What they said (`character_dialogue`)
   - Their motivation (`character_motivation`)
   - What changed (`state_changes`)
   - What became actionable (`actionable_implications`)
   - Which issues moved (`issue_updates`)
   - Final rendered output (`rendered_output`)

Turn rows in **`_narrative.json`** aggregate **post-commit** continuity and orchestration fields; they are **not** a spec for mandatory fields on the raw **`{character}_full.json`** `parsed_output` move.

`character_dialogue` here is the **acting character’s full structured `dialogue`** for that beat (canonical story trace). It is **not** a per-viewer view: other characters’ prompts may omit or stub private/directed lines. For perception audits, open each subject’s `{character}_full.json` and compare `input_messages` on the same round/turn, and/or the parsed `move`’s `audibility` / `audience` in ground-truth artifacts.

### Audit Continuity and State Transitions
1. Start with `_audit_summary.json`
2. Review `continuity_overview` for:
   - `turns_with_state_change`
   - `turns_with_issue_update`
   - `turns_without_material_change`
   - `presence_transition_count`
3. Review `round_summaries[]` for:
   - `continuity_event_types`
   - `state_change_count`
   - `issue_update_count`
   - `presence_change_count`
   - `scene_recent_deltas`
   - whether issue updates read like pressure shifts instead of dialogue paraphrase
4. Cross-check `_narrative.json` `turns[]` if you need the exact turn that changed state

When reviewing `issue_updates`, treat the most useful fields as:

- `pressure_kind`
- `blocked_what`
- `required_next_step`
- `status_reason`

The current issue engine is pressure-first but still hybrid. If a turn only updated an issue through
textual fallback, that should be read as a continuity safety-net path rather than the ideal signal path.

### Check Spotlight Balance
1. Open `_narrative.json`
2. Review `character_stats` section
3. Compare `spotlight_percentage` across characters
4. Check `turns` count per character
5. Look at `avg_response_length` for verbosity patterns

### Audit Scene-Template Role Coverage
1. Open `_audit_summary.json`
2. Check `scene_template.template_id` to confirm the intended template was active
3. Review `scene_template.role_coverage` for each assigned character's:
   - `role`
   - `presence_constraint`
   - `authority_label`
   - `turns`
   - `spotlight_percentage`
4. Check `scene_template.must_remain.characters_with_zero_turns`
5. Treat any `must_remain` character with zero turns as a watch item for soft dropout or Director neglect
6. Treat any audit artifact showing role changes after setup as a bug, not a presumed setup error

### Debug Director Decisions
1. Check `_audit_summary.json` `round_summaries[].director_reasons`
2. Check `_narrative.json` `turns[].director_reason`
3. If more detail needed, open granular file:
   `{owner}_session{###}_round{#}_director_full.json`
4. Review `input_messages` for what Director saw
5. Compare `raw_response` vs `parsed_output`
6. Check `metadata.turn_selection_issues` and semantic assessment metadata
7. If scene templates are active, confirm the Director saw `context_snapshot.scene_template`

### Debug Character Behavior
1. Check `_narrative.json` `turns[].character_motivation`
2. If more detail needed, open:
   `{owner}_session{###}_round{#}_{character}_full.json`
3. Review full prompt in `input_messages`
4. Check identity anchors were present
5. Check `turns[].character_role` and `turns[].character_presence_constraint`
6. Check `context_snapshot.continuity_event` and `scene_state_after` to see what state the turn created

### Debug Narrator Rendering
1. Compare `turns[].character_dialogue` vs `turns[].rendered_output`
2. Check verbatim preservation
3. If issues, open:
   `{owner}_session{###}_round{#}_narrator_full.json`
4. Review render prompt and rules given
5. If scene templates are active, confirm the acting character's role metadata is present in the narrator audit

### Character Audit v1 (`metadata.character_audit_v1`)

**Scope:** Advisory, deterministic, **no LLM**. Built from the **validated parsed character move**, the **Director decision**, orchestration snapshots (`recent_structured_moves` tail, optional `continuity_active_issues`), and continuity-backed digests when `continuity_scope` is `continuity_enabled`. **Not** a verdict on continuity correctness.

**Advisory scope — all `derived` dimensions:** Every heuristic under `metadata.character_audit_v1`.`derived` (including dimensions commonly referenced as **CA1–CA7**) is **advisory** and **non-authoritative**. None of these fields are continuity correctness checks, quality metrics, engagement scores, or story-truth indicators on their own.

**What v1 evaluates:** Heuristic dimensions under `derived`: motivation↔action overlap (`motivation_action_alignment`), dialogue↔action token overlap (`dialogue_action_consistency`), issue engagement proxy (`issue_engagement`), self-repetition vs prior structured moves (`repetition_vs_prior_self`), cast-vs-present substring flags (`scene_plausibility_flags`), Director tension/environment (`pressure_director`), and move-emitted pressure fields if present (`pressure_move`).

**CA3 (`issue_engagement`):** A **heuristic proxy** for how issue-related information appears on the **validated parsed move**. It uses **move-emitted** fields when present — **`issue_updates`**, **`tension_shift`**, **`consequences`** — together with **textual / structural heuristics** (for example lexical overlap against continuity-backed issue digests exposed in the audit payload; see per-turn `limitations` strings in logged JSON). It is **not** a direct measure of whether the character **engaged the issue in the story** or whether continuity considers the beat high-pressure. Classifications such as **`possibly_passive`** mean the proxy did not score strong **move-level** linkage — **not** “no in-fiction engagement.” Any apparent mismatch with **`_narrative.json`** or continuity **requires cross-layer verification**; it is **not** automatic evidence of error or disengagement.

**CA7 (`pressure_move`):** Reflects **only** **move-emitted** structured pressure-related fields on the parsed move (the same optional slots CA3 keys on, when they carry pressure-shaped content; see logged `fields_present` / `classification`). A value such as **`none`** means **no such move-emitted pressure structure was scored**, **not** that the scene lacked pressure in continuity. **Director-applied** pressure cues are reported separately under **`pressure_director`** in the same `derived` block — CA7 does **not** subsume Director or continuity pressure. **Continuity-level** pressure and consequences remain authoritative in continuity and **`_narrative.json`**.

**Contract note (optional fields):** The runtime does **not** require the character contract to emit `issue_updates`, `tension_shift`, or `consequences` on every beat. “Low signal” CA3 / CA7 readings therefore often reflect **implicit versus explicit encoding on the move** (an **observability / contract alignment** question for these checks), not by itself **character-agent failure**.

#### Interpretation and Intended Use

- **Expression, not behavior:** CA3 and CA7 measure **move-level expression / observability** — how structured issue and pressure information appears on the **parsed move** — **not** story-level engagement or whether pressure “really” moved in the authoritative scene state.
- **`possibly_passive` (CA3) and `none` (CA7):** Indicate **absence or weakness of explicit move-level structure** as scored by the heuristics — **not** absence of story activity, not absence of continuity issue pressure, and not a statement that the scene failed to progress.
- **Authority:** **`_narrative.json`**, continuity snapshots, and Director audits carry **truth-layer** signals for issues and pressure. Use CA3 / CA7 for **explicit vs implicit comparison**, **schema and prompt evaluation**, and **structured-output debugging** — not as standalone quality or correctness verdicts.

**Recommended analysis order:**

1. Read **`_narrative.json`** and continuity-relevant slices for the beat (and Director audits when selection context matters).
2. Read **CA3 / CA7** on the character `*_full.json` for the same turn.
3. **Compare** move-level encoding to continuity-visible pressure. Divergence **requires cross-layer verification**; treat it as a **diagnostic** prompt to inspect layers, **not** as proof of over-declaration, under-engagement, or implementation error unless other evidence supports that.

**Cross-layer quick reference (neutral framing):**

| Continuity / narrative (truth layer) | CA3 / CA7 (move expression layer) | How to read it |
|--------------------------------------|-----------------------------------|----------------|
| Issue-shaped pressure visible | Strong move-level signals | Move encoding aligns with continuity snapshot; CA fields remain heuristic-only. |
| Issue-shaped pressure visible | Weak CA3 and/or CA7 `none` | Often **implicit engagement** or optional fields omitted on the move — **verify** in narrative/continuity; **not** “ignored issues” by default. |
| Little or no issue-shaped pressure in snapshot | Strong move-level signals | **Verify** in continuity — may reflect verbosity, a different beat shape, or snapshot timing; **not** proof of a defect without context. |
| Little or no issue-shaped pressure in snapshot | Weak / `none` | Often consistent; still **not** a standalone quality score. |

**Known limitations (v1):**

- **CA1 / CA2** — Token overlap only; metaphor, subtext, and reported speech are not modeled (lexical noise; false weak or “disconnected” bands). **Audit v2 escalation** does not consume them (**#42**; scored **`excluded_deprecated`**).
- **CA3 / CA7** — See **CA3**, **CA7**, and **Interpretation and Intended Use** above; do not infer in-fiction engagement or continuity pressure from these dimensions alone.
- **CA5 (`scene_plausibility_flags`)** — Name vs `present_characters` matching is imperfect (display vs internal ids); **informational only**, not a correctness signal.
- **`continuity_scope: orchestration_only`** — Used when the continuity manager is absent on the path that still logs character audit; **rare in normal Streamlit**; less exercised than `continuity_enabled` in typical `--audit` runs (see **Validation (tests)** below for CI coverage).

**Validation (tests):**

- **`orchestration_only` wiring** (`turn_runner_turn` → `build_character_audit_v1` → `log_character_turn_audit`): `tests/test_rp_app_smoke_flows.py::test_execute_character_turn_character_audit_v1_orchestration_only_logged` (no continuity manager; asserts `metadata.character_audit_v1.observed.continuity_scope` and `scene_state_pre_source` on a captured audit entry).
- **`repetition_vs_prior_self` (CA4):** `tests/test_character_audits_v1.py` (`test_ca4_repetition_no_prior_same_speaker`, `test_ca4_repetition_prior_same_speaker_dissimilar_wording`, `test_ca4_repetition_high_similarity_identical_action_dialogue`) use synthetic `orchestration_state.recent_structured_moves`. Short LLM `--audit` runs may still show `prior_turns_compared: 0` when same-speaker structured history is thin — that reflects run length / cast rotation, not necessarily a bug.

### Narrator Audit v1 (per-turn metadata)

Per-turn narrator granular logs (`*_narrator_full.json` / `_light.json`) may include **three advisory or observational layers** under `metadata`, **alongside** the existing `semantic_validation` block. They are **separate keys** and must not be confused with runtime validation:

| Key | Role |
|-----|------|
| `narrator_output_audit_v1` | Heuristic advisory: action vs render, environment cue; **`single_actor_scope_heuristic` is deprecated** (see below). |
| `narrator_validation_audit_v1` | Observational: captures raw render path, deterministic fallback flag, semantic validator payload, and **derived** flags (`fallback_triggered`, `output_replaced`, etc.). Does **not** re-run validation. |
| `prose_dialogue_audit_v1` | Heuristic advisory: readability/redundancy/dialogue/attribution/tone proxies. |

**Non-mutating:** These blobs are computed for logging only. They do **not** change narrator output, fallbacks, or continuity.

**v1 limitations (read audits with these in mind):**

- **Output and prose layers are heuristic-only** (no LLM scoring in v1); false positives/negatives are expected.
- **No narrator audit row** (and thus no v1 blobs) when `log_narrator_render_audit` early-returns because `narrator_raw` is falsy or audits are disabled—same guard as before v1.
- **`single_actor_scope_heuristic` (deprecated, GitHub #9, removal GitHub #41):** **Non-authoritative**, **non-gating**, **not suitable for narrator quality evaluation.** It used substring presence of other cast names (not turn-ownership violations); corpus review found **no meaningful evidence** of real single-actor ownership breaks while the signal produced **high false-positive noise**. The blob is **retained temporarily** for compatibility and historical traceability; **`nar_scope_proxy`** in Audit V2 still logs the same raw fields but escalation **always passes** that check so it cannot qualify LLM escalation on scope alone. **Do not** treat `passes_bar: false` as a narrator defect. Physical removal is tracked on the maintenance issue above.
- **`prose_dialogue_audit_v1` → `attribution_proxy`:** Pronoun-only or implicit attribution can yield **false negatives** (`passes_bar`); see the `limitations` string in the logged blob. This check is **advisory only**, **non-authoritative**, and **non-gating**; high `passes_bar: false` rates are **expected** under v1 and **must not** be read as narrator failure without corroborating signals (see also `interpretation: advisory_non_gating` on the blob when present).
- **`prose_dialogue_audit_v1` → `readability_proxy` / `tone_consistency_local`:** Lexical heuristics only (word length, long-token ratio, simple present-tense token hits). **Heuristic-only**, **non-authoritative**, **non-gating**, **low-signal**; `passes_bar: false` is **not** narrator incorrectness and **must not** be used to assess narrator correctness, trigger escalation, or drive system decisions. Use for **monitoring / observability** only; expect threshold-adjacent noise and false positives (see `interpretation` / `note` on the blob when present; GitHub **#10**).
- **Redundancy** compares against the **prior assistant** message only (last assistant `content` in `chat_history` before the current append), not a long window.

**Scope:** Per-turn narrator renders only; scene-opening narrator calls are **not** covered by v1.

### Debug Summary Retrieval and Prompt Compression
1. Open `_audit_summary.json`
2. Review `summary_block_visibility`
3. Review `summary_block_quality`
4. Check `round_summaries[].summary_block_usage`
5. If needed, open the corresponding `_full.json` files and inspect `metadata.summary_blocks`

## Multi-Character Scenes

For scenes with 2-6 characters:

- All characters appear in `_manifest.json` `cast`
- Scene-template sessions also record `scene_template.role_assignments` in `_manifest.json`
- `_round_index.json` shows turn order inside each round
- `_narrative.json` `character_stats` compares contributions and `turns[]` captures continuity deltas
- `_audit_summary.json` `scene_template.role_coverage` helps spot role imbalance and soft dropout watch items
- `_audit_summary.json` `continuity_overview` helps spot consequence-free drift across the whole session
- Granular files are named by the **acting character** (not owner)

Example 3-character scene:
```
rp_audits/session_042/
├── _manifest.json (cast: ["Ayame", "Celina", "Kizzie"])
├── _round_index.json (round 1 turns: Ayame, Celina; round 2 turns: ...)
├── _narrative.json (stats for all 3)
├── round_001/
│   ├── ayame_session042_round001_turn01_director_full.json
│   ├── ayame_session042_round001_turn01_ayame_full.json
│   ├── ayame_session042_round001_turn01_narrator_full.json
│   ├── ayame_session042_round001_turn02_director_full.json
│   ├── ayame_session042_round001_turn02_celina_full.json
│   └── ayame_session042_round001_turn02_narrator_full.json
├── round_002/
│   └── ayame_session042_round002_turn01_director_full.json
└── ...
```

## Common Audit Tasks

### "Who dominated the conversation?"
Check `_narrative.json` → `character_stats` → `spotlight_percentage`

### "Did the scene keep changing, or did it drift into low-consequence beats?"
Check `_audit_summary.json` → `continuity_overview`

### "Did a `must_remain` character effectively disappear?"
Check `_audit_summary.json` → `scene_template.must_remain.characters_with_zero_turns`

Then cross-check `_round_index.json` and `_narrative.json` to see whether the character remained structurally
present but stopped receiving turns.

### "Who was filling each template role?"
Check `_manifest.json` → `scene_template.role_assignments`

### "Which role was active on a given turn?"
Check `_narrative.json` → `turns[]` → `character_role`

### "Why did the Director choose X at round 3?"
Check `_narrative.json` → `turns[2]` (0-indexed: round 3 = index 2) → `director_reason`

### "Was dialogue preserved verbatim?"
Compare `_narrative.json` → `turns[].character_dialogue` vs `turns[].rendered_output`

### "What was the environment event at round 5?"
Check `_narrative.json` → `turns[4]` → `environment_event`

### "What actually changed on a given turn?"
Check `_narrative.json` → `turns[]` → `state_changes`, `actionable_implications`, `issue_updates`,
`scene_recent_delta`

For issue movement, inspect whether `status_reason`, `pressure_kind`, `blocked_what`, and
`required_next_step` describe a concrete pressure shift or merely restate speech content.

### "Show me the complete scene as rendered"
Check `_narrative.json` → `complete_narrative`

### "How did character motivations evolve?"
Check `_narrative.json` → `turns[].character_motivation` across all rounds for that character

## File Reference for AI Assistants

For workflow from raw artifacts to GitHub issues (classification, evidence, re-test), read **Audit interpretation and issue tracking** above.

When asked to audit a scene:

1. **Locate the session**: 
   - Ask user for the session number (or check most recent session folder)
   - Navigate to `rp_audits/`
   - Find the relevant `session_{###}` folder

2. **Start with the audit dashboard**:
   - Read `_audit_summary.json`
   - Extract `overview`, `continuity_overview`, `issue_categories`, and `recent_rounds`
   - For issue movement, prefer pressure-shaped evidence over raw counts alone

3. **Then read the narrative trace**:
   - Read `_narrative.json`
   - Extract `complete_narrative` for the story
   - Use `turns[]` for exact continuity/state transitions
   - Use `character_stats` for contribution analysis

4. **Drill down as needed**:
   - For specific turn details: use `_narrative.json` `turns[]`
   - For turn order and continuity counts: use `_round_index.json`
   - For bot debugging: open granular `_full.json` files

5. **Cross-reference cast**:
   - Check `_manifest.json` for full character list
   - Ensure you're accounting for all characters in analysis

## Long-Scene Context Safeguard

This RP app uses bounded AutoGen model contexts for the Director, Narrator, and character agents.

- Character agents are created with `BufferedChatCompletionContext(buffer_size=1)`
- Director and Narrator agents are also created with `BufferedChatCompletionContext(buffer_size=1)`
- On reruns and resumed sessions, character agents are rebuilt from stored state so they do not keep stale accumulated internal chat history

This matters because the source of truth for the scene is intended to be:

- `team_state` / `scene_state`
- `character_states`
- recent structured moves (orchestration store may include full **`dialogue`** for ground truth)
- **Perception-filtered** recent scene transcript and structured slices **as assembled into each LLM prompt** (character prompts and Director payload differ; see `perception_audibility.py`)

**Important:** Persisted **`chat_history`** entries store **full narrator `rendered`** text for each beat. That is **not** identical to what another character’s prompt contains after filtering. When auditing “what character X could know,” use **per-character prompt artifacts** or **structured `move` + `audibility`**, not the raw shared chat log alone.

**Audit artifacts:** Turn payloads may include **full parsed moves** (e.g. dialogue previews) for debugging—that reflects **ground-truth structured output**, not necessarily the **redacted** view shown to every other character in the same round.

Not the agent's hidden accumulated chat transcript.

### If a future token-limit error occurs

Future AI assistants auditing a context-length failure should check these in order:

1. Whether the failure came from a single oversized prompt payload
2. Whether bounded model context is still configured on the relevant agent constructors
3. Whether character agents are being rebuilt correctly on rerun / session restore
4. Whether a new feature introduced unbounded data into `scene_state`, prompt assembly, or audit payload construction

Do not assume that a long-scene token failure is caused by the visible prompt text alone. In this codebase, an important prior failure mode was hidden agent-side context accumulation from unbounded model context.

## Technical Notes

- Audit files are **not version controlled** (in `.gitignore`)
- Files are UTF-8 encoded JSON
- Timestamps are UTC ISO format
- File writes are wrapped in try/except - audit failures don't break scene flow
- Round numbers start at 1; `turn_number` increments within each round
- Session numbers are 3-digit, allocated by the audit logger's next-session lookup
