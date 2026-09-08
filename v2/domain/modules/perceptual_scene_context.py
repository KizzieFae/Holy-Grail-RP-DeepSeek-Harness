"""Optional authoritative perceptual scene context (#155)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PortalState = Literal["open", "closed"]
PortalOpacity = Literal["opaque", "transparent"]
PortalAcoustic = Literal["ordinary", "soundproof", "unknown"]

PERCEPTUAL_SCENE_CONTEXT_SCHEMA_VERSION = 1


@dataclass
class PortalContext:
    portal_id: str
    state: PortalState = "closed"
    opacity: PortalOpacity = "opaque"
    acoustic: PortalAcoustic = "ordinary"
    connects: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "portal_id": self.portal_id,
            "state": self.state,
            "opacity": self.opacity,
            "acoustic": self.acoustic,
            "connects": list(self.connects),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PortalContext | None:
        portal_id = str(data.get("portal_id", "") or "").strip()
        if not portal_id:
            portal_id = "portal"
        state = str(data.get("state", "closed") or "closed").strip().lower()
        if state not in ("open", "closed"):
            state = "closed"
        opacity = str(data.get("opacity", "opaque") or "opaque").strip().lower()
        if opacity not in ("opaque", "transparent"):
            opacity = "opaque"
        acoustic = str(data.get("acoustic", "ordinary") or "ordinary").strip().lower()
        if acoustic not in ("ordinary", "soundproof", "unknown"):
            acoustic = "ordinary"
        connects_raw = data.get("connects") or []
        connects = tuple(str(z).strip() for z in connects_raw if str(z).strip())
        return cls(
            portal_id=portal_id,
            state=state,  # type: ignore[arg-type]
            opacity=opacity,  # type: ignore[arg-type]
            acoustic=acoustic,  # type: ignore[arg-type]
            connects=connects,
        )


@dataclass
class PerceptualSceneContextV1:
    schema_version: int = PERCEPTUAL_SCENE_CONTEXT_SCHEMA_VERSION
    character_zones: dict[str, str] = field(default_factory=dict)
    portals: dict[str, PortalContext] = field(default_factory=dict)
    observation_channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "character_zones": dict(self.character_zones),
            "portals": {k: v.to_dict() for k, v in self.portals.items()},
            "observation_channels": list(self.observation_channels),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PerceptualSceneContextV1 | None:
        if not isinstance(data, dict):
            return None
        zones_raw = data.get("character_zones")
        zones: dict[str, str] = {}
        if isinstance(zones_raw, dict):
            for key, value in zones_raw.items():
                k = str(key or "").strip()
                v = str(value or "").strip()
                if k and v:
                    zones[k] = v
        portals: dict[str, PortalContext] = {}
        portals_raw = data.get("portals")
        if isinstance(portals_raw, dict):
            for key, value in portals_raw.items():
                if isinstance(value, dict):
                    portal = PortalContext.from_dict({**value, "portal_id": str(key)})
                    if portal is not None:
                        portals[str(key)] = portal
        channels = [
            str(item).strip()
            for item in (data.get("observation_channels") or [])
            if str(item).strip()
        ]
        return cls(
            schema_version=int(data.get("schema_version", PERCEPTUAL_SCENE_CONTEXT_SCHEMA_VERSION)),
            character_zones=zones,
            portals=portals,
            observation_channels=channels,
        )


def resolve_template_perceptual_scene_context(
    template_context: dict[str, Any] | None,
    *,
    role_assignments: dict[str, str],
) -> dict[str, Any] | None:
    """Resolve role-keyed template perceptual context to character-keyed scene state."""
    if not isinstance(template_context, dict):
        return None
    zones_by_role = template_context.get("character_zones_by_role")
    if not isinstance(zones_by_role, dict):
        return None
    character_zones: dict[str, str] = {}
    for character_name, role_name in role_assignments.items():
        role_key = str(role_name or "").strip()
        char_key = str(character_name or "").strip()
        if not role_key or not char_key:
            continue
        zone = zones_by_role.get(role_key)
        if zone:
            character_zones[char_key] = str(zone).strip()
    if not character_zones:
        return None
    portals_raw = template_context.get("portals")
    portals: dict[str, Any] = {}
    if isinstance(portals_raw, dict):
        portals = {str(k): dict(v) for k, v in portals_raw.items() if isinstance(v, dict)}
    channels = [
        str(item).strip()
        for item in (template_context.get("observation_channels") or [])
        if str(item).strip()
    ]
    return {
        "schema_version": int(
            template_context.get("schema_version", PERCEPTUAL_SCENE_CONTEXT_SCHEMA_VERSION)
        ),
        "character_zones": character_zones,
        "portals": portals,
        "observation_channels": channels,
    }


def perceptual_scene_context_from_scene_state(scene_state: Any) -> PerceptualSceneContextV1 | None:
    if scene_state is None:
        return None
    raw = None
    if isinstance(scene_state, dict):
        raw = scene_state.get("perceptual_scene_context")
    else:
        raw = getattr(scene_state, "perceptual_scene_context", None)
    return PerceptualSceneContextV1.from_dict(raw if isinstance(raw, dict) else None)


def _find_connecting_portal(
    context: PerceptualSceneContextV1,
    zone_a: str,
    zone_b: str,
) -> PortalContext | None:
    for portal in context.portals.values():
        if zone_a in portal.connects and zone_b in portal.connects:
            return portal
    return None


def viewer_event_zones(
    context: PerceptualSceneContextV1 | None,
    *,
    viewer_character: str,
    event_character: str | None,
) -> tuple[str | None, str | None]:
    if context is None:
        return None, None
    viewer_zone = context.character_zones.get(viewer_character)
    event_zone = None
    if event_character:
        event_zone = context.character_zones.get(event_character)
    return viewer_zone, event_zone


def evaluate_portal_perception(
    context: PerceptualSceneContextV1 | None,
    *,
    viewer_character: str,
    event_character: str | None,
    channel: str,
) -> tuple[str, str, list[str]]:
    """Return (decision, basis, fact_refs) for portal-aware entitlement."""
    if channel == "non_perceptual":
        return "withheld", "non_perceptual_delivery", []

    viewer_zone, event_zone = viewer_event_zones(
        context, viewer_character=viewer_character, event_character=event_character
    )
    if not viewer_zone or not event_zone:
        return "unknown", "insufficient_entitlement_evidence", []

    if viewer_zone == event_zone:
        if channel == "visual":
            return "permitted", "same_zone_visual", [f"zone:{viewer_zone}"]
        if channel == "auditory":
            return "permitted", "same_zone_auditory", [f"zone:{viewer_zone}"]
        return "withheld", "non_perceptual_delivery", []

    portal = _find_connecting_portal(context, viewer_zone, event_zone)
    if portal is None:
        if channel == "visual" and context.observation_channels:
            link = f"{viewer_zone}->{event_zone}"
            if link in context.observation_channels:
                return "permitted", "observation_channel_visual", [
                    f"zone_viewer:{viewer_zone}",
                    f"zone_event:{event_zone}",
                    f"observation_channel:{link}",
                ]
        return "unknown", "insufficient_entitlement_evidence", []

    refs = [f"portal:{portal.portal_id}", f"zone_viewer:{viewer_zone}", f"zone_event:{event_zone}"]

    if portal.state == "open":
        if channel in ("visual", "auditory"):
            return "permitted", "open_portal_connection", refs
        return "withheld", "non_perceptual_delivery", refs

    if channel == "visual":
        if portal.opacity == "transparent":
            return "permitted", "transparent_portal_visual", refs
        return "withheld", "barrier_blocks_visual", refs

    if channel == "auditory":
        if portal.acoustic == "soundproof":
            return "withheld", "barrier_blocks_auditory", refs
        if portal.acoustic == "unknown":
            return "unknown", "insufficient_entitlement_evidence", refs
        return "permitted", "ordinary_barrier_auditory", refs

    return "withheld", "non_perceptual_delivery", refs
