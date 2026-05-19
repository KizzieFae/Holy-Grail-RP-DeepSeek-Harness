# Director + Narrator Mediated Architecture

**Scope:** This file is the **RP app** runtime architecture (Director, Narrator, continuity, enforcement, scene lifecycle). Broader repo orientation: [`ARCHITECTURE_OVERVIEW.md`](../../../ARCHITECTURE_OVERVIEW.md), [`MODULE_INDEX.md`](../../../MODULE_INDEX.md). Package-level guardrails under `autogen_rp/`: [`docs/architecture.md`](../../docs/architecture.md). **Audit signal interpretation** (**#59**, **#70**, inventory): [`AUDIT_DOCUMENTATION.md`](./AUDIT_DOCUMENTATION.md) — authoritative; not duplicated here. **Continuity authority / evidence vocabulary (stable doctrine):** [Continuity authority and evidence lanes (GitHub #224)](#continuity-authority-and-evidence-lanes-github-224) — umbrella [**#224**](https://github.com/KizzieFae/Holy_Grail_RP/issues/224).

## Overview

This branch implements a director- and narrator-mediated roleplay architecture with private
per-character state.

**Goal:** Each non-narrator bot writes only their own parts and progresses their own character objectives without cross-character writing bleed.

**Audit contracts and engineering roles:** **Issue #59** applicability, **Issue #70** engineering-role taxonomy (Tier 1 kernel), and related audit operator contracts are maintained only in **`AUDIT_DOCUMENTATION.md`**—that file is the **source of truth** for the taxonomy table. **#59 applicability class** and **#70 `engineering_role`** are **orthogonal**; triage uses both when both apply. This architecture document does not duplicate the Tier 1 registry.

## Operating Rules

### Participant and control model

- Active LLM-controlled participants are the selected scene characters.
- The user is present in-scene but remains separate from the LLM actor pool while directly controlled.
- Any character-profile, including the user's persona if represented as a character card, may be either player-controlled or bot-controlled per scene, but never both at once.
- A player-controlled character does not make an LLM call, and the user's post ends the round.

### Round structure

- Default bot replies per user turn equals the number of active bot participants, with user override allowed.
- The configured reply limit is a per-round cap on total bot replies, not a per-character quota.
- The same character should not act twice in the same response cycle.

### Scene lifecycle

- Ending a scene saves and closes it.
- Starting a new scene closes the current one first.
- Interrupted active sessions are finalized on next startup.

**Session identity (Issue #109):** New **`session_id`** values are **opaque UUIDv4** strings minted by **`SessionManager.generate_session_id`** (no cast, scenario, template, or run-class tokens). **Streamlit** audited runs set **`audit_session_owner`** from that id via **`audit_identity.streamlit_audit_owner_label_from_session_id`** (#106 rules preserved). **Headless** audit naming stays scenario/harness/ad-hoc driven and is **not** tied to `session_id` for folder prefixes.

**Implemented in the current app:**

- Director-controlled turn selection using structured scene state
- Narrator-only prose rendering with verbatim dialogue preservation
- Stronger identity anchors in character prompts and state
- Per-character interpretation summaries to reduce worldview convergence
- Structured motivation in place of flat intent strings

### Structural turn identity vs `PublicEvent` (Issue #72)

- **Continuity beat index** — **`ContinuityManager.turn_counter`** (mirrored in full audits as **`context_snapshot.continuity_turn_index`**) is the **structural** “which turn committed” identity. It exists **without** requiring a **`PublicEvent`** row for that beat.
- **`PublicEvent.event_id`** — **Semantic** id for knowability, retrieval, and grounding; **optional** at the beat level. It is **not** the primary offline join key for narrator↔character audit pairing.
- **Audit / offline pairing (Issue #72)** — Narrator↔character **`*_full.json`** pairing for **manual/scripted** analysis — and **specified** Issue **#69** offline evaluation when implemented — uses **structural turn identity** (**`context_snapshot.continuity_turn_index`**) as the primary join; **`event_id`** is **legacy fallback** only when top-level **`continuity_turn_index`** is absent. **`run_scene_eval_v2`** does **not** ship today (documentation reconciliation **#211**). Spec: **`AUDIT_DOCUMENTATION.md`** (*Canonical structural join contract*).
- **Not runtime control** — These join fields are **observability / post-hoc tooling**; Director, validation, progression, and continuity commits **do not** branch on audit evaluation join keys.

### Continuity mutation audit surfaces (Issues #81 / #79)

**Runtime (#81):** Spatial and excursion lifecycle commits on the **`process_turn`** path flow through **`continuity_mutation_pipeline`**; **`turn_metadata_by_index[beat]`** may include **`continuity_mutation_resolution`** (composer output; authoritative for what committed on that beat).

**Audit (#79, observational — not #59 runtime authority):** Per-turn **`*_full.json`** rows expose **CTAR** under **`metadata.ctar`** (projection of that turn bucket, not a full dump of **`turn_metadata_by_index`**), **`context_snapshot.scene_state_after`** as a **direct** **`SceneState.to_dict()`** mirror, optional **`metadata.excursion_audit_digest_v1`**, and optional **`metadata.continuity_audit_origin`** for **`pipeline_turn`** provenance when applicable. Session-level **`_audit_summary.json`** includes **`continuity_observability_summary_v1`** (strict schema rollup, including **`session_audit_origin`** for bypass beats) when a **`ContinuityManager`** is passed into **`write_summary_report`**, else **`continuity_observability_status_v1`** (**`unavailable`**). Normative field definitions and #59 boundaries: **`AUDIT_DOCUMENTATION.md`** (*Continuity observability (Issue #79)* and subsections).

### Continuity authority and evidence lanes (GitHub #224)

**Doctrine anchor:** **[Issue #224](https://github.com/KizzieFae/Holy_Grail_RP/issues/224)** records the **stable** continuity-authority reconciliation for exit/off-focal semantics, audit read discipline, and related contract tensions (umbrella **audit/doctrine** issue). **Child lanes** for follow-on work — [#225](https://github.com/KizzieFae/Holy_Grail_RP/issues/225) (bounded implementation/design), [#226](https://github.com/KizzieFae/Holy_Grail_RP/issues/226) (strategic reshaping), [#227](https://github.com/KizzieFae/Holy_Grail_RP/issues/227) (`must_remain` reevaluation) — are **not** canonized here beyond pointers; **do not** treat unfinished or speculative outcomes from those issues as **implemented** architecture in this file.

**Committed truth:** **`SceneState`** and the continuity structures that **`ContinuityManager`** updates on the **authoritative** path — principally **`process_turn`** (plus documented bootstrap/setup seams) — define **committed** focal presence, excursions, issues, events, and related narrative state for the live session.

**Evidence vocabulary (stable doctrine):**

| Lane | Meaning |
|------|---------|
| **Intent** | What the **character move** expresses structurally (beats, motivation, etc.). **Input** to validation and continuity processing — **not** by itself proof of what **committed**. |
| **Interpretation** | Deterministic or heuristic **readings** of the move or scene (classifiers, exit heuristics, narrative summaries, operator-facing labels). May **inform** continuity; **does not** replace **`SceneState`** as proof of commit. |
| **Commit** | What continuity **adopts** on the authoritative path for that beat (**`process_turn`**, pipeline-backed mutations, reconciled presence). This is what the runtime **treats as true** after processing. |
| **Observation** | **Audits**, **mirrors** (e.g. **`scene_state_after`** when emitted), session **`consequences`** / **tags** in narrative or metadata, and similar **telemetry**. These are **observational** or **tooling-facing** unless they reflect the same facts **already** in committed continuity; they **do not** override **`SceneState`**. |

**Narrator `rendered` prose** is **presentation only** — not continuity authority (see **Off-focal / reentry signal contract** and Narrator sections below).

**Classifier tags** (**`exit`**, **`repositioning`**, etc.) and **`turn_metadata["consequences"]`** document the **classifier lane**; an **`exit`** tag **does not** by itself prove physical removal from **`present_characters`**. Use **`SceneState`** / roster fields after commit for **committed** presence (see **Exit narrative vs effective on-stage presence**).

**Explicitly deferred from this section (see linked issues):** Global **proposal-framework** semantics, **compatibility-view** governance, **scratch-authority** redesign, and full **ingress/OUTPUT** legality closure — **#226**. Bounded **operational** posture for specific template/must-remain lanes — **#225** until implemented. Long-term **`must_remain` primitive** evaluation — **#227**.

## Architecture Changes

### Before (Free-form character prose)

- Characters wrote unrestricted third-person narrative prose
- Characters could accidentally narrate other characters' actions/thoughts
- No hard separation between self-narration and scene-narration

### After (Narrator-mediated)

- Characters produce structured self-only output:
  - `action`: brief visible action (self only)
  - `dialogue`: spoken words
  - `motivation`: private goal/tactic/emotional driver/risk level
- Director decides who acts next and may introduce a light environment or tension beat
- Narrator converts structured output into polished scene prose while preserving dialogue verbatim
- Each character has private state:
  - long-term goal
  - medium-term goal
  - short-term tactics
  - emotional state
  - private memories/interpretations
  - persistent identity anchors (`voice_profile`, `reaction_profile`, `speech_fingerprint`, `core_goals`)

## Key Components

### 1. Character State Management (`character_state.py` facade over `character_state_model.py` and `character_state_manager.py`)

Tracks per-character:

- Identity (name, description, personality)
- Goals (long-term, medium-term, current tactic/objective)
- Emotional state
- Persistent identity anchors:
  - `voice_profile`
  - `reaction_profile`
  - `speech_fingerprint`
  - `core_goals`
- Private memory/notes
- Character-specific interpretation summaries of scene events
- Relationship states

**Prompt assembly note:** Identity and relationship text for character prompts comes from **`CharacterState.to_prompt_identity_context`**. Episodic list formatting (**`character_memory_summary`**, **`recent_observations`**) is owned by **`memory_layer.retrieval`** and composed into a single **`state_context`** string in **`app_turn_prompting.build_character_turn_prompt`** via **`build_character_state_context_for_prompt`**, then passed unchanged into **`prompt_builders.build_character_turn_prompt`**. See **`autogen_rp/docs/architecture.md`** for the full `state_context` contract and fallback-vs-memory invariant.

Commit-time episodic writes are owned by **`memory_layer`** (facade → writes → storage); observer lines are perception-filtered at write time (`perception_audibility`). **`ContinuityManager`** remains authoritative for scene/issue/event truth—do not conflate it with per-character episodic prompt text.

#### Runtime Packet Seam (Phase 0.5 — character prompt path complete)

A **read-only** seam for **character** prompts: **`CharacterPromptInputAssembly`** captures the **exact inputs** to **`prompt_builders.build_character_turn_prompt`** once per turn. **`live_bundle_from_character_prompt_assembly`** and **`runtime_packets_from_character_prompt_assembly`** derive the live kwargs dict and **`RuntimeScenePacket`** / **`RuntimeCharacterPacket`** from that assembly (**no dual derivation**). **`RuntimeScenePacket`** (stable scene slice + session fields) supports this character path; it is **not** yet the full shared-scene packet for Director/Narrator. **`RetrievedContextBundle`** (Phase 2+: optional authored index + episodic merge; non-authoritative). **Continuity and `CharacterState` remain the source of truth**; packets are **normalized projections** for future packaging, not a second store.

- **Phase 2–3.1 retrieval (authored index only):** **Non-authoritative** optional snippets from a **JSON index** on disk (`schema_version` 2 includes **`lore`**). **Phase 3.1:** offline **`authored_index_compile.compile_authored_index`** from a **manifest** → compiled JSON; CLI **`scripts/compile_authored_retrieval_index.py`**. Not vector search, graph DB, transcript mining, or dynamic memory. Selection runs **once** in **`app_turn_prompting.build_character_turn_prompt`** via **`retrieved_context_select.py`**; **`runtime_packets.build_runtime_character_packet`** only receives **`retrieved=`** (no selector calls inside `runtime_packets`). Optional index path: env **`RP_RETRIEVED_CONTEXT_INDEX`**. Primary lane order: **template → setup → world_lore (template/tag match) → self (`character_local` only) → relationship**; per-`source_kind` subcaps; **lore text truncated at selection** if over cap (full text stored in compiled index). Formatted text is injected in **`prompt_builders.build_character_turn_prompt`** **immediately after** the scene grounding block and **before** **CURRENT SCENE STATE** (therefore before **RECENT SCENE TRANSCRIPT** and the rest of the structured prompt). Active retrieval logs at INFO under **`rp_app.retrieved_context`** (item count, char count, `source_ref` list). **Accepted baseline + Phase 4A:** **minimal `lore_facts` + template `role_slots` + `premise`**; activation **only** via **`RP_RETRIEVED_CONTEXT_INDEX`** (optional CLI **`--retrieved-context-index`** on headless sim). **Headless** **`scene_template_id`** for template-aware selection. **Audits:** **`retrieval_summary`** per character turn; **`retrieval_session`** merged into **`_audit_summary.json`** after **`write_summary_report`** (Streamlit and headless via **`apply_retrieval_session_to_audit_summary`**); also in headless **`structured_eval`** when metrics are exported — see **`AUDIT_DOCUMENTATION.md`**. **Strict** headless verify when ON + template id. **Historical pilot** + **rejected situational cap:** **`data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md`** / **`RP_SETUP_TODO.md`**.
- **Where built:** `app_turn_prompting.build_character_turn_prompt` constructs **`CharacterPromptInputAssembly`**, then the live kwargs bundle, then calls the prompt builder. When env **`RP_PACKET_SHADOW_COMPARE`** is `1`, `true`, or `yes` (default **off**), packets are built **from the same assembly**, reconstructed, and compared. Shadow adds **no** continuity/character-state mutations—only logging on mismatch (`rp_app.packet_shadow`, **stderr**; not audit-persisted). Optional core prompt-text compare when structured bundles match; suffix layers excluded.
- **Validation:** **Structured** comparison of the kwargs-shaped bundle for `prompt_builders.build_character_turn_prompt` (live vs reconstructed from packets + the same `CharacterState` instance), including **`retrieved_context_section`**. Parity corpus: **`tests/test_runtime_packets.py`**. Helpers in **`runtime_packets.py`**; shared ladder/relationship logic in **`prompt_derivations.py`** avoids circular imports.
- **Cast / presence labels (id vs display):** **`prompt_builders.build_cast_and_scene_role_participants`** (with **`prompt_identity_same`**) excludes the acting character from the others-only cast and dedupes **CAST ROLE MAP** inputs using the same **`get_character_display_name_fn`** as live assembly. **`runtime_packets.reconstruct_character_prompt_input_bundle`** requires that resolver for parity with **`app_turn_prompting.build_character_turn_prompt`**. **`prompt_derivations`** still uses raw string equality where it compares names; the normalized **`cast`** list supplied to the prompt builder addresses the id/display duplicate and self-in-others failure mode on this path.
- **Post–#24 validation wave (2026-04-07):** Headless scenario matrix with audits **`session_388`–`session_393`** and sampled character `*_full.json` checks — **no regression** on this seam for the runs recorded under **`SCENARIO_VALIDATION_FRAMEWORK.md`** / **`RP_SETUP_TODO.md`** (Issue Tracking). Identity bleed (**GitHub #1**) was **not** targeted for reproduction; remains **open**.
- **Phase 1 — scoped retrieval-lock (complete):** Inventory confirmed **no retrieval seam bypass** on this path; **`RetrievedContextBundle`** on **`CharacterPromptInputAssembly`** is the **behavioral source**; **`retrieved_context_section`** is **pure derived** from that bundle (**assembly invariant**). Added invariant + snapshot + prompt-shape tests only — **no** new selector behavior, lanes, or retrieval architecture. See **`RP_SETUP_TODO.md`** Phase 1; **`tests/test_phase1_retrieval_seam.py`**.

**Phase 3.4 — canonical knowledge (contract only):** The repo-root **`CANONICAL_KNOWLEDGE_MODEL.md`** defines the **canonical knowledge entry** contract, **authority ceilings** by `knowledge_type`, **`subject_scope`** resolution rules, and **future** graph/vector/agent retrieval compatibility. Phase 3.4 is **spec + static ingestion contract**; it **does not** require changing the runtime retrieval selector, merge behavior, or packet APIs unless a later phase explicitly schedules that work.

### 2. Structured Output Format

Character moves are **versioned**. **Normative post-boundary** shape for the **v2** migration (**GitHub #134** / **#136**) is defined under **Normative v2 character move** below. **Runtime parsers and validators** follow the **child-issue cutover** order in **#134** (**#137–#143**). **Production model-facing prompts** (character system prompts, turn **OUTPUT RULES**, retry discipline) require **canonical v2** output (**GitHub #142**): root **`move_schema_version` 2**, non-empty **`beats[]`**, no root **`action`** / **`dialogue`**. **Ingress is v2-only** (**GitHub #143**): model output must include **`move_schema_version: 2`**; legacy v1-shaped root objects are **rejected** at the parse boundary (not normalized).

#### Historical v1 shape (archival / pre-#143)

The following root-level **`action`** / **`dialogue`** layout appears in **older audits** and documentation as the pre-v2 self-only shape. It is **not** accepted at ingress after **#143**. **Post-boundary** canonical shape is **v2** with **`move_schema_version: 2`** and **`beats[]`**. Do **not** treat root **`action`** / **`dialogue`** as valid alongside **`beats`** on the same conforming v2 document.

```json
{
  "action": "lifted her cup, eyes narrowing at the doorway",
  "dialogue": "Who is she?",
  "motivation": {
    "goal": "test whether Celina knows the stranger",
    "tactic": "probe with a direct question",
    "emotional_driver": "suspicion",
    "risk_level": "low"
  },
  "audibility": "public",
  "audience": []
}
```

For **canonical v2** moves, per-beat **`audibility`** / **`audience`** on **`speech`** beats are **normalized** in `perception_audibility.py`. **Perception boundaries use the structured move as ground truth**; narrator `rendered` prose is not parsed to infer who heard what. Historical v1 root **`audibility`** / **`audience`** exist only in archived records, not in live ingress.

#### Normative v2 character move (`move_schema_version` 2)

> **Semantic proposal authority (#232):** Root **`semantic_proposals`** is **governed on the wire** (#230) and **consumed by continuity** on the authoritative path. **Accepted** proposals are the **sole commit source** for v1 covered semantics (`off_focal`, `reentry`, `excursion_lifecycle`). Reconstruction-era covered commit paths (flatten exit/reentry, classifier tag → presence, βʹ) are **suppressed** until removal ([#235](https://github.com/KizzieFae/Holy_Grail_RP/issues/235)–[#238](https://github.com/KizzieFae/Holy_Grail_RP/issues/238)). **No proposal → no covered commit.** **Reject** → `proposal_legality` retry / forfeit; **no** `process_turn`; **no** reconstruction fallback.

This subsection is the **single in-repo normative contract** for **v2** structured character moves (**GitHub #136**). **Semantic** contents of **`scene_state_updates`** are **not** specified here (optional **object envelope** only); mutation payload definitions are owned by continuity / later seams (**e.g. GitHub #140**). **Ingress** is duplicate-key–safe JSON + **v2** validation (**#137**); v1-shaped ingress was removed in **#143**; **prompt** cutover is **#142**.

**Canonical example** (illustrative; not all optional roots need appear):

```json
{
  "move_schema_version": 2,
  "beats": [
    {
      "type": "action",
      "action": "She squared her shoulders, watching the door."
    },
    {
      "type": "speech",
      "dialogue": "Who is she?",
      "audibility": "directed",
      "audience": ["Marlene Fletcher"]
    }
  ],
  "motivation": {
    "goal": "test whether Celina knows the stranger",
    "tactic": "probe with a direct question",
    "emotional_driver": "suspicion",
    "risk_level": "low"
  },
  "scene_state_updates": {}
}
```

**Versioning**

| Rule | Definition |
|------|------------|
| Field name | `move_schema_version` |
| JSON type | integer |
| Required | Yes for conforming v2 documents |
| Location | Root only; must not appear on beats or inside `motivation` / `scene_state_updates` |
| Allowed values | Exactly `2` for this contract. Broader beat or root layout changes require a **new** `move_schema_version`, not silent extension within v2 |

**Root fields**

- **Required:** `move_schema_version` (`2`), `beats` (array), `motivation` (object)
- **Optional:** `scene_state_updates` (JSON **object** when present; `{}` valid). **Envelope only** — inner keys and domain meaning are **out of scope** for this contract; **`#137`** may verify “is an object,” not continuity semantics under **`#136`** authority.
- **Optional (A1 — GitHub #230):** `semantic_proposals` (JSON **array** when present). **Intent only** on the wire until **#232** consumption; see **A1 `semantic_proposals`** below.
- **Prohibited at root:** `action`, `dialogue`, `audibility`, `audience`, `type`, reconstruction-era carriers (`presence_changes`, `excursion_lifecycle`, `spatial_transition`, and legacy v1 presence/spatial roots), and any property not named in required/optional above

**Legacy root `action` / `dialogue`:** Not part of v2. A document with root **`action`** and/or **`dialogue`** is not a conforming v2 object, even if `move_schema_version` is `2` and `beats` is present (invalid v2 or pre-boundary legacy input).

**`beats[]`**

- JSON array; **minimum length 1**; empty array **invalid**
- **Order is authoritative** for the turn’s beat sequence (downstream presentation may merge adjacent beats only where a later seam explicitly allows; no reordering)
- **Maximum length:** not specified by this contract
- Each element is an object with **`type`** exactly **`action`** or **`speech`** (case-sensitive)

**Unknown fields on any beat are invalid under v2.** Only the fields listed below for that `type` are permitted.

**`type`: `action`**

- **Required:** `type`, `action` (non-empty string after trim)
- **Optional:** none
- **Forbidden:** all other keys (including `dialogue`, `audibility`, `audience`, `motivation`, `scene_state_updates`, `move_schema_version`, `beats`)

**`type`: `speech`**

- **Required:** `type`, `dialogue` (non-empty string after trim)
- **Optional:** `audibility`, `audience`
- **Forbidden:** the beat-level **`action`** field used on `action` beats, and all keys not listed in required/optional

**Speech audibility**

- **`audibility`** only on **`speech`** beats; **omit** → effective **`public`**
- Allowed values: **`public`**, **`directed`**, **`private`** (strings, case-sensitive)
- **`audience`:** JSON array of strings
- If **`audibility`** is omitted or **`public`**: **`audience`** must be **omitted** or **`[]`**; **non-empty `audience` is invalid**
- If **`directed`** or **`private`**: **`audience`** required and must be a **non-empty** array of strings
- Root-level **`audibility`** / **`audience`:** **prohibited** on v2

**`motivation`**

- **Required keys:** `goal`, `tactic`, `emotional_driver`, `risk_level` (each a JSON string, non-empty after trim)
- **Additional keys:** allowed (forward extension without v2 shape churn)

**A1 `semantic_proposals` (GitHub #230 — wire + emission; consumption #232)**

- **Omit** the root key when the turn has **no** off-focal / reentry / excursion lifecycle **commit intent** to declare.
- When present: JSON **array**, maximum **8** items (**ingress cap**).
- Each item is an object with **only** these keys:
  - **`kind`** (required string): exactly **`off_focal`**, **`reentry`**, or **`excursion_lifecycle`**
  - **`character`** (required string): non-empty after trim; names the subject of the proposal
  - **`operation`** (required **only** when **`kind`** is **`excursion_lifecycle`**): exactly **`open`**, **`update`**, or **`close`**
- **Forbidden on items:** any key not listed above; **`operation`** on **`off_focal`** or **`reentry`**
- **Semantics:** proposals express **semantic commit intent**, not proof of commit. **`beats[]`** carry narrative; proposals declare what continuity **should** consider committing **after** the consumption lane (**#232**). Until then, validators retain proposals on the parsed move; **continuity must not** treat proposals as authoritative commits in Phase A.
- **Do not** use root **`presence_changes`**, root **`excursion_lifecycle`**, or **`spatial_transition`** on v2 moves (ingress rejects; prompts must not teach them).

**Invalid under v2 (summary)**

- Missing or non-integer **`move_schema_version`**, or any value other than **`2`**
- Any **prohibited** or **unknown** root property; root **`action`**, **`dialogue`**, **`audibility`**, or **`audience`**
- **`beats`** missing, not an array, or **empty**
- **`motivation`** missing, not an object, or any required key missing / not a non-empty string after trim
- Any beat not an object; **`type`** not exactly **`action`** or **`speech`**; **unknown keys** on a beat
- **`action`** beat missing **`action`** or containing any disallowed key; **`speech`** beat missing **`dialogue`** or containing any disallowed key (including the **`action`** field used on action beats)
- **`speech`** **`audibility`** not one of **`public`** / **`directed`** / **`private`**; **public** (explicit or by omission) with **non-empty** **`audience`**; **`directed`** / **`private`** with **`audience`** missing, not an array, or empty
- **`audibility`** or **`audience`** on an **`action`** beat; nested **`move_schema_version`**, **`beats`**, **`motivation`**, or **`scene_state_updates`** inside a beat
- **`scene_state_updates`** present but not a JSON **object**
- **`semantic_proposals`** present but not a JSON **array**, over cap, or any item failing **A1** shape rules above
- Root **`presence_changes`**, **`excursion_lifecycle`**, **`spatial_transition`**, or other non-allowlisted root keys (**ingress** enforces allowlist)
- Invalid JSON or **duplicate keys** at parse time: not a conforming document

**Compatibility boundary (contract only)**

- **Ingress** accepts **only** v2 documents with root **`move_schema_version: 2`** (**#143**). Legacy v1 root layouts are **not** normalized; they are **rejected** with a clear error.
- **Downstream** layers consume **only** objects satisfying this v2 contract after a successful parse; **#142** model-facing instructions require **`beats[]`** and forbid root **`action`** / **`dialogue`** on conforming model output.
- **Read-only** helpers (`character_move_adapters`, audit projections) may still interpret **archived** rows or fixtures that use historical root **`action`**/**`dialogue`** for display or offline checks — that is **not** ingress.

**Parse implementation (GitHub #137 / #143 — narrow scope)**

- **Module:** `character_move_ingress.py` — fenced unwrap, then `json.loads` with an `object_pairs_hook` that **rejects duplicate keys in every object** (before schema detection). `parse_json_payload` (Director, etc.) uses the same loader.
- **v2-only:** root **`move_schema_version`** must be present and **integer `2`**. Missing version, or v1-shaped root object without **`move_schema_version`**, **rejects** (no v1 allowlist, no `RP_LEGACY_V1_*` flag).
- **`move_schema_version`** present but not **integer 2**: **reject** (no other-version fallback in this layer).
- **Caps** (structural only): `MAX_V2_BEATS` 64, `MAX_V2_TEXT_CODEPOINTS` 8192, `MAX_V2_AUDIENCE_ITEMS` 32, `MAX_V2_SEMANTIC_PROPOSALS` 8, `MAX_V2_PROPOSAL_TEXT_CODEPOINTS` 256 per proposal string field.
- **Handoff type:** :class:`CanonicalV2Move` in `character_move_adapters.py` — a ``dict`` subclass with **only** v2 keys stored. Legacy ``.get("action")`` / ``.get("dialogue")`` and ``["action"]`` / ``["dialogue"]`` return **read-only** concatenations from ``beats`` (no root-level v1 shadow fields persisted on the object).
- **``scene_state_updates``:** this layer checks **JSON object** when present, not internal semantics.
- **Turn runner:** for ``move_schema_version == 2``, root-level v1 ``normalize_move_audibility`` heuristics do **not** apply to the whole move; **speech** beats are normalized per beat in ``perception_audibility`` (Issue **#138**).

**v2 perception / audibility (GitHub #138)**

- **Ground truth:** structured move / ``beats[]`` only; **no** narrator ``rendered`` parsing for audibility.
- **Speech beats:** ``audibility`` / ``audience`` only on ``type: speech``; **omit** audibility → **public**. **Directed** and **private** are **visibility-equivalent** here (who may receive verbatim ``dialogue`` for that beat), not a claim of semantic equivalence elsewhere.
- **Action beats:** always visible to all recipients in structured views; **not** audibility-gated.
- **Canonical vs derived:** ``recent_structured_moves`` entries retain **full** v2 ``beats`` (authoritative, unredacted). **Per-recipient** prompt/history views use **derived** projections: non-perceivable speech ``dialogue`` is replaced by a **deterministic stub**; **beat order** is unchanged; beats are **not** removed.
- **Director:** consumes **unredacted** canonical structured character actions. **Characters** consume **projected** structured tails where applicable. Recent **transcript** lines for the Director use **full** stored ``rendered`` text (orchestration is not an in-world perceiver).
- **Helpers:** ``character_move_adapters`` supplies read-only iteration / shallow copy helpers; projections do **not** introduce a second stored truth.

**v2 continuity / consequences (GitHub #140)**

- **Commit authority:** ``ContinuityManager.process_turn`` is the sole runtime commit path for continuity state. Ingress and response validation may **reject** moves; they do **not** apply ``scene_state_updates`` or other continuity commits. Registry-backed ``scene_state_updates`` apply via ``apply_registered_resolved_outcome_updates`` / ``resolved_outcome_registry`` on that path.
- **Classifier input:** ``ConsequenceClassifier.classify_turn`` consumes **canonical** structured moves: for v2, **flat** ``action``/``dialogue``-equivalent text is derived from ``beats[]`` via ``character_move_adapters`` (concatenations), not per-recipient **projected** stubs.
- **PublicEventExtraction:** ``PublicEvent.summary`` is **not** a raw dump of canonical dialogue. ``perception_audibility.public_safe_event_summary`` (alias ``public_event_extraction``) strips non-public verbatim speech from provisional summaries before the text is stored on ``PublicEvent``. Private/directed speech must not appear verbatim in that global-facing prose.
- **Knowledge (eligibility only):** ``continuity_knowledge_helpers`` gates who may receive verbatim speech in **interpretation** strings and **event knowledge** propagation using the same audibility rules; this does **not** define episodic storage policy.

### 3. Director Agent

Director receives structured orchestration inputs and returns:

- `next_actor`
- optional `environment_event`
- optional `tension_shift`
- `reason`

**`director_model_reason` (GitHub #207):** Optional field on the post-parse Director **`decision`** dict. Present only when the model JSON includes a **`reason`** or **`reason_for_choice`** key and parse succeeded. Value is the **verbatim** rationale string from that parse, **before** addressee alignment, progression override, participation fairness, validation/diagnostic merges, and before display-name substitution on **`reason`**. **Omitted** on hard routes (no available actors, forced speaker, continuation override), on parse-failure fallback decisions, and when neither rationale key is present. **Immutable** after parse.

**Episodic interpretation ladder (GitHub #208):** `memory_layer` chooses the **`interpretation`** string stored with the actor episodic event as follows when **`director_model_reason`** exists and is non-empty after strip → use **that verbatim tier** (**no** display-name normalization). Else use merged **`decision["reason"]`** (full operator/diagnostic chain). Else fall back to move **`motivation`** `goal=` / `tactic=` formatting as before. This keeps operator logs and episodic retrieval aligned when diagnostics matter, while avoiding blind dependence on merged **`reason`** when a clean verbatim model rationale is available.

Distinct from merged, operator-facing **`reason`** (and from narrative **`director_reason`** audit mirrors). See **`AUDIT_DOCUMENTATION.md`** (*Selection attribution and `director_model_reason`*).

Director inputs are intentionally structured and lightweight:

- current scene state, including location, scene phase, present characters, and recent tension or environment beats
- scene-template context, including template ID and premise
- cast role map, including assigned roles, `presence_constraint`, and informational authority labels
- recent structured character actions (**verbatim** canonical v2 structured moves, including per-beat speech; Issue **#138**)
- public character goal/emotion snapshot
- active issues and recent public events
- recent scene transcript (**Director:** full ``rendered`` lines; **characters:** perception-filtered via ``perception_audibility``—see Issue **#138**)
- spotlight history and currently available next actors

Director selection policy is prompt-guided rather than hard-coded. It is instructed to:

- treat roles, presence constraints, authority labels, active issues, location, scene phase, and the latest trigger as primary evidence for who should act next
- prefer the smallest relevant pressure core for the current beat instead of rotating the cast for fairness
- treat `must_remain` as structural presence in the scene, not as a requirement to speak every beat
- avoid selecting secondary present characters unless they were directly addressed, are the natural responder, or would create an immediate consequential complication

The Director does not write prose.

#### Hybrid tension pacing (continuity application)

When the Director is **neutral** on directional `tension_shift` (no valid `escalate` / `soften` token), classified consequence tags may recommend a tension nudge **`up`** or **`down`** via `tension_pacing_policy.resolve_hybrid_pacing`, applied in `ContinuityManager._update_scene_state`. **Saturation gate:** consequence-driven **`up`** is **suppressed** when `current_tension_level` is already **`extreme`** (effective `none` / `hold`; character audit `metadata.hybrid_pacing` may set `consequence_up_suppressed_saturation: true`). **Director** explicit `escalate` / `soften` and consequence **`down`** are unaffected. **No** phase- or climax-specific logic in this gate.

**Deterministic selection gates (before / after Director):** `app_turn_director.py` applies **forced speaker** and **continuation override** when eligible. **v1 policy:** if continuation override targets an actor who is already the **last spotlight** speaker, continuation is **skipped** (C2) and the Director runs instead — see `RP_SETUP_TODO.md` Phase 0 §I. After Director output, **progression override** and **participation fairness** may adjust the pick; they are explicitly gated so they do not apply when continuation already fired.

**Progression-gated addressee alignment:** When the **progression enforcement gate** is active for the beat, `semantic_validation.apply_gated_addressee_alignment_under_progression_enforcement` may **override** `decision["next_actor"]` with the resolved semantic **`direct_address_target`** if the semantic assessment is clean (no parse error), confidence ≥ `SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD`, `should_flag_direct_address_miss` is true, and the target is in the available pool. The human-visible reason suffix for this hop is assembled in **`director_selection_postprocess`** via **`director_reason_projection.merge_addressee_alignment_reason`** (GitHub **#210 C-A**) — **`semantic_validation`** must not mutate `decision["reason"]` directly. Hybrid pacing and other Director policies are unchanged; this path is **narrow** and **does not** subsume post-validation **fairness_rotation** or general validated-vs-final pick reconciliation (tracked separately: GitHub **#25**).

#### Progression advisory (MVP)

When the deterministic **progression advisory** layer detects elevated **stall pressure**, the Director may receive a short **PROGRESSION ADVISORY** prefix (outside the JSON payload) suggesting advancement channels from the optional static profile in **`{template_id}_progression.json`** (Template-associated support file) or **built-in** defaults—see **`load_progression_profile_for_template_id`** (**#119**). This is **guidance only**; it does not override selection logic or continuity.

Beat-shift activation uses the **same** computed **`stall_score`** threshold as this advisory layer (alongside the existing short-user-message path), so there is a **single** plateau-related signal rather than duplicate detectors.

#### Progression enforcement vs continuity classification

When **`stall_score`** is at or above the enforcement threshold (`progression_enforcement.py` / `progression_advisory.STALL_BEAT_SHIFT_THRESHOLD`), the character turn runner may **require** a qualifying structural delta after continuity **`process_turn`**. Qualification uses **Q1–Q4** in **`progression_enforcement.py`**, which read **`turn_metadata_by_index[turn_index]["consequences"]`** and related continuity fields (issues, presence markers, allowlisted `scene_state_updates`). **Continuity remains authoritative:** those consequence strings are produced by **`ContinuityManager._classify_turn_consequences`** → **`ConsequenceClassifier.classify_turn`** (`continuity_consequence_classifier.py`), not by progression enforcement.

##### `turn_metadata["consequences"]` (classifier lane) vs continuity commits

- **`turn_metadata["consequences"]`** is the **deterministic classifier output only** (the string list from **`ConsequenceClassifier`**). It does **not** enumerate every change continuity recognizes or commits.
- **Continuity commits**—**`PublicEvent`** / narrative state, **issue** lifecycle updates, **scene** / registry-backed fields (including allowlisted **`scene_state_updates`**), and related metadata—proceed through **`ContinuityManager.process_turn`** and helpers **independently** of whether the classifier emitted tags for that turn.
- **Progression qualification** may still succeed when **`consequences == []`**: for example **Q2** (issue change) and **Q4** (allowlisted **`scene_state_updates`**) can satisfy the structural-delta gate alongside an empty **Q1** consequence list. An empty classifier list therefore does **not** mean “no structural progression” in the continuity sense.
- **Audit visibility:** When character audit logging includes **Audit v2**, the deterministic check **`char_masked_progression_strict`** may flag this pattern for operators (`metadata.audit_v2`); it is **observational only** and does **not** change runtime behavior—see **`AUDIT_DOCUMENTATION.md`** (Audit v2 / **#73**).

**Long-session / progression-retry instability (resolved posture):** Spurious **`validation_progression_retry`** cases where the structured move was materially progressive but **`consequences`** was empty or Q1 was tripped by single-tag repetition were fixed by **improving deterministic consequence classification**, not by weakening enforcement or changing Q1–Q4. Concretely:

- **`REPOSITIONING`** uses bounded movement, locus, and transition substring rules; **`turn`** counts as locomotion only with **word-boundary** verb matching, and **negated** phrases such as “did not turn” / “didn’t turn” / “not turning” are scrubbed so they do not falsely satisfy movement.
- **`REFUSAL`** / stance uses **intent-aligned** rules on goal/tactic (**resist** / **challenge** / extended seeds) plus curated dialogue tokens, **legacy** dialogue markers (`won't`, `refuse`, `deny` remain substring-based), or strong intent phrases—**not** dialogue alone. In the **legacy** path only, **`no`** and **`not`** match as **standalone words** (word-boundary / token style), not raw substrings, so words like "nothing" or "know" do not trigger REFUSAL via those two markers.
- **Multi-tag** emission per turn is preserved (duplicate **categories** deduped); richer tag sets support **Q1** without altering Q1–Q4 definitions.
- **`progression_enforcement.py`** and advisory **thresholds** were **not** relaxed to mask thin classification.

Regression coverage: `python/tests/test_continuity_consequence_classifier.py`.

**Known coverage gap (low priority):** Deterministic rules still omit **`consequences`** for some **low-intensity** beats (passive compliance, soft interaction shifts without geometry or strong stance signals). That is consistent with current design and does not imply incorrect labels when enforcement is stable; broadening sensitivity without inflating Q1 or calm-scene noise is **future work**. Tracked on GitHub: https://github.com/KizzieFae/Holy_Grail_RP/issues/23

#### Exit narrative vs effective on-stage presence

**Resolution (GitHub #18):** **`ContinuityManager.process_turn`** finalizes scene presence (reconcile / invariants) **before** creating **`PublicEvent`**. When **`exit`** is classified but the actor **remains** in **`present_characters`** (e.g. **`must_remain`** or soft exit skip), **`_align_exit_narrative_with_effective_presence`** replaces definitive **“left the immediate scene”**-style **`state_changes`** / matching **`summary`** / standard EXIT **`actionable_implications`** with wording that reflects **retained on-stage presence**. **True** departures (actor **not** on **`present_characters`**) keep the original EXIT phrasing. Classifier, rendering, prompts, and **`tags` / `consequences`** lists were unchanged in that fix.

**Watch:** **`exit`** may still appear in **`tags`** or **`consequences`** when the actor stays on the roster. **`present_characters`** (and related **`SceneState`**) are **authoritative** for whether someone has actually left; do **not** infer physical removal from the **`exit`** tag alone.

#### Scene Grounding layer (MVP)

A **read-only** **SETTLED SCENE FACTS** block is injected into Director and character prompts when facts exist. Facts are a **deterministic, capped, allowlisted** projection **derived from** `PublicEvent.grounding_markers` (computed in continuity classification) — not a second authority (PRD §5.8). See `scene_grounding.py` and `autogen_rp/docs/scene-grounding-layer.md`. Rebuilt in `turn_runner_updates` after each successful continuity `process_turn`; **no** writes to `CharacterState` or continuity.

**Character prompts only — BINDING CONSTRAINTS:** a **high-priority** subsection lists a **filtered** subset of the same promoted facts (allowlisted keys) so the model treats assignment / entry-type settlements as non-deniable in dialogue. Formatted by `format_character_binding_constraints_section` in `scene_grounding.py`, passed as `scene_binding_constraints_section` from `app_turn_prompting`, inserted in `prompt_builders.build_character_turn_prompt` **before** **OUTPUT RULES**.

**Binding contradiction enforcement — `assignment:sleeping_surface` (narrow slice, validated 2026-04):** Continuity **promotion** and scene-grounding **projection** for `assignment:sleeping_surface` are unchanged. **Deterministic** validation rejects character moves that **deny** a promoted sleeping-surface assignment or **assert a different** settled surface for the same assignee, using **closed phrase lists** and declarative-frame checks in `response_validation_binding_sleeping_surface.py` (`validate_binding_sleeping_surface_contradiction`). It runs inside `response_validation_content.validate_bot_response` **after** registry slot checks and **after** the scene-truth tier—**no** LLM judge and **no** retrieval. **`turn_runner_turn.execute_character_turn`** uses the **unified character attempt budget** (see **§5** — *Character slot attempt budget*): on **`[BINDING_SLEEPING_SURFACE]`** when a binding-class retry is still allowed, log **`validation_binding_retry`**, append a short **`[BINDING_RETRY]`** note on the next attempt, **`continue`**; otherwise use the normal validation hard-fail path. **`turn_execution_metadata`** records `binding_retry_*` fields for observability. **Scope limit:** This is the **first** narrow enforcement slice only—not a generalized multi-fact contradiction system. **`[REGISTRY_SLOT] sleeping_surface_assignment: invalid_surface_id`** (allowlisted surface id mismatch on `scene_state_updates`) is a **separate** response-validation path (`response_validation_registry_slots.py`); repeated occurrences in long runs are tracked separately (**GitHub #31**; do not conflate with this slice).

**Character prompts only — EVIDENCE & AUTHORITY DISCIPLINE:** a **static** instruction block in `prompt_builders.py` (after binding constraints, before **OUTPUT RULES**) discourages stating **unsupported** concrete specifics as clinical / institutional / “noted” fact while still allowing strong pressure and contestable bluffing. Prompt-only; no schema or validator changes.

### 4. Narrator Rendering

**v2 (GitHub #139):** The narrator is **presentation only**; it does **not** choose visibility. ``execute_character_turn`` supplies a pre-selected structured view:

- **Canonical, unredacted** v2 move — when the session has no **in-scene** player character on the cast (``player_character`` missing or not in the active ``char_names``), via ``redact_structured_move_for_orchestration`` (or equivalent pass-through).
- **Per-recipient projected** v2 move — when ``player_character`` is set and is on the active cast, via ``filter_structured_move_for_viewer`` (Issue **#138** rules: speech stems may be replaced by the deterministic inaudible stub; beat order preserved).

Narration uses **only** that supplied dict for prompts, fallbacks, and verbatim checks. The stored ``move`` on canonical continuity / character audits remains the **parsed** character output where applicable; **chat** history still carries the authoritative structured move; the **rendered** line matches the **narration** view, not a second re-derived truth.

**v2 ``beats[]`` contract for narrator output (summary):** speech lines must appear in ``rendered`` as **ordered, contiguous, verbatim** substrings from the **supplied** view. Action beats may be paraphrased; beat order is preserved; adjacent speech may be merged in prose only if every speech substring remains intact in order. **No** v2 path uses deprecated root ``dialogue`` for fallback. **v1** moves keep the previous flat ``action`` / ``dialogue`` narrator prompt and ``"…"`` presence check.

**Implementation (narrow):** ``app_turn_rendering.render_character_move``, ``fallback_render_move``, ``prompt_builders.build_narrator_render_prompt`` (v2 shape via ``structured_move``), and ``turn_runner_turn._narrate_move_for_character_turn``.

### 5. Orchestration Flow

**Per-orchestration-turn pre-turn routing (GitHub #213):** In `turn_runner.run_character_turns`, each Director selection pass resolves the **effective user trigger for that orchestration turn** (Streamlit: the same user message each beat; headless: optional per-turn schedule), runs `ContinuityManager.apply_pre_turn_user_presence_routing` with that string and session `pending_forced_speaker`, **then** derives `eligible_participants`, `offstage_list`, and `available_actors`. Continuity truth is unchanged; this is **ordering only** so trigger-driven offstage / release heuristics align with the pool passed to `choose_next_actor`.

```text
User Input
    ↓
Director evaluates structured scene state, roles, current pressures, and the latest trigger
    ↓
Available actor set excludes any character already used this round
    ↓
Character Agent sees:
    - Current scene state
    - Recent structured actions (**`dialogue` redacted** when this character is not allowed to perceive it)
    - Recent scene transcript (**perception-filtered for this character**; full narrator prose for others’ beats only when audibility is `public` or this character is in `audience`)
    - Director decision for the current beat
    - Its own private state
    ↓
Character outputs structured move (action/dialogue/motivation)
    ↓
Validation: reject if tries to narrate others
    ↓
Narrator renders character move → polished prose
    ↓
Update character private state (goals, emotional shift, memories)
    ↓
Update per-character interpretation summaries
    ↓
Render to UI
```

#### Character slot attempt budget (`execute_character_turn`, GitHub #133)

Each director-selected character runs in a **single outer loop** over **`max_character_attempts`** (default **3**; `DEFAULT_MAX_CHARACTER_ATTEMPTS` / parameter in `turn_runner_turn.py`). **Continuity `process_turn`**, narrator render, and **`chat_history`** append happen only after a **successful structured parse** and **validation** for that slot; failed attempts do **not** mutate continuity or transcript.

- **Parse recovery:** If the model output does not parse as a structured move, the runner logs **`parse_retry`** (non-terminal) and **`continue`** while a later attempt index remains, adding a JSON-discipline note to subsequent system prompts. **`parse`** (terminal), **`actors_failed_this_round`**, and forfeiture of the slot for that round batch occur only when the **last** attempt still fails parse. **LLM generation exceptions** for the character call remain an **immediate** hard fail (no retry against the attempt budget).

- **Validation-class retries:** For **`[DUPLICATE]`**, **`[BINDING_SLEEPING_SURFACE]`**, **`[INVESTIGATION_ANCHOR]`**, **`[PROPOSAL_SCOPE]` / `[PROPOSAL_INCONSISTENT]` / `[PROPOSAL_COHERENCE]`** (GitHub **#231**), and **progression enforcement** (after **`process_turn`** rollback when the gate is active), the runner may **`continue`** at most **once per failure class** per character slot, and only if the unified cap still allows a later attempt. Further rejection of the same class or other validation failures follow the normal hard-fail path. **Director `decision` and `next_actor` are unchanged** across attempts in the same slot.

- **Proposal legality (#232, pre-`process_turn`):** After #231 coherence and **`validate_bot_response`**, **`evaluate_proposal_legality`** runs when proposals are non-empty. Illegal batch → **`[PROPOSAL_LEGALITY]`** → class **`proposal_legality`** retry (distinct from **`proposal_coherence`**). Exhausted → forfeit; **no** `process_turn`; **no** narrator. **Accept** / **no_proposal** → `process_turn` with **`ProposalAuthorityContext`**.
- **Proposal coherence (#231, pre-`process_turn`):** After parse/ingress, **`validate_proposal_structural_coherence`** (self-only proposals, proposal-set consistency) runs **before** **`validate_bot_response`**. When **`semantic_proposals`** is non-empty and structural checks pass, **`assess_proposal_beat_contradiction`** may run (typed proposals + flattened v2 beats text via **`legacy_flat_action_text` / `legacy_flat_dialogue_text`**; no **`SceneState`** or **`motivation`** in the checker payload). Only **`contradicted`** rejects; **`aligned`**, **`unclear`**, parse failure, disabled checker (**`RP_PROPOSAL_COHERENCE_LLM=0`**), or unavailable model client **fail-open**. **`[SCENE_PRESENCE]`** semantic override remains **after** **`validate_bot_response`**, unchanged.

The diagram above omits these branches for brevity.

The user's controlled character is not included in the available actor set for Director selection.

### 6. Current Context Window Strategy

The current implementation now uses a hidden continuity manager plus bounded prompt windows.

The active prompt is kept bounded by:

- recent structured moves (**per-recipient**: non-perceivable **`dialogue`** cleared)
- recent scene transcript (**per-recipient** / Director-global-safe via `perception_audibility`)
- scene state windows for tension/environment beats
- active issues / pressures
- recent public events and retrieved summary blocks
- each character's private state, interpretations, and canon anchors

The following identity anchors are treated as persistent and should not be summarized away:

- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`
- `core_goals`

#### Why continuity remains the main architectural lever

The current system already reduces prompt bloat better than a raw transcript-driven chat loop.

- recent dialogue is windowed
- recent structured moves are bounded
- agent model contexts are small
- scene state now carries structured continuity context

That means the main long-session problem is no longer just token count. The bigger issue is that
continuity quality now depends on how well the hidden continuity layer converts turns into durable,
pressure-shaped state rather than dialogue residue.

This causes several known failure modes:

- repetition and scene loops
- weak or overly text-driven pressure tracking when consequence classification is thin
- temporary tactics becoming sticky identities
- viewpoint collapse when interpretation and fact are not separated cleanly

The next architectural step is therefore to keep strengthening the continuity engine, not to move
weight back into prompts or transcript windows.

Complementing that, the **Scene Grounding** MVP projects a **small subset** of already-settled truths into prompts so models stop **re-asking** or **resetting** logistics the continuity layer has already established — without making prompts the **author** of those truths (see PRD §5.8).

## Planned Additions

### 7. Scene Opening System (Janitor-style initial messages)

**Implemented subset (GitHub #83):** Fresh continuity startup—including resolving template `scene_setup` and merging it into `ContinuityManager.scene_state` on **first** init—uses one **canonical** bootstrap path (`scene_start_bootstrap.initialize_fresh_continuity_scene_core`, invoked from `app_state_continuity.restore_or_initialize_continuity_manager`). **Streamlit** (`scene_lifecycle_start.start_scene`) and **headless simulation** (`headless_scene_simulation.prepare_headless_session`) are **input surfaces** into that spine, not parallel template-timing models; there is no headless-only late template patch after partial init. **Issue #94** adds **`bootstrap_composition.py`**: both surfaces compose a **`BootstrapInterpretation`** (intent-locked opening strategy, canonical opener refs, location precedence, `first_round_user_line` with CLI as a composition operand when no user-trigger schedule) and pass **only** interpretation-derived opening text plus **`initial_continuity`** projection into `restore_or_initialize_continuity_manager` (not raw parallel `scene_setup` authority). **Issue #101** (Streamlit): template- and character-asset paths require an explicit **`selected_opener_id`** when multiple **Opener** JSON assets exist in scope; a single opener auto-selects; opener **`label` / `description`** are displayed from file metadata (`ui_sidebar_opening`). **Issue #100** removed generic template `opening_text` as the primary Start Scene path in Streamlit. Scenario manifests declare **`startup_trigger_mode`** (`parity` \| `overlay`) for explicit round-1 simulated user-line semantics relative to the opening; CLI **`--trigger`** feeds composition when no schedule (Model A); **`--user-trigger-schedule`** remains a multi-turn harness overlay. The subsections below remain **design notes** for richer opener assets beyond the current pipeline.

The app needs authored starting messages similar to Janitor bot first messages. These are not generated from scratch each time. They are curated scene openers that establish tone, location, current pressure, and the immediate hook for player response.

#### Source pattern from archived definitions

Archived initial messages, such as Celina's, follow a clear structure:

- third-person past-tense prose
- immediate environmental framing
- character introduced through action, not biography
- clear situational tension
- direct final engagement hook aimed at `{{user}}`

#### Example shape

- setup: weather/location/mood
- inciting discovery or pressure event
- character reaction that reveals personality
- immediate playable situation
- closing line that invites user response

#### Planned AutoGen adaptation

Rather than asking the narrator to invent every opening, the narrator should select from stored authored opening assets.

#### Opening flow

```text
Scene start request
    ↓
Load selected characters + scenario metadata
    ↓
Load available authored opening message(s)
    ↓
Narrator selects or lightly adapts best-fit opener
    ↓
Narrator posts opening prose to chat
    ↓
Character turn orchestration begins from that established state
```

#### Recommended data model

Each character/scenario package should support an optional `initial_message` asset containing:

- opening prose
- scenario tags
- involved actors
- location/time metadata if known
- optional trigger conditions

#### Responsibility split

- character definitions provide authored opener content
- narrator chooses and posts the opener
- character agents do not post the initial scene block directly

### 8. Story Progression and Continuity System (Scribe2-inspired)

The RP app now includes a hidden continuity manager. The archived Scribe2 design was useful as a
directional model, but the current implementation has already adopted its central idea: a hidden
state compiler that turns transient interaction into durable continuity.

#### Current continuity model

The current continuity design uses five durable structures plus one prompt policy.

**Runtime Continuity Contract (GitHub #77 / #81):** Issue **#77** holds the agreed **contract text** (anchor/focal rules, **`ContinuityPromptProjectionV77`**, excursion store/invariants). **Validated Slice A (#77)** covers the **foundation** only—setup seam, anchor resolution with **#80**, focal **projection** parity, API-level excursions, **P_focal ∩ E_active = ∅** on covered paths. **Issue #81 (closed)** delivered **Slice A (spatial):** **`continuity_mutation_pipeline`** composes **D → S → M** precedence per **`MutationResolutionKey`** for **`CanonicalAtom.LOCATION`**, validates, and commits **`SceneState.location`** inside **`ContinuityManager.process_turn`** (optional move field **`spatial_transition.location`**; optional **`session_mutation_candidates`**). **Slice B (excursion lifecycle):** the same pipeline resolves **`CanonicalAtom.EXCURSION_LIFECYCLE`** keys scoped by **`excursion_id`** (pending-open uses an internal sentinel until an id is assigned). **M**-class proposals use optional move field **`excursion_lifecycle`** with **`operation`**: **`open`** / **`update`** / **`close`**. Validation enforces anchor-not-on-excursion, no overlapping active excursion membership on open/update, and unknown ids on update/close; apply calls **`open_excursion`** / **`update_excursion`** / **`close_excursion`** with **`commit_turn_index`** so opened/closed turn metadata matches the authoritative beat. **Slice C (reintegration):** optional **`reintegration`** on **close** applies structured merges (**events** / **issues** / **resolved outcomes**) via **`continuity_reintegration`**; **`reintegration_commit_id`** **rejects** conflicting ids after a successful apply; **late merge** on an already-closed excursion is **first-class** when no prior commit id was applied (**validated**, not best-effort). Further atoms and broader offscreen product paths are **follow-on** if filed.

**#81 — authoritative behavioral model (as implemented):**

- **Mutation authority (runtime turns):** For normal character turns, **`ContinuityManager.process_turn`** runs **`compose_resolved_mutations` → `validate_resolved_mutations_globally` → `apply_resolved_mutations`** — that pipeline is the **authoritative mutation path for runtime turns**. The same codebase also exposes **`open_excursion` / `update_excursion` / `close_excursion`**, direct assignment to **`SceneState.location`** (callers **outside** the unified fresh-scene bootstrap — GitHub **#83** — in **`scene_start_bootstrap` / `restore_or_initialize_continuity_manager`**; **not** the standard UI or headless scenario path), and the module function **`apply_excursion_close_reintegration_mutation`**. Those entry points **bypass** pipeline validation; they are **not** the runtime-turn authority surface and are **unsafe** for parity with production turn rules unless callers replicate the same checks.
- **Presence:** **`present_characters`**, **`offstage_characters`**, **`character_presence_status`**, and related **`SceneState`** fields hold **canonical stored state** (reconciled and written back via **`_resync_presence_through_authority`**). Reconciliation enforces **`present_characters` ∩ `E_active` = ∅** ( **`E_active`** = participants on **ACTIVE** excursions) and removes excursion participants from offstage lists and purges their presence-status rows while on **`E_active`**. **Soft offstage** (`temporary_offstage` / offstage membership) is **canonical** but **subordinate** to excursion state. **`present_characters` ∩ `absent_but_relevant`** is a **warning** by default; set **`RP_CONTINUITY_STRICT_INVARIANTS=1`** for a hard **`AssertionError`** on that overlap.
- **Reintegration:** A **structured merge** tied to excursion **close** (optional payload). It is **not** the only source of **`PublicEvent`**, **issues**, or **`ResolvedOutcome`** updates — ordinary **`process_turn`** logic still creates events and applies registry-backed **resolved outcomes** from structured moves. Reintegration supports **same-beat** close+merge and **late merge** after close when no **`reintegration_commit_id_applied`** is set yet (**`validate_close_reintegration_globally`**).
- **Atomicity:** **All-or-nothing rollback** (restore events, outcomes, issues, excursion snapshot, then **`_resync_presence_through_authority`**) is implemented **only** inside **`apply_excursion_close_reintegration_mutation`**. **Spatial** transitions, **excursion open/update**, **`close_excursion`** without that merge path, and **multi-key** resolved batches **do not** guarantee a single transactional rollback across keys — a failure after an earlier applied key leaves earlier mutations in place.
- **Idempotency:** **`reintegration_commit_id`** enables **idempotent** replay of the same merge; **`close_excursion`** **no-ops** when the excursion is already **CLOSED**. There is **no** global idempotency model for **spatial** moves or **excursion open** (duplicate open still conflicts).

**Off-focal / reentry signal contract (GitHub #216):** **Continuity** (`process_turn`, mutation pipeline, then `_update_scene_state`) remains the **only** routine authority for **committed** focal roster / excursion truth. **Preferred** explicit carriers for **continuity-owned** off-focal intervals: structured **`excursion_lifecycle`** (optional **`reintegration`** on **`close`**) and, when the beat commits setting, **`spatial_transition`**, composed through **`continuity_mutation_pipeline`**; **`session_mutation_candidates`** use the same **D→S→M** validation. **`ConsequenceClassifier`** / **`scene_exit_detection`** / tags feeding legacy presence scratch are **candidate-supporting** and **heuristic** relative to those fields—not a substitute for **excursion lifecycle** when an operator or checklist requires **proof** of committed off-focal state. **Orchestration** reads **mirrored** **`present_characters` / `offstage_characters`**; it does **not** author them. **Perception** (`audience` / audibility on speech beats) governs **verbatim dialogue visibility**, not **`SceneState` presence**. **Narrator `rendered` prose** is **non-authoritative** for continuity (see **`perception_audibility`**, **`AUDIT_DOCUMENTATION.md`** — perception vs continuity-grounded offstage).

##### Durable structures

- `SceneState`
- `IssueState`
- public event memory
- character interpretation memory
- canon anchors

##### Prompt policy

- maintain only a small rolling dialogue window in prompts
- promote important developments into durable memory instead of carrying forward long dialogue logs

This keeps dialogue ephemeral while preserving the narrative state that actually matters.

#### Source pattern from Scribe2

Scribe2 is explicitly non-roleplay. It acts as a continuity manager that updates a compact structured memory block from story summaries.

#### Key lessons to carry over

##### Objective layering

Each AI-controlled character should have:

- long-term objective
- medium-term objective
- short-term objective

##### Knowledge boundaries

Characters should only know what they:

- directly observed
- were told
- can plausibly infer

##### Memory compression

Not all prior events should remain in active prompt context. The Scribe2 pattern separates:

- active facts affecting immediate play
- background facts needed for continuity
- canon anchors that should rarely change

For this RP app, the same principle should be extended to separate:

- public story events
- per-character interpretations of those events
- active vs resolved pressures
- canon anchors that should resist casual drift

##### Momentum tracking

Story progression is not just "what happened". It is also:

- what tensions were resolved
- what tensions remain unresolved
- whether a character's objectives are escalating, stable, compromised, or reversing

#### Implemented AutoGen adaptation

Instead of making Scribe2 a visible chat participant, the app uses a hidden continuity layer that
runs between scene beats.

This continuity manager acts as a story-state compiler:

- dialogue and structured actions go in
- durable story state comes out

Its job is not to write prose. Its job is to convert transient interaction into usable continuity.

#### Continuity flow

```text
User turn + character turns complete
    ↓
Inspect recent structured moves + recent transcript window (prompt-facing views are perception-filtered)
    ↓
Promote significant developments into event objects
    ↓
Update scene state, issue state, and character interpretations
    ↓
Feed layered public + private context into next prompts
```

#### Recommended split between systems

- director: selects the next actor and optional environmental/tension beats
- narrator: posts prose to the chat
- character agents: choose self-only actions/dialogue/motivation
- continuity manager: updates durable structured story state

The narrator should remain lightweight. It should not become a long-horizon memory reasoner.

#### Practical mapping onto current codebase

Current `CharacterState` covers private goals, identity anchors, and private interpretation
summaries, while the continuity layer now provides the missing shared story-state structures:

- structured knowledge map through `PublicEvent.known_by` / `observed_by` / `told_to` / `inferred_by` (**`known_by` is authoritative** for retrieval; new events scope knowers by audibility; summaries avoid embedding verbatim non-public **`dialogue`**—see `perception_audibility.public_safe_event_summary`)
- active vs background fact separation through recent public events plus retrieved summary blocks
- resolved vs unresolved pressure tracking through `IssueState` lifecycle and filtered active issues
- scene-level continuity state shared across prompts through `SceneState`
- public event memory separated from private interpretation memory
- canon anchors made explicit as protected truths
- **Registry-backed resolved outcomes** (including `transaction.scene_commitment` for transactional scene commitments — GitHub #127): slot-scoped **authoritative** facts in `ContinuityManager.resolved_outcomes` with `value` carrying domain state (e.g. phase, kind, `subject_scope`, `thread_instance_id`); the type name `ResolvedOutcome` refers to **row** lifecycle (`active` / `superseded` / `revoked`), not “narrative resolved” — see `continuity_state.ResolvedOutcome` and `resolved_outcome_registry`. Scene grounding **projects** these; it does not write continuity.

The issue layer is currently a pressure-first hybrid rather than a fully consequence-native engine:

- issue creation builds a pressure profile from consequence tags, state changes, actionable implications, and bounded text fallback
- matching is primarily driven by participants, `pressure_kind`, blocked objective, and required next step
- update transitions still retain compatibility fallbacks through signal and text heuristics when structural evidence is weak

This means the continuity engine is now structurally grounded, but still intentionally conservative
about removing older fallback behavior.

#### Example conceptual split

- `SceneState`
  - setting
  - current time
  - present actors
  - environment state
  - active tensions
  - resolved tensions
  - scene phase
  - recent delta
  - canon anchors
- `IssueState`
  - issue id
  - participants
  - current status
  - `pressure_kind`
  - `blocked_what`
  - `blocked_characters`
  - `last_change`
  - `required_next_step`
  - `required_next_step_plateau_*` — streak / last-normalized text / last turn index / whether an **`advanced`** transition occurred in the current streak window; supports `continuity_issue_helpers.apply_mixed_transition_plateau_refresh` (fires after repeated **`advanced`** / **`escalated`** transitions when obligation text is frozen)
  - escalation / resolution compatibility signals
- public event memory
  - event id
  - participants
  - event type
  - summary
  - story significance
- `CharacterState`
  - long/medium/short objectives
  - emotional state
  - private interpretation memory
  - known fact IDs
  - relationship stance

#### Guardrails for continuity updates

- not every line of dialogue should become an event
- event memory must not become a disguised transcript
- characters should only receive events they know or can plausibly infer
- director reasoning must not be written into character memory as self-truth
- canon anchors should constrain interpretation drift over long sessions

#### Retrieval strategy

Retrieval should begin with deterministic filters such as:

- participants involved
- issue ids
- location
- recency
- story significance

Embeddings may be useful later, but only after event schemas, knowledge boundaries, and deterministic retrieval behavior are stable and debuggable.

#### Why this matters

This is the most important path for improving story quality over long sessions because it addresses:

- repetition
- loss of scene pressure
- character drift
- omniscient responses
- weak long-horizon character development

## Near-Term Roadmap

1. Expand authored `initial_message` asset support during scene creation.
2. Reweight issue updates further toward structured pressure/consequence matching over fallback signal matches.
3. Tighten issue creation confidence without sacrificing continuity stability when classifier output is weak.
4. Strengthen scene state and issue / pressure tracking beyond the current bounded recent-history windows.
5. Continue improving summary retrieval and reload continuity so pressure developments survive compression cleanly.
6. Add deterministic retrieval improvements before evaluating any embedding-based retrieval.

## Benefits

- **Strong separation**: characters can't write for others
- **Objective tracking**: each bot has explicit goals it advances
- **Consistent narration**: narrator controls prose style while dialogue stays character-authored
- **Deliberate orchestration**: director balances spotlight and scene pressure
- **Identity retention**: persistent voice/reaction anchors reduce character convergence
- **Extensible**: foundation for secrets, private knowledge, relationship systems

## Issue Tracking & Investigation Workflow

> **Governance relocation (GitHub Issue #45):** The authoritative **§A–§K** specification for GitHub Issues, Projects metadata, and the issue body contract is maintained in **[`governance/rp-app/issue-tracking-workflow.md`](../../../governance/rp-app/issue-tracking-workflow.md)** (repository root).
>
> **§** references used across the repo (**§B.2**, **§H**, etc.) refer to that document. Runtime Director / RP app architecture sections above are unchanged.

**Section index:** §A System of record · §A.1 Audit-driven workflow · §B Standard workflow · §B.0 Terminology · §B.1 GitHub CLI · §B.2 Verification · §B.3 Project sync (execution stages) · §B.4 Rejection · §B.5 Selection, Priority, comments, handoffs · §B.6 Template repository parity · §C Labels · §D Body template · §E Type · §F Layer · §G Title · §H Status / execution stages · §I Pattern status · §J Principles · §K Flexibility

