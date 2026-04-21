# Authored source contract (canonical file types)

This document is the **single in-repo authority** for **what authored files are** in the Holy Grail RP stack: **which JSON shapes are canonical**, **how they relate to each other**, and **what belongs elsewhere** (runtime, session, ingestion manifests).

**Relationship to other specs**

- **[CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md)** — Defines the **compiled runtime knowledge entry** (canonical envelope) produced by **offline** ingestion from sources. That is the **retrieval/inject** contract, not the **authored file** layout.
- **[PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)** — Describes **runtime** packet intent (`RuntimeCharacterPacket`, `RuntimeScenePacket`, `RetrievedContextBundle`). Packets are **assembled at turn time**; they are **not** authored JSON file types.
- **Scene-start code paths** — `scene_start_bootstrap`, `scene_lifecycle_start`, headless `prepare_headless_session` consume **bootstrap + templates + characters**; see [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md) and [MODULE_INDEX.md](./MODULE_INDEX.md).

**Legacy state (explicit)**

Until the **migration issue** (see GitHub; linked from **Issue #82** discussion) is implemented, **on-disk** character cards, scene templates, scenario/bootstrap JSON, and opener assets may still be **legacy or mixed**: extra fields, deprecated keys, or shapes that predate this contract. **Do not assume** every file matches the tables below without checking. The **contract** is normative for **new authoring** and **post-migration** files.

---

## 1. Four canonical authored file types

These are the **only** canonical **authored** (designer-written, versionable) **file kinds** for RP knowledge and scene start. Everything else in the list below is a **supporting layer**, not a duplicate “authored type.”

| Type | Owns (one sentence) |
|------|---------------------|
| **Character** | Who someone is (durable character **knowledge**). |
| **Template** | What **kind** of scene structure exists (reusable structural **knowledge**). |
| **Scenario / Bootstrap** | **How** a **specific** scene **starts** (deterministic scene-start **contract**). |
| **Opener** | **What prose** opens the scene (authored **opening prose** asset). |

**Supporting layers (not canonical authored file types)**

- **Session / runtime bootstrap inputs** — Ephemeral or persisted session wiring; not a substitute for the bootstrap **contract** document.
- **Run-control** — Flags, CLI, app settings; not character or scene knowledge.
- **Ingestion / compile configuration** — Retrieval **manifests**, compile CLI, adapter tables; **inputs** to offline compile, **not** bootstrap truth at runtime.

---

## 2. Ownership and boundary rules (locked)

- **Character** = who someone is.
- **Template** = what kind of scene structure exists (not a specific scene instance).
- **Scenario / Bootstrap** = how a **specific** scene starts.
- **Opener** = what prose opens the scene.

**Boundaries**

- **Bootstrap** should be **reference-based** where possible (`character_refs`, `template_ref`, opener references), instead of embedding full character or template payloads.
- **Templates** define **structure** (roles, surfaces, slots), **not** a specific narrative scene identity.
- **Openers** define **authored opening prose**, **not** structural scene layout.
- **`opening_text`** on a template (if present) is **legacy fallback / compatibility** only — **not** the primary authored opening model.
- **`initial_messages`** is **not** canonical template knowledge.
- **`progression_profile`** is **not** canonical template knowledge (advisory/progression layers may still **read** legacy fields until migration).
- **`agent_name`** is **not** canonical character knowledge.
- **Retrieval manifests** are **ingestion / compile inputs**; they are **not** runtime or bootstrap **truth** by themselves.

---

## 3. Canonical Character (knowledge) schema

**Include** (normative authored fields):

- `name`
- `description`
- `personality`
- `speaking_style`
- `goals`
- `medium_term_goal`
- `core_goals`
- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`
- `system_prompt`
- `relationships`
- `lore_facts`

**Exclude** from this authored type:

- `agent_name`
- Any bootstrap, session-only, run-control, or ingestion-manifest fields (those belong in their respective layers).

---

## 4. Canonical Template (knowledge) schema

**Include**:

- `template_id`
- `premise`
- `anchor_role_name`
- `role_slots`
- `sleeping_surface_slots`
- `location_entry_slots`
- Optional **legacy compatibility** only: `opening_text` (fallback; not the primary opener model)

**Exclude**:

- `initial_messages`
- `progression_profile`
- Bootstrap, session, run-control, ingestion-manifest fields

---

## 5. Canonical Scenario / Bootstrap (scene-start contract)

Normative top-level shape:

| Field | Required | Notes |
|------|----------|--------|
| `bootstrap_schema_version` | Yes | Version of this contract. |
| `id` | Yes | Stable identifier for this scenario/bootstrap. |
| `metadata` | No | e.g. `title`, `intent` |
| `character_refs` | Yes | References to character knowledge sources (not inline character cards). |
| `template_ref` | No | Reference to a template when the scene uses one. |
| `role_assignments` | Conditional | Present when the contract requires fixed slot-to-character bindings. |
| `location` | Yes | Scene location specification (as agreed for the product). |
| `opening` | Yes | Opening selection (see below). |
| `first_round_user_line` | Yes | Deterministic first user line or sentinel per product rules. |
| `initial_continuity` | Yes | Initial continuity/bootstrap payload for the scene start. |

### Opening model (`opening`)

- **`opening.strategy`** — One of: `template_asset` | `character_asset` | `template_static_text` | `generated`
- **`opening.ref`** — Present when the strategy requires an asset reference (e.g. opener id, template fragment, or character-bound asset path — **exact resolution rules** follow loader implementation).

**Interpretation**

- **`template_static_text`** corresponds to **legacy** inline template text paths; prefer **`template_asset`** / **`character_asset`** / dedicated **Opener** assets when authoring new content.
- **`generated`** covers model-generated openings where no static asset is mandated.

---

## 6. Opener (authored opening prose asset)

**Opener** is a **first-class authored artifact** for **opening prose** that is **not** the template structural contract and **not** the full bootstrap record.

- Referenced from **bootstrap** `opening` when `strategy` is `template_asset` or `character_asset` (or as otherwise specified by loader conventions).
- **Does not** replace **Template** structure fields (`role_slots`, etc.).
- **Does not** alone define **bootstrap** identity; **Scenario / Bootstrap** remains the scene-start contract document.

*(Concrete on-disk filename conventions and JSON keys for pure opener files may be added when migration tooling lands; **semantic** role is fixed here.)*

---

## 7. Where this is enforced

- **Authoring** and **reviews** should use this document as the checklist.
- **Loaders / compilers** may **accept** legacy fields **until** the migration issue is closed; behavior is defined in code and release notes, **not** by redefining this contract per file.

---

## 8. Related issues

- **[Issue #82](https://github.com/KizzieFae/Holy_Grail_RP/issues/82)** — Scenario canonization; Issue body includes an **Authored-source contract (supplement)** with links to this doc and **#91** (see thread for authored-source vs headless/UI scenario scope).
- **[Issue #91](https://github.com/KizzieFae/Holy_Grail_RP/issues/91)** — Migrates on-disk files to these shapes; legacy fields, compatibility, and sequencing (**do not** use #82 for bulk conversion work).
