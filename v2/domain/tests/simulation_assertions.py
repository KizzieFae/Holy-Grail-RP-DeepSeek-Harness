"""Lightweight assertions for headless simulation runs (st_module + result; audit optional).

Core checks use runtime state only. Prompt substring checks require audit JSON when enabled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# --- st_module / CharacterState ---


def _state_manager(st_module: Any) -> Any:
    return st_module.session_state.get("character_state_manager")


def resolve_memory_lookup_key(st_module: Any, display_or_agent_key: str) -> str | None:
    """Map a card display name (or raw agent key) to the key used in ``CharacterStateManager``.

    Headless sessions register states under ``AssistantAgent.name``, which defaults to
    ``make_agent_identifier(card['name'])`` (e.g. ``Hannah Lovelace`` → ``Hannah_Lovelace``).
    Continuity ``present_characters`` uses card display names, so tests must resolve.
    """
    from character_loader import make_agent_identifier

    label = str(display_or_agent_key or "").strip()
    if not label:
        return None
    sm = _state_manager(st_module)
    if sm is None:
        return None
    if sm.get_state(label):
        return label
    derived = make_agent_identifier(label)
    if derived != label and sm.get_state(derived):
        return derived
    for key, st in getattr(sm, "_states", {}).items():
        if getattr(st, "name", None) == label:
            return str(key)
    return None


def session_agent_names(st_module: Any) -> list[str]:
    """``agent.name`` values for loaded character bots (canonical memory / turn-runner keys)."""
    out: list[str] = []
    for a in st_module.session_state.get("characters") or []:
        n = str(getattr(a, "name", "") or "").strip()
        if n:
            out.append(n)
    return out


def _character_state(st_module: Any, character_name: str) -> Any | None:
    sm = _state_manager(st_module)
    if sm is None:
        return None
    key = resolve_memory_lookup_key(st_module, character_name)
    if key is None:
        return None
    return sm.get_state(key)


def memory_combined_text(st_module: Any, character_name: str) -> str:
    """Interpretation + private episodic + self-trace (parity with what prompts may surface)."""
    st = _character_state(st_module, character_name)
    if st is None:
        return ""
    parts: list[str] = []
    parts.extend(str(x) for x in (getattr(st, "character_memory_summary", None) or []))
    parts.extend(str(x) for x in (getattr(st, "private_memories", None) or []))
    parts.extend(str(x) for x in (getattr(st, "recent_observations", None) or []))
    return "\n".join(parts)


def assert_memory_contains(st_module: Any, character_name: str, text: str) -> None:
    blob = memory_combined_text(st_module, character_name)
    assert text in blob, (
        f"Expected {character_name!r} memory to contain {text!r}; got len={len(blob)}"
    )


def assert_memory_not_contains(st_module: Any, character_name: str, text: str) -> None:
    blob = memory_combined_text(st_module, character_name)
    assert text not in blob, (
        f"Expected {character_name!r} memory NOT to contain {text!r}"
    )


def assert_memory_bounded(
    st_module: Any,
    character_name: str,
    *,
    max_summary: int = 12,
    max_private: int = 20,
) -> None:
    st = _character_state(st_module, character_name)
    assert st is not None, f"No CharacterState for {character_name!r}"
    assert len(st.character_memory_summary) <= max_summary
    assert len(st.private_memories) <= max_private


def snapshot_memory_line_counts(st_module: Any) -> dict[str, tuple[int, int]]:
    """Per character: (len(character_memory_summary), len(private_memories))."""
    sm = _state_manager(st_module)
    if sm is None:
        return {}
    out: dict[str, tuple[int, int]] = {}
    for name, st in getattr(sm, "_states", {}).items():
        out[str(name)] = (
            len(getattr(st, "character_memory_summary", []) or []),
            len(getattr(st, "private_memories", []) or []),
        )
    return out


def assert_no_episodic_growth(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
    character_name: str,
    *,
    st_module: Any | None = None,
) -> None:
    """Both interpretation and private episodic list lengths must not increase.

    ``character_name`` may be a display name if ``st_module`` is passed (resolved to manager key).
    """
    key = character_name
    if st_module is not None:
        resolved = resolve_memory_lookup_key(st_module, character_name)
        if resolved is not None:
            key = resolved
    b = before.get(key)
    a = after.get(key)
    assert b is not None and a is not None, (
        f"No snapshot for {character_name!r} (key {key!r}); keys={sorted(before.keys())}"
    )
    assert a[0] <= b[0] and a[1] <= b[1], (
        f"Episodic growth for {character_name!r}: before {b} after {a}"
    )


# --- HeadlessSimulationResult / session lists ---


def selector_text(result_or_st: Any) -> str:
    if hasattr(result_or_st, "selector_decisions"):
        lines = result_or_st.selector_decisions or []
    else:
        lines = result_or_st.session_state.get("selector_decisions") or []
    return "\n".join(str(x) for x in lines)


def assert_selector_mentions(result_or_st: Any, substring: str) -> None:
    text = selector_text(result_or_st)
    assert substring in text, f"Expected selector_decisions to mention {substring!r}"


def rejected_entries(st_module: Any) -> list[dict[str, Any]]:
    raw = st_module.session_state.get("rejected_messages") or []
    return [x for x in raw if isinstance(x, dict)]


def assert_chat_assistant_turns_at_least(st_module: Any, minimum: int) -> None:
    hist = st_module.session_state.get("chat_history") or []
    n = sum(1 for m in hist if m.get("role") == "assistant")
    assert n >= minimum, f"Expected at least {minimum} assistant chat turns, got {n}"


def continuity_scene_state(st_module: Any) -> dict[str, Any]:
    from continuity_manager import ContinuityManager
    import app_state_helpers as state_helpers

    cm = state_helpers.get_continuity_manager(
        st_module=st_module, continuity_manager_cls=ContinuityManager
    )
    if cm is None or cm.scene_state is None:
        return {}
    return cm.scene_state.to_dict() if hasattr(cm.scene_state, "to_dict") else {}


def assert_selected_actor_not_offstage(st_module: Any) -> None:
    """Heuristic: parse last 'Director selected X' from selector_decisions; X not in offstage."""
    lines = list(st_module.session_state.get("selector_decisions") or [])
    last_pick = ""
    for line in reversed(lines):
        s = str(line)
        if "Director selected" in s or "selected" in s.lower():
            # e.g. "Director selected Celina: ..."
            parts = s.split()
            for i, p in enumerate(parts):
                if p.lower() == "selected" and i + 1 < len(parts):
                    last_pick = parts[i + 1].rstrip(":")
                    break
            if last_pick:
                break
    if not last_pick:
        return
    scene = continuity_scene_state(st_module)
    off = [str(x) for x in (scene.get("offstage_characters") or []) if str(x).strip()]
    assert last_pick not in off, (
        f"Selected actor {last_pick!r} is listed offstage {off!r}"
    )


# --- Audit (optional; non-gating for core suite) ---


def _audit_json_files(session_dir: Path) -> list[Path]:
    if not session_dir.is_dir():
        return []
    # Audits nest files under session_<n>/round_<nnn>/
    return sorted(session_dir.rglob("*_full.json"))


def character_prompt_text_from_audit(session_dir: Path, character_name: str) -> str:
    """Concatenate input message contents for character bot entries (best-effort)."""
    from character_loader import make_agent_identifier

    label = str(character_name or "").strip()
    aliases = {label, make_agent_identifier(label)}
    chunks: list[str] = []
    for path in _audit_json_files(session_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(data.get("bot_name", "")).strip() not in aliases:
            continue
        if str(data.get("bot_type", "")).strip().lower() != "character":
            continue
        for msg in data.get("input_messages") or []:
            if isinstance(msg, dict):
                chunks.append(str(msg.get("content", "") or ""))
    return "\n".join(chunks)


def assert_prompt_contains_if_audit(
    audit_session_dir: Path | None,
    character_name: str,
    text: str,
) -> None:
    if audit_session_dir is None or not audit_session_dir.is_dir():
        return
    blob = character_prompt_text_from_audit(audit_session_dir, character_name)
    assert text in blob, (
        f"Audit prompt for {character_name!r} expected {text!r} (audit-assisted check)"
    )


def assert_prompt_section_if_audit(
    audit_session_dir: Path | None,
    character_name: str,
    heading: str,
) -> None:
    assert_prompt_contains_if_audit(audit_session_dir, character_name, heading)
