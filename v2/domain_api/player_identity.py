"""Player identity and control-mode helpers for session setup."""

from __future__ import annotations

from typing import Any

ControlMode = str  # "player" | "ai"


def normalize_user_persona_id(value: str | None) -> str:
    persona = str(value or "").strip()
    return persona or "Player"


def resolve_player_display_name(
    *,
    player_character_file_id: str | None,
    names_by_file: dict[str, str],
) -> str | None:
    if not player_character_file_id:
        return None
    file_id = str(player_character_file_id).strip()
    if not file_id:
        return None
    return str(names_by_file.get(file_id, file_id))


def build_control_modes(
    *,
    cast_display_names: list[str],
    player_display_name: str | None,
) -> dict[str, ControlMode]:
    modes: dict[str, ControlMode] = {}
    for name in cast_display_names:
        if player_display_name and name == player_display_name:
            modes[name] = "player"
        else:
            modes[name] = "ai"
    return modes


def player_character_file_id(snapshot: dict[str, Any] | None) -> str | None:
    if not snapshot:
        return None
    value = str(snapshot.get("player_character_file_id", "") or "").strip()
    return value or None


def user_persona_id_from_snapshot(snapshot: dict[str, Any] | None) -> str:
    if not snapshot:
        return "Player"
    return normalize_user_persona_id(snapshot.get("user_persona_id"))


def control_modes_from_snapshot(snapshot: dict[str, Any] | None) -> dict[str, ControlMode]:
    if not snapshot:
        return {}
    raw = snapshot.get("control_modes") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def is_player_controlled(snapshot: dict[str, Any] | None, character_display_name: str) -> bool:
    modes = control_modes_from_snapshot(snapshot)
    return modes.get(character_display_name) == "player"
