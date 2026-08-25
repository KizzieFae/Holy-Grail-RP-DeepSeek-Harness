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
from .retrieval_contract import RetrievalAccessRequest, RetrievalCandidate
from .session_state import LiveSession

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


_AUTHORED_INFORMATION_CLASSES = frozenset({"authored_static", "compiled_index"})
_SCOPE_INFORMATION_CLASSES = frozenset({"promoted_learned_world", "user_profile"})


def build_viewer_retrieval_request(
    fixture: LiveSession,
    *,
    character_id: str,
    request_id: str | None = None,
    information_classes: frozenset[str] | None = None,
    audit_reason: str = "viewer_retrieval_access",
) -> RetrievalAccessRequest:
    """Build a viewer-scoped RetrievalAccessRequest for #31 contract tests and KnowledgeService."""
    import uuid

    from .retrieval_contract import ALL_INFORMATION_CLASSES, GenerationHints, HardAccessConstraints, ResponseBudget

    classes = information_classes or ALL_INFORMATION_CLASSES
    file_id = fixture.character_file_ids.get(character_id)
    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    anchors = character_index_keys(
        character_file_id=file_id,
        character_display_name=character_id,
    )
    last_round = fixture.rounds[-1] if fixture.rounds else None
    return RetrievalAccessRequest(
        request_id=request_id or f"hg-retrieval-{uuid.uuid4()}",
        consumer_role="host_internal",
        hg_scene_id=fixture.hg_session_id,
        hg_round_id=str(last_round.hg_round_id if last_round else "unbound"),
        turn_index=int(last_round.turn_index if last_round else 0),
        memory_scope_id=fixture.memory_scope_id,
        hard_access=HardAccessConstraints(
            viewer_character_id=character_id,
            subject_character_file_id=file_id,
            session_template_id=template_id,
            allowed_information_classes=classes,
            exclude_authoritative_live=True,
            known_by_character_name=character_id,
        ),
        generation_hints=GenerationHints(
            entity_anchors=anchors,
            recall_mode="broad",
            class_recall_budgets={
                "promoted_learned_world": 8,
                "user_profile": 6,
            },
        ),
        response_budget=ResponseBudget(),
        audit_reason=audit_reason,
    )


def candidate_to_authored_record(candidate: RetrievalCandidate) -> AuthoredKnowledgeRecord | None:
    if candidate.information_class not in _AUTHORED_INFORMATION_CLASSES:
        return None
    legacy = candidate.host_internal_metadata.get("legacy_authored_record")
    if isinstance(legacy, dict):
        return AuthoredKnowledgeRecord(
            knowledge_id=str(legacy["knowledge_id"]),
            knowledge_kind=str(legacy["knowledge_kind"]),
            content=str(legacy["content"]),
            authority_class=str(legacy["authority_class"]),
            visibility=str(legacy["visibility"]),
            subject_character_file_id=legacy.get("subject_character_file_id"),
            source_kind=str(legacy["source_kind"]),
            source_asset_id=str(legacy["source_asset_id"]),
            provenance=dict(legacy.get("provenance") or {}),
        )
    provenance = dict(candidate.provenance)
    return AuthoredKnowledgeRecord(
        knowledge_id=candidate.candidate_id,
        knowledge_kind=str(provenance.get("knowledge_lane", "authored")),
        content=candidate.payload.content,
        authority_class=candidate.authority_class,
        visibility=candidate.visibility,
        subject_character_file_id=candidate.subject_character_file_id,
        source_kind=str(provenance.get("source_kind", "")),
        source_asset_id=str(provenance.get("source_asset_id", "")),
        provenance=provenance,
    )


def candidate_to_scope_record(candidate: RetrievalCandidate) -> ScopeKnowledgeRecord | None:
    from .scope_knowledge_repository import ScopeKnowledgeRecord

    if candidate.information_class not in _SCOPE_INFORMATION_CLASSES:
        return None
    legacy = candidate.host_internal_metadata.get("legacy_scope_record")
    if isinstance(legacy, dict):
        return ScopeKnowledgeRecord.from_dict(legacy)
    provenance = dict(candidate.provenance)
    return ScopeKnowledgeRecord(
        knowledge_id=candidate.candidate_id,
        scope_id=str(provenance.get("scope_id", "")),
        knowledge_kind=str(provenance.get("knowledge_lane", candidate.information_class)),
        content=candidate.payload.content,
        authority_class=candidate.authority_class,
        visibility=candidate.visibility,
        subject_character_file_id=candidate.subject_character_file_id,
        source_kind=str(provenance.get("source_kind", "")),
        provenance=provenance,
        created_at=str(candidate.temporal_metadata.get("created_at", "")),
        profile_key=candidate.host_internal_metadata.get("profile_key"),
        user_persona_id=candidate.host_internal_metadata.get("user_persona_id"),
    )
