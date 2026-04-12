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

## Issue #29 Investigation Tooling

This section documents **headless harnesses**, **deterministic audit analysis**, and **optional AI-assisted interpretation** introduced or formalized during **Issue #29** (long-session “forgetting” triage). It complements **§D / §F** discipline in **`ARCHITECTURE.md`**: machine-visible audit signals support **Type** / **Layer** hypotheses; advisory AI labels do **not** replace them.

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
- **Not sole validation** — Do **not** file **`bug`** / **`quality`** / **`design_gap`** issues from AI labels alone; align with **`ARCHITECTURE.md` §D** evidence and **deterministic reasoning**.

### 4. Workflow integration (machine vs AI)

**Machine layer** (`issue29_investigation.py`, manifest diffs, harness metrics):

- Detects **presence**, **absence**, **timing**, and **structured support change** in audit JSON.
- Emits **`T_sup`** and **`T_beh`** (and related flags) for deterministic triage.

**AI layer** (advisory causal pass):

- Explains **prioritization and behavior** when outputs ignore **present** support—e.g. **`COMPETING_SIGNAL_OVERRIDE`** vs **`LOW_SALIENCE`**.

**Together:** Use the machine layer to **distinguish persistence / support-loss failures** from **selection / utilization failures** (context **present** at **`T_beh`** but **not** reflected in the move). That split matches **GitHub Issue #29** disposition: **not** a memory-loss **bug** where anchors remain in prompt and continuity; **quality / design_gap** discussion when **utilization** is unreliable under competing narrative pressure (see **`ARCHITECTURE.md`** Issue Tracking **§E** / **§F**).

## Audit interpretation and issue tracking

### Audit pipeline

**Simulation → Audit → Interpretation → Issue detection → Classification → Tracking → Fix → Re-test.**

Headless or in-app runs with audit logging produce artifacts under `rp_app/data/rp_audits/`. **Interpretation** (human and/or AI-assisted) compares layers—`_audit_summary.json`, `_narrative.json`, granular `*_full.json`—before filing work. After a fix, **re-run the same or equivalent scenarios** with audit enabled and confirm the reported pattern is resolved without regressions on adjacent signals.

### Roles

**AI-assisted (agents / tooling):**

- Run simulations (e.g. `--audit`, headless CLI).
- Generate and refresh audit artifacts.
- Interpret outputs: reconcile narrative trace, continuity fields, progression retries, narrator/character audit blocks.
- Propose **candidate issues** with mandatory evidence and a primary **Layer** (see `ARCHITECTURE.md` Issue Tracking).

**Human:**

- Approve or reject filing or scope of an issue.
- Assign priority.
- Steer validation and implementation.

### When to file a GitHub Issue

File when **Pattern status** and **Type** are assigned per `ARCHITECTURE.md` **§I** and **§E**, mandatory evidence (**§D**) is complete, and work should outlive the session. **Pattern status** and **audit-only** discipline are defined there (single instance, escalation, audit-only notes).

### Type and Layer (GitHub body)

- **Type** — `bug` | `quality` | `design_gap` with **PRD/architecture as authority** (`ARCHITECTURE.md` **§E**). Labels alone are not enough.
- **Layer** — Exactly one primary **Layer** from `ARCHITECTURE.md` **§F** (snake_case). Use **orchestration** vs **response_validation** per the explicit boundary in **§F**.
- **Pattern status** — `single_instance` | `potential_pattern` | `confirmed_pattern` (**§I**).
- **Current status** — Workflow line and allowed transitions: `ARCHITECTURE.md` **§H**.

### Tracking policy

- **GitHub Issues** are the system of record (`ARCHITECTURE.md`, Issue Tracking).
- **bug** → implement after **`consensus_reached`**, then validate with audited re-runs; cite PRD/architecture clause in the issue.
- **quality** → calibration or UX; do not file as **bug** without an explicit spec violation.
- **design_gap** → spec or design completion; may pair with **`DESIGN_GAP`** title prefix.

### Evidence requirements

Align with `ARCHITECTURE.md` **§D**:

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

Per-turn logs may include **`audit_v2`** (character) and narrator-side **`audit_v2_narrator`** metadata with extra deterministic checks. Same non-mutating contract as v1 add-ons. Read **`pass` / `fail` / `border`** together with **`limitations`** and assign a GitHub issue **Layer** from `ARCHITECTURE.md` **§F** (e.g. **audit_simulation** for harness/log shape issues; **rendering** or **response_validation** when separate runtime evidence shows a defect outside the audit heuristic). For **`nar_scope_proxy`**, the scored **`result`** is always **`pass`** for escalation purposes while raw scope metrics remain in the payload (**GitHub #9**, removal **#41**).

### Audit signal limitations

Many dimensions are **heuristic**: token overlap, substring scope proxies, short-window attribution tests, etc. They may be **conservative** by design and produce **high false-positive** rates on otherwise healthy runs.

Examples from baseline audits:

- **Prose attribution** / attribution proxies — pronoun-led or implicit attribution often fails fixed-window name tests.
- **CA1 (`char_ca1_motivation_action`)** — low lexical overlap between motivation text and action/dialogue on coherent, subtext-heavy moves.

Treat chronic **`fail`** on these as **quality**-class signals or **design_gap** discussions for metrics unless **independent runtime evidence** shows incorrect behavior attributable to a concrete **Layer**. They **should not** alone trigger “fix the narrator/character” work without that evidence.

### GitHub issue usage (this repo)

- **Labels** (**§C**): **mandatory** on create for tracked issues (`bug`, `improvement`, `research`, `tech-debt`, `blocked`, `validation`, `docs`, `needs-reproduction`, `documentation`, `infrastructure`, `type:*`, … per **§C**). Labels do **not** replace **Type** or **Layer** in the body. **Projects:** **§B.1**–**§B.3** (**RP System Workflow**, **Status**, **Workflow**); **§B.2** verification.
- **Issue body:** `ARCHITECTURE.md` **§D** (canonical contract). **Layer** definitions and tie-breaks: **§F**. **Title** prefixes **`[BUG]`** | **`[QUALITY]`** | **`[DESIGN_GAP]`**: **§G**.
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

- **CA1 / CA2** — Token overlap only; metaphor, subtext, and reported speech are not modeled (lexical noise; false weak or “disconnected” bands).
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
