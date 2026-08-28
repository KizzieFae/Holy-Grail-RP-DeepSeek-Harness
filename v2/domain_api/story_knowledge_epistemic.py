"""Live epistemic eligibility for story knowledge records (#50)."""

from __future__ import annotations

from .session_state import LiveSession
from .story_knowledge_contract import EpistemicAuthorityRef, StoryKnowledgeRecord


def _event_knowable(fixture: LiveSession, event_id: str, viewer_character_id: str | None) -> bool:
    if not viewer_character_id:
        return True
    for event in getattr(fixture.manager, "public_events", []) or []:
        if str(getattr(event, "event_id", "") or "") != event_id:
            continue
        if hasattr(event, "knowledge_level_for"):
            return event.knowledge_level_for(viewer_character_id) is not None
        known_by = list(getattr(event, "known_by", []) or [])
        return viewer_character_id in known_by
    return False


def resolve_epistemic_authority_ref(
    fixture: LiveSession,
    authority_ref: EpistemicAuthorityRef,
    *,
    viewer_character_id: str | None,
    viewer_role: str | None = None,
) -> bool:
    kind = authority_ref.ref_kind
    payload = dict(authority_ref.ref_payload or {})

    if kind == "orchestration_visibility":
        allowed_roles = {str(x) for x in payload.get("allowed_viewer_roles", []) if str(x).strip()}
        if not allowed_roles:
            return viewer_role in {"orchestration", "narrator", "host_internal"}
        return (viewer_role or "") in allowed_roles

    if kind == "establishment_decision":
        decision_id = str(payload.get("decision_id", "") or "").strip()
        if not decision_id:
            return False
        allowed_viewers = {str(x) for x in payload.get("allowed_viewers", []) if str(x).strip()}
        if allowed_viewers and viewer_character_id:
            return viewer_character_id in allowed_viewers
        if payload.get("orchestration_only"):
            return viewer_role in {"orchestration", "narrator", "host_internal"}
        return bool(payload.get("authorized", False))

    if kind == "inherit_source_events":
        event_ids = [str(x) for x in payload.get("event_ids", []) if str(x).strip()]
        if not event_ids:
            return False
        inherit_mode = str(payload.get("inherit_mode", "explicit") or "explicit")
        if inherit_mode == "explicit":
            return bool(payload.get("viewer_authorized", False))
        if inherit_mode == "all_source_events_known":
            if not viewer_character_id:
                return True
            return all(_event_knowable(fixture, event_id, viewer_character_id) for event_id in event_ids)
        return False

    return False


def story_record_epistemically_eligible(
    fixture: LiveSession,
    record: StoryKnowledgeRecord,
    *,
    viewer_character_id: str | None,
    viewer_role: str | None = None,
) -> bool:
    if record.record_kind == "occurrence":
        event_id = str(record.event_id or "").strip()
        if not event_id:
            return False
        return _event_knowable(fixture, event_id, viewer_character_id)

    if record.epistemic_authority_ref is not None:
        return resolve_epistemic_authority_ref(
            fixture,
            record.epistemic_authority_ref,
            viewer_character_id=viewer_character_id,
            viewer_role=viewer_role,
        )

    return False
