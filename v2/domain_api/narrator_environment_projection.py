"""EnvironmentalCurrentView deterministic projection (#49)."""

from __future__ import annotations

import re
from typing import Any

from .narrator_environment_location_binding import (
    bind_location_stable_ref,
    normalize_location_label,
)
from domain_api.authored_knowledge import (
    AuthoredKnowledgeRecord,
    compile_authored_records_from_snapshot,
)
from domain_api.narrator_environment_contract import (
    ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
    ENVIRONMENTAL_DESCRIPTOR_MARKER,
    EnvironmentalConflict,
    EnvironmentalCurrentView,
    EnvironmentalDescriptor,
    parse_environmental_descriptor_payload,
)
from domain_api.session_state import LiveSession
from domain_api.story_knowledge_contract import StoryKnowledgeRecord, StoryRelation


def _record_applies_to_location(record: StoryKnowledgeRecord, location_ref: str) -> bool:
    record_refs = {ref.stable_ref for ref in record.stable_refs}
    if record_refs:
        return location_ref in record_refs
    if record.location and location_stable_ref_from_label(record.location) == location_ref:
        return True
    return False


def location_stable_ref_from_label(location: str) -> str:
    return bind_location_stable_ref(location).stable_ref


def _is_environmental_derived_record(record: StoryKnowledgeRecord) -> bool:
    if record.record_kind != "derived":
        return False
    if record.event_type == ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE:
        return True
    return ENVIRONMENTAL_DESCRIPTOR_MARKER in list(record.grounding_markers or [])


def descriptor_from_story_record(record: StoryKnowledgeRecord) -> EnvironmentalDescriptor | None:
    if not _is_environmental_derived_record(record):
        return None
    payload = parse_environmental_descriptor_payload(record.evidence.committed_text)
    if payload is None:
        return None
    supersedes = str(payload.get("supersedes", "") or "").strip() or None
    if not supersedes:
        for rel in record.related_refs:
            if rel.rel == "supersedes" and rel.target_id:
                supersedes = rel.target_id
                break
    refs = tuple(
        ref.stable_ref
        for ref in record.stable_refs
        if str(ref.stable_ref or "").strip()
    ) or tuple(str(item) for item in payload.get("stable_refs", []) if str(item).strip())
    return EnvironmentalDescriptor(
        property_key=str(payload.get("property_key", "")).strip(),
        value=str(payload.get("value", "")).strip(),
        source="story_derived",
        stable_refs=refs,
        story_record_id=record.story_record_id,
        supersedes=supersedes,
        turn_index=record.turn_index,
    )


def _authored_descriptor_from_record(
    record: AuthoredKnowledgeRecord,
    *,
    location_ref: str,
) -> EnvironmentalDescriptor | None:
    content = str(record.content or "").strip()
    if not content:
        return None
    if record.knowledge_kind not in {
        "scene_setup_fact",
        "lore_reference",
        "environmental_detail",
    }:
        lane = str((record.provenance or {}).get("knowledge_lane", "") or "")
        if lane != "scene_reference":
            return None
    location_label = location_ref.split(":", 1)[-1].replace("_", " ")
    if location_label and location_label not in content.casefold():
        if record.knowledge_kind != "scene_setup_fact":
            return None
    match = re.search(
        r"(?P<key>[A-Za-z][\w\s-]{1,40}?)\s*(?:is|are|:)\s*(?P<value>[^.;]{1,120})",
        content,
    )
    if not match:
        if record.knowledge_kind == "scene_setup_fact":
            return EnvironmentalDescriptor(
                property_key="scene_setup",
                value=content[:200],
                source="authored",
                stable_refs=(location_ref,),
                authored_knowledge_id=record.knowledge_id,
            )
        return None
    return EnvironmentalDescriptor(
        property_key=match.group("key").strip().casefold().replace(" ", "_"),
        value=match.group("value").strip(),
        source="authored",
        stable_refs=(location_ref,),
        authored_knowledge_id=record.knowledge_id,
    )


def load_authored_environmental_descriptors(
    fixture: LiveSession,
    *,
    location_ref: str,
) -> list[EnvironmentalDescriptor]:
    snapshot = dict(fixture.setup_snapshot or {})
    if not snapshot:
        return []
    records = compile_authored_records_from_snapshot(snapshot)
    descriptors: list[EnvironmentalDescriptor] = []
    seen: set[str] = set()
    for record in records:
        desc = _authored_descriptor_from_record(record, location_ref=location_ref)
        if desc is None:
            continue
        dedupe = f"{desc.property_key}|{desc.value}"
        if dedupe in seen:
            continue
        seen.add(dupe)
        descriptors.append(desc)
    return descriptors


def load_story_derived_environmental_descriptors(
    records: list[StoryKnowledgeRecord],
    *,
    location_ref: str,
) -> list[EnvironmentalDescriptor]:
    descriptors: list[EnvironmentalDescriptor] = []
    for record in records:
        if not _record_applies_to_location(record, location_ref):
            continue
        desc = descriptor_from_story_record(record)
        if desc is not None:
            descriptors.append(desc)
    return descriptors


def _apply_precedence(
    descriptors: list[EnvironmentalDescriptor],
) -> tuple[dict[str, EnvironmentalDescriptor], list[EnvironmentalConflict]]:
    effective: dict[str, EnvironmentalDescriptor] = {}
    conflicts: list[EnvironmentalConflict] = []
    grouped: dict[str, list[EnvironmentalDescriptor]] = {}
    for desc in descriptors:
        grouped.setdefault(desc.property_key, []).append(desc)

    for key, items in grouped.items():
        story_items = [item for item in items if item.source == "story_derived"]
        authored_items = [item for item in items if item.source == "authored"]
        if not story_items:
            if authored_items:
                effective[key] = authored_items[0]
            continue

        active: dict[str, EnvironmentalDescriptor] = {
            item.story_record_id or f"anon-{key}-{idx}": item
            for idx, item in enumerate(story_items)
            if item.story_record_id
        }
        for item in story_items:
            if not item.supersedes:
                continue
            if item.supersedes in active:
                del active[item.supersedes]
            if item.story_record_id:
                active[item.story_record_id] = item

        if len(active) > 1:
            values = tuple(sorted({item.value for item in active.values()}))
            if len(values) > 1:
                conflicts.append(
                    EnvironmentalConflict(
                        property_key=key,
                        values=values,
                        record_ids=tuple(sorted(active.keys())),
                    )
                )
                continue
        if active:
            winner = max(
                active.values(),
                key=lambda item: (
                    item.turn_index if item.turn_index is not None else -1,
                    item.story_record_id or "",
                ),
            )
            effective[key] = winner
        elif authored_items:
            effective[key] = authored_items[0]

    for key, items in grouped.items():
        if key in effective:
            continue
        if len(items) == 1:
            effective[key] = items[0]
        elif len(items) > 1:
            values = tuple(sorted({item.value for item in items}))
            if len(set(values)) > 1:
                conflicts.append(
                    EnvironmentalConflict(
                        property_key=key,
                        values=values,
                        record_ids=tuple(
                            item.story_record_id or item.authored_knowledge_id or ""
                            for item in items
                        ),
                    )
                )

    return effective, conflicts


def build_environmental_current_view(
    fixture: LiveSession,
    *,
    story_records: list[StoryKnowledgeRecord] | None = None,
    location: str | None = None,
) -> EnvironmentalCurrentView:
    mgr = fixture.manager
    scene_state = mgr.scene_state
    location_label = normalize_location_label(
        location or (scene_state.location if scene_state is not None else "") or "unknown"
    )
    location_ref_obj = bind_location_stable_ref(location_label)
    location_ref = location_ref_obj.stable_ref

    authored = load_authored_environmental_descriptors(fixture, location_ref=location_ref)
    story_derived: list[EnvironmentalDescriptor] = []
    if story_records is not None:
        story_derived = load_story_derived_environmental_descriptors(
            story_records,
            location_ref=location_ref,
        )

    combined = authored + story_derived
    effective_map, conflicts = _apply_precedence(combined)

    recent = sorted(
        [item for item in story_derived if item.turn_index is not None],
        key=lambda item: item.turn_index or -1,
        reverse=True,
    )[:5]

    sub_refs: set[str] = set()
    for desc in effective_map.values():
        for ref in desc.stable_refs:
            if ref != location_ref:
                sub_refs.add(ref)

    return EnvironmentalCurrentView(
        location_ref=location_ref,
        location_label=location_label,
        effective_descriptors=dict(effective_map),
        conflicts=list(conflicts),
        recent_changes=recent,
        assembly_metadata={
            "authored_count": len(authored),
            "story_derived_count": len(story_derived),
            "memory_scope_id": fixture.memory_scope_id,
        },
    )
