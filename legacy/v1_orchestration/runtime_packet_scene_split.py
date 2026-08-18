"""Stable vs dynamic scene state split / merge (Issue #166)."""

from __future__ import annotations

from typing import Any

from runtime_packet_types import (
    CharacterRuntimePromptProjection,
    RuntimeScenePacket,
    STABLE_SCENE_STATE_KEYS,
)


def split_scene_state(scene_state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    stable: dict[str, Any] = {}
    dynamic: dict[str, Any] = {}
    for key, value in scene_state.items():
        if key in STABLE_SCENE_STATE_KEYS:
            stable[key] = value
        else:
            dynamic[key] = value
    return stable, dynamic


def merge_scene_state_from_packets(
    scene_packet: RuntimeScenePacket,
    projection: CharacterRuntimePromptProjection,
) -> dict[str, Any]:
    return {**scene_packet.stable_scene_state, **projection.dynamic_scene_state}
