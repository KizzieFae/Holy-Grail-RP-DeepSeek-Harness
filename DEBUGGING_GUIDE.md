# RP debugging guide

How to **approach problems** in the Holy Grail RP runtime without fixing the wrong layer. Product and layers: [Holy Grail PRD.md](./Holy%20Grail%20PRD.md), [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md). **Where to open code first:** [MODULE_INDEX.md](./MODULE_INDEX.md) (symptom table; modules live under `autogen_rp/python/rp_app/`). **On-disk data:** [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md).

---

## Golden rules

1. **Continuity and orchestration before Director prompts** — If the wrong person speaks or state feels wrong, inspect structured state and orchestration before editing Director instructions (`prompt_builders.py` / `app_turn_director.py`).
2. **Do not use prompts as long-term memory** — Truth for scenes/issues/events lives in **continuity** (`continuity_manager.py`), not in growing hidden transcripts.
3. **Validation is not continuity** — Validators reject or shape outputs; they do not author “what happened.” Fix extractors/updaters in continuity if fiction state is wrong.
4. **`must_remain` is structural presence** — Not “must speak every turn.” Presence bugs: `response_validation_presence.py`, templates, then semantics overrides if needed.

---

## Suggested diagnosis order (runtime)

Aligned with `autogen_rp/docs/architecture.md` RP audit order:

1. **Continuity extraction and state** — Are events, issues, and scene snapshot correct after the turn? (`continuity_manager.py`, `continuity_*_helpers.py`)
2. **Orchestration state** — Spotlight, forced speaker, continuation override (`orchestration_helpers.py`, `st.session_state` keys used in `app_turn_director.py`)
3. **Summaries / retrieval windows** — What the prompt actually sees (`summary_audit_helpers.py`, `prompt_builders.py` only after 1–2 look sane)
4. **Validation boundaries** — Parsing, presence, drift, selection (`response_validation_*.py`)
5. **Director** — Selection policy and prompts when evidence points here
6. **Narrator** — Prose polish; dialogue must stay verbatim (`app_turn_rendering.py`)

---

## By problem type

### Turn selection issues

- **Who speaks next** — `orchestration_helpers.py` (address / continuation / caps), `app_turn_director.py` (Director call and overrides), `response_validation_selection.py`, then `semantic_validation.py` for reconciliation.
- **Director ignores context** — Check what **structured** inputs the prompt receives (`prompt_builders.py`, continuity snapshot helpers), not only the Director system text.

### Character drift (voice, tone, anchors)

- **Post-move checks** — `response_validation_drift.py`
- **Anchor source** — `character_state_model.py`, JSON cards under `python/data/autogen_characters/`
- **Drift false positives** — Tune checks in `response_validation_drift.py`, not Narrator prose prompts first.

### Presence bugs (`must_remain`, exits, absence)

- **Deterministic rules** — `response_validation_presence.py`, `scene_exit_detection.py` (continuity), template constraints in `scene_template.py`
- **Semantic override** — `semantic_validation.py`, `should_override_presence_rejection` path in `turn_runner_turn.py` (only after understanding deterministic path)

### Duplicate dialogue / repeated outputs

- **Detection** — `response_validation_content.py` (`is_duplicate_dialogue`, `is_duplicate_content`)
- **Retry behavior** — `turn_runner_turn.py` (duplicate retry branch)
- **Do not** “fix” with Narrator instructions until duplicate rejection logic is understood.

### Knowledge leaks / wrong “who knows what”

- **Authoritative propagation** — `continuity_knowledge_helpers.py`, `continuity_manager.py`
- **Validation** — Knowledge-related checks live alongside other validators; boundary truth is continuity, not retrieval (future: [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)).

### Persistence / reload issues

- **Save path** — `session_lifecycle_save.py` → `SessionManager.save_session`
- **Load path** — `session_lifecycle_load.py`, `session_manager.py`
- **Startup** — `app_bootstrap.py` (incomplete session recovery)
- **Files** — `python/data/sessions/*.json`, `_session_index.json` — see [rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md)

### Audit output / regression analysis

- **Layout and file meanings** — `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`
- **Workflow** — `autogen_rp/docs/audit-workflows.md`
- **Writers** — `audit_logger*.py`

---

## Layer responsibility (who owns what)

| Layer | Owns |
|-------|------|
| **Ingestion** (future) | Source extraction, graph/vector stores — not live turn loop |
| **Packaging** (future) | Merging packets + retrieved context — not replacing continuity truth |
| **RP runtime (`rp_app`)** | Director, orchestration, agents, Narrator, **continuity**, validation, session/audit I/O |

---

## Related

- [GLOSSARY.md](./GLOSSARY.md)
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — future seam; do not implement retrieval as authoritative state
