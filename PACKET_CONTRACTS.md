# Packet contracts (intent)

These are **architectural contracts** for the **packaging layer** described in [Holy Grail PRD.md](./Holy%20Grail%20PRD.md) §§3.2, 4.1–4.3. They are the **future integration seam** between knowledge/retrieval and the **RP runtime** (`autogen_rp/python/rp_app`). They are **not** fully implemented as dedicated types yet; existing code uses cards, continuity structures, and prompt builders.

For runtime behavior today, see `autogen_rp/python/rp_app/ARCHITECTURE.md` and `prompt_builders.py`.

---

## Design rules

1. **Stable vs dynamic** — Identity and long-lived voice/world anchors change slowly; per-turn overlays and retrieved snippets change every turn.
2. **Authoritative vs retrieved** — Scene truth, issues, presence, and knowledge boundaries come from **runtime continuity** (authoritative). Retrieval supplies **candidates**; packaging **selects and bounds** them. Neither vectors nor raw cards are “truth” for state.
3. **Runtime receives packets, not raw stores** — AutoGen agents should consume **assembled** packets, not ad-hoc DB/graph calls mid-turn.

---

## RuntimeCharacterPacket

**Intent:** Everything a **single character agent** needs for **one** generation step, already **merged and budgeted**.

| Grouping | Stability | Role |
|----------|-----------|------|
| Identity core | Stable | Name, persistent traits, canon anchors, core goals — aligned with card fields that must not be summarized away |
| Voice / style | Mostly stable | Profiles and fingerprints guiding diction; may include **examples** from retrieval later |
| Scene-facing slice | Dynamic (authoritative) | Subset of shared scene truth relevant to this actor: location, phase, who is present, active pressures/issues |
| Relationship overlays | Mixed | Structured relationship state toward others + user; trends as summaries |
| Retrieved context | Dynamic (non-authoritative) | `RetrievedContextBundle` scoped to this character (see below) |
| Knowledge constraints | Authoritative | What this character may/must not treat as known (boundaries from continuity) |

**Not in scope here:** raw JSON card path on disk, full chat transcript, or unbounded tool logs.

---

## RuntimeScenePacket

**Intent:** **Shared** context for Director, Narrator, and cross-character prompts — the “table” everyone agrees on for this beat.

| Grouping | Stability | Role |
|----------|-----------|------|
| Participants | Dynamic | Who is in scene; control mode (player vs bot) where relevant |
| Environment & phase | Dynamic | Setting, tone, scene phase / beat |
| Active issues / pressures | Dynamic | Issue list and metadata the Director and validators use |
| Recent structured history | Dynamic | Bounded windows of events/moves/dialogue **as chosen by packaging** from authoritative continuity |
| Template / role context | Setup-time | Template id, premise, role assignments, presence constraints (when using templates) |
| **Settled scene facts** (Scene Grounding MVP) | Dynamic (derived, read-only) | Capped, allowlisted **facts/locks** projected from continuity for prompt coherence — not a second authority ([PRD](./Holy%20Grail%20PRD.md) §5.8, [spec](./autogen_rp/docs/scene-grounding-layer.md)) |

This packet **does not** replace the continuity manager’s full internal state; it is the **projection** used for prompts and decisions.

---

## RetrievedContextBundle

**Intent:** **Per-turn**, **optional**, **bounded** context — **inputs to packaging**, not to validation truth. **Phase 2 (current):** snippets come from a **deterministic authored JSON index** only (`retrieved_context_select.py`, env `RP_RETRIEVED_CONTEXT_INDEX`). **Later:** vector/graph/search pipelines may feed the same bundle shape.

**Phase 2 placement:** formatted block is injected **after** scene grounding and **before** `CURRENT SCENE STATE` in `prompt_builders.build_character_turn_prompt`, with explicit **non-authoritative** instructions. Selection runs **only** in `app_turn_prompting.build_character_turn_prompt`.

Typical contents (all subject to token budget and relevance gates):

- Snippets of **past interactions** or summarized moments
- **Relationship** highlights (who to whom)
- **Emotional / behavioral** patterns (lightweight, not a second continuity engine)
- **World knowledge** excerpts (lore), clearly labeled as reference

**Explicit non-responsibilities:**

- Storing canonical “what happened” (that remains events/issues in continuity)
- Deciding **must_remain** or presence (orchestration/validation)
- Replacing Director logic

---

## Evolution path (documentation-only commitment)

1. Map today’s card + continuity + prompt sections → fields above **without behavior change**.
2. Introduce a `packet_builder` (or equivalent) in packaging that produces these structures; runtime reads packets instead of assembling ad hoc.
3. Wire retrieval outputs only into `RetrievedContextBundle`.

Track tasks: `autogen_rp/python/RP_SETUP_TODO.md` (Phase 0.5 packet seam, Phase 2 retrieval).
