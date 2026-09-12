"""Update source snapshot gathering and authority projection for Plot Cognition (#61)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_scene_pressure_projection import (  # noqa: E402
    compute_issue_material_fingerprint,
    get_projectable_issue_pressure_overlay,
)
from scene_grounding import rebuild_scene_grounding_from_continuity  # noqa: E402

from .plot_cognition_model_facing_transport import build_model_facing_transport
from .plot_cognition_semantic_authority import build_semantic_authority_excerpts
from .plot_cognition_overlay_store import (
    AssimilatedAuthority,
    AssimilatedSessionAuthority,
    PlotCognitionOverlayStore,
)
from .plot_cognition_update_contract import (
    UPDATE_SOURCE_SNAPSHOT_SCHEMA,
    CatchUpMode,
    CognitionUpdateSourceSnapshot,
    ContributorAuthoritySnapshot,
    new_snapshot_id,
)
from .narrator_environment_contract import (
    ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
    ENVIRONMENTAL_DESCRIPTOR_MARKER,
    parse_environmental_descriptor_payload,
)
from .session_state import LiveSession
from .story_knowledge_contract import StoryKnowledgeRecord


def _digest_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_json(value: Any) -> str:
    if value is None:
        return ""
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _scene_state_digest(fixture: LiveSession) -> dict[str, Any]:
    mgr = fixture.manager
    scene_state = getattr(mgr, "scene_state", None)
    if scene_state is None:
        return {}
    return {
        "location": str(getattr(scene_state, "location", "") or ""),
        "opening_description_digest": _digest_text(
            getattr(scene_state, "opening_description", "")
        ),
        "present_characters": sorted(
            str(name)
            for name in (getattr(scene_state, "present_characters", None) or fixture.cast)
        ),
        "offstage_characters": sorted(
            str(name) for name in (getattr(scene_state, "offstage_characters", None) or [])
        ),
        "absent_but_relevant": sorted(
            str(name) for name in (getattr(scene_state, "absent_but_relevant", None) or [])
        ),
        "phase": str(getattr(getattr(scene_state, "phase", None), "value", scene_state.phase)),
        "current_tension_level": str(getattr(scene_state, "current_tension_level", "") or ""),
        "role_assignments_digest": _digest_json(getattr(scene_state, "role_assignments", {}) or {}),
    }


def _issue_digest(fixture: LiveSession) -> list[dict[str, Any]]:
    mgr = fixture.manager
    issues = getattr(mgr, "issues", {}) or {}
    active_ids = list(getattr(mgr.scene_state, "active_issue_ids", None) or [])
    entries: list[dict[str, Any]] = []
    for issue_id in sorted(active_ids):
        issue = issues.get(issue_id)
        if issue is None:
            continue
        overlay = get_projectable_issue_pressure_overlay(mgr, str(issue_id))
        entry: dict[str, Any] = {
            "issue_id": str(issue.issue_id),
            "status": str(getattr(issue.status, "value", issue.status)),
            "participants": sorted(str(item) for item in (issue.participants or [])),
            "pressure_kind": str(getattr(issue, "pressure_kind", "") or ""),
            "description_digest": _digest_text(getattr(issue, "description", "")),
            "blocked_what_digest": _digest_text(getattr(issue, "blocked_what", "")),
            "required_next_step_digest": _digest_text(getattr(issue, "required_next_step", "")),
            "material_fingerprint": compute_issue_material_fingerprint(issue),
        }
        if overlay is not None:
            entry["librarian_overlay_digest"] = _digest_json(
                {
                    "semantic_unmet_condition": overlay.get("semantic_unmet_condition"),
                    "semantic_authority": overlay.get("semantic_authority"),
                }
            )
        entries.append(entry)
    return entries


def _through_continuity_turn_index(
    fixture: LiveSession,
    through_domain_commit_id: str | None,
) -> int | None:
    target = str(through_domain_commit_id or "").strip() or None
    if target is None:
        return None
    for rnd in fixture.rounds:
        for turn in rnd.character_turns:
            if str(turn.domain_commit_id or "") == target:
                return int(turn.continuity_turn_index)
        if str(rnd.domain_commit_id or "") == target and rnd.continuity_turn_index is not None:
            return int(rnd.continuity_turn_index)
    for entry in reversed(fixture.rp_history):
        if entry.get("kind") != "committed_turn":
            continue
        if str(entry.get("domain_commit_id") or "") != target:
            continue
        meta = dict(entry.get("metadata") or {})
        turn_index = meta.get("continuity_turn_index")
        if turn_index is not None:
            return int(turn_index)
    return None


def _public_event_digest(fixture: LiveSession, *, through_domain_commit_id: str | None) -> list[dict[str, Any]]:
    mgr = fixture.manager
    through_turn = _through_continuity_turn_index(fixture, through_domain_commit_id)
    entries: list[dict[str, Any]] = []
    for event in getattr(mgr, "public_events", []) or []:
        event_id = str(getattr(event, "event_id", "") or "")
        turn_index = getattr(event, "turn_index", None)
        if through_turn is not None and turn_index is not None and int(turn_index) > through_turn:
            continue
        entries.append(
            {
                "event_id": event_id,
                "turn_index": turn_index,
                "event_type": str(getattr(event, "event_type", "") or ""),
                "summary_digest": _digest_text(getattr(event, "summary", "")),
                "participants": sorted(str(item) for item in (getattr(event, "participants", None) or [])),
                "related_issue_ids": sorted(
                    str(item) for item in (getattr(event, "related_issue_ids", None) or [])
                ),
                "significance": str(getattr(event, "significance", "") or ""),
                "revelation_significance_digest": _digest_json(
                    getattr(event, "revelation_significance_by_character", None)
                ),
            }
        )
    return sorted(entries, key=lambda item: (item.get("turn_index") or 0, str(item.get("event_id", ""))))


def _character_state_digest(fixture: LiveSession) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for display_name in sorted(fixture.cast):
        state = fixture.character_states.get(display_name)
        if state is None:
            continue
        entries.append(
            {
                "character_id": display_name,
                "long_term_goal_digest": _digest_text(getattr(state, "long_term_goal", "")),
                "medium_term_goal_digest": _digest_text(getattr(state, "medium_term_goal", "")),
                "core_goals_digest": _digest_json(getattr(state, "core_goals", [])),
                "relationships_digest": _digest_json(getattr(state, "relationships", {})),
                "circumstances_digest": _digest_text(getattr(state, "circumstances", "")),
            }
        )
    return entries


def _scene_grounding_digest(fixture: LiveSession) -> dict[str, Any]:
    grounding = rebuild_scene_grounding_from_continuity(fixture.manager)
    facts = [
        {
            "fact_id": str(item.get("fact_id", "")),
            "statement_digest": _digest_text(item.get("statement")),
            "binding_digest": _digest_json(item.get("binding")),
        }
        for item in (grounding.get("facts") or [])
        if isinstance(item, dict)
    ]
    return {
        "schema_version": grounding.get("schema_version"),
        "last_rebuilt_turn": grounding.get("last_rebuilt_turn"),
        "facts": sorted(facts, key=lambda item: str(item.get("fact_id", ""))),
    }


def _commit_lineage_index(fixture: LiveSession, through_domain_commit_id: str | None) -> int | None:
    target = str(through_domain_commit_id or "").strip() or None
    if target is None:
        return None
    commit_ids = list(fixture.commit_ids)
    if target in commit_ids:
        return commit_ids.index(target)
    return None


def _committed_move_digests(
    fixture: LiveSession,
    *,
    through_domain_commit_id: str | None,
) -> list[dict[str, Any]]:
    target = str(through_domain_commit_id or "").strip() or None
    entries: list[dict[str, Any]] = []
    for rnd in fixture.rounds:
        for turn in rnd.character_turns:
            commit_id = str(turn.domain_commit_id or "").strip()
            if not commit_id:
                continue
            entries.append(
                {
                    "domain_commit_id": commit_id,
                    "character_id": turn.character_id,
                    "continuity_turn_index": turn.continuity_turn_index,
                    "move_digest": _digest_json(turn.committed_move),
                    "director_decision_digest": _digest_json(turn.director_decision),
                }
            )
        if rnd.domain_commit_id and not rnd.character_turns:
            entries.append(
                {
                    "domain_commit_id": str(rnd.domain_commit_id),
                    "character_id": rnd.committed_character_id,
                    "continuity_turn_index": rnd.continuity_turn_index,
                    "move_digest": _digest_json(rnd.committed_move),
                    "director_decision_digest": _digest_json(rnd.director_decision),
                }
            )
    if target is None:
        return entries
    filtered: list[dict[str, Any]] = []
    for item in entries:
        filtered.append(item)
        if item["domain_commit_id"] == target:
            break
    return filtered


def _is_accepted_b2_record(record: StoryKnowledgeRecord) -> bool:
    if record.record_kind != "derived":
        return False
    if record.event_type != ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE and (
        ENVIRONMENTAL_DESCRIPTOR_MARKER not in list(record.grounding_markers or [])
    ):
        return False
    authority = record.epistemic_authority_ref
    if authority is None:
        return False
    return str(authority.ref_kind) == "establishment_decision"


def _is_k2_occurrence_duplicate(record: StoryKnowledgeRecord) -> bool:
    if record.record_kind != "occurrence":
        return False
    projection = record.evidence_projection
    if projection is None:
        return False
    return bool(str(projection.source_event_id or "").strip())


def _story_derived_b2_digest(
    story_records: list[StoryKnowledgeRecord] | None,
    *,
    through_domain_commit_id: str | None,
    lineage_commit_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not story_records:
        return []
    target = str(through_domain_commit_id or "").strip() or None
    commit_ids = list(lineage_commit_ids or [])
    allowed_commits = set(_lineage_prefix(commit_ids, target)) if target is not None else None
    entries: list[dict[str, Any]] = []
    for record in story_records:
        if _is_k2_occurrence_duplicate(record):
            continue
        if not _is_accepted_b2_record(record):
            continue
        commit_id = str(record.source_domain_commit_id or "").strip()
        if allowed_commits is not None and commit_id and commit_id not in allowed_commits:
            continue
        payload = parse_environmental_descriptor_payload(record.evidence.committed_text)
        if payload is None:
            continue
        entries.append(
            {
                "story_record_id": str(record.story_record_id or ""),
                "source_domain_commit_id": commit_id,
                "property_key": str(payload.get("property_key", "")),
                "value_digest": _digest_text(payload.get("value")),
                "stable_refs": sorted(ref.stable_ref for ref in record.stable_refs),
                "supersedes": str(payload.get("supersedes", "") or "") or None,
            }
        )
    return sorted(entries, key=lambda item: str(item.get("story_record_id", "")))


def _lineage_prefix(commit_ids: list[str], target: str) -> list[str]:
    if target in commit_ids:
        return commit_ids[: commit_ids.index(target) + 1]
    return commit_ids


def build_plot_cognition_authority_projection(
    fixture: LiveSession,
    story_records: list[StoryKnowledgeRecord] | None,
    through_domain_commit_id: str | None,
) -> dict[str, Any]:
    """Deterministic Plot-Cognition-relevant authoritative projection body."""
    return {
        "plot_cognition_scope_id": str(fixture.plot_cognition_scope_id or ""),
        "hg_scene_id": fixture.hg_scene_id,
        "through_domain_commit_id": through_domain_commit_id,
        "continuity": {
            "scene_state": _scene_state_digest(fixture),
            "issues": _issue_digest(fixture),
            "public_events": _public_event_digest(
                fixture,
                through_domain_commit_id=through_domain_commit_id,
            ),
            "scene_grounding": _scene_grounding_digest(fixture),
        },
        "character_states": _character_state_digest(fixture),
        "committed_moves": _committed_move_digests(
            fixture,
            through_domain_commit_id=through_domain_commit_id,
        ),
        "story_knowledge_b2_environmental": _story_derived_b2_digest(
            story_records,
            through_domain_commit_id=through_domain_commit_id,
            lineage_commit_ids=list(fixture.commit_ids),
        ),
    }


def compute_authority_source_fingerprint(canonical_body: dict[str, Any]) -> str:
    payload = json.dumps(canonical_body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _current_domain_commit_id(fixture: LiveSession) -> str | None:
    if fixture.commit_ids:
        return str(fixture.commit_ids[-1])
    for rnd in reversed(fixture.rounds):
        if rnd.domain_commit_id:
            return str(rnd.domain_commit_id)
        for turn in reversed(rnd.character_turns):
            if turn.domain_commit_id:
                return str(turn.domain_commit_id)
    return None


def _contributor_snapshots_from_store(
    store: PlotCognitionOverlayStore,
) -> tuple[ContributorAuthoritySnapshot, ...]:
    authority = store.assimilated_authority
    if authority is None:
        return ()
    return tuple(
        ContributorAuthoritySnapshot(
            hg_scene_id=session.hg_scene_id,
            through_domain_commit_id=session.through_domain_commit_id,
            through_continuity_version=session.through_continuity_version,
            authority_source_fingerprint=session.authority_source_fingerprint,
        )
        for session in authority.sessions
    )


def gather_update_source_snapshot(
    fixture: LiveSession,
    store: PlotCognitionOverlayStore,
    story_records: list[StoryKnowledgeRecord] | None,
    contributors: tuple[str, ...],
    *,
    catch_up_mode: CatchUpMode = "sequential",
    evidence_gap: bool = False,
    evidence_gap_detail: str | None = None,
) -> CognitionUpdateSourceSnapshot:
    through_commit = _current_domain_commit_id(fixture)
    canonical_body = build_plot_cognition_authority_projection(
        fixture,
        story_records,
        through_commit,
    )
    fingerprint = compute_authority_source_fingerprint(canonical_body)
    semantic_authority_excerpts = build_semantic_authority_excerpts(
        fixture,
        through_domain_commit_id=through_commit,
    )
    from .plot_cognition_forensics_capture import bounded_prior_operative_cognition

    prior_operative_cognition = bounded_prior_operative_cognition(store)
    snapshot_id = new_snapshot_id()
    model_facing_transport = build_model_facing_transport(
        fixture,
        store,
        story_records,
        semantic_authority_excerpts=semantic_authority_excerpts,
        canonical_body=canonical_body,
        authority_source_fingerprint=fingerprint,
        snapshot_id=snapshot_id,
        through_domain_commit_id=through_commit,
        continuity_version=int(fixture.continuity_version),
        prior_store_revision=int(store.store_revision),
        plot_cognition_scope_id=str(fixture.plot_cognition_scope_id or ""),
    )
    contributor_bodies: list[dict[str, Any]] = []
    for scene_id in contributors:
        if scene_id != fixture.hg_scene_id:
            continue
        contributor_bodies.append(
            {
                "hg_scene_id": scene_id,
                "through_domain_commit_id": through_commit,
                "through_continuity_version": int(fixture.continuity_version),
                "authority_source_fingerprint": fingerprint,
            }
        )
    if not contributor_bodies and fixture.hg_scene_id:
        contributor_bodies.append(
            {
                "hg_scene_id": fixture.hg_scene_id,
                "through_domain_commit_id": through_commit,
                "through_continuity_version": int(fixture.continuity_version),
                "authority_source_fingerprint": fingerprint,
            }
        )
    return CognitionUpdateSourceSnapshot(
        schema=UPDATE_SOURCE_SNAPSHOT_SCHEMA,
        snapshot_id=snapshot_id,
        plot_cognition_scope_id=str(fixture.plot_cognition_scope_id or ""),
        prior_store_revision=int(store.store_revision),
        prior_assimilated_authority=_contributor_snapshots_from_store(store),
        contributors=tuple(contributors) if contributors else (fixture.hg_scene_id,),
        through_domain_commit_id=through_commit,
        continuity_version=int(fixture.continuity_version),
        authority_source_fingerprint=fingerprint,
        committed_move_refs=tuple(
            str(item.get("domain_commit_id", ""))
            for item in canonical_body.get("committed_moves", [])
            if str(item.get("domain_commit_id", "")).strip()
        ),
        catch_up_mode=catch_up_mode,
        evidence_gap=evidence_gap,
        evidence_gap_detail=evidence_gap_detail,
        canonical_body=canonical_body,
        semantic_authority_excerpts=semantic_authority_excerpts,
        prior_operative_cognition=prior_operative_cognition,
        model_facing_transport=model_facing_transport,
    )


def build_assimilated_authority_from_snapshot(
    snapshot: CognitionUpdateSourceSnapshot,
) -> AssimilatedAuthority:
    sessions = tuple(
        AssimilatedSessionAuthority(
            hg_scene_id=item.hg_scene_id,
            through_domain_commit_id=item.through_domain_commit_id,
            through_continuity_version=item.through_continuity_version,
            authority_source_fingerprint=item.authority_source_fingerprint,
        )
        for item in snapshot.contributor_authority_targets()
    )
    return AssimilatedAuthority(
        schema="hg_plot_cognition_assimilated_authority_v1",
        sessions=sessions,
    )
