from datetime import datetime
from typing import Any, Optional

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    ContinuitySnapshot,
    ExcursionRecord,
    IssueState,
    PublicEvent,
    ResolvedOutcome,
    ScenePhase,
    SceneState,
    SummaryBlock,
)


def serialize_manager_state(*, manager: Any) -> dict[str, Any]:
    return {
        "scene_state": manager.scene_state.to_dict() if manager.scene_state else None,
        "issues": {
            issue_id: issue.to_dict() for issue_id, issue in manager.issues.items()
        },
        "public_events": [event.to_dict() for event in manager.public_events],
        "resolved_outcomes": [
            outcome.to_dict() for outcome in getattr(manager, "resolved_outcomes", [])
        ],
        "interpretations": {
            name: [item.to_dict() for item in items]
            for name, items in manager.interpretations.items()
        },
        "canon_anchors": [anchor.to_dict() for anchor in manager.canon_anchors],
        "summary_blocks": [summary.to_dict() for summary in manager.summary_blocks],
        "event_counter": manager.event_counter,
        "summary_counter": manager.summary_counter,
        "turn_counter": manager.turn_counter,
        "last_summarized_event_index": manager.last_summarized_event_index,
        "summary_interval": manager.summary_interval,
        "recent_event_window": manager.recent_event_window,
        "turn_metadata_by_index": {
            str(k): v for k, v in manager.turn_metadata_by_index.items()
        },
        "anchor_character_id": getattr(manager, "anchor_character_id", None),
        "setup_seam_complete": bool(
            getattr(manager, "setup_seam_complete", False)
        ),
        "excursions": {
            eid: rec.to_dict()
            for eid, rec in getattr(manager, "excursions", {}).items()
        },
    }


def restore_manager_state(
    *,
    manager_cls,
    data: dict[str, Any],
    default_summary_interval: int,
    default_recent_event_window: int,
):
    manager = manager_cls(
        summary_interval=int(data.get("summary_interval", default_summary_interval)),
        recent_event_window=int(
            data.get("recent_event_window", default_recent_event_window)
        ),
    )
    scene_state = data.get("scene_state")
    manager.scene_state = (
        SceneState.from_dict(scene_state) if isinstance(scene_state, dict) else None
    )
    manager.issues = {
        str(issue_id): IssueState.from_dict(issue_data)
        for issue_id, issue_data in data.get("issues", {}).items()
        if isinstance(issue_data, dict)
    }
    manager.public_events = [
        PublicEvent.from_dict(event_data)
        for event_data in data.get("public_events", [])
        if isinstance(event_data, dict)
    ]
    manager.resolved_outcomes = [
        ResolvedOutcome.from_dict(outcome_data)
        for outcome_data in data.get("resolved_outcomes", [])
        if isinstance(outcome_data, dict)
    ]
    manager.interpretations = {
        str(name): [
            CharacterInterpretation.from_dict(item)
            for item in items
            if isinstance(item, dict)
        ]
        for name, items in data.get("interpretations", {}).items()
        if isinstance(items, list)
    }
    manager.canon_anchors = [
        CanonAnchor.from_dict(anchor_data)
        for anchor_data in data.get("canon_anchors", [])
        if isinstance(anchor_data, dict)
    ]
    manager.summary_blocks = [
        SummaryBlock.from_dict(summary_data)
        for summary_data in data.get("summary_blocks", [])
        if isinstance(summary_data, dict)
    ]
    manager.event_counter = int(data.get("event_counter", len(manager.public_events)))
    manager.summary_counter = int(
        data.get("summary_counter", len(manager.summary_blocks))
    )
    manager.turn_counter = int(data.get("turn_counter", manager.event_counter))
    manager.last_summarized_event_index = int(
        data.get("last_summarized_event_index", 0)
    )
    manager.turn_metadata_by_index = {
        int(k): v
        for k, v in data.get("turn_metadata_by_index", {}).items()
        if isinstance(v, dict)
    }
    _raw_anchor = data.get("anchor_character_id")
    manager.anchor_character_id = (
        str(_raw_anchor).strip()
        if _raw_anchor is not None and str(_raw_anchor).strip()
        else None
    )
    manager.setup_seam_complete = bool(data.get("setup_seam_complete", False))
    raw_excursions = data.get("excursions")
    if isinstance(raw_excursions, dict):
        manager.excursions = {
            str(eid): ExcursionRecord.from_dict(rec)
            for eid, rec in raw_excursions.items()
            if isinstance(rec, dict)
        }
    else:
        manager.excursions = {}
    return manager


def initialize_scene_state(
    *,
    manager: Any,
    location: Optional[str],
    opening_description: str,
    present_characters: list[str],
    initial_issues: Optional[list[IssueState]] = None,
) -> None:
    manager.scene_state = SceneState(
        location=location,
        opening_description=opening_description,
        present_characters=present_characters[:],
        phase=ScenePhase.OPENING,
        current_tension_level="low",
    )
    manager.issues = {}
    manager.public_events = []
    manager.resolved_outcomes = []
    manager.interpretations = {name: [] for name in present_characters}
    manager.event_counter = 0
    manager.summary_blocks = []
    manager.summary_counter = 0
    manager.turn_counter = 0
    manager.last_summarized_event_index = 0

    if initial_issues:
        for issue in initial_issues:
            manager.issues[issue.issue_id] = issue
            manager.scene_state.active_issue_ids.append(issue.issue_id)

    manager.anchor_character_id = None
    manager.setup_seam_complete = False
    manager.excursions = {}


def build_snapshot(
    *, manager: Any, timestamp: Optional[datetime], normalize_timestamp_fn
) -> ContinuitySnapshot:
    normalized_timestamp = normalize_timestamp_fn(timestamp)
    active_issues = manager.get_active_issues(limit=0)
    recent_events = manager.retrieve_public_events(limit=manager.recent_event_window)
    return ContinuitySnapshot(
        scene_state=manager.scene_state or SceneState(),
        active_issues=active_issues,
        recent_public_events=recent_events,
        character_interpretations=manager.interpretations,
        canon_anchors=manager.canon_anchors,
        summary_blocks=manager.summary_blocks[:],
        snapshot_at=normalized_timestamp,
    )


def build_character_context(
    *,
    manager: Any,
    character_name: str,
    max_interpretations: int,
    default_active_issue_limit: int,
    default_summary_prompt_limit: int,
) -> dict[str, Any]:
    snapshot = manager.get_snapshot()
    character_interps = [
        item for item in manager.interpretations.get(character_name, [])
    ][-max_interpretations:]
    known_events = manager.retrieve_public_events(
        known_by=character_name,
        limit=manager.recent_event_window,
    )
    relevant_issue_ids = [issue.issue_id for issue in snapshot.active_issues]
    return {
        "scene_state": snapshot.scene_state,
        "active_issues": manager.get_active_issues(
            limit=default_active_issue_limit,
            participants=[character_name],
        )
        or snapshot.active_issues,
        "recent_events": known_events,
        "my_interpretations": character_interps,
        "canon_anchors": manager.get_relevant_canon_anchors(character_name),
        "summary_blocks": manager.retrieve_summary_blocks(
            participants=[character_name],
            issue_ids=relevant_issue_ids,
            location=manager.scene_state.location if manager.scene_state else None,
            limit=default_summary_prompt_limit,
        )
        or manager.get_summary_blocks(),
    }


def build_orchestration_context(
    *,
    manager: Any,
    active_issue_limit: int,
    recent_event_limit: int,
    summary_limit: int,
) -> dict[str, Any]:
    return {
        "scene_state": manager.scene_state,
        "active_issues": manager.get_active_issues(limit=active_issue_limit),
        "recent_public_events": manager.retrieve_public_events(
            limit=recent_event_limit
        ),
        "summary_blocks": manager.retrieve_summary_blocks(limit=summary_limit),
        "resolved_events": manager.get_resolved_issue_descriptions(),
        "scene_canon_anchors": manager.get_scene_canon_anchors(limit=6),
    }
