"""Shared helpers for perceptual entitlement tests (#155)."""

from __future__ import annotations

from perceptual_scene_context import PerceptualSceneContextV1, PortalContext


def co_present_zone_context(
    cast: list[str],
    zone: str = "shared_room",
    *,
    extra_characters: list[str] | None = None,
) -> PerceptualSceneContextV1:
    zones = {name: zone for name in cast}
    for name in extra_characters or []:
        key = str(name or "").strip()
        if key:
            zones[key] = zone
    return PerceptualSceneContextV1(
        character_zones=zones,
        portals={},
    )


def ayame_threshold_context(
    *,
    host: str = "Ayame",
    applicant: str = "Kizzie",
    door_state: str = "closed",
) -> PerceptualSceneContextV1:
    return PerceptualSceneContextV1(
        character_zones={applicant: "exterior_threshold", host: "interior_entry"},
        portals={
            "main_entrance_door": PortalContext(
                portal_id="main_entrance_door",
                state=door_state,  # type: ignore[arg-type]
                opacity="opaque",
                acoustic="ordinary",
                connects=("exterior_threshold", "interior_entry"),
            )
        },
    )
