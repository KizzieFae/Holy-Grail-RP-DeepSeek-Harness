"""Project committed PublicEvents into searchable story-knowledge records (#50)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .story_knowledge_contract import (
    STORY_KNOWLEDGE_SCHEMA_VERSION,
    EstablishmentEpistemic,
    StableRef,
    StoryEvidence,
    StoryEvidenceProjectionProvenance,
    StoryKnowledgeRecord,
)
from .session_state import LiveSession

try:
    from continuity_state_occurrence_evidence import (
        OccurrenceEvidence,
        globally_embeddable_occurrence_text,
        globally_projected_source_manifest,
        parse_occurrence_evidence,
    )
except ImportError:  # pragma: no cover - domain path bootstrap in tests
    OccurrenceEvidence = None  # type: ignore[misc, assignment]
    globally_embeddable_occurrence_text = None  # type: ignore[assignment]
    globally_projected_source_manifest = None  # type: ignore[assignment]
    parse_occurrence_evidence = None  # type: ignore[assignment]

_CONTEXT_LINES = 3


def _grounding_markers_to_stable_refs(markers: list[str]) -> list[StableRef]:
    refs: list[StableRef] = []
    for marker in markers:
        token = str(marker or "").strip()
        if not token:
            continue
        parts = token.split(":", 1)
        if len(parts) == 2:
            refs.append(StableRef(ref_kind=parts[0], stable_ref=token, display_hint=parts[1]))
        else:
            refs.append(StableRef(ref_kind="grounding", stable_ref=token))
    return refs


def _transcript_context(fixture: LiveSession, *, turn_index: int | None) -> tuple[str, str]:
    if turn_index is None:
        return "", ""
    before: list[str] = []
    after: list[str] = []
    for entry in fixture.rp_history:
        meta = dict(entry.get("metadata") or {})
        entry_turn = meta.get("continuity_turn_index")
        if entry_turn is None:
            continue
        try:
            idx = int(entry_turn)
        except (TypeError, ValueError):
            continue
        content = str(entry.get("content", "") or "").strip()
        if not content:
            continue
        if idx < turn_index:
            before.append(content)
        elif idx > turn_index:
            after.append(content)
    return (
        "\n".join(before[-_CONTEXT_LINES:]),
        "\n".join(after[:_CONTEXT_LINES]),
    )


def _occurrence_evidence_from_event(event: Any) -> OccurrenceEvidence | None:
    raw = getattr(event, "occurrence_evidence", None)
    if raw is not None and hasattr(raw, "contributions"):
        return raw
    if parse_occurrence_evidence is None:
        return None
    data = raw if isinstance(raw, dict) else None
    if data is None and hasattr(event, "to_dict"):
        payload = event.to_dict()
        data = payload.get("occurrence_evidence") if isinstance(payload, dict) else None
    return parse_occurrence_evidence(data if isinstance(data, dict) else None)


def _committed_text_from_public_event(event: Any, *, summary: str) -> str:
    evidence = _occurrence_evidence_from_event(event)
    if globally_embeddable_occurrence_text is not None:
        return globally_embeddable_occurrence_text(
            summary=summary,
            occurrence_evidence=evidence,
        )
    return summary


def project_occurrence_from_public_event(
    fixture: LiveSession,
    event: Any,
    *,
    source_domain_commit_id: str,
) -> StoryKnowledgeRecord | None:
    event_id = str(getattr(event, "event_id", "") or "").strip()
    if not event_id:
        return None
    scope_id = str(getattr(fixture, "memory_scope_id", "") or "").strip()
    if not scope_id:
        return None

    summary = str(getattr(event, "summary", "") or "").strip()
    evidence = _occurrence_evidence_from_event(event)
    committed_text = _committed_text_from_public_event(event, summary=summary)
    projection_raw: dict[str, Any] | None = None
    if globally_projected_source_manifest is not None:
        projection_raw = globally_projected_source_manifest(
            event_id=event_id,
            summary=summary,
            occurrence_evidence=evidence,
        )
    evidence_projection = (
        StoryEvidenceProjectionProvenance.from_dict(projection_raw)
        if projection_raw is not None
        else None
    )
    turn_index = getattr(event, "turn_index", None)
    context_before, context_after = _transcript_context(fixture, turn_index=turn_index)
    known_by = [str(x) for x in list(getattr(event, "known_by", []) or []) if str(x).strip()]
    routes: dict[str, str] = {}
    for name in known_by:
        level = None
        if hasattr(event, "knowledge_level_for"):
            level = event.knowledge_level_for(name)
        if level:
            routes[name] = str(level)

    markers = [str(x) for x in list(getattr(event, "grounding_markers", []) or []) if str(x).strip()]
    record = StoryKnowledgeRecord(
        schema_version=STORY_KNOWLEDGE_SCHEMA_VERSION,
        record_kind="occurrence",
        memory_scope_id=scope_id,
        source_session_id=str(fixture.hg_session_id),
        source_domain_commit_id=source_domain_commit_id,
        hg_scene_id=str(fixture.hg_scene_id),
        turn_index=int(turn_index) if turn_index is not None else None,
        event_type=str(getattr(event, "event_type", "") or "") or None,
        participants=[str(x) for x in list(getattr(event, "participants", []) or [])],
        location=getattr(event, "location", None),
        stable_refs=_grounding_markers_to_stable_refs(markers),
        grounding_markers=markers,
        evidence=StoryEvidence(
            summary=summary or None,
            committed_text=committed_text,
            context_before=context_before,
            context_after=context_after,
        ),
        establishment_epistemic=EstablishmentEpistemic(known_by_at_commit=tuple(known_by), routes=routes),
        event_id=event_id,
        written_at=datetime.now(UTC).isoformat(),
        evidence_projection=evidence_projection,
    )
    record.content_hash = record.compute_content_hash()
    return record


def project_missing_occurrences(
    fixture: LiveSession,
    *,
    source_domain_commit_id: str,
    event_ids: list[str] | None = None,
) -> list[StoryKnowledgeRecord]:
    projected: list[StoryKnowledgeRecord] = []
    targets = set(event_ids or [])
    for event in list(getattr(fixture.manager, "public_events", []) or []):
        eid = str(getattr(event, "event_id", "") or "").strip()
        if not eid:
            continue
        if targets and eid not in targets:
            continue
        record = project_occurrence_from_public_event(
            fixture,
            event,
            source_domain_commit_id=source_domain_commit_id,
        )
        if record is not None:
            projected.append(record)
    return projected
