# V2 Continuity Context — M11.3 Implementation Report

**Status:** Completed (M11.3 — authoritative scene grounding + canon context projection)  
**Date:** 2026-08-18  
**M11.2 anchor:** `4b920b8`  
**M11 architecture anchor:** `5d1aa26`  
**Implementation HEAD:** (see §21 after commit)

---

## 1. Scope

Project **live authoritative** continuity/scene context into ContextAssembly without persisting a second canon store:

- enhanced `scene_state` (presence/offstage/absent/opening);
- `continuity_canon` from live canon anchors;
- `scene_grounding` from `rebuild_scene_grounding_from_continuity`;
- `active_constraints` (binding grounding facts) for character inference.

**Not in scope:** new KnowledgeService persistence, vectors, episodic retrieval, DSH changes, scope-ID changes, V1 deletion.

---

## 2. Previous scene/canon context architecture

| Path | Class | M11.3 disposition |
|------|-------|-------------------|
| `prepare_context` inline `scene_state` | Authoritative (minimal) | **Refined** via projector |
| `continuity_summary` (round commits) | Authoritative round-local | **Retained** (priority 15) |
| KnowledgeService `learned_world_knowledge` | Suggestive/reference | **Retained** — separate lane |
| M11.1 `scene_reference` | Authored suggestive | **Retained** — distinct from grounding |
| V1 `prompt_builders` canon/grounding blocks | Direct prompt injection | **Superseded on V2 path** |
| V1 `scene_grounding` session bucket copy | Denormalized cache | **Rejected** — live rebuild only |

---

## 3. Authoritative projection architecture

| Module | Role |
|--------|------|
| `v2/domain_api/continuity_context_projector.py` | Stateless projector: live ContinuityManager → bounded contributions |
| `v2/domain_api/kernel.py` | Calls projector in `prepare_context`, `prepare_director_context`, `prepare_narrator_context` |

No persistence layer. Reads `SceneState`, `canon_anchors`, `public_events`/`resolved_outcomes` each prepare call.

---

## 4. SceneState projection

**Changed:** uses actual `present_characters`, `offstage_characters`, `absent_but_relevant`, and `opening_description` from live `SceneState` (not full cast list).

**Retained:** `source_kind=scene_state`, `authority_class=authoritative`, priority 10.

Director variant adds actors-used/eligible metadata.

---

## 5. Canon/grounding projection

| Lane | Source | Role visibility |
|------|--------|-----------------|
| `continuity_canon` | `get_relevant_canon_anchors` (character) / `get_scene_canon_anchors` (director/narrator) | Character-filtered vs scene-wide |
| `scene_grounding` | `rebuild_scene_grounding_from_continuity` | Director: all facts; character: non-binding |
| `active_constraints` | Binding subset of grounding | Character only |

Caps: 6 character canon anchors; 10 scene-wide; grounding capped by V1 `MAX_SCENE_FACTS`.

---

## 6. Authority/precedence behavior

```text
scene_state / continuity_canon / scene_grounding / active_constraints  → authoritative
continuity_summary (round-local)                                       → authoritative
authored / learned / user_profile                                      → suggestive
character_memory                                                       → derived
```

When learned knowledge conflicts with current canon anchor statement, M11.2 suppression applies; authoritative `continuity_canon` carries current truth.

---

## 7. Visibility/privacy behavior

- Character canon: `get_relevant_canon_anchors` — subject match, `world_fact`, relationship with scene participants
- Other characters' `character_trait` anchors not projected to unrelated characters
- `character_private` lane unchanged
- Director receives broader scene canon; does not receive character-private

---

## 8. Provenance and caps

Provenance on every authoritative contribution:

- `projection_kind` (`live_scene_state`, `live_canon_anchors`, `live_scene_grounding`, `live_binding_constraints`)
- `continuity_version`, `hg_scene_id`, `hg_round_id`
- `anchor_ids` / `fact_ids` where applicable
- `authority_note: live_continuity_projection_not_knowledge_store`

---

## 9. ContextAssembly ordering

| Priority | Lane |
|----------|------|
| 10 | `scene_state` |
| 11 | `continuity_canon` |
| 12 | `scene_grounding` |
| 13 | `active_constraints` (character) |
| 15 | `continuity_summary` (if round commits exist) |
| 20 | `character_profile` |
| 21+ | authored / scene_reference / learned / user_profile |
| 25 | `character_private` |
| 26+ | `character_memory` |
| 30 | `inference_instruction` |

---

## 10–14. Proofs (tests)

`v2/tests/test_continuity_context_m11_3.py`:

- Mid-session location mutation reflects immediately
- Scope knowledge store unchanged by scene mutation alone
- Stale learned fact suppressed when canon anchor updated
- Character canon visibility filtered
- Director authoritative lanes with canon
- Restart persistence from domain state
- Real-card coexistence with M11.1/M11.2 lanes
- Projector reads live state (no persisted copy)

---

## 15. Duplication cleanup

- Removed inline duplicate `scene_state` builders from kernel prepare paths
- Scene location no longer implied from full cast when presence lists differ
- Template `scene_reference` remains separate from authoritative grounding

---

## 16. V1 retirement impact

| V1 | V2 replacement |
|----|----------------|
| `format_grounding_*` direct prompt assembly | `continuity_context_projector` → manifest |
| `serialize_canon_anchors_for_prompt` in character/director payloads | `continuity_canon` lane |
| Session `scene_grounding` bucket for V2 inference | Live rebuild from continuity |

V1 code retained until broader retirement authorization.

---

## 17. Behavioral validation

```text
python -m pytest v2/tests/ -q  → 93 passed (+9 M11.3)
cd v2/rp_runtime && npm test   → (see commit validation)
```

---

## 18. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `continuity_context_projector`, authoritative lanes, kernel integration |
| **Reused** | V1 `scene_grounding` rebuild/format helpers, canon anchor selection |
| **Superseded** | Inline kernel scene_state strings; V2 direct prompt canon injection |
| **Deferred** | episodic continuity retrieval, vectors, knowledge tools |
| **Test-only** | Synthetic anchor fixtures |

---

## 19. Challenge/refinement

| Question | Answer |
|----------|--------|
| Second canon store? | **No** — live projection only |
| SceneState duplicated? | **Refined**, not duplicated |
| Canon bounded? | **Yes** — deterministic caps |
| Hidden facts leak? | **No** — character-filtered canon |
| Continuity outranks KnowledgeService? | **Yes** |
| Authored vs grounding distinct? | **Yes** |
| Restart from domain only? | **Yes** |

---

## 20. Architecture verdict

**Validated as designed** — authoritative context projected from live Continuity; KnowledgeService remains reference-only.

---

## 21. Next recommended migration slice

**M12 — V1 orchestration retirement inventory / first bounded cutover** (or **M11.4 episodic continuity retrieval investigation** only if product evidence requires it). Recommend **M12 orchestration retirement scoping** as the next slice based on remaining V1 capability gap. Do not implement without Governance review.
