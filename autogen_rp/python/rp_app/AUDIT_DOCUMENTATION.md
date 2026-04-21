# RP App Audit System Documentation

This document describes the audit logging system for the RP app, enabling scene analysis and bot behavior debugging.

## Onboarding: where to read first

Pointers only — **no new contracts** here. Misreading **#59** applicability or **light** vs **full** rows is the most common triage failure mode.

- **[Audit signal applicability (contract)](#audit-signal-applicability-contract)** — GitHub **#59**: applicability classes, inventory, runtime use allowlist, and interpretation discipline.
- **[Effective user trigger (headless simulation harness)](#effective-user-trigger-headless-simulation-harness)** — `effective_user_trigger`; **Light vs full** serialization (`*_full.json` vs light rows).
- **[Authored index retrieval (standard evaluation mode — Phase 4A)](#authored-index-retrieval-standard-evaluation-mode-phase-4a)** — `metadata.retrieval_summary`, top-level `retrieval_session` on `_audit_summary.json`.
- **[Continuity observability (Issue #79 — closed)](#continuity-observability-issue-79-closed)** — CTAR, `scene_state_after`, summary rollups vs availability markers on `_audit_summary.json`.

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

**Disk layout vs session restore:** Audit JSON under **`rp_audits/session_*`** may **mirror** committed **`SceneState`** / continuity-related fields for a turn (for example **`context_snapshot.scene_state_after`**), but those mirrors exist for **operators and tooling**, not as a parallel store of truth. **Authoritative runtime state** remains in **`ContinuityManager`** and **`SceneState`** in memory, persisted for resume via **`python/data/sessions/*.json`** (see `docs/rp-data-layout.md`). **Session restore reads only `python/data/sessions/*.json` and does not depend on `rp_audits/`.** Removing or omitting audit files does **not** roll back or change continuity; it only removes **observational artifacts**.

### Continuity observability (Issue #79 — closed)

**Runtime truth** remains **`ContinuityManager`**, **`SceneState`**, and the excursion store (**#81**). **Issue #79** adds **named audit surfaces** so operators can inspect committed behavior without treating audit JSON as authority (**#59**).

| Surface | Where it appears | Role |
|--------|------------------|------|
| **CTAR** (`metadata.ctar`) | Character / narrator **`*_full.json`** | Primary structured projection of **`turn_metadata`** for the beat: **`continuity_turn_index`**, optional sorted **`consequences`**, optional canonicalized **`continuity_mutation_resolution`**. **Not** duplicated under **`context_snapshot`**. |
| **`context_snapshot.scene_state_after`** | Same rows | **Direct** **`SceneState.to_dict()`** mirror (no derived presence). |
| **`metadata.excursion_audit_digest_v1`** | Same rows | Sorted id + status only; full records stay in **`ContinuityManager.excursions`**. |
| **`metadata.continuity_audit_origin`** | Same rows | **`pipeline_turn`** when the row corresponds to a committed **`process_turn`** for the current **`turn_counter`** (pending marker match). **Not** used for bypass-only labeling per row; bypass kinds accumulate session-level (see below). |
| **`continuity_observability_summary_v1`** | **`_audit_summary.json`** (top-level when **`ContinuityManager`** is passed into **`write_summary_report`**) | Session rollup only: counts, **`beats_with_mutation_resolution`**, and **`session_audit_origin`** (`has_bypass`, **`bypass_beats`** — bypass kinds only; **`pipeline_turn`** never appears in **`bypass_beats`**). **Mutually exclusive** with **`continuity_observability_status_v1`** for the same write. |
| **`continuity_observability_status_v1`** | **`_audit_summary.json`** (top-level when **no** **`ContinuityManager`** was passed) | Explicit **`{ "status": "unavailable", "reason": "continuity_manager_not_provided" }`** — documents that the continuity-backed rollup was **not** emitted (not a silent omission). **No** fabricated or zero-filled **`continuity_observability_summary_v1`**. Allowed **`reason`** values are defined only in code as **`CONTINUITY_OBSERVABILITY_STATUS_REASONS`** (`continuity_observability_summary.py`). |
| **`bootstrap_interpretation_snapshot_v1`** | **`_audit_summary.json`** (top-level when **`_manifest.json`** contains non-empty **`bootstrap_interpretation`**) | **Observational** copy of **`interpretation_to_jsonable`** (Issue **#94**) persisted on manifest at scene start when audit is enabled. Shape: **`{ "schema_version": "bootstrap_interpretation_snapshot.v1", "interpretation": { ... } }`**. **Not** canonical authored bootstrap (**`AUTHORED_SOURCE_CONTRACT.md`**), **not** a **`Canonical Knowledge Entry`**, **not** retrieval or runtime authority (**#59**). |

**`session_audit_origin`:** Populated via **`flush_continuity_audit_origin_export_payload`**, which is invoked from **`build_continuity_observability_summary_v1`** when the rollup is built. That call **clears** **`continuity_audit_origin_log`** after producing **`has_bypass`** / **`bypass_beats`** for the summary file.

### Continuity turn-level audit record (CTAR) — Issue #79 (Slice 1)

**Purpose:** Per-turn **observability** for continuity metadata tied to the same beat as **`ContinuityManager.turn_counter`** after a successful continuity commit on the logging path, without duplicating full **`turn_metadata_by_index`**.

**Location:** Character and narrator **`*_full.json`** rows expose **`metadata.ctar`** (not under **`context_snapshot`**).

**Slice 1 contents (bounded):**

- **`continuity_turn_index`** — integer beat index (same family as **`turn_metadata_by_index`** keys).
- **`consequences`** — included when present on the turn bucket; classifier lane only (see [Progression enforcement and `consequences` in audits](#progression-enforcement-and-consequences-in-audits)); values are **sorted lexicographically** at write time for deterministic diffing.
- **`continuity_mutation_resolution`** — included **only** when the runtime attached a non-empty resolution object for that beat (Issue **#81** pipeline); **`mutation_type`**, **`source`**, **`payload`** preserved; **`payload`** is **opaque** to audit semantics (do not infer narrative truth from it). Object and nested **`payload`** dict keys are **sorted lexicographically** at write time.

**Authority:** CTAR fields **mirror** runtime **`ContinuityManager`** turn metadata for that beat; they are **not** a separate **Signal id** layer and are **not** on the **#59** runtime use allowlist. Do not treat CTAR as a substitute for **`scene_state`** / **`excursions`** for physical presence or excursion truth—use those stores when debugging committed state.

### Scene state mirror and excursion digest — Issue #79 (Slice 2)

**Purpose:** Per-turn **`*_full.json`** rows expose a **direct runtime mirror** of committed **`SceneState`** after the beat, and a **compact excursion pointer** so operators can see which excursions exist and their lifecycle status **without** duplicating full **`ExcursionRecord`** payloads on every row.

**`context_snapshot.scene_state_after`**

- **Source:** **`SceneState.to_dict()`** only (`audit_runtime_mirrors.scene_state_after_runtime_mirror`). **No** recomputation of presence, **no** alternate presence projections (including **`E_active`**), **no** derived “excursion presence” fields in this object.
- **Expected keys** (from the runtime object): **`location`**, **`present_characters`**, **`offstage_characters`**, **`character_presence_status`** — treat as **authoritative** for what the continuity layer committed for that snapshot.

**`metadata.excursion_audit_digest_v1`**

- **Location:** Character and narrator **`*_full.json`** rows — **`metadata` only** (not under **`context_snapshot`**, not inside CTAR).
- **Shape:** When present, a **sorted** list of **`{"excursion_id": str, "status": str}`** entries (`ExcursionStatus` values, e.g. **`active`** / **`closed`**). **No** participant lists, **no** full excursion dicts, **no** reintegration payloads.
- **Absence:** Omitted when there are **no** excursions on the manager ( **`None`** at write time — not an empty list).
- **Authority:** Full excursion records remain in **`ContinuityManager.excursions`** / session-level continuity artifacts only; per-turn audit rows must **not** become a second source of truth for excursion bodies.

### Continuity audit origin — Issue #79 (Slice 3)

**Purpose:** Classify whether continuity-affecting work ran through the **`process_turn`** / mutation pipeline (**`pipeline_turn`**) or through a **bypass** path, and expose that for per-turn audits and a session-level accumulator (Slice **#79**). **Observational only** — does **not** influence runtime validation or decisions (**#59**).

**Closed kind enum**

| Kind | Meaning |
|------|---------|
| **`pipeline_turn`** | Commit went through **`ContinuityManager.process_turn`** (mutation pipeline). |
| **`bypass_direct_excursion_api`** | **`open_excursion`** / **`update_excursion`** / **`close_excursion`** invoked while **not** in a pipeline excursion commit (direct API). |
| **`bypass_raw_location`** | **`scene_state.location`** assigned outside the pipeline; callers invoke **`notify_raw_location_bypass_for_audit()`** after the write (e.g. Streamlit opener, headless sim seed). |
| **`bypass_oor_reintegration`** | **`apply_excursion_close_reintegration_mutation`** invoked while **not** inside **`process_turn`** (out-of-pipeline reintegration apply / close). |

**Session accumulator:** **`ContinuityManager.continuity_audit_origin_log`** — append-only list of **`{ "continuity_turn_index": int, "kind": str }`** (includes **`pipeline_turn`** entries). **`flush_continuity_audit_origin_export_payload(continuity_manager)`** returns **`{ "has_bypass": bool, "bypass_beats": [...] }`** (**`bypass_beats`**: bypass kinds only) and **clears** the full log. It is **called from** **`build_continuity_observability_summary_v1`** when **`_audit_summary.json`** is written with a continuity manager, so the log is consumed as part of that rollup (not a separate manual export step).

**Per-turn `metadata.continuity_audit_origin`:** When present on character/narrator **`*_full.json`** rows, **`{ "kind": "pipeline_turn", "continuity_turn_index": int }`** — emitted **only** when the manager’s pending pipeline marker matches **`turn_counter`** (avoids labeling non-commit audit paths as pipeline). Omitted when not applicable.

### `continuity_observability_summary_v1` — Issue #79 (Slice 4)

**Location:** Optional **top-level** key on **`_audit_summary.json`** only (not merged into unrelated sections).

**Purpose:** Session-level **rollup** of continuity observability: turn index, mutation-resolution coverage, excursion counts, and **Slice 3** **`session_audit_origin`** (via **`flush_continuity_audit_origin_export_payload`**). **Summary only** — no full CTAR, **`turn_metadata_by_index`**, **`excursions`**, or **`scene_state`**.

**Allowed fields (strict):** **`schema_version`**, **`continuity_turn_count_observed`**, **`beats_with_mutation_resolution`** (sorted ascending), **`excursion_record_count`**, **`excursion_active_count`**, **`excursion_closed_count`**, **`session_audit_origin`** (`has_bypass`, **`bypass_beats`** sorted by **`continuity_turn_index`** then **`kind`**; **`pipeline_turn`** never appears in **`bypass_beats`**).

**Write behavior:** On each summary write, the block is **replaced** in full (no incremental merge of a prior **`continuity_observability_summary_v1`** from disk). Other top-level keys remain owned by existing summary logic.

### `continuity_observability_status_v1` — Issue #79 (availability marker)

**Location:** Optional **top-level** key on **`_audit_summary.json`** only, written **instead of** **`continuity_observability_summary_v1`** when **`audit_logger.write_summary_report`** runs **without** a **`ContinuityManager`**.

**Purpose:** Make non-rollup writes **explicit** so absence of **`continuity_observability_summary_v1`** is not mistaken for a broken audit path.

**Allowed shape (strict):** **`{ "status": "unavailable", "reason": "<closed_enum>" }`**. The closed set of **`reason`** strings is **`CONTINUITY_OBSERVABILITY_STATUS_REASONS`** in **`continuity_observability_summary.py`** (currently **`continuity_manager_not_provided`** only). **No** empty or synthetic summary block.

**Canonical key order:** **`status`**, then **`reason`** (enforced at write time). **`continuity_observability_summary_v1`** and **`continuity_observability_status_v1`** are **mutually exclusive** on the same report (enforced in **`audit_logger_summary_report.write_summary_report`**).

### Offline evaluation layer (Issue #66 — v1)

**Purpose:** Offline-only mechanism that reads existing audit artifacts and emits **structured judgments**. It does **not** define a detection layer, quality gate, or runtime authority.

**Scope:** Implemented in `scene_eval_v1.py` (`run_scene_eval_v1`). **Fixed predicates only**; logic is **deterministic** and **artifact-driven** (character `*_full.json` via `load_character_audit_rows`, optional `structured_eval` JSON).

**Critical constraints:** Judgments are **descriptive**, not pass/fail or system verdicts. They **must not** infer narrative or continuity correctness. They **must not** consume Character Audit v1 **CA3–CA7** `derived` fields, Audit v2 heuristic bundles, narrator/prose heuristic audits, or LLM-generated audit layers. The layer **must not** modify runtime behavior, prompts, audit writers, or continuity state.

**Interpretation:** `fired` means the predicate’s observable condition held — **not** failure. `clear` means that condition was not observed — **not** success or health. `inconclusive` means inputs were insufficient or out of scope for that predicate.

Normative applicability, authority, inventory, and examples for operators and tooling are defined under **[Audit signal applicability (contract)](#audit-signal-applicability-contract)** below (**GitHub #59**).

### Offline evaluation layer (Issue #69 — `scene_eval_v2`)

**Purpose:** **In-family** extension of Issue #66: same offline, artifact-driven judgment envelope, **not** a parallel evaluator system. **`scene_eval_v2`** adds versioned predicates that require **narrator `*_full.json`** rows and **deterministic cross-row joins** to character rows. Still **offline-only**; **not** runtime authority (**#59** allowlist remains the only runtime coupling path).

**Implementation:** `scene_eval_v2.py` (`run_scene_eval_v2`). **Includes all Issue #66 v1 judgments** by delegating to `run_scene_eval_v1`, then appends v2 predicates (currently **`verbatim_dialogue_contract_v1`**).

**Contract delta vs v1**

| | v1 (#66) | v2 (#69) |
|---|----------|----------|
| Character `*_full.json` | Yes (sole row source for v1 predicates) | Yes (unchanged v1 predicates + join target) |
| Narrator `*_full.json` | Not read by v1 | **Read** for v2 predicates |
| `context_snapshot` | Not used by v1 predicate logic | **Used** for v2 **join proof**: **`continuity_turn_index`** (primary, Issue #72 — post-commit beat identity); legacy fallback **`continuity_event.event_id`** + optional embedded **`continuity_event.turn_index`** when top-level index absent; plus `character` |
| `metadata.narrator_validation_audit_v1` | Listed as observational telemetry elsewhere | **Used as input** to `verbatim_dialogue_contract_v1` (`observed.rendered_final` only) |

#### Canonical structural join contract (Issue #72)

Normative rules for **deterministic cross-row joins** in **`scene_eval_v2`** (currently **`verbatim_dialogue_contract_v1`**):

- **`context_snapshot.continuity_turn_index`** — **Primary structural join key** when **present** on both rows: integer **post-commit** beat identity (same value as **`ContinuityManager.turn_counter`** after a successful **`process_turn`** for that beat—see **`context_snapshot.continuity_turn_index` (field)** below). **Matching values** are the **authoritative** proof of beat linkage for evaluation. This identity is **independent** of whether a **`PublicEvent`** was created for the beat.
- **`context_snapshot.continuity_event.event_id`** (when `continuity_event` embeds a serialized **`PublicEvent`**) — **Optional** and **semantic** (narrative tooling, knowability, grounding refs). **Legacy join fallback only:** use **only when** one or both rows **lack** top-level **`continuity_turn_index`**, and then **only** if **both** sides expose a **non-empty**, **equal** `event_id`. Missing `event_id` on a row is **not** a defect when primary join succeeds.

**`verbatim_dialogue_contract_v1`** must **not** infer joins from **`(round_number, turn_number)`** alone or fabricate beat identity; pairing is **explicit** via the primary or legacy paths above.

#### `context_snapshot.continuity_turn_index` (field)

- **Definition:** On **character** and **narrator** `context_snapshot` objects, the integer **`ContinuityManager.turn_counter`** at audit snapshot time (same index family as **`turn_metadata_by_index`** and scene-grounding audit **`phase1.continuity_turn_index`**). The writers emit this key **only** when **`turn_runner_audit._get_turn_continuity_payload`** returns a **non-`None`** beat index, which **requires** **`continuity_manager` non-`None`** and **`continuity_manager.scene_state` non-`None`**—i.e. continuity snapshot input is **available**, not pre-commit or speculative. On the **dominant** **`execute_character_turn`** path, that snapshot follows a **successful** **`process_turn`** for the acting beat and **no** continuity rollback before **`log_character_turn_audit`**; the field is **omitted** on paths that only log **minimal** failure/retry snapshots **without** that payload.
- **Source:** **`log_character_turn_audit`** and **`log_narrator_render_audit`** (**`turn_runner_audit`**) set **`context_snapshot.continuity_turn_index`** from that payload when the index is present.
- **Guaranteed (current writers):** Full **`log_character_turn_audit`** / **`log_narrator_render_audit`** rows include this key **only when** the payload contract above holds. In the primary character turn path, that aligns with a **successful** **`process_turn`** and **no** continuity rollback before the full audit write (failed validation / progression rollback / similar paths emit **minimal** snapshots—e.g. **`log_turn_failure_fn`**—**without** this field). Offline evaluation uses matching values as the **primary** narrator↔character join **when both rows include the key**.
- **Not implied / absent:** **`continuity_manager` or `scene_state` unavailable**, **pre-commit** or **non-committed** snapshots, **failure / retry** rows that omit the full continuity snapshot, **continuity inactive** for the session, **`*_light.json`**, **pre–#72** artifacts, or serialization defects. Evaluators may attempt **legacy** **`continuity_event.event_id`** only when both sides provide it; otherwise the join is **`inconclusive`** (not dialogue-contract **`fired`** / **`clear`**).

**Invocation:** **Explicit only.** Headless simulation **does not** run `scene_eval_v2` automatically. Operators, CI, or scripts call `run_scene_eval_v2(session_dir, ...)` after audits exist.

**Output artifact (stable path):** By default writes **`<session_dir>/_scene_eval_v2.json`** (JSON with `scene_eval_version`, `session_dir`, optional `structured_eval_path`, `judgments`, `artifact_path`). Per-turn judgments live **only** in the `judgments` array; **`structured_eval`** rollups (if any) remain **optional summaries** and must not be the sole record.

**Predicate: `verbatim_dialogue_contract_v1` (`predicate_version` `1`)**

- **Normalization:** `dialogue = str(parsed_output.get("dialogue") or "").strip()` on the **paired** character row only. **No** quote folding, punctuation normalization, or multiline tricks. Required literal substring: ASCII double quotes (U+0022) around `dialogue` — i.e. the substring `f'"{dialogue}"'` — must appear inside `rendered_final`.
- **Outcomes:** empty `dialogue` → `skipped`; non-empty + literal present → `clear`; non-empty + absent → `fired`; join/linkage failure → `inconclusive`.
- **Verbatim join (implements [canonical contract](#canonical-structural-join-contract-issue-72)):** **Primary join** = **equal** integer **`context_snapshot.continuity_turn_index`** on narrator and character rows (**no** dependency on **`PublicEvent`** existing). **Legacy join** = **equal** non-empty **`context_snapshot.continuity_event.event_id`** when top-level **`continuity_turn_index`** is missing on one or both sides, plus legacy **`continuity_event.turn_index`** agreement when **both** sides expose embedded `turn_index`. **No inferred joins** (including from **`(round_number, turn_number)`** alone). **Per narrator row:** `bot_type` narrator; **`context_snapshot.character`** non-empty; **exactly one** character `*_full.json` with same `round_number`, `turn_number`, `bot_name ==` acting character. Character `parsed_output` must be a **dict** with **`dialogue`**; narrator must expose **`metadata.narrator_validation_audit_v1.observed.rendered_final`** as a **string**. **Duplicates** or **any** failed check → **`inconclusive`** (no guessing).

**Operator rule (telemetry vs evaluation layer):** For questions about this predicate, **`scene_eval_v2` judgments are the authoritative evaluation-layer record.** Dialogue-related **telemetry** (e.g. `prose_dialogue_audit_v1`, Audit v2 dialogue integration) remains **diagnostic context**. **Disagreement is not a system contradiction** — do not revert to “metric = verdict” (**Issue #60**).

**Interpretation:** Same as v1: `fired` / `clear` / `skipped` / `inconclusive` are **not** continuity verdicts or runtime health.

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

For the **full** end-to-end procedure (corpus definition, independent validation, disposition, and **#66** alignment), see **[Audit Signal Evaluation Methodology](#audit-signal-evaluation-methodology)** (GitHub **Issue #71**).

#### Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)

<a id="issue67-operator-interpretation"></a>

**Interpretation axes**

| Axis | Governs | Meaning |
|------|---------|--------|
| **#59 applicability class** (`always-on` / `conditional` / `heuristic / advisory`) | **Silence, absence, and when silence is diagnostically meaningful** | Contract in this document (“Key interpretation rule”, “Interpretation discipline”): predicates, always-on shape expectations, heuristic corroboration rule. |
| **Issue #67 engineering family** (`telemetry` / `guardrail` / `aggregation` / `heuristic proxy`) | **What the emitted JSON *is* as an engineering artifact** | Describes instrumentation vs rollup vs orchestration mechanism vs true quality proxy—not pass/fail and not substitute for continuity. |

**What each axis governs**

- **What the signal *is* (nature of the blob):** **Engineering family** (telemetry = trace/snapshot/config; aggregation = packaged metrics; guardrail = orchestration mechanism; heuristic proxy = scored/structured quality proxy such as CA* / Audit v2 bands when applicable).
- **How silence/absence is interpreted:** **Only #59 applicability class** (plus stated predicate for `conditional`, shape rules for `always-on`, corroboration for `heuristic / advisory`). **Engineering family must not be used to invent new silence rules.**

**Reading rule (when Class = `heuristic / advisory` and engineering family = `telemetry` for the same row)**

1. **Step 1 — Silence:** Apply **#59** only (evaluate predicate; apply silence semantics from the inventory row).
2. **Step 2 — Content:** Read the field as **telemetry** (pressure/config/trace/rollup snapshot), **not** as a labeled defect detector. **Do not** apply TP/FP or “detector fired” language to **telemetry** rows. Per **Interpretation discipline** below, TP/FP language applies only after locating the Signal id and applying class; **telemetry** rows are **not** “fired” as failures.
3. **Gloss:** In this document, **`heuristic / advisory`** (applicability class) does **not** mean “this row is a narrative heuristic detector.” It means **#59 layer semantics** (non-authoritative; corroborate). **`Heuristic proxy`** (engineering family) is reserved for **true proxy/scoring-style** inventory rows (e.g. CA dimensions, Audit v2 checks)—**orthogonal wording** to avoid collapsing “heuristic” into “detector.”

**Heuristic proxy (engineering family)** — standalone definition

**Definition:** A **named, emitted score, band, or structured judgment** whose **purpose** is to **stand in for** a qualitative property of the scene or output (e.g. alignment, repetition, prose checks) using **deterministic rules, lexical checks, or model-assisted scoring**—**without** being continuity truth and **without** being raw instrumentation or a rollup artifact.

| Contrast | Meaning |
|----------|--------|
| **vs telemetry** | Telemetry is **state/trace/config serialization** (what was present, counts, fingerprints, snapshots). It does **not** assign a **scene-quality proxy score**; it records **what happened** in the logging pipeline. |
| **vs aggregation** | Aggregation is **packaged rollups** (metrics bundles, session summaries). It may combine numbers but is **not** itself a per-turn **proxy score** row unless the inventory lists that rollup as a separate Signal id. |
| **vs guardrail** | Guardrail is **runtime orchestration or enforcement** (selection, retries, validation gates). It **acts** on the turn path. A **heuristic proxy** in audits **observes**; it does **not** enforce. |
| **vs #59 `heuristic / advisory` class** | That **class** governs **silence and corroboration obligations** for an inventory row (“not continuity-competitive; corroborate before runtime bugs”). It does **not** mean the row is an **engineering-family `heuristic proxy`**—many rows are **`heuristic / advisory` in #59** but **`telemetry` in engineering family** (see reading rule above). **`Heuristic proxy` (family)** is reserved for **actual proxy/scoring-style** inventory rows (e.g. CA-derived dimensions, Audit v2 checks named in the table). |

**Anti-ambiguity:** The word **“heuristic”** in documentation **must** be read with its **modifier**: either **“#59 applicability: heuristic/advisory”** (silence semantics) or **“engineering family: heuristic proxy”** (proxy score nature)—**never** as shorthand for **“detector.”**

**Normative rule**

**Operators MUST NOT infer detector behavior, defect detection, pass/fail scene verdicts, or TP/FP labels from the #59 applicability class alone.** Applicability class **only** constrains **silence/absence interpretation** and **corroboration rules** per the inventory row; **detector-like conclusions** require an **explicit** engineering-family **`heuristic proxy`** (or a documented offline **`detector`** / evaluation layer **outside** this inventory rule) **and** a **declared** evaluation methodology—**never** from **`conditional`**, **`always-on`**, or **`heuristic / advisory`** **by themselves**.

**Anti-drift (normative)** — Except for this subsection and the **inventory table** below (including **Engineering family** column and per-row **Description**), **no other section of this document may define, redefine, or qualify the meaning of** `#59 applicability class`, **`heuristic proxy` (engineering family)**, **`telemetry`**, **`aggregation`**, **`guardrail`**, or **detector-like reading rules** for inventory-listed fields. Other sections **must** use **one sentence + link** to this subsection and the relevant **Signal id** row.

### Audit signal applicability inventory

**Excluded from this table:** **Runtime outcome records** (see **Authority rules**). Examples: `stage: validation_progression_retry`, validation reason strings, successful `turn_execution_metadata` fields that mirror retry state — interpret via **`ARCHITECTURE.md`** and validation docs, not applicability class.

| Signal id | Description | Class | Predicate (conditional only) | Silence semantics | Engineering family |
|-----------|-------------|-------|-------------------------------|-------------------|---------------------|
| `cav1.schema_version` | `metadata.character_audit_v1.schema_version` when the v1 block is written | always-on | `metadata.character_audit_v1` object is present on the character audit row | When the predicate holds, missing `schema_version` indicates a serialization / contract defect in the audit path. When the v1 block is absent entirely, evaluate **`cav1.block`** first (conditional). | telemetry |
| `cav1.block` | Entire `metadata.character_audit_v1` advisory bundle | conditional | Per-turn character audit logging is enabled **and** the character turn produced a logged `*_full.json` / `*_light.json` row where v1 is attached | When audit logging is off or the row type omits v1, absence is **neutral**. When the predicate holds, absence of the block is an audit-path defect. | telemetry |
| `cav1.observed` | `metadata.character_audit_v1.observed` (Director excerpt, digests, tails; pre-continuity context) | heuristic / advisory | Same as `cav1.block` | Silence or empty excerpts are common on short prompts or redacted paths; interpret only in context of **`cav1.block`** and continuity. | heuristic proxy |
| `cav1.derived.issue_engagement` | CA3 — move-level issue linkage proxy | heuristic / advisory | Same as `cav1.block` | `possibly_passive` means weak **move-level** linkage, not “no story engagement.” | heuristic proxy |
| `cav1.derived.repetition_vs_prior_self` | CA4 — repetition vs prior self | heuristic / advisory | Same as `cav1.block` | Silence uncommon when block present; interpret with tail windows in `observed`. | heuristic proxy |
| `cav1.derived.scene_plausibility_flags` | CA5 — plausibility flags | heuristic / advisory | Same as `cav1.block` | Advisory only; corroborate with scene state. | heuristic proxy |
| `cav1.derived.pressure_director` | CA6 — Director pressure snapshot | heuristic / advisory | Same as `cav1.block` | Reflects decision excerpt, not full orchestration truth. | heuristic proxy |
| `cav1.derived.pressure_move` | CA7 — declared pressure fields on move | heuristic / advisory | Same as `cav1.block` | `none` / weak readings reflect optional move fields, not absence of continuity pressure. | heuristic proxy |
| `av2.check.char_ca4_repetition` | Audit v2 CA4 repetition band | heuristic / advisory | `metadata.audit_v2` present with character deterministic bundle | `fail` / `border` / `pass` are heuristic bands; corroborate with narrative. | heuristic proxy |
| `av2.check.char_ca7_declared_fields` | Audit v2 CA7 declared fields | heuristic / advisory | Same as `av2.check.char_ca4_repetition` | Border/fail still advisory vs continuity. | heuristic proxy |
| `av2.check.char_masked_progression_strict` | Audit v2 strict-tier **masked progression** observability (classifier lane empty + structural proxy) | heuristic / advisory | Same as `av2.check.char_ca4_repetition` | Payload `observation` is `fired` / `clear` / `skipped` — **not** continuity truth or a defect signal. Escalation tri-state is always **`pass`** (**#73**); does not qualify LLM audit or product escalation. | heuristic proxy |
| `av2.check.nar_strict_action_overlap` | Narrator strict action overlap | heuristic / advisory | `metadata.audit_v2_narrator` (or narrator bundle path used for prose) present | Absent when narrator v2 not built; neutral. | heuristic proxy |
| `av2.check.nar_environment_cue` | Environment cue presence in render | heuristic / advisory | Same as `av2.check.nar_strict_action_overlap` | Conditional on Director/environment context; `environment_event` absent → check often inert (see payload). | heuristic proxy |
| `av2.check.prose_readability` | Prose readability proxy | heuristic / advisory | Prose bundle present in v2 path | High false-positive rate possible; not narrator correctness. | heuristic proxy |
| `av2.check.prose_redundancy` | Prose redundancy Jaccard | heuristic / advisory | Same as `av2.check.prose_readability` | `prior_turns_used == 0` → scored **`pass`** path per policy; interpret with `limitations`. | heuristic proxy |
| `av2.check.prose_dialogue_integration` | Prose dialogue integration proxy | heuristic / advisory | Same as `av2.check.prose_readability` | Advisory only. | heuristic proxy |
| `av2.check.prose_attribution` | **Removed (GitHub #40).** Legacy v2 check (lexical proximity near quoted dialogue; fed from v1 `attribution_proxy`). | heuristic / advisory | Historical `*_full.json` only | **New outputs:** absent — **neutral**. **Historical rows:** legacy telemetry only; do **not** treat as attribution truth (see **Issue #40 — Deprecation of narrator attribution heuristic**). | **removed** |
| `av2.check.prose_tone` | Prose local tone proxy | heuristic / advisory | Same as `av2.check.prose_readability` | Lexical heuristic only. | heuristic proxy |
| `av2.llm_character` | LLM-assisted character audit v2 layer (when enabled) | conditional | LLM audit enabled for the run/build path | When disabled, absence is **neutral**. When enabled but missing where expected, investigate harness. | heuristic proxy |
| `av2.llm_narrator` | LLM-assisted narrator audit v2 layer | conditional | Same as `av2.llm_character` | Same silence semantics. | heuristic proxy |
| `av2.llm_prose` | LLM-assisted prose audit v2 layer | conditional | Same as `av2.llm_character` | Same silence semantics. | heuristic proxy |
| `metadata.progression_advisory` | Stall / progression advisory snapshot (not continuity truth) | heuristic / advisory | Progression advisory MVP active for session | When feature off, absence is **neutral**. | telemetry |
| `metadata.anti_regression_advisory` | Anti-regression advisory snapshot | heuristic / advisory | Anti-regression path armed / used for session | When inactive, absence is **neutral**. | guardrail + telemetry |
| `metadata.retrieval_summary` | Retrieved bundle summary (counts/refs) | conditional | Authored retrieval or merged episodic path produced a summary for the character turn | When retrieval OFF and no merge, absence is **neutral**. | telemetry |
| `metadata.scene_grounding` / `scene_grounding_summary` | Grounding observability snapshot | conditional | Scene grounding MVP produced facts for projection | When no promoted facts, absence or empty snapshot is **neutral**. | telemetry (partial) |
| `metadata.support_manifest` | Support manifest `support_manifest.v1` | conditional | Character `*_full.json` audit path attached manifest (`audit_support_manifest`) | Per **Support Manifest** section: absent on Director/Narrator rows by design — **neutral**. | telemetry |
| `audit.retrieval_session` | `_audit_summary.json` top-level `retrieval_session` | conditional | `write_summary_report` followed by `apply_retrieval_session_to_audit_summary` (Streamlit `refresh_audit_summary_report` and headless `run_headless_llm_scene`) | When audit is disabled or no summary file, **neutral**. | telemetry |
| `audit.effective_user_trigger` | Top-level `effective_user_trigger` on **full** per-turn rows | conditional | Full per-turn row (`*_full.json`); key present on **all** such rows (Streamlit or headless). **Per-turn user-trigger schedule** (headless CLI) changes **values** only, not key presence | Light audits omit by design; absence **neutral** for light rows. | telemetry |
| `context_snapshot` | Top-level continuity/scene/orchestration snapshot for the turn (not continuity truth) | conditional | Parsed artifact is a **full** per-turn audit row: filename matches `*_full.json` **and** root `bot_type` ∈ {`character`, `director`, `narrator`} | If predicate **false** (`*_light.json` or invalid row): **neutral**. If predicate **true**: **absence** of top-level `context_snapshot` is **neutral**; **presence** is telemetry only. | telemetry |
| `structured_eval.bundle` | Headless `structured_eval` / metrics JSON (scenario id, metrics, `retrieval_session`, verdict flags when set) | conditional | Run requested metrics output (`--metrics-out` or suite aggregation) | Absent file or block means no metrics artifact — **neutral** for audit quality of the scene itself. | aggregation |

### Worked examples

#### Example A — Always-on (`cav1.schema_version`)

**Artifact:** `round_001/*_turn03_Celina_full.json` (character), `metadata.character_audit_v1` present.

**Expectation:** `schema_version` is a non-empty string (current v1 schema).

**If missing:** Treat as **audit serialization / contract failure** (logging pipeline), not as evidence Celina “broke” continuity. Open an **audit_simulation** or infrastructure issue with the file path and writer version.

#### Example B — Conditional (`audit.effective_user_trigger`)

**Artifact:** Same `*_full.json` row from a headless run using **`--user-trigger-schedule`**.

**Predicate:** Full audit row + harness supplied an override line for this orchestration turn.

**If key absent:** First confirm **`light` vs `full`** serialization (light omits the field by contract). Then confirm the schedule JSON and CLI actually targeted this turn index. If predicate true and full row still lacks the field, treat as **harness / writer** issue — **not** evidence the model ignored the user line in continuity.

#### Example C — Heuristic / advisory (`cav1.derived.repetition_vs_prior_self` + `av2.check.char_ca4_repetition`)

**Artifact:** `metadata.character_audit_v1.derived.repetition_vs_prior_self` shows elevated similarity vs the speaker’s prior structured move; Audit v2 row `check_id: "char_ca4_repetition"` may score `border` or `fail` per band rules.

**Interpretation:** Repetition bands are **structural** similarity signals, not proof of a bad beat. Do **not** infer a **response_validation** or **continuity_state** bug from CA4 alone. Read **`_narrative.json`** and scene context; file **quality** / calibration under **audit_simulation** only with corroboration — not a runtime regression without independent runtime evidence.

**Historical note:** Legacy CA1/CA2 lexical overlap fields and Audit v2 `char_ca1_*` / `char_ca2_*` rows are **removed** from current emission (**Issue #44**); older session JSON may still contain them.

### Runtime use allowlist

**Status:** **Empty** — no inventory Signal id is currently authorized to drive **runtime authority** decisions.

**How entries are added** — See **Authority rules → C. Positive exception mechanism**. Each new row must list Signal id, runtime subsystem, effect, and PRD/`ARCHITECTURE`/governance anchor, and must be paired with a tracked GitHub Issue.

**How entries are removed** — Same process in reverse: doc edit + issue note so downstream tooling does not rely on stale coupling.

### Signal interpretation envelope (`metadata.signal_interpretation`) — Issue #68

**Purpose:** Machine-readable **operator interpretation** for a **partial** set of advisory/grounding audit blocks. This object is **not** a **#59 Signal id**, **not** narrative truth, **not** on the **[Runtime use allowlist](#runtime-use-allowlist)**, and **must not** be read as input to any **runtime authority** decision. Runtime code **does not** consume this field.

**Shape (v1):**

- `metadata.signal_interpretation.schema_version` — integer, **`1`**.
- `metadata.signal_interpretation.signals` — object map **`signal_id` → `{ "role": "telemetry" | "guardrail" | "aggregation" }`** (closed enum).

**v1 registry (partial — not exhaustive over all metadata):**

| `signal_id` (map key) | `role` | Audit blocks covered |
|------------------------|--------|----------------------|
| `progression_advisory` | `telemetry` | `metadata.progression_advisory` |
| `anti_regression_advisory` | `guardrail` | `metadata.anti_regression_advisory` |
| `scene_grounding` | `telemetry` | `metadata.scene_grounding` (Phase 1 family: `phase1` + optional `summary`) |

An id appears under **`signals`** only when the corresponding **`metadata`** block is present on that row. **No implicit role** for unregistered keys; **no** inference from naming alone.

**`role` vs #59 / #67:** These strings are **reading hints** for operators. They are **not** #59 applicability classes (`always-on` / `conditional` / `heuristic / advisory`). **`guardrail`** here means “this audit blob reflects **narrow orchestration guardrail** visibility,” not “runtime guardrail enforcement reads this audit field.” See **[Operator interpretation — #59 applicability class vs Issue #67 engineering family](#issue67-operator-interpretation)** for inventory-backed signals.

**Coverage gaps (normative):**

- **STOP-REGISTRY-GAP:** A registered payload exists (e.g. `progression_advisory`) but **`signal_interpretation.signals` omits that id** → treat as **audit writer / rollout defect**, not as story meaning.
- **STOP-UNREG:** A metadata block exists whose **interpretation is not** in the v1 registry → apply **observational-only** rules from this contract and #59; **do not** assign a `signal_interpretation` role by guesswork.
- **STOP-4:** **`signal_interpretation` absent** on a row → v1 role map **not in force** for that row; fall back to **[Audit signal applicability (contract)](#audit-signal-applicability-contract)** and **[Progression advisory](#progression-advisory-mvp-in-audits)** / **[Anti-regression](#anti-regression-advisory-mvp-in-audits)** / **[Scene Grounding](#scene-grounding-mvp-in-audits)** sections **observational-only**. Do not infer correctness or failure from absence of this envelope alone.

**Absence rule (progression / anti-regression):** **Absence** of `progression_advisory` or `anti_regression_advisory` (or of the whole envelope) **must not** be read as evidence of correct/incorrect scene health, stall, regression, or grounding pass/fail. **Presence** does not imply a verdict either.

#### Deterministic operator recipe (Issue #68)

Use **continuity-backed state** and **runtime outcome records** for any **verdict-style** claim (stall, regression bug, grounding wrong). Use **telemetry / guardrail / aggregation** blocks only as **mechanism or pressure** visibility.

1. Load **continuity** slice / **`_narrative.json`** / committed **`consequences`** as needed for the question.
2. Load **runtime outcome records** for the turn (`stage`, retry flags, validation reasons — factual log only).
3. Open **`metadata`** for the audit row.
4. If **`signal_interpretation` missing** → **STOP-4**; continue with #59 observational rules only (no v1 role map).
5. If present, confirm **`schema_version === 1`**. If unsupported version → stop applying v1 role semantics; treat as **documentation / writer mismatch**.
6. For **verdict questions** (“is the scene stalled?”, “is grounding broken?”): **do not** answer from **`progression_advisory`**, **`anti_regression_advisory`**, or **`scene_grounding`** alone; require **continuity** (+ **runtime outcome records** when the question is about validation path). If insufficient → **no verdict**.
7. For **`metadata.scene_grounding.phase1`:** use as **non-authoritative mirror** only; **`grounding_derivation_refs`** lists **continuity-native** ids when emitted; if the key is **omitted**, no clean refs were available at write time (**reduced scope**, not proof of absence of promotion). On conflict, **continuity wins**.

**Phase 2:** Full prompt-projection parity for grounding in audits is **out of scope for #68** (explicit non-goal unless a later issue promotes it).

### Progression advisory (MVP) in audits

**Signal id:** `metadata.progression_advisory` — interpretation axes and silence rules: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** telemetry; not a discriminative scene-failure detector).

When enabled, Director turn metadata may include a **`progression_advisory`** object (not continuity truth): **`stall_score`**, **`progression_pressure`** (`low` / `medium` / `high`), template-sourced **`recommended_channels`**, human-readable **`note`**, **`stall_components`** (booleans: same phase, high tension, issue stability, exact structural repetition), and related fields consistent with `progression_advisory.py`. Logs may also record when advisory text is injected into prompts or when beat-shift eligibility is influenced by the unified **`stall_score`** threshold.

### Anti-regression advisory (MVP) in audits

**Signal id:** `metadata.anti_regression_advisory` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** guardrail + telemetry; runtime orchestration guardrail in `anti_regression_advisory.py`, audit row is a snapshot).

Director turn metadata may include **`anti_regression_advisory`**: **`active`** (whether the ANTI-REGRESSION Director prefix was injected this call), **`ping_pong_detected`**, **`post_break_window_active`**, **`low_player_agency`**, **`ping_pong_actors`** (the two alternating `next_actor` ids when detected), and **`ticks_after_decrement`** (remaining post-break window ticks after this Director step). This mirrors orchestration cache fields from `anti_regression_advisory.py` and is not continuity truth. Application logs under **`rp_app.anti_regression_advisory`** record injection and post-break arming when enabled.

**Character** and **Narrator** per-turn audit metadata also include **`progression_advisory`** and **`anti_regression_advisory`** snapshots read from orchestration cache at log time (same fields as above, where present). That lets you correlate each rendered beat with stall pressure, ping-pong flags, and post-break window state without relying on Director JSON alone.

### Progression enforcement and `consequences` in audits

When progression enforcement is on, a character failure log may show **`validation_progression_retry`**: the move passed parse/presence checks but **Q1–Q4** in **`progression_enforcement.py`** failed after continuity **`process_turn`**, so continuity was rolled back and the turn retried. **Q1–Q4 logic is unchanged;** they consume **`turn_metadata_by_index[*]["consequences"]`** and related continuity outputs.

Structured **`consequences`** (and the enriched narrative mirror of them) are emitted by **`continuity_consequence_classifier.py`** via **`ContinuityManager._classify_turn_consequences`**. **Fixes for false retries** from empty or overly thin consequence lists are **continuity-side classification** improvements—**not** enforcement weakening. **`REPOSITIONING`** uses bounded movement/locus/transition rules and excludes **negated `turn`** phrasing as locomotion; **`REFUSAL`** / stance uses deterministic intent-aligned rules; **legacy** dialogue markers **`no` / `not`** match as **standalone words** only (word boundaries), not substrings inside words like "nothing" or "know". **Multi-tag** categories per turn remain supported (per-category dedupe only). See **`ARCHITECTURE.md`** (*Progression enforcement vs continuity classification*).

**`exit` in audits vs on-stage roster:** Event-facing lines and **`recent_delta`** are aligned with **effective** **`present_characters`** when a classified exit does not remove the actor (see **`ARCHITECTURE.md`** — *Exit narrative vs effective on-stage presence*). The **`exit`** string may still appear in **`consequences` / tags** in **`turn_metadata`** for those turns. Interpret **physical presence** from **`SceneState`** (e.g. **`present_characters`**), not from **`exit`** alone.

#### Classifier lane vs continuity truth (audit reading)

- **Classifier lane** — **`metadata.consequences`** / **`turn_metadata["consequences"]`**: the **deterministic** tag list from **`continuity_consequence_classifier`** (via **`ContinuityManager._classify_turn_consequences`**). Use it for **Q1-style** progression signals and taxonomy, not as a full inventory of “what changed.”
- **Continuity truth** — Committed **events**, **issue** deltas, **scene** / registry updates, and related continuity-owned fields after **`process_turn`**. These can move even when the classifier lane is empty.

**Reading rule:** An **empty** **`metadata.consequences`** list does **not** imply **no progression** or **no structural change**; always cross-check **`context_snapshot.continuity_event`** (or narrative continuity slice), **`metadata.issue_updates`**, and allowlisted **`scene_state_updates`** / **`parsed_output`** when triaging audits. See **`ARCHITECTURE.md`** (*`turn_metadata["consequences"]` (classifier lane) vs continuity commits*).

#### Masked progression (interpretation concept; GitHub **#73**)

**Masked progression** names an **audit interpretation** pattern: continuity or progression-relevant paths advanced (e.g. issues, committed event fields, allowlisted registry updates; **Q2** / **Q4** can qualify) while the **classifier lane** stayed **empty**. It is a **label for operators and offline analysis**, not a runtime defect class by itself.

- **#59 / authority:** Treat this concept as **non-authoritative** and **heuristic / advisory** in the spirit of **GitHub #59**—it **must not** be read as continuity truth, a production gate, or automatic evidence of classifier or continuity failure.
- **Runtime:** It is **not** on the **[Runtime use allowlist](#runtime-use-allowlist)** and **must not** drive **`ContinuityManager`**, **progression_enforcement**, validators, or prompt injection.
- **Implemented signal:** Character **`metadata.audit_v2`** deterministic bundle includes **`char_masked_progression_strict`** (strict tier: empty classifier lane + structured intent + **Q2** / **Q4** / committed **`state_changes`** proxy; initial attempt only; skips progression-retry paths). Inventory row: **`av2.check.char_masked_progression_strict`**. **Observational-only** — escalation **`result`** is always **`pass`**.

### Scene Grounding (MVP) in audits

**Signal id:** `metadata.scene_grounding` / `scene_grounding_summary` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** telemetry (partial); prompt-projection observability, not a defect detector).

**Issue #68 — audit metadata family (`extend`, not replace):** On Director, character, and narrator rows, **`metadata.scene_grounding`** may include:

- **`phase1`** — minimal observability derived only from the existing session **`scene_grounding`** dict (same pipeline as prompts): `continuity_turn_index`, `fact_count`, `binding_fact_count`, `non_binding_fact_count`, and optionally **`grounding_derivation_refs`** (sorted unique **`PublicEvent.event_id`** and/or fact **`source.ref`** values when present). The **`grounding_derivation_refs` key is omitted** when no continuity-native refs could be collected cleanly (no invented ids).
- **`summary`** — optional one-line count summary when facts are non-empty.

This does **not** duplicate full session `scene_grounding` facts in audit metadata (bounded payload); it is **not** a second source of truth.

Audits may also record legacy compact **`scene_grounding`** / **`scene_grounding_summary`** shapes per older notes: **active fact count**, **categories** present, **`fact_id`** list or hashed fingerprint of `(category, key)` pairs, and optionally the **exact `value_summary` lines** injected into prompts. This remains **observability** for the prompt projection — **not** continuity truth (continuity remains authoritative; facts are derived).

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

**Signal id:** `audit.effective_user_trigger` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** telemetry).

**Field:** Top-level **`effective_user_trigger`** on **full** per-turn audit records (Director, character, narrator success paths, and turn failure entries where the harness supplies it). It records the **simulated user trigger string actually used for that orchestration turn** in the production prompts for that beat (Director selection, character generation, narrator render path for that turn).

**Streamlit UI:** There is **no** per-turn user-trigger schedule; every orchestration turn in a user round uses the **same** user message, so **`effective_user_trigger`** matches that string for each bot turn in the round.

Compare this field to **`by_orchestration_turn`** / CLI **`--trigger`** / scenario defaults when debugging “wrong user framing” in **headless** runs. Rules and JSON shape are documented in [SCENARIO_VALIDATION_FRAMEWORK.md](../../../SCENARIO_VALIDATION_FRAMEWORK.md) (**Per-turn user trigger schedule**). The schedule file is **harness input only**—it is not written into continuity or scenario files.

**Light vs full:** **`effective_user_trigger`** appears in **full** audit serialization (`entry_to_full_dict`). **Light** audit rows do **not** include it; use **`*_full.json`** when you need the per-turn line.

**Triage:** If the key is absent from on-disk `*_full.json` for a run that used `--user-trigger-schedule`, confirm turn-level behavior with **`_round_index.json`**, **`structured_eval`**, or metrics before assuming continuity/runtime failure—artifact layout or writer path may not expose the field in every session.

### Authored index retrieval (standard evaluation mode — Phase 4A)

**Signal ids:** `metadata.retrieval_summary`, `audit.retrieval_session` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and [inventory rows](#audit-signal-applicability-inventory) (**engineering family:** telemetry for both).

**Activation:** **`RP_RETRIEVED_CONTEXT_INDEX`** only (path to compiled JSON, or unset / empty = OFF). Optional CLI: `scripts/run_scene_simulation_llm.py --retrieved-context-index [PATH]` (see [SCENARIO_VALIDATION_FRAMEWORK.md](../../../SCENARIO_VALIDATION_FRAMEWORK.md) from repository root).

**Accepted baseline** (content, not audit-specific): character **`lore_facts`**; template **`role_slots`** + refined **`premise`**; retrieval remains **non-authoritative** (same prompt contract as Phase 2). **Historical pilot** artifacts and the **rejected situational template-row cap** are documented in `data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md` — that file is the **runbook + manifest map**; day-to-day validation workflow is **standard**, not pilot-only.

**Per-turn (character `*_full.json` / light):** `metadata` may include **`retrieval_summary`**: `retrieved_block_present`, `retrieved_item_count`, `retrieved_char_count`, `retrieved_source_refs` (capped list). **No** full retrieved text is stored. Populated from the **`RetrievedContextBundle`** at prompt build time (`app_turn_prompting` → `turn_runner_audit`).

**Session summary (`_audit_summary.json`):** Top-level **`retrieval_session`** (same shape as `structured_eval.retrieval_session`: mode, path, `retrieval_verified_active`, fingerprint) is **merged** after **`write_summary_report`** via **`apply_retrieval_session_to_audit_summary`** — **both** Streamlit (`refresh_audit_summary_report`) and headless (`run_headless_llm_scene`). Same build/merge helper; **`sim_retrieval_saw_nonempty_bundle`** in session state mirrors whether any character turn saw a non-empty authored bundle.

**Simulation-only (not Streamlit):** **`structured_eval`** JSON, **`sim_progression_metrics`** event buffer, **`verify_retrieval_strict_or_raise`**, and **`--user-trigger-schedule`** remain headless/CLI harness features.

**Strict verification (headless only):** If retrieval is **ON** and the continuity scene has **`scene_template_id`**, the headless run **raises** if no character turn had a non-empty retrieved bundle (guards silent misconfiguration). The UI does **not** run this gate.

### Structured eval bundle (headless metrics)

**Signal id:** `structured_eval.bundle` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** aggregation; optional human `verdict` / `failure_classification` are external annotations, not system detection). Validate rollups against lower-level artifacts per **Stage 3.4** in [Audit Signal Evaluation Methodology](#audit-signal-evaluation-methodology).

### Support Manifest (`metadata.support_manifest`)

#### Purpose

**Signal id:** `metadata.support_manifest` — interpretation: **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the [inventory row](#audit-signal-applicability-inventory) (**engineering family:** telemetry).

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

## Audit Signal Evaluation Methodology

Canonical end-to-end procedure for evaluating **#59 inventory** **Signal ids** (GitHub **Issue #71**). Use this when classifying signal behavior, deciding dispositions, or aligning work with the **offline evaluation layer** (**Issue #66** / `scene_eval_v1.py`). This methodology does **not** change applicability class or runtime authority by itself; it informs **documentation**, **follow-on issues**, and **predicate** design.

Empirical runs that follow the **Issue #60** pilot pattern use the **execution profile** below; that profile is **subordinate** to this section and **does not** replace or redefine Stages 1–6.

### Audit Signal Evaluation — Empirical Execution Profile (Issue #60 Pilot)

This subsection is an **execution profile** for how **empirical** signal evaluation was run during **GitHub Issue #60** (Phase 3 — Heuristic Evaluation). It is **not** a separate methodology. All work **still** follows **Stages 1–6** in this document.

**Execution constraints (from Issue #60):**

- **One signal at a time** — each cycle evaluates a single Signal id before moving on.
- **Strict sequence** — advance in **locked inventory order**; do not skip or reorder rows ad hoc.
- **Append-only evaluation state** — completed work and evidence accumulate; do not erase or rewrite prior completed evaluations as the norm.
- **No reuse of completed signals as the next unit** — do not select an already-completed signal as the **next** evaluation target; supporting or comparative use of a signal in another cycle does **not** count as “next in sequence.”
- **Evidence posted per evaluation** — record corpus, session/turn identifiers, paths, trigger (**fired**) definition, denominators, and tier/depth artifacts where the team tracks work (Issue #60 comments during the pilot).

**Evaluation depth (terminology):**

Use the term **evaluation depth** for pilot tiering (avoid bare “Tier 1” without qualifier):

| Evaluation depth | Pilot label (historical) | Meaning |
|------------------|---------------------------|---------|
| **Evaluation depth 1** | Tier 1 (pilot) | **Full evaluation** — problem existence, detector quality with labeled sample and denominators as required, system-role inputs toward disposition. |
| **Evaluation depth 2** | Tier 2 (pilot) | **Detector evaluation** — detector-quality evidence and interpretation; problem-existence brief optional when the signal is explicitly non-continuity, per Stage 2–3. |
| **Evaluation depth 3** | Tier 3 (pilot) | **Observational** — qualitative usefulness; no mandatory FP-rate target. |

**Rule — naming collision:** **Evaluation depth** (pilot Tier 1 / 2 / 3) **MUST NOT** be confused with the **Issue #70 Tier 1 kernel** registry / **`engineering_role`** taxonomy in [Issue #70 — Engineering-role taxonomy (Tier 1 kernel)](#issue-70--engineering-role-taxonomy-tier-1-kernel). In prose, prefer **evaluation depth** vs **#70 Tier-1 kernel** (or **engineering_role**).

**Inventory authority:**

- **During the pilot** — row order and locked list match the **heuristic inventory** fixed on **closed Issue #60** (issue body and thread).
- **After promotion** — order and classes follow this document’s **[Audit signal applicability inventory](#audit-signal-applicability-inventory)** (**#59**), unless a **successor issue** documents a deliberate change.

**Execution rules:**

- **Finish the evaluation before switching signals** — satisfy Stage 1–6 requirements for the current signal (for its evaluation depth) before starting the next.
- **Do not advance using a comparison-only signal** — a signal already used as **comparative / supporting** evidence must **not** be selected as the **next sequential** evaluation unit; continue with the **next unevaluated** inventory row (Issue #60 sequence correction precedent).
- **Spawn / sub-issue criteria** — when scope would swamp a single thread or results imply design or policy work, follow the pilot’s **spawn assessment** and sub-issue rules recorded on **Issue #60**.

### Methodology ↔ Execution Mapping

| Stage | Execution behavior |
|-------|-------------------|
| **Stage 1** | Corpus definition (artifact classes, row types, loaders, predicates, sessions/scenarios). |
| **Stage 2** | Trigger / **fired** definition (code path, JSON fields, observable condition — not failure or “correctness”). |
| **Stage 3** | **Validation** — independence of evidence; allowed sources per **#59**; aggregation vs lower-level data; dependency disclosure; and **TP / FP / ambiguous** (or equivalent) labeling **when** detector-quality evaluation is required for the evaluation depth. |
| **Stage 4** | **Disposition** (exactly one canonical disposition). |
| **Stage 5** | Predicate mapping and evaluation-layer alignment (**Issue #66**). |
| **Stage 6** | Documentation / registry updates (as disposition and follow-ons require). |

**Rule:** **Evaluation depth** determines **which artifacts and evidence tables are required within** the stages (especially Stage 3); it is **not** a parallel stage sequence.

### Stage 1 — Evidence & corpus definition

#### 1.1 Define the target

- **Signal id under evaluation** (from the [Audit signal applicability inventory](#audit-signal-applicability-inventory); **GitHub #59**).

#### 1.2 Define artifact scope

Explicitly declare:

- **Artifact class**
  - per-turn (`*_full.json`, `*_light.json`)
  - session-level (`_audit_summary.json`, `structured_eval`)
  - offline outputs (e.g. **#66** evaluation artifacts; optional **#62**-style offline artifacts when relevant)
- **Row types included**
  - character
  - narrator
  - director

#### 1.3 Loader / access path (critical)

You **must** specify how data is loaded. Example:

- `load_character_audit_rows` (`issue29_investigation.py`) → **character `*_full.json` only** (filters `bot_type == "character"`).

If narrator or director rows are in scope, specify the **alternate access path** (read patterns, glob, or tooling) explicitly.

**Important constraint:** **#66 v1** shipped predicates in `scene_eval_v1.py` operate on **character `*_full.json` rows only** (via `load_character_audit_rows`) unless a future change explicitly extends them.

#### 1.4 Conditional predicate scope

For **conditional** signals (per #59):

- define the **predicate** explicitly;
- restrict the corpus to **predicate-satisfying rows only**.

#### 1.5 Corpus definition

Document:

- scenario ids / session paths;
- loader(s) and access paths;
- any corpus expansion performed and why.

---

### Stage 2 — Trigger evaluation

For the **Signal id**:

- identify **code path**, **JSON field(s)**, and **emission conditions**.

Define:

> **“Fired”** = the **observable condition** for that signal occurred.

**Constraints:**

- **Not** failure  
- **Not** correctness  
- **Not** a system judgment  

Validate firing behavior on **real** artifacts.

---

### Stage 3 — Independent validation

#### Goal

Determine whether the **target phenomenon** exists **independently of the signal’s own output**.

Stage 3 **always** requires: **independence of evidence** (no using the signal under evaluation as sole proof), use of **allowed evidence sources** per **#59** class (see §3.3), **aggregation validation** where rollups are in scope (see §3.4), and **dependency disclosure** when another signal or score contributes (see §3.5). **TP / FP / ambiguous** (or equivalent) row labeling is **additional** and **mandatory only when** detector-quality evaluation is required for the chosen **evaluation depth** (see §3.6). **Labeled rows do not replace** §3.1–3.5.

#### 3.1 Corpus constraint

- Use a **predicate-conditioned corpus** (same predicate rules as Stage 1.4 when the signal is conditional).

#### 3.2 Independence rules

You **must**:

- **not** rely on the signal’s own output as proof of the phenomenon;
- **declare** all independence sources used.

#### 3.3 Allowed independence sources

| Signal class (#59) | Allowed sources |
|--------------------|-----------------|
| heuristic / advisory | `_narrative.json`, raw move data (`parsed_output` / structured move fields as present in audit rows), **declared** per-turn or session audit artifacts (paths/keys listed explicitly) |
| conditional | same as above, **predicate-filtered** |
| always-on | audit structure, emission **presence/absence** semantics (contract vs artifact shape) |

#### 3.4 Aggregation constraint

For aggregation artifacts (e.g. `structured_eval` / `structured_eval.bundle`), **engineering family** and applicability semantics are defined in **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the **`structured_eval.bundle`** [inventory row](#audit-signal-applicability-inventory)—do not redefine them here.

- **must** validate against **lower-level** per-turn or session data;
- **must not** treat aggregation output as ground truth.

#### 3.5 Signal dependency rule

If another **inventory signal** (or derived audit score) is used as evidence:

- **declare** it explicitly;
- the result is **not fully independent** (dependency is documented).

#### 3.6 Detector-quality labeling (when required)

When the evaluation depth requires **detector-quality** evidence (typically **evaluation depth 1** or **2**), you **must** document **labeled rows** among applicable **fired** (or equivalent) instances — e.g. **true positive**, **false positive**, **ambiguous** — with **denominators**, using a rubric consistent with project precedent (e.g. semantic vs lexical guidance from **Issue #13** where referenced). When detector-quality tables are **out of scope** (typically **evaluation depth 3**), state **N/A with reason**; Stage 3 **still** requires §3.2–3.5 (including a **declared independence basis** and qualitative usefulness where applicable).

---

### Stage 4 — Disposition

Each evaluated signal receives **exactly one** disposition:

- **deprecate**
- **improve**
- **hybrid candidate**
- **no action**

#### 4.1 Disposition meaning

| Disposition | Meaning |
|-------------|---------|
| deprecate | Not useful as a signal in its current role (may remain for observability). |
| improve | Signal needs redesign or refinement. |
| hybrid candidate | Candidate for a structured + heuristic combination. |
| no action | Signal is acceptable as-is for the evaluated scope. |

#### 4.2 Follow-on actions (0..n)

Each disposition may produce **zero or more** follow-ons:

- documentation update;
- classification update (**#67** or **successor** issue);
- taxonomy alignment (**#70** or **successor** issue);
- redesign work (**#68** or **successor** issue);
- hybrid exploration (**#69** or **successor** issue);
- evaluation predicate work (**#66** or **successor** issue);
- **none** — explicit justification in the evaluation record.

**Important:**

- Deprecation does **not** require code removal.  
- A **documentation-only** downgrade is valid.

#### 4.3 Future-proofing

If referenced umbrella issues are replaced, use the **successor** issue instead.

#### 4.4 Appendix — Issue #60 outcome language → canonical disposition

Issue #60 pilot summaries sometimes used **outcome buckets** for communication. Map them to the **four canonical dispositions only**:

| Issue #60 outcome language (pilot) | Canonical disposition |
|------------------------------------|------------------------|
| **high value** | **no action** |
| **weak but useful** | **improve** (use **hybrid candidate** instead when the evaluation record explicitly proposes a structured + heuristic combination) |
| **noise / misleading** | **deprecate** |

Do **not** introduce disposition categories outside **deprecate / improve / hybrid candidate / no action** in evaluation records or methodology text.

---

### Stage 5 — Evaluation layer alignment (Issue #66 v1)

#### 5.1 Predicate definition

Evaluation **predicates**:

- are **independent** of **Signal ids** (many-to-many: one signal may map to zero or many predicates; one predicate may inform many signals);
- may consume **raw audit artifacts** and **allowed metadata** per **#66** (see **Input constraints** below).

Each predicate definition **must** include:

- `predicate_id`;
- `predicate_version`;
- explicit **inputs** (artifact paths, fields, row filters);
- **deterministic** evaluation logic.

##### Input constraints (critical)

Per **#66** / `scene_eval_v1.py`:

- **must** follow existing **allowed** inputs for the evaluation layer;
- **must not** use:
  - CA3–CA7 **derived** fields (`metadata.character_audit_v1.derived`, etc.; CA1/CA2 removed — **Issue #44**);
  - Audit v2 heuristic bundles;
  - narrator/prose audit signals as predicate inputs;
  - LLM-generated audit layers.

**Explicit clarification:** `context_snapshot` may be **present** on character rows loaded by `load_character_audit_rows`, but it is **not** used in **v1** predicates in `scene_eval_v1.py`. Silence and applicability for this field are defined by the **[inventory row `context_snapshot`](#audit-signal-applicability-inventory)** and **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)**—do not redefine them here.

#### 5.2 Judgment emission (v1 — normative)

All judgments **must** match this JSON shape. The `result` field is **one** of the three strings `fired`, `clear`, or `inconclusive` (not a combined literal).

```json
{
  "predicate_id": "string",
  "predicate_version": "string",
  "result": "fired",
  "subject": null,
  "summary": "string",
  "limitations": []
}
```

**Interpretation:**

- `fired` — condition **observed** (not failure, not “bad scene”).  
- `clear` — condition **not** observed (not success or health).  
- `inconclusive` — inputs insufficient or out of scope.

Judgments are **descriptive only**; they are **not** pass/fail verdicts on the RP system.

#### 5.3 Signal ↔ predicate relationship (evaluation role)

Relationships between **inventory Signal ids** and **evaluation predicates** are **not** 1:1. Possibilities include:

- one signal → multiple predicates;
- one predicate → informs multiple signals;
- signals with **no** associated predicate (evaluation role **excluded** or **supporting-only** only in narrative docs).

Each Signal id under this methodology should be assigned an **evaluation role** for tracking:

- **contributes to evaluation** — at least one predicate is defined or planned that consumes allowed inputs to characterize behavior relevant to this signal;
- **supporting-only** — used as context for other signals or predicates but not the primary subject of a predicate set;
- **excluded** — out of scope for **#66 v1** predicate work (document why).

**Orthogonality (critical):** Evaluation role is **orthogonal** to **#59 applicability class** (`always-on`, `conditional`, `heuristic / advisory`) and **must not** be conflated with it. Applicability class governs **silence and inventory semantics**; evaluation role governs **relationship to offline predicates** only.

#### 5.4 Optional extensions (non-normative)

Additional fields (e.g. operator-facing **severity**):

- allowed only as **non-normative** metadata **outside** the v1 judgment object unless a future versioned schema is adopted;
- **must not** affect runtime, imply pass/fail, or bypass the **#59** allowlist rules.

#### 5.5 Authority constraints (critical)

- The evaluation layer is **offline / advisory** unless a signal is explicitly on the **[Runtime use allowlist](#runtime-use-allowlist)** with a documented coupling (**#59**).
- Judgments **must not** override **continuity** truth or other **runtime authority**.

---

### Stage 6 — Documentation & integration

When an evaluation completes, record outcomes where the team tracks work (e.g. GitHub issue comments or linked notes).

**Doc and registry updates — scope (mandatory):**

> Updates to **#59** (inventory / applicability text in this document), **#70** (Tier 1 registry / taxonomy in this document), and **`AUDIT_DOCUMENTATION.md` generally** are required **only when the disposition or selected follow-on necessitates them**, **not** for every evaluation.

- Choosing follow-on **none** (with explicit justification) **typically** implies **no** required inventory edit, **#70** registry edit, or broad doc churn—unless a separate policy requires a minimal audit trail entry.
- Optional pointers for operators: `autogen_rp/docs/audit-workflows.md` (scene triage procedure); issue template helper text may reference this section when filing **audit_simulation** / signal work.

> **Governance:** **Incidental findings / adjacent discoveries** for **evaluation depth 1** GitHub completion records — canonical rule only in **`governance/rp-app/issue-tracking-workflow.md`** **§A.2** (do not duplicate here).

### Evaluation Record Requirements

Each **evaluation** (pilot thread, issue comment series, or internal record) **must** state explicitly, where the team tracks work:

| Requirement | Notes |
|-------------|--------|
| **Stages satisfied** | Which of Stages **1–6** apply and are complete for this signal. |
| **#59 applicability class** | **always-on**, **conditional**, or **heuristic / advisory** for the Signal id. |
| **Evaluation depth** | **1 / 2 / 3** (pilot terminology); see **Empirical Execution Profile (Issue #60 Pilot)** in this methodology section. |
| **Evidence type** | Aligned with **Stage 1.2** — artifact classes (per-turn, session-level, offline) and **row types** (character, narrator, director). |
| **Independence basis** | Sources used for Stage 3; confirm signal-under-test is not sole proof. |
| **Aggregation validation** | If rollups apply: which **lower-level** paths were checked (Stage 3.4); **N/A with reason** otherwise. |
| **Dependency disclosure** | If another inventory signal or score was used as evidence (Stage 3.5); **none** if fully independent. |
| **Disposition** | Exactly one of **deprecate / improve / hybrid candidate / no action**. |
| **#66 predicate involvement** | Whether predicates or evaluation roles are touched; **none** if out of scope. |

**Runtime authority rule:** Evaluations **MUST NOT** imply **runtime authority** for any audit signal **unless** that Signal id is on the **[Runtime use allowlist](#runtime-use-allowlist)** per **#59**. Methodology and dispositions are **offline / documentation / backlog** unless a separate tracked change allowlists runtime use.

### Edge cases (methodology)

#### Evaluation depth 3 (observational)

- **Qualitative usefulness** is required (narrative of when the signal helped or misled operators).
- **Independence** is still required: **declare** the independence basis per Stage 3.2–3.3; do **not** treat the signal’s own output as sole proof of the phenomenon. Detector-quality TP/FP tables are **not** mandatory unless you voluntarily expand scope.

#### Aggregate signals

- Claims about phenomena **represented in rollups** (**`structured_eval`**, **`structured_eval.bundle`**, session summaries) **must** be checked against **lower-level** per-turn or session artifacts (Stage 3.4). **Rollup-only** validation is **insufficient** for independent validation of those claims.

#### Cross-signal dependency

- Using another **inventory signal** (or derived score) as evidence **must** be **explicitly declared** (Stage 3.5). That path **cannot** be described as **fully independent** validation without that disclosure.

### Promotion of the execution profile

The **Empirical Execution Profile (Issue #60 Pilot)** text in this document is **derived from** **GitHub Issue #60**. It becomes **repo-canonical** for “how empirical evaluation runs” **only when**:

- **Issue #60** **pilot exit criteria** are satisfied **and** recorded, **or**
- a **successor issue** explicitly **promotes** the profile (waiving or replacing specific exit clauses with rationale).

Until then, treat **Issue #60**’s locked body and thread as the **historical pilot record**; this subsection anticipates alignment and **must not** silently override **#59** or Stages 1–6.

---

## Issue #70 — Engineering-role taxonomy (Tier 1 kernel)

This section is the **canonical Tier 1 kernel registry** for GitHub **Issue #70**: a small, curated set of **fully qualified surface instances** (`surface_id`) so operators do not conflate observability, guardrails, rollups, and offline detectors. **Normative Issue #59 rules** (applicability classes, inventory, allowlist) are **orthogonal** to **`engineering_role`** here: interpret both when both apply. **Outcome records** are audit mirrors of runtime authority; they are **not** #59 inventory signals—**omit `engineering_role` and `applicability_class`** for those rows (do not set them to `null`). A **`detector`** surface is **offline-first**, uses explicit **`predicate_id`** + **`judgment_schema`**, emits structured judgments, is **advisory** unless separately allowlisted under #59, and is **not** LLM-only at the core. **Runtime enforcement** (validation, progression Q1–Q4 gate, semantic overrides) is **`guardrail`**, never **`detector`**. Full methodology for evaluating signals: [Audit Signal Evaluation Methodology](#audit-signal-evaluation-methodology) (GitHub **Issue #71**); the offline evaluation layer specification: **Issue #66** / `scene_eval_v1.py`.

**Issue #67 alignment:** Applicability-class vs **engineering family** reading rules (telemetry, guardrail, aggregation, heuristic proxy) are **normative** only in **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)** and the **[Audit signal applicability inventory](#audit-signal-applicability-inventory)**. This registry **does not** redefine those axes; use it together with that subsection when both apply.

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

**Character bundle — `char_masked_progression_strict` (GitHub #73):** Detects **masked progression** (classifier lane empty while a **strict-tier** continuity/progression proxy advanced: **Q2**, **Q4**, and/or non-empty committed **`state_changes`** on the turn’s `PublicEvent`, plus structured intent; initial attempt only). **Observational only** and **non-authoritative**; **not** on the **[Runtime use allowlist](#runtime-use-allowlist)**; **must not** be used for runtime gating, continuity control, or pass/fail verdicts (**#59**). Escalation **`result`** is **always `pass`** (non-escalating); use **`payload.observation`** (`fired` / `clear` / `skipped`) and **`payload.signals`** for triage only.

Per-turn logs may include **`audit_v2`** (character) and narrator-side **`audit_v2_narrator`** metadata with extra deterministic checks. Same non-mutating contract as v1 add-ons. Read **`pass` / `fail` / `border`**, documented non-tri-state values (below), and **`limitations`** together when interpreting logs; assign a GitHub issue **Layer** from `governance/rp-app/issue-tracking-workflow.md` **§F** (e.g. **audit_simulation** for harness/log shape issues; **rendering** or **response_validation** when separate runtime evidence shows a defect outside the audit heuristic). For **`char_masked_progression_strict`** (**#73**), the scored **`result`** is always **`pass`** for escalation; interpret only the check **`payload.observation`** (`fired` / `clear` / `skipped`) and **`payload.signals`** — **not** a runtime failure or classifier bug.

**`character_intra_move_coherence`:** The reserved dimension id remains in **`dimension_aggregate`** for shape compatibility. Current character deterministic checks (**CA4**, **CA7**, **`char_masked_progression_strict`**) map to **other** dimensions; none map to intra-move, so the aggregate is **`not_applicable`**. See **`intra_move_summary`** on character deterministic bundles (**Issue #44** — lexical CA1/CA2 removed from computation and emission).

### Audit signal limitations

Many dimensions are **heuristic**: token overlap, substring scope proxies, short-window attribution tests, etc. They may be **conservative** by design and produce **high false-positive** rates on otherwise healthy runs.

Examples from baseline audits:

- **Prose attribution** / attribution proxies — pronoun-led or implicit attribution often fails fixed-window name tests.
- **CA4 repetition** — structural similarity vs prior self can flag **`border`** / **`fail`** bands on otherwise acceptable dialogue; corroborate with narrative.

**Prose attribution** and **other** heuristics listed above (for example CA4–CA7 where referenced in this doc): chronic **`fail`** or noise may inform **quality**-class or **design_gap** discussion of **metrics** when **corroborated**; they **should not** alone trigger “fix the narrator/character” work without **independent runtime evidence** for a concrete **Layer**. Historical logs may still show removed CA1/CA2 keys (**Issue #44**); do not treat them as current contract signals.

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

When audit is enabled at scene start (Streamlit and headless), **`bootstrap_interpretation`** may be present: the exact **`interpretation_to_jsonable`** dict from Issue **#94** composition (observational; see **`bootstrap_interpretation_snapshot_v1`** on **`_audit_summary.json`**).

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
- **`retrieval_session`**: run-level authored-retrieval observability (see *Authored index retrieval* above), merged whenever the audit summary is refreshed with auditing enabled — **Streamlit and headless**.

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

**Narrator `*_narrator_full.json` (prose fields):**

- **`parsed_output.rendered`:** **Full final rendered narrator prose** for that beat—the string produced after the narrator/render pipeline (including deterministic dialogue fallback or semantic replacement when those paths apply). It is **not** a length-capped preview.
- **`raw_response`:** The narrator model’s **raw** return. It may **differ** from `parsed_output.rendered` when a fallback or post-model replacement changes the text operators see in chat and in the narrative trace.
- **Modern rows** typically include **`metadata.narrator_validation_audit_v1.observed.rendered_final`**, which records the same **final** rendered string for validation-audit observability.
- **Legacy** narrator full rows may **lack** `narrator_validation_audit_v1`. For those historical artifacts, use **`_narrative.json`** (`turns[].rendered_output` for the matching `round` / `turn`) as the reliable source for **final** rendered prose on the beat.

When scene templates are active, the granular `_full.json` logs also include `context_snapshot.scene_template`
with the template ID, premise, role assignments, presence constraints, and authority labels that were active
for that turn.

**`context_snapshot` (Signal id):** Silence and engineering-family semantics are **only** in the **[inventory row](#audit-signal-applicability-inventory)** and **[Operator interpretation — #59 applicability class vs Issue #67 engineering family (canonical)](#issue67-operator-interpretation)**—this section documents **field usage** for debugging only.

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
6. Check `context_snapshot.continuity_event` and **`context_snapshot.scene_state_after`** (committed **`SceneState`** mirror — Issue **#79**) for what continuity attached after the beat

### Debug Narrator Rendering
1. Compare `turns[].character_dialogue` vs `turns[].rendered_output`
2. Check verbatim preservation
3. If issues, open:
   `{owner}_session{###}_round{#}_narrator_full.json`
4. Review render prompt and rules given
5. If scene templates are active, confirm the acting character's role metadata is present in the narrator audit

### Character Audit v1 (`metadata.character_audit_v1`)

**Scope:** Advisory, deterministic, **no LLM**. Built from the **validated parsed character move**, the **Director decision**, orchestration snapshots (`recent_structured_moves` tail, optional `continuity_active_issues`), and continuity-backed digests when `continuity_scope` is `continuity_enabled`. **Not** a verdict on continuity correctness.

**Advisory scope — all `derived` dimensions:** Every heuristic under `metadata.character_audit_v1`.`derived` (dimensions commonly referenced as **CA3–CA7**; CA1/CA2 removed — **Issue #44**) is **advisory** and **non-authoritative**. None of these fields are continuity correctness checks, quality metrics, engagement scores, or story-truth indicators on their own.

### Issue #44 — CA1 / CA2 removed (interpretation contract)

**Removed in Issue #44:** Character Audit v1 no longer computes **`motivation_action_alignment`** or **`dialogue_action_consistency`**. Audit v2 no longer emits **`char_ca1_motivation_action`** or **`char_ca2_dialogue_action`**. Escalation policy no longer references CA1/CA2; **`character_intra_move_coherence`** defaults to **`not_applicable`** when no check maps to that dimension.

**Historical sessions:** Older `*_full.json` rows may still contain legacy `derived` keys or v2 check ids. Treat those as **archival**; do **not** assume current builds emit them.

**Prior rationale (archived):** CA1/CA2 were lexical overlap proxies with a high false-positive rate vs semantic coherence (**#13**). They were excluded from escalation aggregation before removal (**#42**).

#### Interpretation rule (audit output)

When interpreting **current** logs:

- Expect **`intra_move_summary.pattern: intra_move_not_applicable`** when the character bundle has no intra-move checks; read the human-readable string on the bundle for context.
- Use **CA3–CA7** and Audit v2 checks named in the [inventory](#audit-signal-applicability-inventory) — not removed CA1/CA2 keys.

**What v1 records under `derived`:** **CA3–CA7 and related entries:** issue engagement proxy (`issue_engagement`), self-repetition vs prior structured moves (`repetition_vs_prior_self`), cast-vs-present substring flags (`scene_plausibility_flags`), Director tension/environment (`pressure_director`), and move-emitted pressure fields if present (`pressure_move`).

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

- **CA1 / CA2 (removed)** — No longer emitted (**Issue #44**). Legacy rows may still list old keys; ignore for current contract interpretation.
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
| `narrator_output_audit_v1` | Heuristic advisory: action vs render, environment cue. **`action_coverage_heuristic` does not include `passes_bar`** (removed, GitHub **#76**); use `action_token_overlap_ratio`, `action_non_stopword_hits`, and `acting_name_in_render` with Audit v2 `nar_strict_action_overlap` for tri-state. |
| `narrator_validation_audit_v1` | Observational: captures raw render path, deterministic fallback flag, semantic validator payload, and **derived** flags (`fallback_triggered`, `output_replaced`, etc.). Does **not** re-run validation. |
| `prose_dialogue_audit_v1` | Heuristic advisory: readability/redundancy/dialogue/tone proxies. |

**Non-mutating:** These blobs are computed for logging only. They do **not** change narrator output, fallbacks, or continuity.

**v1 limitations (read audits with these in mind):**

- **Output and prose layers are heuristic-only** (no LLM scoring in v1); false positives/negatives are expected.
- **No narrator audit row** (and thus no v1 blobs) when `log_narrator_render_audit` early-returns because `narrator_raw` is falsy or audits are disabled—same guard as before v1.
- **Legacy narrator scope heuristic (removed, GitHub #41):** Historical rows may still contain **`single_actor_scope_heuristic`** (v1) and/or Audit v2 **`nar_scope_proxy`** / **`scope_proxy_context`**; **ignore** for current contract interpretation (retirement rationale: closed **#9**).
- **`prose_dialogue_audit_v1` → `attribution_proxy`:** **Removed (GitHub #40).** Historical rows may still contain this key; treat as **legacy only** (see **Issue #40 — Deprecation of narrator attribution heuristic**).
- **`prose_dialogue_audit_v1` → `readability_proxy` / `tone_consistency_local`:** Lexical heuristics only (word length, long-token ratio, simple present-tense token hits). **Heuristic-only**, **non-authoritative**, **non-gating**, **low-signal**; `passes_bar: false` is **not** narrator incorrectness and **must not** be used to assess narrator correctness, trigger escalation, or drive system decisions. Use for **monitoring / observability** only; expect threshold-adjacent noise and false positives (see `interpretation` / `note` on the blob when present; GitHub **#10**).
- **Redundancy** compares against the **prior assistant** message only (last assistant `content` in `chat_history` before the current append), not a long window.

**Scope:** Per-turn narrator renders only; scene-opening narrator calls are **not** covered by v1.

## Issue #40 — Deprecation of narrator attribution heuristic

### A. What the heuristic did

The narrator attribution path attempted to infer **attribution clarity** using **lexical proximity**: whether an acting-character token appeared in a short window **before the first ASCII double-quoted segment** in the rendered narration. That v1 `attribution_proxy` fed Audit v2 **`av2.check.prose_attribution`**, and v2 could emit **`attribution_ambiguity_hint`** (including a `possible_speaker_ambiguity` tier when dialogue integration passed but multiple quotes were present).

### B. Why it was removed

Offline evaluation (**Issue #40**) on a multi-scenario audit corpus (sessions **598–610**, **93** join-valid narrator turns after structural pairing) found:

- **`prose_attribution` heuristic fail rate ~91%** (85/93 scored turns) on that corpus.
- **Reader-fidelity AI review** (blind to heuristics; dual-pass agreement) labeled **0** turns **problematic** and **0** **ambiguous** — all agreed labels were **clear**.

The signal therefore **misaligned** with reader-level attribution failure: it measured **explicit lexical attribution patterns**, not whether a reader could follow who was speaking.

### C. Key conclusion

> The heuristic measured explicit attribution patterns, not actual attribution failure.

### D. Replacement

> No direct replacement. Attribution failure is better detected via:
> - audit inspection
> - manual tagging of real ambiguity cases

### E. Archival note

> This signal may appear in historical audit artifacts but is not present in new outputs.

## Schema changes

### Issue #40 — Removal of narrator attribution heuristic (v1 + v2)

**Removed:** `prose_dialogue_audit_v1.checks.attribution_proxy` (new narrator audit rows); Audit v2 deterministic check **`prose_attribution`**; prose deterministic block **`attribution_ambiguity_hint`**; escalation dimension **`prose_attribution`**. **Compatibility:** historical `*_narrator_full.json` may still list the removed keys; treat as legacy only (retirement rationale: **Issue #40 — Deprecation of narrator attribution heuristic**).

### Issue #76 — Removal of `action_coverage_heuristic.passes_bar`

`action_coverage_heuristic.passes_bar` was removed (**Issue #76**). Nothing in the repository consumed it; the related v2 signal **`nar_v1_action_passes_bar`** was removed in **Issue #75**, and the field duplicated v1-only summary logic that did not align with v2 **`nar_strict_action_overlap`**. Use v1 **`action_token_overlap_ratio`** (and, on older rows, `action_non_stopword_hits` / `acting_name_in_render` as context) plus Audit v2 **`nar_strict_action_overlap`** for tri-state interpretation. **Compatibility:** historical narrator audit JSON may still contain `passes_bar`; new outputs do not.

### Issue #41 — Removal of narrator scope heuristic and Audit v2 bridge

**Removed:** v1 **`single_actor_scope_heuristic`**; Audit v2 check **`nar_scope_proxy`**; deterministic block **`scope_proxy_context`**; dimension id **`narrator_scope_proxy`**; Streamlit session key **`audit_v2_last_narrator_other_cast_names`**. Narrator v2 deterministic output now includes **`nar_strict_action_overlap`** and **`nar_environment_cue`** only. **Compatibility:** historical `*_narrator_full.json` and bundled metadata may still list the removed keys; treat as legacy only (retirement decision: closed **#9**).

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
