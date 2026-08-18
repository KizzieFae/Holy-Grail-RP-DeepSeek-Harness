"""Per-recipient structured move derivation and Director canonical copy."""

from __future__ import annotations

from typing import Any

from character_move_adapters import (
    copy_move_shallow_with_deep_beats,
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)

from perception_audibility_constants import AUDIBILITY_PUBLIC, REDACTED_SPEECH_STUB
from perception_audibility_normalize import normalize_move_audibility, normalize_speech_beat_audibility
from perception_audibility_visibility import (
    speech_beat_viewer_may_perceive,
    viewer_may_perceive_dialogue,
)


def redact_structured_move_for_orchestration(
    move_entry: dict[str, Any],
    *,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return an unredacted copy for Director structured history (Issue #138).

    ``present_characters`` is retained for call-site compatibility only.
    """
    _ = present_characters  # Director consumes canonical truth; arg unused
    if not isinstance(move_entry, dict):
        return move_entry
    return copy_move_shallow_with_deep_beats(move_entry)


def filter_structured_move_for_viewer(
    move_entry: dict[str, Any],
    *,
    viewer_character_name: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Derive per-recipient structured move entry (redacted speech stubs when needed)."""
    if not isinstance(move_entry, dict):
        return move_entry
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]
    speaker = str(move_entry.get("speaker", "") or "").strip()
    if not speaker or speaker == viewer_character_name:
        out = copy_move_shallow_with_deep_beats(move_entry)
        if is_canonical_v2_move(out):
            beats = out.get("beats")
            if isinstance(beats, list):
                new_beats = [
                    normalize_speech_beat_audibility(dict(b), speaker, present)
                    if isinstance(b, dict) and b.get("type") == "speech"
                    else (dict(b) if isinstance(b, dict) else b)
                    for b in beats
                ]
                out["beats"] = new_beats
                flat: dict[str, Any] = {"move_schema_version": 2, "beats": new_beats}
                out["action"] = legacy_flat_action_text(flat)
                out["dialogue"] = legacy_flat_dialogue_text(flat)
        return out

    if is_canonical_v2_move(move_entry):
        out = copy_move_shallow_with_deep_beats(move_entry)
        beats = out.get("beats")
        if not isinstance(beats, list):
            return out
        new_beats: list[Any] = []
        for b in beats:
            if not isinstance(b, dict):
                new_beats.append(b)
                continue
            if b.get("type") == "speech":
                nb = normalize_speech_beat_audibility(dict(b), speaker, present)
                if not speech_beat_viewer_may_perceive(
                    nb,
                    acting_character=speaker,
                    viewer_character=viewer_character_name,
                ):
                    nb = dict(nb)
                    nb["dialogue"] = REDACTED_SPEECH_STUB
                new_beats.append(nb)
            else:
                new_beats.append(dict(b))
        out["beats"] = new_beats
        flat = {"move_schema_version": 2, "beats": new_beats}
        out["action"] = legacy_flat_action_text(flat)
        out["dialogue"] = legacy_flat_dialogue_text(flat)
        out["audibility"] = AUDIBILITY_PUBLIC
        out["audience"] = []
        return out

    out = dict(move_entry)
    move_like = {
        "action": out.get("action", ""),
        "dialogue": out.get("dialogue", ""),
        "audibility": out.get("audibility", AUDIBILITY_PUBLIC),
        "audience": out.get("audience", []),
    }
    move_like = normalize_move_audibility(move_like, speaker, present)
    if not viewer_may_perceive_dialogue(
        move_like, acting_character=speaker, viewer_character=viewer_character_name
    ):
        out["dialogue"] = ""
    out["audibility"] = move_like.get("audibility", AUDIBILITY_PUBLIC)
    out["audience"] = move_like.get("audience", [])
    return out
