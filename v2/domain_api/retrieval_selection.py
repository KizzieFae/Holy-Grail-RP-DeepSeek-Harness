"""Deterministic retrieval selection for KnowledgeService (M12.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    MAX_AUTHORED_CHARACTER_ITEMS,
    MAX_LORE_EXCERPT_CHARS,
    MAX_SCENE_REFERENCE_ITEMS,
)

MAX_GLOBAL_RETRIEVAL_ITEMS = 8
MAX_GLOBAL_RETRIEVAL_CHARS = 8000

LANE_PRIORITY = {
    "scene_reference": 0,
    "authored_character_knowledge": 1,
}


@dataclass(frozen=True)
class RetrievalQueryContext:
    character_file_id: str | None
    character_display_name: str
    session_template_id: str | None
    character_index_keys: tuple[str, ...] = ()


@dataclass
class RetrievalDiagnostics:
    provider_id: str = "deterministic-local"
    index_path: str | None = None
    setup_snapshot_hash: str | None = None
    candidate_count: int = 0
    visibility_dropped: int = 0
    dedupe_dropped: int = 0
    cap_dropped: int = 0
    selected_ids: list[str] = field(default_factory=list)
    selected_character_count: int = 0
    selected_scene_count: int = 0
    total_chars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "index_path": self.index_path,
            "setup_snapshot_hash": self.setup_snapshot_hash,
            "candidate_count": self.candidate_count,
            "visibility_dropped": self.visibility_dropped,
            "dedupe_dropped": self.dedupe_dropped,
            "cap_dropped": self.cap_dropped,
            "selected_ids": list(self.selected_ids),
            "selected_character_count": self.selected_character_count,
            "selected_scene_count": self.selected_scene_count,
            "total_chars": self.total_chars,
        }


def character_index_keys(
    *,
    character_file_id: str | None,
    character_display_name: str,
) -> tuple[str, ...]:
    keys: list[str] = []
    for raw in (character_file_id, character_display_name):
        value = str(raw or "").strip()
        if value and value not in keys:
            keys.append(value)
    spaced = str(character_display_name or "").strip()
    if spaced:
        underscored = spaced.replace(" ", "_")
        if underscored not in keys:
            keys.append(underscored)
    return tuple(keys)


def merge_authored_record_sets(
    snapshot_records: list[AuthoredKnowledgeRecord],
    supplemental_records: list[AuthoredKnowledgeRecord],
) -> tuple[list[AuthoredKnowledgeRecord], int]:
    """Merge records with snapshot precedence on knowledge_id collisions."""
    merged: dict[str, AuthoredKnowledgeRecord] = {}
    dedupe_dropped = 0
    for record in snapshot_records:
        merged[record.knowledge_id] = record
    for record in supplemental_records:
        if record.knowledge_id in merged:
            dedupe_dropped += 1
            continue
        merged[record.knowledge_id] = record
    return list(merged.values()), dedupe_dropped


def _visibility_allows(
    record: AuthoredKnowledgeRecord,
    *,
    character_file_id: str | None,
    session_template_id: str | None,
) -> bool:
    visibility = str(record.visibility or "").strip()
    if visibility == "character_scoped":
        return bool(character_file_id) and record.subject_character_file_id == character_file_id
    if visibility == "template_participants":
        if not session_template_id:
            return False
        return record.source_asset_id == session_template_id
    if visibility in {"public", "scope_global"}:
        return True
    return False


def _lane_for_record(record: AuthoredKnowledgeRecord) -> str:
    lane = str(record.provenance.get("knowledge_lane", "") or "").strip()
    if lane in LANE_PRIORITY:
        return lane
    if record.source_kind == "scene_template":
        return "scene_reference"
    return "authored_character_knowledge"


def _record_sort_key(record: AuthoredKnowledgeRecord) -> tuple[int, int, str]:
    lane = _lane_for_record(record)
    source_index = int(record.provenance.get("source_index", 0) or 0)
    return (LANE_PRIORITY.get(lane, 9), source_index, record.knowledge_id)


def select_retrieval_records(
    records: list[AuthoredKnowledgeRecord],
    *,
    character_file_id: str | None,
    session_template_id: str | None,
    diagnostics: RetrievalDiagnostics | None = None,
) -> tuple[list[AuthoredKnowledgeRecord], list[AuthoredKnowledgeRecord]]:
    """Filter, rank, and cap authored retrieval records deterministically."""
    diag = diagnostics or RetrievalDiagnostics()
    diag.candidate_count = len(records)

    visible: list[AuthoredKnowledgeRecord] = []
    seen_ids: set[str] = set()
    for record in records:
        if record.knowledge_id in seen_ids:
            diag.dedupe_dropped += 1
            continue
        if not _visibility_allows(
            record,
            character_file_id=character_file_id,
            session_template_id=session_template_id,
        ):
            diag.visibility_dropped += 1
            continue
        seen_ids.add(record.knowledge_id)
        visible.append(record)

    visible.sort(key=_record_sort_key)

    character_records: list[AuthoredKnowledgeRecord] = []
    scene_records: list[AuthoredKnowledgeRecord] = []
    total_chars = 0
    selected_ids: list[str] = []

    for record in visible:
        lane = _lane_for_record(record)
        if lane == "scene_reference":
            if len(scene_records) >= MAX_SCENE_REFERENCE_ITEMS:
                diag.cap_dropped += 1
                continue
        else:
            if len(character_records) >= MAX_AUTHORED_CHARACTER_ITEMS:
                diag.cap_dropped += 1
                continue

        content_len = len(record.content)
        if content_len > MAX_LORE_EXCERPT_CHARS and lane != "scene_reference":
            diag.cap_dropped += 1
            continue
        if len(selected_ids) >= MAX_GLOBAL_RETRIEVAL_ITEMS:
            diag.cap_dropped += 1
            continue
        if total_chars + content_len > MAX_GLOBAL_RETRIEVAL_CHARS:
            diag.cap_dropped += 1
            continue

        if lane == "scene_reference":
            scene_records.append(record)
        else:
            character_records.append(record)
        selected_ids.append(record.knowledge_id)
        total_chars += content_len

    diag.selected_ids = selected_ids
    diag.selected_character_count = len(character_records)
    diag.selected_scene_count = len(scene_records)
    diag.total_chars = total_chars
    return character_records, scene_records
