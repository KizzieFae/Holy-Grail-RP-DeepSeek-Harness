# Authored source contract (canonical file types)

This document is the **single in-repo authority** for **what authored files are** in the Holy Grail RP stack: **which JSON shapes are canonical**, **how they relate to each other**, and **what belongs elsewhere** (runtime, session, ingestion manifests).

**Relationship to other specs**

- **[CANONICAL_KNOWLEDGE_MODEL.md](./CANONICAL_KNOWLEDGE_MODEL.md)** — Defines the **compiled runtime knowledge entry** (canonical envelope) produced by **offline** ingestion from sources. That is the **retrieval/inject** contract, not the **authored file** layout.
- **[PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)** — Describes **runtime** packet intent (`RuntimeCharacterPacket`, `RuntimeScenePacket`, `RetrievedContextBundle`). Packets are **assembled at turn time**; they are **not** authored JSON file types.
- **Scene-start code paths** — `scene_start_bootstrap`, `scene_lifecycle_start`, headless `prepare_headless_session` consume **bootstrap + templates + characters**; see [autogen_rp/docs/architecture.md](./autogen_rp/docs/architecture.md) and [MODULE_INDEX.md](./MODULE_INDEX.md).

**Legacy state (explicit)**

**Issue #91 (closed)** removed **`initial_messages`** from on-disk scene templates; **opening prose** for those scenes lives in **Opener** assets (e.g. `{template_id}_initial_message.json`). Template **`opening_text`** remains an optional **legacy fallback** until **Issue #92** / follow-on work. The **v1** **normative** **metadata** **schema** for **Opener** JSON is **section 6** (consensus: **[Issue #93](https://github.com/KizzieFae/Holy_Grail_RP/issues/93)**; contract encoding: **[Issue #96](https://github.com/KizzieFae/Holy_Grail_RP/issues/96)**). **Runtime/bootstrap** wiring to the canonical Scenario/Bootstrap model is **Issue #94**.

Other **on-disk** character cards, templates, scenario/bootstrap JSON, and opener assets may still carry **other** legacy or mixed keys (e.g. `progression_profile` on templates, `agent_name` on characters) until addressed separately. **Do not assume** every file matches the tables below without checking. The **contract** is normative for **new authoring** and for files **after** applicable migration.

---

## 1. Four canonical authored file types

These are the **only** canonical **authored** (designer-written, versionable) **file kinds** for RP knowledge and scene start. Everything else in the list below is a **supporting layer**, not a duplicate “authored type.”

| Type | Owns (one sentence) |
|------|---------------------|
| **Character** | Who someone is (durable character **knowledge**). |
| **Template** | What **kind** of scene structure exists (reusable structural **knowledge**). |
| **Scenario / Bootstrap** | **How** a **specific** scene **starts** (deterministic scene-start **contract**). |
| **Opener** | **Opening** **prose** **and** **v1** **per-asset** **metadata** (see **section 6**) for the **scene** **open**. |

**Supporting layers (not canonical authored file types)**

- **Session / runtime bootstrap inputs** — Ephemeral or persisted session wiring; not a substitute for the bootstrap **contract** document.
- **Run-control** — Flags, CLI, app settings; not character or scene knowledge.
- **Ingestion / compile configuration** — Retrieval **manifests**, compile CLI, adapter tables; **inputs** to offline compile, **not** bootstrap truth at runtime.

---

## 2. Ownership and boundary rules (locked)

- **Character** = who someone is.
- **Template** = what kind of scene structure exists (not a specific scene instance).
- **Scenario / Bootstrap** = how a **specific** scene starts.
- **Opener** = the authored opening prose and v1 Opener metadata (section 6) for that asset.

**Boundaries**

- **Bootstrap** should be **reference-based** where possible (`character_refs`, `template_ref`, opener references), instead of embedding full character or template payloads.
- **Templates** define **structure** (roles, surfaces, slots), **not** a specific narrative scene identity.
- **Openers** define authored opening prose and the v1 metadata fields listed in section 6, not structural scene layout.
- **Scenario / Bootstrap** must not duplicate Opener prose as a second authored source; it references openers via `opening` (see section 5).
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

**Prose location (authoring authority)** — The authoritative copy of static opening prose resides in **Opener** JSON assets (see section 6), not in the **Scenario / Bootstrap** record. The `opening` field selects how the scene starts and which asset applies (via `strategy` and `ref`); it must not embed a second authoritative authored copy of that prose. Choosing which variant (`id`) is a selection / `ref` problem among **Opener** assets; it does not relocate prose into the bootstrap file.

---

## 6. Opener (authored opening prose asset)

**Opener** is a first-class authored file type for opening prose and v1 per-asset metadata (below). It is not the **Template** structural contract and not the full **Scenario / Bootstrap** record.

- Referenced from **bootstrap** `opening` when `strategy` is `template_asset` or `character_asset` (or as otherwise specified by loader conventions).
- **Does not** replace **Template** structure fields (`role_slots`, etc.).
- **Does not** alone define **bootstrap** identity; **Scenario / Bootstrap** remains the scene-start contract document.
- **Opener** JSON assets are the sole canonical authored home of opening prose and of the v1 metadata fields in this section.
- **Scenario / Bootstrap** does not duplicate that prose as a second authoritative authored source; it references openers via `opening.strategy` and `opening.ref` (or composition inputs that resolve to the same refs per loader / [Issue #94](https://github.com/KizzieFae/Holy_Grail_RP/issues/94)). Per-run which variant (which `id`) is a bootstrap / UI / session selection problem among **Opener** assets; it does not move prose into the bootstrap file.

On-disk paths for template-scoped opener files follow [Issue #91](https://github.com/KizzieFae/Holy_Grail_RP/issues/91) (e.g. `{template_id}_initial_message.json`). Schema design consensus: [Issue #93](https://github.com/KizzieFae/Holy_Grail_RP/issues/93).

### 6.1 v1 normative JSON shape (flat document)

**Required fields**

| Field | Type | Notes |
|--------|------|--------|
| `text` | string | Opening prose. **Non-empty** after trim, or the asset is **not** a valid loaded opener. |
| `id` | string | **Required** whenever **more than one** opener exists for the same **template** or **character** **scope** (see **6.2**). |

**Optional fields**

| Field | Type | Notes |
|--------|------|--------|
| `label` | string | Short display name; UI and selection. A loader may synthesize if missing on some paths. |
| `description` | string | Longer summary for lists, tooltips, docs. Canonical source: this Opener file only (see 6.2 and 6.3). |
| `tags` | array of string | Categorization / filtering; not orchestration triggers unless a future issue defines that. |
| `location` | string or null | Editorial / descriptive only (see **6.2**). |
| `time` | string or null | Editorial / descriptive only (see **6.2**). |

**Not in v1 (deferred)** — A nested `authoring` object (or any editor-only bag of the same class) is deferred and not part of the v1 canonical schema; a future tracked change may add it. Do not treat it as implied by v1.

### 6.2 Field rules (enforceable)

**`id`**

- **Uniqueness:** Each `id` **must** be **unique** within its **scope**:
  - **Template-scoped** openers: unique among all opener assets **for that** `template_id` (all files / refs that resolve as that template’s openers).
  - **Character-scoped** openers: unique among openers for that **character card stem** (same rule as file naming / resolution in use today).
- **When `id` is required:** If **two or more** opener assets exist in the **same** scope, **every** such asset **must** include a **non-empty** `id`. **Authoring** / **validation** should **reject** or **flag** scope sets that **violate** this.
- **`"default"`:** Allowed **only** when **exactly one** opener exists in that scope. If a second opener is added, **no** asset in that scope may use `id` **`"default"`**; each must have a **distinct** explicit `id`.
- **Single-opener scope:** If there is **exactly one** opener in the scope, `id` **may** be **omitted**; the runtime **may** treat **missing** `id` as **`"default"`** for resolution. **Authoring** **policy:** prefer an **explicit** `id` even for a **single** asset to avoid **collision** when a **second** asset is added later.

**`description`**

- **Canonical:** The file-level `description` on the Opener JSON asset is the only canonical authored long summary for that opener.
- **`TemplateInitialMessage.description`** (when a template shim still lists `initial_messages`) is not canonical for that summary. It must not be treated as a second source of truth for the same field. Do not rely on it for display of that opener; do not merge with file `description` unless a future issue defines a single explicit merge rule. It may remain as legacy or index-only text, or be dropped from authoring once file-level `description` is universal. Loaders that do not apply `msg_ref.description` to the loaded opener object align with file = canonical for the asset.

**`location` and `time`**

- **Meaning:** **Editorial / descriptive** metadata (tone, in-world feel, list sorting, **non-binding** labels for authors and UI).
- **Prohibited** (unless a **future** **issue** **explicitly** **connects** them):
  - They **do** **not** **define** or **update** **continuity** state.
  - They **do** **not** **feed** **scene** **grounding** as **settled** **facts** or **binding** **constraints**.
  - They **do** **not** **override** **bootstrap** `location` / `opening` / `initial_continuity`, or **template** **structural** **configuration** (`role_slots`, slots, `premise` as template knowledge, etc.).
- They are not authoritative inputs to runtime systems beyond opener-loader pass-through of metadata (e.g. for UI) unless a future issue wires them into another subsystem.

**`label` and `tags`**

- `label`: **optional**; for **display** and **matching** in selection; **not** **continuity** **truth**.
- `tags`: **optional**; **categorization** **only** unless a **future** **issue** **defines** **orchestration** use.

**`text`**

- **Required** for a **valid** opener: **non-empty** after trim. **Empty** `text` **means** the **loader** **must** **not** **surface** that file as a **loaded** opener (consistent with the **intended** **code** path).

### 6.3 Legacy and compatibility

| Item | Status |
|------|--------|
| **File-level** `description`, `label`, `tags`, `location`, `time`, `text`, `id` | **Canonical** per **6.1**–**6.2** in this document. |
| **Template** `opening_text` | Legacy fallback; not the primary opener model (see section 4 and the legacy note at the top). |
| **Template** `initial_messages[]` | Not canonical template knowledge; [Issue #91](https://github.com/KizzieFae/Holy_Grail_RP/issues/91) migrated prose to Opener files. Tolerated where shims still list file + label; `TemplateInitialMessage.description` is not canonical for opener summary (see `description` in 6.2). |
| **Missing** `id` when only one opener in scope | **Tolerated**; may resolve as **`"default"`** in the **loader**; **authoring** should **add** an **explicit** `id` when **adding** a **second** opener. |
| **Deferred** `authoring` **nested** object | **Not** in **v1** (see **6.1**). |

---

## 7. Where this is enforced

- **Authoring** and **reviews** should use this document as the checklist.
- **Loaders / compilers** may **accept** remaining **legacy** fields where compatibility shims exist; behavior is defined in code and release notes, **not** by redefining this contract per file. **Template `initial_messages`** are **not** part of canonical on-disk templates after **#91**.

---

## 8. Related issues

- **[Issue #82](https://github.com/KizzieFae/Holy_Grail_RP/issues/82)** — Scenario canonization; Issue body includes an **Authored-source contract (supplement)** with links to this doc and **#91** (see thread for authored-source vs headless/UI scenario scope).
- **[Issue #91](https://github.com/KizzieFae/Holy_Grail_RP/issues/91)** (**closed**) — Migrated on-disk files to these shapes; legacy fields, compatibility, and sequencing (**do not** use #82 for bulk conversion work).
- **[Issue #93](https://github.com/KizzieFae/Holy_Grail_RP/issues/93)** — Consensus on the v1 Opener metadata schema (field rules, ownership, legacy); decision record on the issue.
- **[Issue #96](https://github.com/KizzieFae/Holy_Grail_RP/issues/96)** — Contract encoding of #93 into this document (task owner for this file).
