# Cross-Session Memory (Current Behavior)

## Overview

Holy Grail RP **aggregates memory across saved sessions** when you start a **new scene** with a cast that overlaps prior sessions (same user + matching character names). Aggregation reads the **session index** and saved session metadata under **`data/sessions/`** (or `HG_SESSIONS_DIR`) — it is **file/index-based**, not embedding search.

Prior runs can influence **new** runs: selected strings are merged into in-memory character state and appear in character prompts (e.g. **CROSS-SESSION USER MEMORY**, **PERSISTENT WORLD FACTS**, **USER PREFERENCES**) and in **PRIVATE STATE** text built from user relationship history.

This behavior is intentional **early-stage progression**: it reuses lightweight buckets from past saves, not a full memory product.

**Ownership:** Domain module `session_manager.get_cross_session_memories` (`v2/domain/modules/session_manager.py`) with policy in `cross_session_memory_policy.py`. Domain Host loads/applies buckets during session setup and prompt assembly; DSH does not implement aggregation logic.

## Toggle

| Variable | Meaning |
|----------|---------|
| `RP_CROSS_SESSION_MEMORY` | `1` (default): load aggregated cross-session buckets and **apply** them into character state for this run. |
| | `0`: **card-only mode** for this layer—aggregation returns empty buckets and **apply** does not inject cross-session data. |
| `RP_CROSS_SESSION_PROMOTE_FILTER` | `1` (default): apply minimal promotion heuristic at aggregation time. `0`: keep all eligible strings (no promotion filter). |

- **Scope:** Affects **cross-session aggregation and injection** only (the path that runs when starting a new scene or when loading a session via the same aggregation flow).
- **Not affected:** **Session resume** still restores the full saved snapshot (`character_states`, `chat_history`, `continuity_state`, etc.) from that session file. The toggle does **not** turn resume off or strip resumed state.

## Injection Report

The primary way to see **what cross-session contributed** on a given run is **`cross_session_injection_report`**:

- **Where it lives (UI):** presentation client session state when running through the Node/UI stack (historically Streamlit `st.session_state`; same report shape via Host/session metadata where exposed).
- **What it contains (high level):**
  - **`cross_session_memory_enabled`**: whether aggregation/injection was active for this run.
  - **`persistence_scope`**: always **`cross_session`** for this report (so it is not confused with resume).
  - **`exclude_session_id`**: session excluded from aggregation when resuming that same session.
  - **`indexed_session_count`**: how many sessions the index knows about (informational).
  - **`load_items`**: entries **considered at aggregation time**, with **`promoted: true`** if kept for returned buckets.
  - **`load_items_filtered`**: entries with **`promoted: false`** — dropped by the promotion heuristic.
  - **`apply_items`**: what **apply** actually merged into character state.
- **Per item fields (when present):** `memory_type`, `injection_reason`, `source_session_id`, `target_character`, `preview`, `prompt_destination`, `persistence_scope`, `stage` (`load` | `apply`).

**Logging:** After apply, a log line with prefix **`[cross_session]`** may emit a compact JSON summary. Configure logging at `INFO` for the session manager logger if you rely on logs.

**Audits:** When audit logging includes scene kwargs, a compact copy of the report may appear under **`cross_session_injection_report`** in that payload.

**Debugging:** Inspect the injection report after scene start or session load. This is the **primary debugging tool** for cross-session-driven behavior.

## Persistence Layers

Two mechanisms coexist; the toggle applies to **only one** of them.

1. **Cross-session aggregation**  
   - Reads other (indexed) sessions, merges bounded text into state for the current run.  
   - **Controlled by** `RP_CROSS_SESSION_MEMORY`.

2. **Session resume**  
   - Loads one session file and restores saved **full** state.  
   - **Not controlled by** `RP_CROSS_SESSION_MEMORY`.

Do not assume “card-only” (`RP_CROSS_SESSION_MEMORY=0`) means a blank slate if you **resumed** a session file—resume is separate.

## Current Limitations

- **Promotion/filtering** at aggregation is **minimal and heuristic**. Edge cases are easy to misclassify.
- **One-off narrative details** can still enter saved relationship history from normal turn recording and later reappear via aggregation if they pass filters—there is **no importance or canon layer** here.
- **No validation** of whether injected text is still true, scene-appropriate, or desired.
- **Injected strings are treated similarly** at prompt assembly time—no weighting or adjudication step.
- **Session summaries** in the aggregation pipeline may appear in the report under destinations like **`session_summaries_aggregate`**; verify report + prompts together if behavior surprises you.

Frame expectations accordingly: this is an **early-stage progression hook**, not a finalized memory model.

## Related

- [docs/rp-data-layout.md](./rp-data-layout.md) — session paths and index
- [GLOSSARY.md](../GLOSSARY.md) — cross-session memory term
- Tests: `v2/domain/tests/test_cross_session_stabilization.py`
