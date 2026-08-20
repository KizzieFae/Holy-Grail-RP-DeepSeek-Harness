# Scene Grounding Layer (MVP) — Technical Specification

**Status:** MVP implemented in `v2/domain/modules/scene_grounding.py` (prompt injection + persistence). Current continuity-owned resolved outcome projection covers `assignment:sleeping_surface`, `communication_state:housing_call`, `medical:suppressant_formulation`, `access:location_entry`, and `transaction:scene_commitment` (transactional scene commitments, GitHub #127).  
**Authority:** [governance/sources/holy-grail-prd.md](../governance/sources/holy-grail-prd.md) (Scene Grounding product intent).  
**Placement:** Derived **after** continuity updates per turn, consumed **before** LLM calls in the packaging/prompt path.

---

## 1. Purpose

Provide a **small, deterministic, read-only** projection of **settled in-scene truths** into prompts so models **do not re-litigate** resolved logistics, object states, medical facts, or communication outcomes.

This layer is **not** continuity. Continuity **writes** truth; scene grounding **reflects** a capped subset for **prompt efficiency and coherence**.

---

## 2. Non-negotiable constraints

| Constraint | Enforcement |
|------------|-------------|
| Single source of truth | Facts are **recomputed or patched only** from continuity outputs + fixed rules + optional explicit system signals. **No** independent writer. |
| Read-only w.r.t. authority | **No** writes to continuity blobs, **no** `CharacterState` mutation, **no** orchestration / Director override. |
| Determinism | **No** LLM classification. **No** fuzzy matching on raw chat. Only structured fields, enums, and explicit rule tables. |
| Scene-local | **Dropped on scene end** (or cleared when starting a new scene). **Not** session-long memory. |
| Bounded | **Hard cap** on fact count; **allowlisted** keys per category. |

---

## 3. Scene Facts Contract (Schema)

### 3.1 Container: `SceneGroundingState`

Stored on the **scene-scoped** portion of runtime state (see §6). Serialized with session JSON under a single key, e.g. `scene_grounding`.

| Field | Type | Notes |
|-------|------|--------|
| `schema_version` | `int` | Start at `1`. |
| `facts` | `list[SceneFact]` | Ordered; **stable sort** by `(category, key)` for deterministic prompts after cap prune. |
| `last_rebuilt_turn` | `int \| null` | Monotonic turn index after full rebuild (optional optimization). |

**Cap:** `MAX_SCENE_FACTS = 16` (config constant). If promotion would exceed cap, **prune** lowest-priority entries (see §6).

### 3.2 `SceneFact` record

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `fact_id` | `string` | yes | Stable id: deterministic hash of `(category, key, scene_id, promotion_seq)` or **continuity source event id** when present. |
| `category` | `enum` | yes | One of: `assignment`, `object_state`, `medical_status`, `medical`, `communication_state`, `access`, `transaction`. |
| `key` | `string` | yes | **Allowlisted** per category (see §3.3). |
| `value` | `object` | yes | Category-specific **closed** shape (§3.3). **No** unbounded prose in v1. |
| `value_summary` | `string` | yes | **Single line**, ≤ 120 chars, **deterministically formatted** from `value` (for prompts). Not an LLM summary. |
| `source` | `object` | yes | Provenance: `{ "kind": "continuity_event" \| "consequence" \| "system", "ref": string }`. |
| `priority` | `int` | yes | **0–100**; higher wins under cap conflict. Default by category table. |
| `supersedes` | `string \| null` | no | Previous `fact_id` if this **overwrites** same `(category, key)`. |

### 3.3 Categories, allowed keys, value shapes

**Extensibility:** New keys require a **code change** to the allowlist and promotion rules — not runtime open-ended JSON.

#### A. `assignment` — spatial / role / logistics commitments

| `key` | `value` shape | Example `value_summary` |
|-------|---------------|-------------------------|
| `sleeping_surface` | `{ "assignee": "<participant_id>", "surface": "top_bunk_marlene" \| "lower_bunk_marlene" \| "top_bunk_willow" \| "lower_bunk_willow" \| "floor" \| "couch" \| "unassigned" }` | `Kizzie: top_bunk_marlene` |
| `territory_claim` | `{ "zone": string_enum, "holder": "<participant_id>" }` | Limited enums per template later; **MVP:** omit if no rules yet. |

#### B. `object_state` — durable prop state

| `key` | `value` shape | Example |
|-------|---------------|---------|
| `phone` | `{ "status": "operational" \| "broken" \| "missing" }` | `Phone: broken` |
| `first_aid_kit` | `{ "location": "willow_room" \| "common_area" \| "with_marlene" \| "unknown" }` | Optional; promote only when continuity encodes it. |

#### C. `medical_status` — agreed medical facts

| `key` | `value` shape | Example |
|-------|---------------|---------|
| `omega_suppressants` | `{ "subject": "<participant_id>", "formulation": "wrong_for_physiology" \| "standard" \| "unknown" }` | `Kizzie: suppressants wrong for physiology` |
| `injury` | `{ "subject": "<participant_id>", "kind": "burn" \| "other", "severity": "mild" \| "moderate" \| "severe" \| "resolved" }` | Only when structured signal exists. |

#### D. `medical` — resolved medical compatibility states

| `key` | `value` shape | Example |
|-------|---------------|---------|
| `suppressant_formulation` | `{ "subject": "<participant_id>", "status": "compatible" \| "incompatible" }` | `Kizzie: suppressant formulation incompatible` |

#### E. `communication_state` — calls, messages, institutional contact

| `key` | `value` shape | Example |
|-------|---------------|---------|
| `housing_call` | `{ "status": "not_started" \| "in_progress" \| "completed" \| "failed" }` | `Housing call: completed` |
| `external_message` | `{ "channel": string_enum, "status": "sent" \| "received" \| "pending" }` | **MVP:** use only if continuity exposes it. |

#### F. `access` — resolved location permission states

| `key` | `value` shape | Example |
|-------|---------------|---------|
| `location_entry` | `{ "subject": "<participant_id>", "location": "<bounded_location_id>", "status": "allowed" \| "denied" }` | `Kizzie: clinic room entry denied` |

#### G. `transaction` — transactional scene commitments (GitHub #127)

Authoritative state lives in **`ContinuityManager.resolved_outcomes`** for aspect **`transaction.scene_commitment`**. **Semantic slot identity** is `kind` + `subject_scope` (see `resolved_outcome_registry`); `thread_instance_id` and lineage sit in the outcome **`value`**. Phases: `initiated` (schema-valid; **MVP** promotion from structured moves is **deferred** until deterministic signals exist), `committed`, `awaiting_fulfillment`, `fulfilled`, `failed`, `voided` (revocation path).

| `key` | `value` (projection) | Example `value_summary` |
|-------|----------------------|------------------------|
| `scene_commitment` | `kind`, `subject_scope`, `phase`, optional `label`, `thread_instance_id`, `source_event_id`, `prior_thread_id` | `food order (cast shared): awaiting fulfillment` |

**Structured input:** `move["scene_state_updates"]["transactional_commitment"]` (object or list of objects) with at least `kind`, `subject_scope`, `phase` (see allowlists in `resolved_outcome_registry`).

**MVP scope note:** Initial implementation may **ship with a subset** of keys (e.g. `sleeping_surface`, `omega_suppressants`, `phone`, `housing_call`) and **no-op** for the rest until extraction catches up. The current registry-backed resolved outcome seam covers `assignment:sleeping_surface`, `communication_state:housing_call`, `medical:suppressant_formulation`, `access:location_entry`, and **`transaction:scene_commitment`**; do not treat it as a general second state system.

**Narrow runtime enforcement (`sleeping_surface` only):** After promotion and projection, **`response_validation_binding_sleeping_surface`** may **reject** moves that **deny** or **incorrectly reassign** the settled sleeping surface (deterministic; Host `validate_move` + DSH character-phase retry). This is **not** a general contradiction engine for all facts. See `docs/architecture.md` (Scene Grounding — binding contradiction enforcement).

---

## 4. Promotion Rules (creation / update)

### 4.1 Allowed inputs

1. **Structured continuity outputs** after `ContinuityManager` (or equivalent) processes a turn:
   - `PublicEvent` / event summaries with **typed** `event_type` or tags (existing or **new narrow types** — extraction improvement track). Event **`summary`** strings for non-public speech are **audibility-safe** (no verbatim private **`dialogue`** in the global summary text); consumers that need word-level private content must use per-recipient prompt state, not shared event text alone.
   - **Issue** lifecycle transitions (e.g. resolved + linked template → promote “call completed”).
   - **Resolved outcomes** compiled inside continuity from structured move fields + issue/consequence signals. **Current coverage:** `assignment:sleeping_surface`, `communication_state:housing_call`, `medical:suppressant_formulation`, `access:location_entry`, and `transaction:scene_commitment` (transactional scene commitments, GitHub #127).
2. **`DetectedConsequence` + `ConsequenceCategory`** from `continuity_consequence_classifier` (deterministic):
   - e.g. `DECISION_MADE`, `AGREEMENT`, `COMMITMENT` **when** paired with **rule rows** that map (category + optional template_id + optional tag) → `SceneFact` patch.
3. **Explicit system signals** (optional, rare):
   - Scene template **initial_facts** seed (deterministic defaults at scene start).
   - **No** user free-text → fact in v1.

### 4.2 Explicitly NOT allowed

- Mining raw `chat_history` or Narrator prose for facts.
- LLM-extracted “memory” into this structure.
- Character JSON or Director JSON as authority (they may **trigger** continuity, which then promotes).

### 4.3 Promotion algorithm (conceptual)

After each successful continuity update:

1. `delta = collect_structured_signals(continuity_delta)` — only new/changed structured fields.
2. For each **rule** in `PROMOTION_RULES` (ordered list):
   - If **preconditions** match `delta`, emit `SceneFact` candidate.
3. **Merge** candidates into `SceneGroundingState`:
   - Same `(category, key)` → **supersede** (new fact, link `supersedes`, drop old from active list).
4. **Apply cap** → sort by `(priority desc, recency desc)`, keep top `MAX_SCENE_FACTS`.
5. **Never** write back to continuity from this step.

---

## 5. Invalidation / supersession

### 5.1 Global rule

**Continuity wins.** If a new continuity-derived signal **explicitly contradicts** an active fact under the same `(category, key)`:

- **Replace** the fact via promotion (new `SceneFact`, `supersedes` old).
- If continuity **removes** the underlying event/issue and rules define **revocation** for that key → **remove** fact (deterministic revocation table).

### 5.2 By category (MVP)

| Category | Overwrite | Invalidate / remove |
|----------|-----------|---------------------|
| `assignment` | New promotion with same `key` | Revocation rule: `EXIT` + `assignee` left scene **and** rule marks assignment void; or explicit `AGREEMENT`/`DECISION_MADE` superseding prior surface. |
| `object_state` | New `status` on same `key` | `object_state` key removed if continuity marks object destroyed/removed and revocation rule fires. |
| `medical_status` | New formulation/injury state | Injury `resolved` promotion; or issue resolution hook clears `injury` for subject. |
| `communication_state` | New `status` | `completed`/`failed` not removed until scene end unless superseded by new call. |

### 5.3 Scene scope

- **On `scene_status` → closed** or new scene start: **clear** `scene_grounding` for that scene (or entire structure reset).
- **No cross-scene** carryover in MVP.

### 5.4 Contradiction without promotion rule

If continuity textually changes but **no structured signal** updates: **fact may stale**. Mitigation is **extraction improvements** (track 2), not LLM patching of facts.

---

## 6. Storage + lifecycle

| Concern | Decision |
|---------|----------|
| **Where** | Extend **team / scene state** persisted in session JSON (alongside `team_state`, continuity snapshot). Exact key: `scene_grounding` parallel to scene-scoped data. |
| **Create** | Scene start: empty or template seed. First promotion after turn 0. |
| **Update** | Only after continuity commit on the Host `commit_move` path (or a single helper called from there). |
| **Remove** | Revocation rules + scene end + cap prune. |
| **Read** | Prompt builders read snapshot; **immutable** for the duration of one LLM call. |

**Pruning:** When over cap, drop lowest `priority`, then oldest `promoted_at` among ties.

---

## 7. Prompt integration

### 7.1 Format

- **One block** per prompt class, e.g.:

```text
SETTLED SCENE FACTS (authoritative for this scene; do not contradict or re-open without new in-fiction development):
- [assignment] Sleeping: Kizzie — top of Marlene's bunk.
- [medical_status] Suppressants: Kizzie — wrong formulation for physiology.
```

- **Concise**, **bullet list**, **category tag** in brackets.
- **Do not** duplicate full continuity dumps — facts are **subset**.

### 7.2 Where injected

| Consumer | Placement | Rationale |
|----------|-----------|-----------|
| **Director** | Short prefix or structured section **after** issues / scene phase, **before** dialogue history chunk. | Turn choice should respect logistics. |
| **Character** | Same block in system or “scene context” section. | Grounding > raw repetition of chat. |
| **Narrator** | Optional **one-line** subset (injury/object only) if Narrator invents environment; **MVP:** same block as character if used. |

**Non-redundancy:** If another prompt section already prints the **same** deterministic line (unlikely), skip duplicate — single canonical builder function.

### 7.3 Character BINDING CONSTRAINTS + evidence discipline (downstream)

**BINDING CONSTRAINTS (HIGH PRIORITY)** — **character prompts only:** a **filtered** bullet list of promoted facts whose `(category, key)` pairs are allowlisted as binding (e.g. sleeping surface assignment, location entry). Built from the **same** `SceneGroundingState` as SETTLED SCENE FACTS via `format_character_binding_constraints_section` in `scene_grounding.py` (see `_BINDING_FACT_KEYS` / preamble there). Host `continuity_context_projector.py` supplies that section into character context; `prompt_builders.build_character_turn_prompt` inserts it **after** sections 1–7 (voice, evidence ladder, canon) and **before** the static **EVIDENCE & AUTHORITY DISCIPLINE** block and **OUTPUT RULES**. Purpose: high-salience “do not contradict these settled facts” without duplicating the full Director grounding block.

**EVIDENCE & AUTHORITY DISCIPLINE** — **not** part of scene grounding; a **fixed** instruction paragraph in `prompt_builders.py` placed **after** binding constraints and **before** **OUTPUT RULES**. It targets a distinct failure mode (unsupported specifics in authoritative / clinical / “noted” voice). See `RP_SETUP_TODO.md` Phase 0 section **H**.

---

## 8. Interaction with existing systems

| System | Relationship |
|--------|----------------|
| **Continuity** | **Upstream authority.** Grounding reads continuity outputs; never writes. |
| **Progression advisory** | **Orthogonal.** Progression suggests **novelty / state change**; grounding says **what is already settled**. Both can appear in Director prompt; **no shared state**. |
| **Anti-regression** | **Orthogonal.** No change in MVP. |
| **Issue tracking** | Issues remain **authoritative** for open pressure. Facts may **mirror** resolved outcomes (e.g. call done) when promotion rules tie issue resolution → `communication_state`. |
| **CharacterState** | **No writes.** Characters may still **react** to facts in prose; facts do not store personality. |

**No duplicate responsibility:** Continuity stores **full** narrative state; grounding stores **prompt-optimized allowlisted projection** only.

---

## 9. Risks flagged and mitigations

| Risk | Mitigation |
|------|------------|
| Second authority | **Single writer path:** only promotion from continuity deltas; PRD **continuity wins**. |
| Stale facts | Revocation rows + extraction improvements; cap keeps harm bounded. |
| Retrieval conflict (future RAG) | PRD: retrieved text is **non-authoritative**; **SETTLED SCENE FACTS** block wins for allowlisted keys. |

---

## 10. Implementation plan (no code in this doc)

### Phase 1 — Schema + state

1. Add `SceneGroundingState` / `SceneFact` dataclasses (or TypedDict) + JSON (de)serialization.
2. Add `scene_grounding` to session save/load path next to scene team state.
3. Clear on scene end / new scene.

### Phase 2 — Promotion (minimal rules)

4. Implement `scene_grounding.py`: `rebuild_scene_grounding(continuity_snapshot, template_id, previous_grounding) -> SceneGroundingState` **or** incremental `apply_turn_delta(...)`.
5. Seed **3–5 promotion rules** with unit tests (e.g. mock continuity event → `sleeping_surface`, `omega_suppressants`).

### Phase 3 — Prompt injection

6. `prompt_builders.py` (or helper): `format_scene_grounding_block(facts) -> str`.
7. Wire Director + character prompts; audit log optional line “grounding_lines: N”.

### Phase 4 — Invalidation

8. Implement supersede + revocation for implemented keys; test contradiction paths.

### Phase 5 — Extraction improvements (initial)

9. Add **narrow** continuity event types or tags for: irreversible object change, completed decision, communication terminal state — **deterministic** only.
10. Map new signals to existing fact keys.

### Testing plan

- **Unit:** promotion from fixture continuity deltas; invalidation; cap prune; formatting.
- **Replay:** session JSON fixtures — assert prompts contain expected bullets; **regression** names: bunk not reassigned, phone broken persists, suppressants formulation not reset **when** continuity supplies the signals (once extraction exists).

---

## 11. Non-goals (MVP)

- Full memory / cross-session graph.
- LLM classification of facts.
- Redesign of `IssueState` or continuity schema beyond **additive** structured hooks.
- Anti-regression expansion.
- Personality or character card edits.
