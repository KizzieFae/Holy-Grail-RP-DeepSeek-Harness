"""Speech authority resolution for perceptual visibility (#90)."""

from __future__ import annotations

from typing import Any

from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
)
from perception_audibility_visibility import (
    resolve_entitled_characters,
    resolve_recipient_scope,
    speech_beat_viewer_may_perceive,
)


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


def speech_authority_from_player_recipients(
    recipients: dict[str, Any],
    *,
    acting_character: str,
) -> dict[str, Any]:
    scope = str(recipients.get("scope", "") or "public").strip().lower() or "public"
    if scope in ("public", "present", "environmental"):
        audibility = AUDIBILITY_PUBLIC
    elif scope == "directed":
        audibility = AUDIBILITY_DIRECTED
    else:
        audibility = AUDIBILITY_PRIVATE
    audience_raw = recipients.get("characters")
    audience = (
        [str(name).strip() for name in audience_raw if str(name).strip()]
        if isinstance(audience_raw, list)
        else []
    )
    return {
        "kind": "speech_audibility",
        "acting_character": str(acting_character or "").strip(),
        "audibility": audibility,
        "audience": audience,
    }


def player_speech_unit_allows_viewer(
    unit: Any,
    *,
    viewer_character: str,
    role_assignments: dict[str, str] | None,
    session_cast: list[str] | None,
) -> bool:
    """Speech eligibility for player units using one role-resolution primitive."""
    scope = resolve_recipient_scope(unit.recipients)
    if scope == "role_private":
        entitled = resolve_entitled_characters(
            scope,
            unit.recipients,
            role_assignments=role_assignments,
            session_cast=session_cast,
        )
        return str(viewer_character or "").strip() in entitled
    return speech_authority_allows_viewer(
        unit.authority,
        viewer_character=viewer_character,
    )


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
