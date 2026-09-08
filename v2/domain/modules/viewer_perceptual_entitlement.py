"""Deterministic viewer perceptual entitlement (Gate 2) for Player PVR (#155)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from perception_channel import (
    PerceptionChannel,
    resolve_unit_perception_channel_with_authority,
    uniform_bundle_requires_decomposition,
)
from perception_audibility_visibility import resolve_recipient_scope
from perceptual_scene_context import (
    PerceptualSceneContextV1,
    evaluate_portal_perception,
)

PerceptualDecision = Literal["permitted", "withheld", "unknown"]


@dataclass
class ViewerPerceptualEntitlementDecision:
    unit_id: str
    segment_index: int
    perception_channel: PerceptionChannel
    recipient_decision: str
    perceptual_decision: PerceptualDecision
    perceptual_basis: str
    reason_code: str
    projected: bool
    authority_refs: list[str] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "segment_index": self.segment_index,
            "perception_channel": self.perception_channel,
            "recipient_decision": self.recipient_decision,
            "perceptual_decision": self.perceptual_decision,
            "perceptual_basis": self.perceptual_basis,
            "reason_code": self.reason_code,
            "projected": self.projected,
            "authority_refs": list(self.authority_refs),
            "text": self.text,
        }


def _event_character_for_player_unit(
    unit: Any,
    *,
    player_character: str | None,
) -> str | None:
    if player_character:
        return player_character
    recipients = getattr(unit, "recipients", None)
    if isinstance(recipients, dict):
        chars = recipients.get("characters") or []
        if isinstance(chars, list) and chars:
            return str(chars[0]).strip() or None
    return None


def _unknown_decision(
    *,
    unit_id: str,
    channel: PerceptionChannel,
    text: str,
    basis: str,
    reason_code: str,
) -> ViewerPerceptualEntitlementDecision:
    return ViewerPerceptualEntitlementDecision(
        unit_id=unit_id,
        segment_index=0,
        perception_channel=channel,
        recipient_decision="allowed",
        perceptual_decision="unknown",
        perceptual_basis=basis,
        reason_code=reason_code,
        projected=False,
        text=text,
    )


def _non_spatial_recipient_contract(unit: Any) -> bool:
    recipients = getattr(unit, "recipients", None)
    if not isinstance(recipients, dict):
        if isinstance(unit, dict):
            recipients = unit.get("recipients")
    if not isinstance(recipients, dict):
        return False
    scope = resolve_recipient_scope(recipients)
    kind = str(getattr(unit, "kind", "") or "")
    if isinstance(unit, dict):
        kind = str(unit.get("kind", "") or kind)
    if scope in ("private", "role_private") and kind in (
        "observable_event",
        "observable_scene",
        "internal",
        "speech",
    ):
        return True
    return False


def evaluate_viewer_perceptual_entitlement(
    unit: Any,
    *,
    viewer_character: str,
    recipient_allowed: bool,
    scene_context: PerceptualSceneContextV1 | None,
    player_character: str | None = None,
) -> list[ViewerPerceptualEntitlementDecision]:
    unit_id = str(getattr(unit, "unit_id", "") or "unit")
    text = str(getattr(unit, "text", "") or "")

    if not recipient_allowed:
        channel = resolve_unit_perception_channel_with_authority(unit).channel
        return [
            ViewerPerceptualEntitlementDecision(
                unit_id=unit_id,
                segment_index=0,
                perception_channel=channel,
                recipient_decision="denied",
                perceptual_decision="withheld",
                perceptual_basis="none",
                reason_code="recipient_denied",
                projected=False,
                text=text,
            )
        ]

    if uniform_bundle_requires_decomposition(unit):
        channel = resolve_unit_perception_channel_with_authority(unit).channel
        return [
            _unknown_decision(
                unit_id=unit_id,
                channel=channel,
                text=text,
                basis="mixed_modality_requires_decomposition",
                reason_code="mixed_modality_requires_decomposition",
            )
        ]

    if _non_spatial_recipient_contract(unit):
        resolution = resolve_unit_perception_channel_with_authority(unit)
        return [
            ViewerPerceptualEntitlementDecision(
                unit_id=unit_id,
                segment_index=0,
                perception_channel=resolution.channel,
                recipient_decision="allowed",
                perceptual_decision="permitted",
                perceptual_basis="non_spatial_recipient_contract",
                reason_code="non_spatial_recipient_contract",
                projected=True,
                text=text,
            )
        ]

    resolution = resolve_unit_perception_channel_with_authority(unit)
    channel = resolution.channel

    if channel == "non_perceptual":
        return [
            ViewerPerceptualEntitlementDecision(
                unit_id=unit_id,
                segment_index=0,
                perception_channel=channel,
                recipient_decision="allowed",
                perceptual_decision="withheld",
                perceptual_basis="non_perceptual_delivery",
                reason_code="non_perceptual_unit",
                projected=False,
                text=text,
            )
        ]

    if resolution.uncertain:
        return [
            _unknown_decision(
                unit_id=unit_id,
                channel=channel,
                text=text,
                basis="uncertain_perception_channel",
                reason_code="uncertain_perception_channel",
            )
        ]

    event_character = _event_character_for_player_unit(unit, player_character=player_character)
    viewer = str(viewer_character or "").strip()
    event = str(event_character or "").strip()
    if viewer and event and viewer == event:
        return [
            ViewerPerceptualEntitlementDecision(
                unit_id=unit_id,
                segment_index=0,
                perception_channel=channel,
                recipient_decision="allowed",
                perceptual_decision="permitted",
                perceptual_basis="self_sourced_player_event",
                reason_code="self_sourced_player_event",
                projected=True,
                authority_refs=[f"event_character:{event}"],
                text=text,
            )
        ]

    decision, basis, refs = evaluate_portal_perception(
        scene_context,
        viewer_character=viewer_character,
        event_character=event_character,
        channel=channel,
    )
    projected = decision == "permitted"
    reason = basis if decision != "unknown" else "insufficient_entitlement_evidence"
    return [
        ViewerPerceptualEntitlementDecision(
            unit_id=unit_id,
            segment_index=0,
            perception_channel=channel,
            recipient_decision="allowed",
            perceptual_decision=decision,
            perceptual_basis=basis,
            reason_code=reason,
            projected=projected,
            authority_refs=refs,
            text=text,
        )
    ]
