"""Model-facing Plot Cognition update transport (#175).

Separates deterministic identity, stable semantic frame, and incremental change
evidence for LLM inference. Domain canonical_body remains authoritative for
fingerprinting, stale checks, and forensic capture.
"""

from __future__ import annotations

from typing import Any

from scene_grounding import rebuild_scene_grounding_from_continuity

from .plot_cognition_overlay_store import PlotCognitionOverlayStore
from .plot_cognition_semantic_authority import bounded_text
from .session_state import LiveSession
from .story_knowledge_contract import StoryKnowledgeRecord

MODEL_FACING_TRANSPORT_SCHEMA = "hg_plot_cognition_model_facing_transport_v1"
CONTEXTUAL_ANCHOR_RECENT_TURNS = 3


def _assimilated_through_commit(store: PlotCognitionOverlayStore) -> str | None:
    return str(store.assimilated_through_domain_commit_id or "").strip() or None


def _assimilated_authority_fingerprint(store: PlotCognitionOverlayStore) -> str | None:
    authority = store.assimilated_authority
    if authority is None or not authority.sessions:
        return None
    return str(authority.sessions[0].authority_source_fingerprint or "").strip() or None


def _issue_fingerprints_at_commit(
    fixture: LiveSession,
    story_records: list[StoryKnowledgeRecord] | None,
    through_domain_commit_id: str | None,
) -> dict[str, str]:
    from .plot_cognition_update_sources import build_plot_cognition_authority_projection

    body = build_plot_cognition_authority_projection(
        fixture,
        story_records,
        through_domain_commit_id,
    )
    return {
        str(item.get("issue_id", "")): str(item.get("material_fingerprint", ""))
        for item in (body.get("continuity", {}).get("issues") or [])
        if str(item.get("issue_id", "")).strip()
    }


def _grounding_fact_map(fixture: LiveSession) -> dict[str, str]:
    grounding = rebuild_scene_grounding_from_continuity(fixture.manager)
    facts: dict[str, str] = {}
    for item in grounding.get("facts") or []:
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get("fact_id", "")).strip()
        if not fact_id:
            continue
        facts[fact_id] = bounded_text(str(item.get("statement") or ""), max_chars=400)
    return facts


def _scene_state_frame(fixture: LiveSession) -> dict[str, Any]:
    from .plot_cognition_update_sources import _scene_state_digest

    digest = _scene_state_digest(fixture)
    mgr = fixture.manager
    scene_state = getattr(mgr, "scene_state", None)
    opening_description = ""
    if scene_state is not None:
        opening_description = bounded_text(
            str(getattr(scene_state, "opening_description", "") or ""),
            max_chars=400,
        )
    return {
        "location": digest.get("location", ""),
        "phase": digest.get("phase", ""),
        "current_tension_level": digest.get("current_tension_level", ""),
        "present_characters": list(digest.get("present_characters") or []),
        "offstage_characters": list(digest.get("offstage_characters") or []),
        "absent_but_relevant": list(digest.get("absent_but_relevant") or []),
        "opening_description": opening_description or None,
    }


def _incremental_public_events(
    excerpts: dict[str, Any],
    *,
    assimilated_turn: int | None,
    through_turn: int | None,
) -> list[dict[str, Any]]:
    incremental: list[dict[str, Any]] = []
    for event in excerpts.get("public_events") or []:
        if not isinstance(event, dict):
            continue
        turn_index = event.get("turn_index")
        if assimilated_turn is None:
            incremental.append(dict(event))
            continue
        if turn_index is None:
            incremental.append(dict(event))
            continue
        if int(turn_index) > int(assimilated_turn):
            incremental.append(dict(event))
    return incremental


def _incremental_committed_moves(
    excerpts: dict[str, Any],
    fixture: LiveSession,
    assimilated_commit: str | None,
) -> list[dict[str, Any]]:
    from .plot_cognition_update_sources import _commit_lineage_index

    assimilated_index = _commit_lineage_index(fixture, assimilated_commit)
    incremental: list[dict[str, Any]] = []
    for move in excerpts.get("committed_moves") or []:
        if not isinstance(move, dict):
            continue
        commit_id = str(move.get("domain_commit_id") or "").strip()
        if not commit_id:
            continue
        if assimilated_commit is None:
            incremental.append(dict(move))
            continue
        move_index = _commit_lineage_index(fixture, commit_id)
        if move_index is None or assimilated_index is None:
            incremental.append(dict(move))
            continue
        if move_index > assimilated_index:
            incremental.append(dict(move))
    return incremental


def _incremental_changed_issues(
    fixture: LiveSession,
    story_records: list[StoryKnowledgeRecord] | None,
    excerpts: dict[str, Any],
    assimilated_commit: str | None,
) -> list[dict[str, Any]]:
    if assimilated_commit is None:
        return []
    prior_fingerprints = _issue_fingerprints_at_commit(fixture, story_records, assimilated_commit)
    current_fingerprints = _issue_fingerprints_at_commit(fixture, story_records, None)
    changed: list[dict[str, Any]] = []
    issue_by_id = {
        str(item.get("issue_id", "")): item
        for item in (excerpts.get("issues") or [])
        if isinstance(item, dict)
    }
    for issue_id, current_fp in current_fingerprints.items():
        prior_fp = prior_fingerprints.get(issue_id)
        if prior_fp is None or prior_fp != current_fp:
            issue_excerpt = issue_by_id.get(issue_id)
            if issue_excerpt is not None:
                changed.append(dict(issue_excerpt))
    return changed


def _incremental_grounding_changes(
    fixture: LiveSession,
    assimilated_commit: str | None,
) -> list[dict[str, Any]]:
    current_facts = _grounding_fact_map(fixture)
    if assimilated_commit is None:
        return [
            {"fact_id": fact_id, "statement": statement}
            for fact_id, statement in sorted(current_facts.items())
        ]
    from .plot_cognition_update_sources import (
        _digest_text,
        build_plot_cognition_authority_projection,
    )

    prior_body = build_plot_cognition_authority_projection(fixture, None, assimilated_commit)
    prior_digest_map = {
        str(item.get("fact_id", "")): str(item.get("statement_digest", ""))
        for item in (
            (prior_body.get("continuity", {}).get("scene_grounding") or {}).get("facts") or []
        )
        if str(item.get("fact_id", "")).strip()
    }
    changes: list[dict[str, Any]] = []
    for fact_id, statement in sorted(current_facts.items()):
        prior_digest = prior_digest_map.get(fact_id)
        if prior_digest is None:
            changes.append({"fact_id": fact_id, "statement": statement, "change_kind": "added"})
            continue
        if prior_digest != _digest_text(statement):
            changes.append({"fact_id": fact_id, "statement": statement, "change_kind": "changed"})
    return changes


def _contextual_anchor_events(
    excerpts: dict[str, Any],
    *,
    active_issue_ids: set[str],
    assimilated_turn: int | None,
    through_turn: int | None,
    incremental_event_ids: set[str],
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    recent_floor = None
    if through_turn is not None:
        recent_floor = max(0, int(through_turn) - CONTEXTUAL_ANCHOR_RECENT_TURNS)
    for event in excerpts.get("public_events") or []:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id", "")).strip()
        if not event_id or event_id in incremental_event_ids:
            continue
        turn_index = event.get("turn_index")
        related_issue_ids = {
            str(item)
            for item in (event.get("related_issue_ids") or [])
            if str(item).strip()
        }
        linked_to_active_issue = bool(related_issue_ids & active_issue_ids)
        in_recent_window = (
            recent_floor is not None
            and turn_index is not None
            and int(turn_index) >= recent_floor
        )
        if linked_to_active_issue or in_recent_window:
            anchors.append(dict(event))
    return anchors


def _incremental_is_empty(incremental: dict[str, Any]) -> bool:
    for key in ("public_events", "committed_moves", "changed_issues", "grounding_changes"):
        if incremental.get(key):
            return False
    return True


def build_model_facing_transport(
    fixture: LiveSession,
    store: PlotCognitionOverlayStore,
    story_records: list[StoryKnowledgeRecord] | None,
    *,
    semantic_authority_excerpts: dict[str, Any],
    canonical_body: dict[str, Any],
    authority_source_fingerprint: str,
    snapshot_id: str,
    through_domain_commit_id: str | None,
    continuity_version: int,
    prior_store_revision: int,
    plot_cognition_scope_id: str,
) -> dict[str, Any]:
    """Build four-lane model-facing transport from authoritative snapshot parts."""
    assimilated_commit = _assimilated_through_commit(store)
    assimilated_fingerprint = _assimilated_authority_fingerprint(store)
    from .plot_cognition_update_sources import (
        _character_state_digest,
        _through_continuity_turn_index,
    )

    assimilated_turn = _through_continuity_turn_index(fixture, assimilated_commit)
    through_turn = _through_continuity_turn_index(fixture, through_domain_commit_id)

    active_issue_ids = {
        str(item.get("issue_id", ""))
        for item in (semantic_authority_excerpts.get("issues") or [])
        if isinstance(item, dict) and str(item.get("issue_id", "")).strip()
    }

    incremental_events = _incremental_public_events(
        semantic_authority_excerpts,
        assimilated_turn=assimilated_turn,
        through_turn=through_turn,
    )
    incremental_moves = _incremental_committed_moves(
        semantic_authority_excerpts,
        fixture,
        assimilated_commit,
    )
    incremental_issues = _incremental_changed_issues(
        fixture,
        story_records,
        semantic_authority_excerpts,
        assimilated_commit,
    )
    incremental_grounding = _incremental_grounding_changes(fixture, assimilated_commit)

    incremental_event_ids = {
        str(item.get("event_id", ""))
        for item in incremental_events
        if str(item.get("event_id", "")).strip()
    }
    incremental_move_ids = {
        str(item.get("domain_commit_id", ""))
        for item in incremental_moves
        if str(item.get("domain_commit_id", "")).strip()
    }

    incremental = {
        "public_events": incremental_events,
        "committed_moves": incremental_moves,
        "changed_issues": incremental_issues,
        "grounding_changes": incremental_grounding,
    }

    contextual_anchors = _contextual_anchor_events(
        semantic_authority_excerpts,
        active_issue_ids=active_issue_ids,
        assimilated_turn=assimilated_turn,
        through_turn=through_turn,
        incremental_event_ids=incremental_event_ids,
    )

    stable = {
        "scene_state": _scene_state_frame(fixture),
        "active_issues": list(semantic_authority_excerpts.get("issues") or []),
        "scene_grounding_facts": list(semantic_authority_excerpts.get("scene_grounding_facts") or []),
        "contextual_anchor_events": contextual_anchors,
        "character_states": _character_state_digest(fixture),
    }

    fail_safe_expanded = False
    fingerprint_changed = bool(
        assimilated_fingerprint
        and authority_source_fingerprint
        and assimilated_fingerprint != authority_source_fingerprint
    )
    if fingerprint_changed and _incremental_is_empty(incremental):
        fail_safe_expanded = True
        stable["supplemental_verbatim_authority"] = {
            "public_events": list(semantic_authority_excerpts.get("public_events") or []),
            "committed_moves": list(semantic_authority_excerpts.get("committed_moves") or []),
        }

    return {
        "schema": MODEL_FACING_TRANSPORT_SCHEMA,
        "deterministic_identity": {
            "authority_source_fingerprint": authority_source_fingerprint,
            "snapshot_id": snapshot_id,
            "through_domain_commit_id": through_domain_commit_id,
            "assimilated_through_domain_commit_id": assimilated_commit,
            "continuity_version": continuity_version,
            "prior_store_revision": prior_store_revision,
            "plot_cognition_scope_id": plot_cognition_scope_id,
        },
        "stable_semantic_frame": stable,
        "incremental_change_evidence": incremental,
        "fail_safe_expanded": fail_safe_expanded,
        "transport_policy": {
            "contextual_anchor_recent_turns": CONTEXTUAL_ANCHOR_RECENT_TURNS,
            "deduplicated_incremental_event_ids": sorted(incremental_event_ids),
            "deduplicated_incremental_move_ids": sorted(incremental_move_ids),
        },
    }
