# Canonical Knowledge Model

Architectural specification for **Phase 3.4 — Canonical Knowledge Shape & Static Ingestion**. This document defines the **canonical runtime knowledge contract** that all authored sources must compile into. It is **not** an implementation guide.

---

## 1. Purpose and Scope

### What this document defines

- The **canonical envelope** for a single unit of injectable knowledge at runtime (`Canonical Knowledge Entry`).
- **Knowledge types** classified by **runtime function** (how the turn runner and prompt assembly consume the item), not by source file format.
- **Authority classes** and **visibility** rules that govern whether and how an item may appear in a character- or scene-facing context.
- **Provenance** requirements so every item is traceable to an origin.
- **Compile expectations** mapping static authored sources into canonical entries.
- **Injection placement** relative to continuity, grounding, retrieval, and transcript lanes.
- **Precedence and deduplication** rules relative to other runtime truth sources.
- The **boundary** between Phase 3.4 (shape + static compile + deterministic injection) and Phase 4 (vector/graph storage and advanced retrieval).

### What systems it governs

- **Runtime packets** and any structured bundle that carries knowledge into prompt construction.
- **Authored ingestion**: compilation from character cards, scenarios, setup/initial materials, lore, and other static sources into canonical entries.
- **Retrieval injection**: deterministic selection and merging of canonical items into the **assistive** retrieval lane (e.g. retrieved context sections), without elevating them to continuity authority.

### Canonical contract for future sources

All **future** knowledge sources—including **dense prose ingestion** (e.g. full novels), graph-backed stores, or vector indexes—must **emit or map into** this canonical model (or a documented extension of it). Storage technology may change; **the runtime contract for “what a knowledge item is and how it may be used”** is defined here and must remain stable enough that Phase 4+ systems **conform** to it rather than inventing parallel shapes.

---

## 2. Non-Goals (Phase 3.4)

The following are **out of scope** for Phase 3.4. They do not appear in this specification as design targets.

- **Vector / embedding** design, index layout, or similarity semantics.
- **Graph schema** design, query languages, or graph-specific optimization.
- **Transcript-wide** or session-log ingestion as a knowledge source.
- **Semantic retrieval** logic (learned rankers, LLM-chosen retrieval sets, etc.).
- **LLM-based selection** of which knowledge items apply (selection and merge must remain **deterministic** given inputs and caps).
- **Weakening** continuity, grounding, or binding authority (see §5, §10).

---

## 3. Canonical Knowledge Entry (Envelope)

Every injectable knowledge item **must** be representable as a record with the following fields. Implementations may use equivalent names or nesting if the semantics are preserved.

### `knowledge_id`

| Aspect | Content |
|--------|--------|
| **Definition** | Stable, unique identifier for this canonical entry within the compile scope (e.g. content hash + source path, or deterministic id from source coordinates). |
| **Purpose** | Deduplication, audit trails, stable references across recompiles and future storage layers. |
| **Constraints** | Must be **deterministic** for the same source content and compile rules. Must not depend on runtime session state. |

### `knowledge_type`

| Aspect | Content |
|--------|--------|
| **Definition** | One of the enumerated **runtime-function types** (see §4). |
| **Purpose** | Drives how the runtime may use the item (truth vs guidance, which prompt regions, merge behavior). |
| **Constraints** | Must be exactly one type from the Phase 3.4 enum (extensions require a spec revision). |

### `subject_scope`

| Aspect | Content |
|--------|--------|
| **Definition** | Structured description of **who or what** the knowledge is about (e.g. agent key(s), scene template id, role slot, “global scene”, “relationship pair”). |
| **Purpose** | Enables deterministic filtering by character, scene, and retrieval caps. |
| **Constraints** | Must be machine-actionable (no prose-only scope). Empty or “unscoped” only where explicitly allowed by type rules. |

### `visibility`

| Aspect | Content |
|--------|--------|
| **Definition** | Enumeration of **who may receive** this item when building prompts (e.g. public, directed recipient set, scene-only, compiler-internal). |
| **Purpose** | Aligns with perception and recipient rules; prevents cross-character leakage. |
| **Constraints** | Must be consistent with `subject_scope` and with project perception/audibility contracts. Private items must not appear in public-only lanes. |

### `authority_class`

| Aspect | Content |
|--------|--------|
| **Definition** | One of the **authority levels** in §5. |
| **Purpose** | Determines whether the item may be stated as fact, suggested as behavior, or offered as reference; governs conflict resolution vs continuity and grounding. |
| **Constraints** | Every entry has exactly one class. **No** class may imply continuity-equivalent authority. |

### `source_ref`

| Aspect | Content |
|--------|--------|
| **Definition** | Opaque or structured pointer to the **origin** of this knowledge (file path + fragment id, manifest row, template id + section, future novel offset + edition id, etc.). |
| **Purpose** | Traceability, regeneration, debugging, future re-ingestion. |
| **Constraints** | Must be **non-empty** and stable across deterministic recompiles from the same sources. |

### `source_kind`

| Aspect | Content |
|--------|--------|
| **Definition** | High-level category of origin: e.g. `character_card`, `scenario`, `scene_template`, `lore_manifest`, `setup_message`, `future_ingestion_novel`, etc. |
| **Purpose** | Policy hooks (compile rules, caps per kind), auditing, Phase 4 adapter boundaries. |
| **Constraints** | Closed enum for Phase 3.4 static sources; extensible for future kinds only via spec update. |

### `tags`

| Aspect | Content |
|--------|--------|
| **Definition** | Ordered or unordered set of short labels for **non-authoritative** grouping (template ids, arc names, faction, retrieval lane hints). |
| **Purpose** | Deterministic filtering, caps, and compile-time grouping without encoding truth. |
| **Constraints** | Tags **do not** override `authority_class`, `visibility`, or continuity. |

### `priority`

| Aspect | Content |
|--------|--------|
| **Definition** | Ordinal or tier used **only within** the assistive retrieval merge (when caps force drops). |
| **Purpose** | Deterministic ordering when multiple items compete for the same slot. |
| **Constraints** | Must not be used to override continuity or grounding. Lower priority does not delete authoritative continuity facts. |

### `text`

| Aspect | Content |
|--------|--------|
| **Definition** | Primary human-readable payload intended for prompt injection (or a normalized excerpt). |
| **Purpose** | The consumable surface for the model after compile. |
| **Constraints** | Must not embed hidden instructions that contradict `authority_class`. Size limits are implementation-defined but compile must enforce caps. |

### `structured_payload` (optional)

| Aspect | Content |
|--------|--------|
| **Definition** | Typed JSON-like object for machine-readable facets (e.g. relationship endpoints, role constraints, numeric tiers) when `text` alone is insufficient. |
| **Purpose** | Supports packet shadow compare, validation, and future graph projection without changing the envelope. |
| **Constraints** | Schema is **type-dependent**; must not duplicate fields that belong in continuity or grounding stores. If absent, `text` must suffice for intended injection. |

---

## 4. Knowledge Types (by Runtime Function)

Types are defined by **runtime function**, not by source filename.

### `identity_fact`

| Aspect | Content |
|--------|--------|
| **Represents** | Stable attributes of a character or entity as **authored setup** (name facets, baseline role, institutional affiliation in setup, etc.). |
| **Runtime use** | Character packet / identity context; seed for prompts. |
| **Truth / guidance** | **Setup-truth** only within authored scope; **not** continuity-updated state. |

### `behavioral_tendency`

| Aspect | Content |
|--------|--------|
| **Represents** | Tendencies, habits, or default reactions **as guidance** for generation. |
| **Runtime use** | Voice/behavior hints; must not be cited as immutable world fact. |
| **Truth / guidance** | **Guidance** (behavioral). |

### `goal_or_drive`

| Aspect | Content |
|--------|--------|
| **Represents** | Authored objectives, motivations, or drives relevant to play. |
| **Runtime use** | Character objective lanes; informs beats without replacing continuity issue state. |
| **Truth / guidance** | **Guidance**; may be superseded by in-scene continuity. |

### `relationship_fact`

| Aspect | Content |
|--------|--------|
| **Represents** | Authored relationship edges or history **as known at setup** (not live relationship state). |
| **Runtime use** | Relationship-focused retrieval; social context in prompts. |
| **Truth / guidance** | **Setup-truth** for static authored backstory; **not** authoritative for “current” relationship if continuity has moved. |

### `world_rule`

| Aspect | Content |
|--------|--------|
| **Represents** | Setting-level rules, physics, institutions, or cosmology **as authored** for the template or lore. |
| **Runtime use** | Scene/world framing; must align with template grounding, not contradict settled grounding. |
| **Truth / guidance** | **Setup-truth** at template level where authoritative; otherwise **reference_only** if contestable. |

### `scene_setup_fact`

| Aspect | Content |
|--------|--------|
| **Represents** | Premise, opening conditions, initial locations, cast expectations for a scene or scenario **before** play advances. |
| **Runtime use** | Scene packet; opening beats. |
| **Truth / guidance** | **Setup-truth** for scene open; may be refined by continuity as play proceeds. |

### `role_constraint`

| Aspect | Content |
|--------|--------|
| **Represents** | Template constraints: presence, authority labels, must-remain, slot obligations. |
| **Runtime use** | Orchestration and template-aware prompts. |
| **Truth / guidance** | **Setup-truth** for **structural** constraints; not a substitute for continuity presence state. |

### `voice_guidance`

| Aspect | Content |
|--------|--------|
| **Represents** | Diction, register, taboo, stylistic notes for portrayal. |
| **Runtime use** | Character prompt voice sections. |
| **Truth / guidance** | **Guidance** only. |

### `lore_reference`

| Aspect | Content |
|--------|--------|
| **Represents** | Pointed lore excerpts or summaries for assistive recall. |
| **Runtime use** | Retrieved reference material; optional cross-links. |
| **Truth / guidance** | **Reference_only** unless explicitly promoted by a separate authoritative process (not this layer). |

### `interpretive_frame`

| Aspect | Content |
|--------|--------|
| **Represents** | How a character or narrator may **frame** information (bias, uncertainty, POV)—not raw world fact. |
| **Runtime use** | Character interpretation lanes; separate from transcript and from settled facts. |
| **Truth / guidance** | **Interpretive guidance**; never continuity-equivalent. |

---

## 5. Authority Classes

Authority classes describe **what the runtime may treat as** when injecting into prompts. **Continuity remains the sole authority** for in-scene established truth; no class here overrides it.

### `foundational_truth`

| **Allows** | Items that are treated as **fixed authored baseline** for identity/setup/world framing where the template or card is authoritative for **pre-play** state. |
| **Cannot** | Override continuity commits, grounded settled facts, or live issue state. Cannot retroactively negate an established continuity event. |
| **Continuity** | If continuity contradicts an authored foundational item, **continuity wins** for current scene truth; the item may be demoted, masked, or flagged at compile/inject time per policy. |

### `setup_truth`

| **Allows** | Truth **at scene or scenario open** (premise, initial cast layout as authored, opening objectives). |
| **Cannot** | Lock post-play outcomes; cannot block continuity updates. |
| **Continuity** | Superseded by continuity as the scene evolves. |

### `behavioral_guidance`

| **Allows** | Shaping likely behavior and voice without asserting world fact. |
| **Cannot** | Be presented as binding scene truth or as grounding-class fact. |
| **Continuity** | Never overrides continuity. |

### `interpretive_guidance`

| **Allows** | Subjective framing, uncertainty, POV-colored summaries. |
| **Cannot** | Assert uncontested institutional or physical facts as authoritative. |
| **Continuity** | Never overrides continuity. |

### `reference_only`

| **Allows** | Assistive recall, citations, optional context; clearly subordinate lanes. |
| **Cannot** | Force model or runtime to treat content as established in-scene truth. |
| **Continuity** | Never overrides continuity. |

---

## 6. Visibility and Recipient Rules

- **Per-character filtering**: Every item with non-public `visibility` must specify recipients (agent keys or an explicit rule resolvable to keys). The compile and inject stages apply **the same recipient resolution** as character prompt assembly; no item may appear for a character outside its visibility class.
- **Perception / audibility**: Directed or private knowledge must align with project **perception_audibility** semantics: if the narrative state would not permit a character to know a fact, visibility must not route that item to that character unless the type and authority class explicitly allow “player-visible but character-stub” patterns already defined by the product (those patterns remain subordinate to continuity and perception gates).
- **Public vs private vs conditional**: **Public** items may appear in any recipient’s retrieval lane subject to caps. **Private** items are restricted to declared recipients. **Conditional** visibility depends on structured predicates (e.g. scene template id, role, relationship focus) that must be **evaluable without LLM interpretation**.
- **Constraint**: Visibility rules **reduce** leakage; they do not grant omniscience. They do not replace continuity’s authority over what has happened in play.

---

## 7. Provenance and Source Requirements

- **`source_ref`** must identify a **specific origin** (path + anchor, manifest key, or future stable offset in an ingested corpus). Bulk imports must still expand to **per-entry** refs or a documented composite ref that resolves to a span.
- **`source_kind`** must classify the **pipeline** that produced the entry so adapters and audits can reason about trust and refresh rules.
- **Traceability**: No canonical entry may exist without both `source_ref` and `source_kind`. Anonymous blobs are invalid inputs to compile.
- **Future novel / graph ingestion**: Dense sources must map to **many** entries, each with span-level `source_ref`, preserving edition/version metadata in `structured_payload` or a dedicated provenance sub-record as specified when that pipeline is added. Graph/vector stores in Phase 4 **reference** the same logical `knowledge_id` / `source_ref` contract; they do not replace it.

---

## 8. Compile Rules (Authored Sources → Canonical Model)

- **Character cards** decompose into multiple entries: typically `identity_fact`, `behavioral_tendency`, `goal_or_drive`, `relationship_fact` (where authored), `voice_guidance`, and optionally `lore_reference` slices. Each field or section maps to **one or more** typed entries with correct `authority_class` and `subject_scope`.
- **Scenarios / setup / initial messages** map to `scene_setup_fact`, `role_constraint`, and template-linked `world_rule` where applicable; user-facing setup text becomes typed entries, not an unlabeled paste.
- **Reshape requirement**: If a source file cannot compile without loss of semantics, **the source is updated** (structure or metadata) rather than bypassing the model via ad-hoc strings.
- **Prohibition**: **No freeform bypass**: unstructured “dump” fields that enter prompts without typing, authority, visibility, and provenance are **not permitted** as a Phase 3.4 outcome. Legacy paths must be migrated or wrapped as explicitly `reference_only` with full provenance.

---

## 9. Runtime Injection Contract

- **Packet entry**: Canonical items appear only in **defined packet or bundle slots** agreed for Phase 3.4 (e.g. retrieved context, character runtime context) as **serialized or structured lists** derived from the envelope.
- **Prompt assembly**: Injection occurs in **assistive** regions (e.g. retrieved reference material, optional lore blocks), **after** continuity-backed state and **alongside**—never **instead of**—scene grounding where grounding is authoritative for settled facts.
- **Placement relative to**:
  - **Scene grounding**: Grounding for **settled** facts takes precedence for binding-style truth; canonical `setup_truth` / `foundational_truth` must not contradict grounded entries; conflicts resolve per §10.
  - **Retrieved context**: Canonical compiled items feed the **same deterministic merge and caps** as existing authored retrieval; no second shadow lane unless explicitly specified for debugging.
  - **Transcript**: Transcript remains the record of play; canonical knowledge is **not** injected as fake transcript unless a product-specific feature explicitly defines that (out of scope here).
- **Non-authoritative guarantee**: This layer **assists** generation; it does not **commit** continuity, does not **settle** grounding, and does not **replace** episodic visibility rules.

---

## 10. Deduplication and Precedence Rules

### Continuity

- **Always authoritative** for established in-scene state, issues, presence consistent with continuity rules, and committed interpretations where continuity owns them.
- Canonical knowledge **never** duplicates a continuity fact in a **truth-bearing** class if continuity already owns that dimension for the current turn.

### Scene grounding

- **Settled scene facts** (grounding) win over conflicting **authored** `world_rule` or `scene_setup_fact` when the scene has moved past setup.
- Canonical items that conflict with grounding are **dropped or demoted** to `reference_only` with explicit policy—not merged as equal truth.

### Authored retrieval

- Multiple entries with the same `knowledge_id` or duplicate semantic content: **dedupe** to one representative per inject scope using deterministic rules (hash, priority, source_kind tier).

### Episodic memory

- Episodic items are **continuity-backed** and **capped**; canonical static knowledge does not impersonate episodic provenance.
- Precedence: **continuity > grounding > episodic (visibility-gated) > canonical static retrieval** for overlapping factual claims; **guidance** classes may coexist if they do not assert conflicting fact.

### Conflicts

- **Truth-bearing vs truth-bearing**: continuity or grounding wins; canonical authored loses for current scene truth.
- **Guidance vs truth**: truth lanes win; guidance may remain if labeled correctly and does not smuggle facts.

### No duplication of authoritative facts

- Compile must avoid emitting a second **foundational_truth** or **setup_truth** copy of information already represented in continuity or grounding for the same beat unless explicitly a **read-only echo** in `reference_only` (auditable).

---

## 11. Phase Boundary (3.4 → Phase 4)

### Phase 3.4 guarantees for future vector/graph work

- A **stable envelope** (`knowledge_id`, types, authority, visibility, provenance, text/payload).
- **Deterministic** compile from static sources and **deterministic** merge into existing packet/retrieval injection.
- **Clear non-authoritative** placement relative to continuity and grounding.
- **Extension point**: new `source_kind` values and new storage backends **project into** this model.

### Intentionally deferred (Phase 4+)

- Embedding models, approximate nearest neighbor indexes, graph query planners.
- Learned ranking and hybrid retrieval.
- Cross-session corpus-scale deduplication strategies beyond deterministic rules.

### Conformance requirement

Phase 4 storage systems **must** store and retrieve **records compatible with** this canonical model (or a versioned extension documented as a delta to this spec). They **must not** introduce a second runtime-facing knowledge shape for the same semantic role.

---

## 12. Open Questions / Deferred Design

The following are **intentionally** not fixed in this document; they are resolved in later specs or implementation when required.

- Exact **JSON schema** versions and validation tooling for `structured_payload` per `knowledge_type`.
- Numeric **caps and tiers** per template, cast size, and lane (product tuning).
- Full **predicate language** for conditional visibility beyond Phase 3.4 needs.
- **Edition control** for novel-scale sources (versioning, diff, partial recompile).
- **Localization** or multi-language canonical text rules.
- **Formal verification** of merge properties (optional engineering work).

---

*End of specification.*
