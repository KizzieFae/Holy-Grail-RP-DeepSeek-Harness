# State-detection hardening backlog (post–progression v1)

**Purpose:** Capture high-impact follow-ups discovered during progression validation. **Backlog only** — no implementation commitment.

**Scope:** presence/exit, issue resolution, settled-fact–adjacent detection. Excludes progression tuning and framework redesign.

---

## Priority 1 — Presence / exit

| Item | Notes | Likely owner |
|------|--------|--------------|
| **Negated departure phrases** | v1 fixed overlap of explicit departure regex with negated “walking out” spans. **Backlog:** catalog similar patterns (“not leaving”, “won’t walk away”, etc.) for regression tests and optional matcher hardening. | `scene_exit_detection.py`, `tests/test_scene_exit_detection.py` |

---

## Priority 2 — Issue resolution (signal quality)

| Item | Notes | Likely owner |
|------|--------|--------------|
| **Empty dialogue in summarized beats** | Long-session audits show `recent_delta` / event summaries with `said: ""` when exact words are omitted (e.g. private speech). Feeds Director and semantic prompts; may inflate noise or confuse “who must respond” heuristics. | Continuity / public-event summarization (trace from `recent_structured_moves` → `recent_delta` / `recent_public_events`) |

---

## Priority 3 — Settled-fact / turn-focus detection

| Item | Notes | Likely owner |
|------|--------|--------------|
| **Addressee vs next-speaker** | Valid run (session 097, turn 10): Director chose **Ayame**; semantic turn-selection flagged **Celina** as addressee and `supports_selected_actor: false`. Pipeline did **not** override the Director. **Backlog:** decide whether this is acceptable advisory-only behavior or whether prompts/schemas should align “who is addressed” with “who acts next” to reduce false disagreement. | `semantic_validation.py` (turn-selection assessment), `app_turn_director.py` |

---

## References

- Progression v1 checkpoint: [progression layer validation status v1.md](./progression%20layer%20validation%20status%20v1.md)
- Long-session treatment / solo-cast endgame notes: [progression layer testing todo.md](./progression%20layer%20testing%20todo.md) (Phase 2b)
