# Cross-Session Memory (Current Behavior)

## Overview

The RP app **already aggregates memory across saved sessions** when you start a **new scene** with a cast that overlaps prior sessions (same user + matching character names). Aggregation reads the **session index** and saved session metadata under `python/data/sessions/`—it is **file/index-based**, not embedding search.

Prior runs can therefore influence **new** runs: selected strings are merged into in-memory character state and appear in character prompts (e.g. **CROSS-SESSION USER MEMORY**, **PERSISTENT WORLD FACTS**, **USER PREFERENCES**) and in **PRIVATE STATE** text built from user relationship history.

This behavior is intentional **early-stage progression**: it reuses lightweight buckets from past saves, not a full memory product.

## Toggle

| Variable | Meaning |
|----------|---------|
| `RP_CROSS_SESSION_MEMORY` | `1` (default): load aggregated cross-session buckets and **apply** them into character state for this run. |
| | `0`: **card-only mode** for this layer—aggregation returns empty buckets and **apply** does not inject cross-session data. |

- **Scope:** Affects **cross-session aggregation and injection** only (the path that runs when starting a new scene or when loading a session via the same `load_cross_session_memories` / `apply_cross_session_memories` flow).
- **Not affected:** **Session resume** still restores the full saved snapshot (`character_states`, `chat_history`, `continuity_state`, etc.) from that session file. The toggle does **not** turn resume off or strip resumed state.

## Injection Report

The primary way to see **what cross-session contributed** on a given run is **`cross_session_injection_report`**:

- **Where it lives:** `st.session_state["cross_session_injection_report"]` (Streamlit session state).
- **What it contains (high level):**
  - **`cross_session_memory_enabled`**: whether aggregation/injection was active for this run.
  - **`persistence_scope`**: always **`cross_session`** for this report (so it is not confused with resume).
  - **`exclude_session_id`**: session excluded from aggregation when resuming that same session.
  - **`indexed_session_count`**: how many sessions the index knows about (informational).
  - **`load_items`**: entries **considered at aggregation time** (from the index / memory buckets / relationship excerpts), with **`promoted: true`** if they were kept for the returned buckets.
  - **`load_items_filtered`**: same shape as load items but **`promoted: false`**—dropped by the minimal **promotion** heuristic (e.g. some relationship-history lines without interaction-like wording).
  - **`apply_items`**: what **apply** actually merged into character state (relationship snapshot merge, per-line history merges).
- **Per item fields (when present):** `memory_type`, `injection_reason`, `source_session_id` (set for **load** when the row came from a specific indexed session; **apply** rows do not carry session provenance), `target_character`, `preview`, `prompt_destination`, `persistence_scope`, `stage` (`load` | `apply`).

**Logging:** After apply, a single log line with prefix **`[cross_session]`** emits a compact JSON summary (truncated lists/previews). Your logging configuration must show `INFO` (or equivalent) for that logger if you rely on logs.

**Audits:** When audit logging includes scene kwargs, a compact copy of the report may appear under **`cross_session_injection_report`** in that payload.

**Debugging:** Inspect `st.session_state["cross_session_injection_report"]` after scene start or session load. This is the **primary debugging tool** for cross-session-driven behavior.

## Persistence Layers

Two mechanisms coexist; the toggle applies to **only one** of them.

1. **Cross-session aggregation**  
   - Reads other (indexed) sessions, merges bounded text into state for the current run.  
   - **Controlled by** `RP_CROSS_SESSION_MEMORY`.

2. **Session resume**  
   - Loads one session file and restores saved **full** state (chat, continuity snapshot, character dicts, etc.).  
   - **Not controlled by** `RP_CROSS_SESSION_MEMORY`.

Do not assume “card-only” (`RP_CROSS_SESSION_MEMORY=0`) means a blank slate if you **resumed** a session file—resume is separate.

## Current Limitations

- **Promotion/filtering** at aggregation is **minimal and heuristic** (rough interaction cues vs. “purely descriptive” lines for relationship history). It is easy to misclassify edge cases.
- **One-off narrative details** (e.g. sensory flavor) can still enter saved relationship history from normal turn recording and later reappear via aggregation if they pass filters—there is **no importance or canon layer** here.
- **No validation** of whether injected text is still true, scene-appropriate, or desired.
- **Injected strings are treated similarly** at prompt assembly time—no weighting or adjudication step.
- **Session summaries** in the aggregation pipeline are traced in the report under destinations like **`session_summaries_aggregate`**; they are **not** the same as the strings currently wired into every character prompt block—check the report and prompts together if behavior surprises you.

Frame expectations accordingly: this is an **early-stage progression hook**, not a finalized memory model.
