"""Speech authority resolution for perceptual visibility (#90)."""

from __future__ import annotations

from typing import Any

from perception_audibility_constants import AUDIBILITY_PUBLIC
from perception_audibility_visibility import speech_beat_viewer_may_perceive


def speech_authority_from_beat(
    beat: dict[str, Any],
    *,
    acting_character: str,
) -> dict[str, Any]:
    aud = str(beat.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    audience_raw = beat.get("audience")
    audience = (
        [str(name).strip() for name in audience_raw if str(name).strip()]
        if isinstance(audience_raw, list)
        else []
    )
    return {
        "kind": "speech_audibility",
        "acting_character": str(acting_character or "").strip(),
        "audibility": aud,
        "audience": audience,
    }


def speech_authority_allows_viewer(
    authority: dict[str, Any] | None,
    *,
    viewer_character: str,
) -> bool:
    if not isinstance(authority, dict):
        return True
    if authority.get("kind") != "speech_audibility":
        return True
    acting_character = str(authority.get("acting_character", "") or "").strip()
    if not acting_character:
        return False
    beat = {
        "audibility": authority.get("audibility", AUDIBILITY_PUBLIC),
        "audience": list(authority.get("audience") or []),
    }
    return speech_beat_viewer_may_perceive(
        beat,
        acting_character=acting_character,
        viewer_character=viewer_character,
    )
