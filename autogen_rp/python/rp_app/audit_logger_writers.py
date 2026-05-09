import json
from pathlib import Path
from typing import Any

from character_move_adapters import root_or_flat_action_text, root_or_flat_dialogue_text


def write_session_manifest(
    *,
    session_path: Path,
    session_owner: str,
    session_number: int,
    cast: list[str],
    opening_description: str,
    user_name: str,
    scene_template_id: str | None,
    scene_premise: str,
    role_assignments: dict[str, str] | None,
    character_presence_constraints: dict[str, str] | None,
    character_authority_labels: dict[str, str] | None,
    continuity_event: dict[str, Any] | None = None,
    scene_state_after: dict[str, Any] | None = None,
    issue_updates: list[dict[str, Any]] | None = None,
    presence_changes: list[dict[str, Any]] | None = None,
    bootstrap_interpretation: dict[str, Any] | None = None,
    cross_session_injection_report: dict[str, Any] | None = None,
    normalize_scene_template_metadata,
    utc_timestamp,
) -> str:
    scene_template = normalize_scene_template_metadata(
        {
            "template_id": scene_template_id,
            "premise": scene_premise,
            "role_assignments": role_assignments or {},
            "character_presence_constraints": (character_presence_constraints or {}),
            "character_authority_labels": character_authority_labels or {},
        }
    )
    manifest = {
        "session_owner": session_owner,
        "session_number": session_number,
        "timestamp": utc_timestamp(),
        "cast": cast,
        "user_name": user_name,
        "opening_description": (
            opening_description[:500] + "..."
            if len(opening_description) > 500
            else opening_description
        ),
        "total_characters": len(cast),
        "scene_template": scene_template,
    }

    if bootstrap_interpretation is not None:
        manifest["bootstrap_interpretation"] = bootstrap_interpretation

    if cross_session_injection_report is not None:
        manifest["cross_session_injection_report"] = cross_session_injection_report

    if any(
        [
            continuity_event,
            scene_state_after,
            issue_updates,
            presence_changes,
        ]
    ):
        manifest["continuity"] = {
            "continuity_event": continuity_event or {},
            "scene_state_after": scene_state_after or {},
            "issue_updates": issue_updates or [],
            "presence_changes": presence_changes or [],
        }

    manifest_path = session_path / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return str(manifest_path)


def write_round_index(
    *,
    session_path: Path,
    round_number: int,
    turn_number: int,
    acting_character: str,
    director_choice_reason: str,
    acting_role: str,
    presence_constraint: str,
    authority_label: str,
    continuity_event_type: str = "",
    state_change_count: int = 0,
    issue_update_count: int = 0,
    presence_change_count: int = 0,
    utc_timestamp,
) -> str:
    index_path = session_path / "_round_index.json"

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"rounds": []}

    round_entry = next(
        (item for item in index["rounds"] if item.get("round_number") == round_number),
        None,
    )
    if round_entry is None:
        round_entry = {
            "round_number": round_number,
            "turns": [],
        }
        index["rounds"].append(round_entry)

    round_entry["turns"].append(
        {
            "turn_number": turn_number,
            "acting_character": acting_character,
            "director_reason": director_choice_reason,
            "acting_role": acting_role,
            "presence_constraint": presence_constraint,
            "authority_label": authority_label,
            "continuity_event_type": continuity_event_type,
            "state_change_count": int(state_change_count or 0),
            "issue_update_count": int(issue_update_count or 0),
            "presence_change_count": int(presence_change_count or 0),
            "timestamp": utc_timestamp(),
        }
    )

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    return str(index_path)


def update_manifest_turn_counter(
    *,
    session_path: Path,
    total_turns: int,
    utc_timestamp,
) -> str:
    """Update ``_manifest.json`` with current total turn count (read-merge-write)."""
    manifest_path = session_path / "_manifest.json"

    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["total_turns"] = total_turns
    manifest["last_updated"] = utc_timestamp()

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return str(manifest_path)


def update_narrative_summary(
    *,
    session_path: Path,
    session_owner: str,
    session_number: int,
    round_number: int,
    turn_number: int,
    acting_character: str,
    rendered_output: str,
    character_move: dict[str, Any],
    director_decision: dict[str, Any],
    acting_role: str,
    presence_constraint: str,
    authority_label: str,
    scene_template_id: str | None,
    scene_premise: str,
    role_assignments: dict[str, str] | None,
    character_presence_constraints: dict[str, str] | None,
    character_authority_labels: dict[str, str] | None,
    continuity_event: dict[str, Any] | None = None,
    scene_state_after: dict[str, Any] | None = None,
    issue_updates: list[dict[str, Any]] | None = None,
    presence_changes: list[dict[str, Any]] | None = None,
    cross_session_injection_report: dict[str, Any] | None = None,
    normalize_scene_template_metadata,
    utc_timestamp,
) -> str:
    narrative_path = session_path / "_narrative.json"

    if narrative_path.exists():
        with open(narrative_path, "r", encoding="utf-8") as f:
            narrative = json.load(f)
    else:
        narrative = {
            "session_owner": session_owner,
            "session_number": session_number,
            "created_at": utc_timestamp(),
            "complete_narrative": "",
            "turns": [],
            "character_stats": {},
            "scene_template": normalize_scene_template_metadata({}),
        }

    scene_template = normalize_scene_template_metadata(
        {
            "template_id": scene_template_id,
            "premise": scene_premise,
            "role_assignments": role_assignments or {},
            "character_presence_constraints": (character_presence_constraints or {}),
            "character_authority_labels": character_authority_labels or {},
        }
    )
    existing_scene_template = normalize_scene_template_metadata(
        narrative.get("scene_template") or {}
    )
    if any(
        [
            scene_template["template_id"],
            scene_template["premise"],
            scene_template["role_assignments"],
            scene_template["character_presence_constraints"],
            scene_template["character_authority_labels"],
        ]
    ):
        narrative["scene_template"] = scene_template
    else:
        narrative["scene_template"] = existing_scene_template

    if cross_session_injection_report is not None:
        narrative["cross_session_injection_report"] = cross_session_injection_report

    turn_entry = {
        "round": round_number,
        "turn": turn_number,
        "character": acting_character,
        "character_role": acting_role,
        "character_presence_constraint": presence_constraint,
        "character_authority_label": authority_label,
        "director_reason": director_decision.get("reason", ""),
        "environment_event": director_decision.get("environment_event", ""),
        "tension_shift": director_decision.get("tension_shift", ""),
        "character_action": root_or_flat_action_text(character_move),
        "character_dialogue": root_or_flat_dialogue_text(character_move),
        "character_motivation": character_move.get("motivation", {}),
        "rendered_output": rendered_output,
        "continuity_event_type": str(
            (continuity_event or {}).get("event_type", "") or ""
        ),
        "continuity_event_summary": str(
            (continuity_event or {}).get("summary", "") or ""
        ),
        "continuity_event_significance": str(
            (continuity_event or {}).get("significance", "") or ""
        ),
        "continuity_related_issue_ids": [
            str(item)
            for item in (continuity_event or {}).get("related_issue_ids", [])
            if str(item).strip()
        ],
        "state_changes": [
            str(item)
            for item in (continuity_event or {}).get("state_changes", [])
            if str(item).strip()
        ],
        "actionable_implications": [
            str(item)
            for item in (continuity_event or {}).get("actionable_implications", [])
            if str(item).strip()
        ],
        "scene_recent_delta": str(
            (scene_state_after or {}).get("recent_delta", "") or ""
        ),
        "scene_phase": str((scene_state_after or {}).get("phase", "") or ""),
        "current_tension_level": str(
            (scene_state_after or {}).get("current_tension_level", "") or ""
        ),
        "active_issue_ids_after": [
            str(item)
            for item in (scene_state_after or {}).get("active_issue_ids", [])
            if str(item).strip()
        ],
        "present_characters_after": [
            str(item)
            for item in (scene_state_after or {}).get("present_characters", [])
            if str(item).strip()
        ],
        "absent_but_relevant_after": [
            str(item)
            for item in (scene_state_after or {}).get("absent_but_relevant", [])
            if str(item).strip()
        ],
        "issue_updates": [
            dict(item) for item in (issue_updates or []) if isinstance(item, dict)
        ],
        "presence_changes": [
            dict(item) for item in (presence_changes or []) if isinstance(item, dict)
        ],
        "timestamp": utc_timestamp(),
    }

    narrative["turns"].append(turn_entry)

    if narrative["complete_narrative"]:
        narrative["complete_narrative"] += "\n\n" + rendered_output
    else:
        narrative["complete_narrative"] = rendered_output

    stats = narrative["character_stats"].get(
        acting_character,
        {
            "turns": 0,
            "dialogue_count": 0,
            "total_response_length": 0,
            "avg_response_length": 0,
        },
    )

    stats["turns"] += 1
    if root_or_flat_dialogue_text(character_move).strip():
        stats["dialogue_count"] += 1
    stats["total_response_length"] += len(rendered_output)
    stats["avg_response_length"] = stats["total_response_length"] // stats["turns"]

    narrative["character_stats"][acting_character] = stats

    total_turns = sum(s["turns"] for s in narrative["character_stats"].values())
    for char_stats in narrative["character_stats"].values():
        char_stats["spotlight_percentage"] = (
            round((char_stats["turns"] / total_turns) * 100, 1)
            if total_turns > 0
            else 0
        )

    narrative["last_updated"] = utc_timestamp()
    narrative["total_rounds"] = len({turn.get("round") for turn in narrative["turns"]})

    scene_template = normalize_scene_template_metadata(
        narrative.get("scene_template") or {}
    )
    narrative["scene_template"] = scene_template

    with open(narrative_path, "w", encoding="utf-8") as f:
        json.dump(narrative, f, indent=2, ensure_ascii=False)

    return str(narrative_path)
