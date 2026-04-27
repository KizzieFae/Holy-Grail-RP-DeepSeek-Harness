"""Read-only derived views of canonical v2 character moves (GitHub #137, #138).

The validated parse handoff is a single ``dict`` with ``move_schema_version: 2`` and
``beats`` (no root-level v1 ``action``/``dialogue`` persistence). Functions here
compute legacy-shaped strings **on read** for callers that still expect v1 field
semantics, and provide **iteration / shallow-copy** helpers for **per-beat**
perception projections (GitHub #138). They must not mutate the input move dict;
callers that need mutable copies use :func:`copy_move_shallow_with_deep_beats`.
"""

from __future__ import annotations

from typing import Any, Mapping

# --- Read-only string projections (for validation / turn runner text) ---


def move_schema_version(move: Mapping[str, Any] | None) -> int:
    """Return ``move_schema_version`` as int, or ``0`` when absent or invalid."""
    if not isinstance(move, Mapping):
        return 0
    try:
        return int(str(move.get("move_schema_version", 0) or 0) or 0)
    except (TypeError, ValueError):
        return 0


def is_canonical_v2_move(move: Mapping[str, Any] | None) -> bool:
    return move_schema_version(move) == 2


def iter_speech_beats(
    move: Mapping[str, Any] | None,
) -> list[tuple[int, dict[str, Any]]]:
    """Return ``(index, beat)`` pairs for ``type: speech`` beats in order (read-only)."""
    if not isinstance(move, Mapping):
        return []
    beats = move.get("beats")
    if not isinstance(beats, list):
        return []
    out: list[tuple[int, dict[str, Any]]] = []
    for i, b in enumerate(beats):
        if isinstance(b, dict) and b.get("type") == "speech":
            out.append((i, b))
    return out


def copy_move_shallow_with_deep_beats(move: Mapping[str, Any]) -> dict[str, Any]:
    """Shallow copy of ``move`` with a fresh list and copied beat dicts (for safe mutation).

    Does not claim to deep-copy ``motivation`` or other nested objects—only ``beats[]``
    dict elements are copied one level. Read-only helper for derived projections.
    """
    base: dict[str, Any] = dict(move)
    raw_beats = move.get("beats")
    if isinstance(raw_beats, list):
        copied: list[Any] = []
        for b in raw_beats:
            copied.append(dict(b) if isinstance(b, dict) else b)
        base["beats"] = copied
    return base


def legacy_flat_action_text(move: Mapping[str, Any] | None) -> str:
    """Concatenate all ``type: action`` beat ``action`` fields with a single space."""
    if not isinstance(move, Mapping):
        return ""
    beats = move.get("beats")
    if not isinstance(beats, list):
        return ""
    parts: list[str] = []
    for b in beats:
        if not isinstance(b, dict) or b.get("type") != "action":
            continue
        s = str(b.get("action", "") or "").strip()
        if s:
            parts.append(s)
    return " ".join(parts).strip()


def legacy_flat_dialogue_text(move: Mapping[str, Any] | None) -> str:
    """Concatenate all ``type: speech`` beat ``dialogue`` fields with a single space."""
    if not isinstance(move, Mapping):
        return ""
    beats = move.get("beats")
    if not isinstance(beats, list):
        return ""
    parts: list[str] = []
    for b in beats:
        if not isinstance(b, dict) or b.get("type") != "speech":
            continue
        s = str(b.get("dialogue", "") or "").strip()
        if s:
            parts.append(s)
    return " ".join(parts).strip()


def legacy_move_text_for_validation(move: Mapping[str, Any] | None) -> str:
    """``action``-like text plus ``dialogue``-like text, same order as v1 string joins.

    For canonical v2, derives from ``beats``; for legacy v1 dicts (no
    ``move_schema_version`` or tests injecting plain dicts), uses root
    ``action``/``dialogue`` when there are no beats.
    """
    if not isinstance(move, Mapping):
        return ""
    if int(str(move.get("move_schema_version", 0) or 0) or 0) == 2:
        a = legacy_flat_action_text(move)
        d = legacy_flat_dialogue_text(move)
        t = f"{a} {d}".strip()
        if t:
            return t
    a1 = str(move.get("action", "") or "").strip()
    d1 = str(move.get("dialogue", "") or "").strip()
    return f"{a1} {d1}".strip()


class CanonicalV2Move(dict):
    """
    A ``dict`` containing only v2 move keys (no root ``action``/``dialogue``). Legacy
    ``.get("action")`` / ``.get("dialogue")`` resolve via :func:`legacy_flat_action_text` /
    :func:`legacy_flat_dialogue_text` (read-only; no v1 root keys are inserted).
    ``dict(flattened_v2)`` and JSON serialization use stored keys only.
    """

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        if int(dict.get(self, "move_schema_version", 0) or 0) == 2:
            if key == "action":
                a = legacy_flat_action_text(self)
                return a if a else default
            if key == "dialogue":
                d = legacy_flat_dialogue_text(self)
                return d if d else default
        return dict.get(self, key, default)

    def __getitem__(self, key: Any) -> Any:  # type: ignore[override]
        if int(dict.get(self, "move_schema_version", 0) or 0) == 2:
            if key == "action":
                return legacy_flat_action_text(self) or ""
            if key == "dialogue":
                return legacy_flat_dialogue_text(self) or ""
        return dict.__getitem__(self, key)
