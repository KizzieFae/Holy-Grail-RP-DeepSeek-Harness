"""Deterministic binding enforcement for ``assignment:sleeping_surface`` (issue #30 slice).

Uses structured ``scene_grounding`` facts and parsed move ``dialogue`` + ``action`` only.
"""

from __future__ import annotations

import re
from typing import Any

from resolved_outcome_registry import get_valid_sleeping_surface_ids
from scene_grounding import is_behaviorally_binding_scene_fact, rebuild_scene_grounding_from_continuity

BINDING_SLEEPING_SURFACE_PREFIX = "[BINDING_SLEEPING_SURFACE]"

BINDING_RETRY_BLOCK_TEMPLATE = (
    "[BINDING_RETRY] Your previous action/dialogue contradicted your established "
    "sleeping-surface assignment (assigned surface: {surface_id}). You may refuse to sleep "
    "there or protest, but you must not deny that this assignment exists or claim a "
    "different official assignment. Revise the move."
)

# Normalized substring checks (dialogue + action, lowercased, punctuation flattened).
_DENIAL_OF_ASSIGNMENT_SUBSTRINGS: tuple[str, ...] = (
    "i was never assigned a bunk",
    "was never assigned a bunk",
    "nobody gave me a bed",
    "nobody gave me a sleeping spot",
    "i don't have a sleeping assignment here",
    "there's no bunk with my name on it—they skipped me",
    "there's no bunk with my name on it-they skipped me",
    "there's no bunk with my name on it",
)

# Declarative frames for incorrect official assignment (substring after normalization).
_DECLARATIVE_ASSIGNMENT_FRAMES: tuple[str, ...] = (
    "my assignment is",
    "i'm assigned to",
    "officially on the",
    "my bed is",
)


def format_binding_sleeping_surface_retry_note(surface_id: str) -> str:
    sid = str(surface_id or "").strip()
    if len(sid) > 64:
        sid = sid[:64] + "…"
    out = BINDING_RETRY_BLOCK_TEMPLATE.format(surface_id=sid)
    if len(out) > 400:
        return out[:397] + "…"
    return out


def _normalize_binding_move_text(*, dialogue: str, action: str) -> str:
    raw = f"{dialogue} {action}"
    raw = raw.replace("“", '"').replace("”", '"').replace("’", "'")
    raw = raw.replace("—", "-").replace("–", "-")
    raw = raw.lower()
    raw = re.sub(r"\s+", " ", raw.strip())
    return raw


def _normalize_actor_key(name: str) -> str:
    return re.sub(r"[_\s]+", " ", str(name or "").strip().lower())


def _active_sleeping_surface_binding_for_actor(
    scene_grounding: dict[str, Any] | None,
    speaker: str,
) -> tuple[str, str] | None:
    """Return (assignee_id, surface_id) if a binding assignment fact applies to speaker."""
    if not isinstance(scene_grounding, dict):
        return None
    facts = scene_grounding.get("facts")
    if not isinstance(facts, list):
        return None
    speaker_n = _normalize_actor_key(speaker)
    candidates: list[tuple[int, str, str]] = []
    for item in facts:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category", "") or "").strip()
        key = str(item.get("key", "") or "").strip()
        if not is_behaviorally_binding_scene_fact(cat, key):
            continue
        if cat != "assignment" or key != "sleeping_surface":
            continue
        val = item.get("value")
        if not isinstance(val, dict):
            continue
        assignee = str(val.get("assignee", "") or val.get("assignee_id", "") or "").strip()
        surface = str(val.get("surface", "") or val.get("surface_id", "") or "").strip()
        if not assignee or not surface:
            continue
        if _normalize_actor_key(assignee) != speaker_n:
            continue
        priority = int(item.get("priority", 0) or 0)
        candidates.append((priority, assignee, surface))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, assignee, surface = candidates[0]
    return (assignee, surface)


def _find_substring(haystack: str, needle: str) -> int:
    return haystack.find(needle)


def _is_negated_before(haystack: str, idx: int) -> bool:
    if idx < 0:
        return False
    start = max(0, idx - 22)
    fragment = haystack[start:idx]
    return any(
        p in fragment
        for p in (
            "not ",
            "n't ",
            "never ",
            "without ",
            "except ",
        )
    )


def _surface_tokens_for_id(surface_id: str) -> list[str]:
    s = str(surface_id or "").strip().lower()
    if not s:
        return []
    out = [s]
    if "_" in s:
        out.append(s.replace("_", " "))
    return list(dict.fromkeys(out))


def _regex_for_surface_token(tok: str) -> str:
    parts = tok.split()
    if len(parts) > 1:
        core = r"\s+".join(re.escape(p) for p in parts)
    else:
        core = re.escape(tok)
    return r"(?<!\w)" + core + r"(?!\w)"


def _first_match_start(text: str, surface_id: str) -> int | None:
    for tok in _surface_tokens_for_id(surface_id):
        if not tok:
            continue
        m = re.search(_regex_for_surface_token(tok), text)
        if m:
            return int(m.start())
    return None


def _incorrect_reassignment_assertion(
    text: str,
    *,
    assigned_surface_id: str,
    scene_state: dict[str, Any] | None,
) -> bool:
    if not any(frame in text for frame in _DECLARATIVE_ASSIGNMENT_FRAMES):
        return False
    valid = get_valid_sleeping_surface_ids(scene_state)
    assigned = str(assigned_surface_id or "").strip().lower()
    for other in valid:
        o = str(other or "").strip().lower()
        if not o or o == assigned:
            continue
        idx = _first_match_start(text, o)
        if idx is None:
            continue
        if _is_negated_before(text, idx):
            continue
        return True
    return False


def binding_sleeping_surface_id_for_actor(
    scene_grounding: dict[str, Any] | None,
    speaker: str,
    *,
    continuity_manager: Any | None = None,
) -> str:
    """Return assigned surface_id for speaker, or '' if none."""
    sg = scene_grounding
    if sg is None and continuity_manager is not None:
        try:
            sg = rebuild_scene_grounding_from_continuity(continuity_manager)
        except Exception:
            sg = None
    b = _active_sleeping_surface_binding_for_actor(sg, speaker)
    return b[1] if b else ""


def validate_binding_sleeping_surface_contradiction(
    *,
    move: dict[str, Any] | None,
    speaker: str,
    scene_grounding: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
    continuity_manager: Any | None,
) -> tuple[bool, str]:
    """Return (True, '') if OK; (False, reason) if binding contradiction."""
    sg = scene_grounding
    if sg is None and continuity_manager is not None:
        try:
            sg = rebuild_scene_grounding_from_continuity(continuity_manager)
        except Exception:
            sg = None

    binding = _active_sleeping_surface_binding_for_actor(sg, speaker)
    if binding is None:
        return True, ""

    _assignee, surface_id = binding
    dialogue = str((move or {}).get("dialogue", "") or "")
    action = str((move or {}).get("action", "") or "")
    text = _normalize_binding_move_text(dialogue=dialogue, action=action)
    if not text.strip():
        return True, ""

    ss = scene_state if isinstance(scene_state, dict) else {}

    for phrase in _DENIAL_OF_ASSIGNMENT_SUBSTRINGS:
        if phrase in text:
            return False, f"{BINDING_SLEEPING_SURFACE_PREFIX} denial_of_assignment_existence"

    if _incorrect_reassignment_assertion(
        text,
        assigned_surface_id=surface_id,
        scene_state=ss,
    ):
        return False, f"{BINDING_SLEEPING_SURFACE_PREFIX} incorrect_reassignment_assertion"

    return True, ""
