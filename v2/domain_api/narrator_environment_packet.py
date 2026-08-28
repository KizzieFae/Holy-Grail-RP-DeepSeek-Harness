"""Deterministic Narrator environmental packet assembly (#49)."""

from __future__ import annotations

from typing import Any

from domain_api.narrator_environment_contract import (
    EnvironmentalCurrentView,
    NarratorEnvironmentPacket,
)
from domain_api.narrator_environment_projection import build_environmental_current_view
from domain_api.session_state import LiveSession
from domain_api.story_knowledge_contract import StoryKnowledgeRecord


def assemble_narrator_environment_packet(
    fixture: LiveSession,
    *,
    story_records: list[StoryKnowledgeRecord] | None = None,
    location: str | None = None,
) -> tuple[NarratorEnvironmentPacket, EnvironmentalCurrentView]:
    view = build_environmental_current_view(
        fixture,
        story_records=story_records,
        location=location,
    )
    descriptors = tuple(view.effective_descriptors.values())
    carryover = tuple(
        desc.story_record_id
        for desc in descriptors
        if desc.story_record_id and desc.source == "story_derived"
    )
    sub_refs = tuple(
        sorted(
            {
                ref
                for desc in descriptors
                for ref in desc.stable_refs
                if ref and ref != view.location_ref
            }
        )
    )
    packet = NarratorEnvironmentPacket(
        location_refs=(view.location_ref,),
        effective_descriptors=descriptors,
        stable_sub_referents=sub_refs,
        recent_environmental_changes=tuple(view.recent_changes),
        carryover_b2_refs=carryover,
        assembly_metadata=dict(view.assembly_metadata),
    )
    return packet, view


def packet_to_manifest_metadata(
    packet: NarratorEnvironmentPacket,
    view: EnvironmentalCurrentView,
) -> dict[str, Any]:
    return {
        "packet": packet.to_dict(),
        "environmental_current_view": view.to_dict(),
    }
