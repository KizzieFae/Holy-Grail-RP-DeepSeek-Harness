import json
import re
from datetime import datetime, timezone
from typing import Any

from continuity_state import IssueState, IssueStatus


def _role_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_scene_holder_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protector",
            "dominator",
            "holder",
            "host",
            "captor",
            "interrogator",
            "caretaker",
            "guardian",
            "handler",
            "owner",
            "boss",
            "warden",
            "guard",
            "miko",
            "staff",
            "roommate",
            "mother",
        )
    )


def _is_scene_protagonist_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protagonist",
            "recovering",
            "patient",
            "guest",
            "subject",
            "captive",
            "ward",
            "charge",
            "outsider",
            "newcomer",
            "supplicant",
            "target",
            "applicant",
            "visitor",
            "arrival",
            "student",
            "child",
            "omega",
        )
    )


def _build_seed_issue_id(prefix: str, participants: list[str]) -> str:
    participant_key = "_".join(
        re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") for name in participants
    )
    return f"seed_{prefix}_{participant_key}".strip("_")


def build_initial_scene_issues(scene_setup: dict[str, Any] | None) -> list[IssueState]:
    if not isinstance(scene_setup, dict):
        return []

    role_assignments = scene_setup.get("role_assignments", {})
    sleeping_surface_slots = scene_setup.get("sleeping_surface_slots", [])
    if not isinstance(role_assignments, dict) or not role_assignments:
        return []

    premise = str(scene_setup.get("premise", "") or "")
    premise_lower = premise.lower()
    template_id = str(scene_setup.get("template_id", "") or "").strip().lower()
    seeded: list[IssueState] = []
    seeded_ids: set[str] = set()
    created_at = datetime.now(timezone.utc)
    character_names = [
        str(name).strip() for name in role_assignments if str(name or "").strip()
    ]

    if isinstance(sleeping_surface_slots, list) and sleeping_surface_slots:
        holder_names = [
            name
            for name in character_names
            if _is_scene_holder_role(role_assignments.get(name, ""))
        ]
        protagonist_names = [
            name
            for name in character_names
            if _is_scene_protagonist_role(role_assignments.get(name, ""))
        ]
        if holder_names and protagonist_names:
            participants = sorted(set(holder_names + protagonist_names))
            sleeping_issue = IssueState(
                issue_id=_build_seed_issue_id(
                    "sleeping_surface_assignment", participants
                ),
                description="Establish where each present character is expected to sleep in the current scene.",
                participants=participants,
                status=IssueStatus.ACTIVE,
                created_at=created_at,
                escalation_signals=[
                    "sleep",
                    "bunk",
                    "bed",
                    "couch",
                    "cot",
                    "floor",
                    "roommate",
                ],
                resolution_signals=[
                    *[
                        str(item)
                        for item in sleeping_surface_slots
                        if str(item or "").strip()
                    ],
                    *[
                        str(item).replace("_", " ")
                        for item in sleeping_surface_slots
                        if str(item or "").strip()
                    ],
                    "sleep here",
                    "take the bed",
                    "take the bunk",
                    "stay here tonight",
                ],
                status_reason="Scene-start sleeping arrangement pressure for bounded sleeping-surface settlement.",
            )
            if sleeping_issue.issue_id not in seeded_ids:
                seeded.append(sleeping_issue)
                seeded_ids.add(sleeping_issue.issue_id)

    # Determine if this is an injury/recovery/rescue scene context
    injury_recovery_tokens = (
        "injured",
        "wounded",
        "recovery",
        "safehouse",
        "rescue",
        "bleeding",
        "blood",
        "hurt",
        "pain",
        "medical",
        "doctor",
        "nurse",
        "hospital",
        "clinic",
        "trauma",
        "unconscious",
        "fainted",
        "collapsed",
        "bandage",
        "treatment",
        "stabilize",
    )
    is_injury_recovery_scene = template_id == "celina_apartment_recovery_watch" or any(
        token in premise_lower for token in injury_recovery_tokens
    )

    for source_name in character_names:
        source_role = _role_text(role_assignments.get(source_name, ""))
        if not _is_scene_holder_role(source_role):
            continue

        for target_name in character_names:
            if target_name == source_name:
                continue
            target_role = _role_text(role_assignments.get(target_name, ""))
            if not _is_scene_protagonist_role(target_role):
                continue

            participants = [source_name, target_name]

            # Only seed injury/recovery issues for injury/recovery scenes
            if is_injury_recovery_scene:
                stabilize_issue = IssueState(
                    issue_id=_build_seed_issue_id("stabilize_and_assess", participants),
                    description=f"Assess and stabilize {target_name}'s injuries, exposure, and immediate safety while keeping them responsive",
                    participants=participants,
                    status=IssueStatus.ACTIVE,
                    created_at=created_at,
                    escalation_signals=[
                        "bleed",
                        "blood",
                        "collapse",
                        "faint",
                        "worse",
                        "weak",
                        "shiver",
                        "fever",
                        "pain",
                        "unresponsive",
                    ],
                    resolution_signals=[
                        "stable",
                        "responsive",
                        "bandage",
                        "warm",
                        "rest easier",
                        "breathing steady",
                        "bleeding stopped",
                    ],
                    status_reason="Scene-start recovery pressure for protector/protagonist roles.",
                )
                if stabilize_issue.issue_id not in seeded_ids:
                    seeded.append(stabilize_issue)
                    seeded_ids.add(stabilize_issue.issue_id)

            if template_id == "celina_apartment_recovery_watch" or any(
                token in premise_lower
                for token in (
                    "dangerous rescue",
                    "criminal pressure",
                    "safehouse",
                    "hide",
                    "hidden",
                    "offscreen",
                )
            ):
                route_issue = IssueState(
                    issue_id=_build_seed_issue_id("direct_route_risk", participants),
                    description=f"Establish whether {target_name} led immediate danger directly to this refuge",
                    participants=participants,
                    status=IssueStatus.ACTIVE,
                    created_at=created_at,
                    escalation_signals=[
                        "followed",
                        "found",
                        "tracked",
                        "hunter",
                        "lead",
                        "building",
                        "apartment",
                        "door",
                    ],
                    resolution_signals=[
                        "didn't lead anyone here",
                        "did not lead anyone here",
                        "didn't run straight here",
                        "did not run straight here",
                        "wouldn't know this building",
                        "would not know this building",
                        "wouldn't know this place",
                        "would not know this place",
                        "wouldn't know this apartment",
                        "would not know this apartment",
                        "doubled back",
                        "lost them in the storm",
                        "no one followed",
                    ],
                    status_reason="Scene-start follow-route pressure for rescue/safehouse setups.",
                )
                if route_issue.issue_id not in seeded_ids:
                    seeded.append(route_issue)
                    seeded_ids.add(route_issue.issue_id)

                danger_issue = IssueState(
                    issue_id=_build_seed_issue_id(
                        "outside_threat_and_next_steps", participants
                    ),
                    description=f"Determine whether outside danger can reach {target_name} here and decide the next protective step",
                    participants=participants,
                    status=IssueStatus.ACTIVE,
                    created_at=created_at,
                    escalation_signals=[
                        "followed",
                        "found",
                        "tracked",
                        "threat",
                        "danger",
                        "boss",
                        "hunter",
                        "door",
                        "phone",
                    ],
                    resolution_signals=[
                        "plan",
                        "safe for now",
                        "move tomorrow",
                        "stay here tonight",
                        "hide better",
                        "lay low",
                    ],
                    status_reason="Scene-start carry-forward pressure for rescue/safehouse setups.",
                )
                if danger_issue.issue_id not in seeded_ids:
                    seeded.append(danger_issue)
                    seeded_ids.add(danger_issue.issue_id)

    return seeded


def apply_scene_setup_to_scene_state(
    *,
    scene_state: Any,
    scene_setup: dict[str, Any] | None,
    get_must_remain_characters_fn,
    continuity_manager: Any | None = None,
) -> None:
    if scene_state is None or not isinstance(scene_setup, dict):
        return

    scene_state.scene_template_id = scene_setup.get("template_id") or None
    scene_state.scene_premise = str(scene_setup.get("premise", "") or "")
    _arn = scene_setup.get("anchor_role_name")
    scene_state.anchor_role_name = (
        str(_arn).strip() if _arn is not None and str(_arn or "").strip() else None
    )
    scene_state.role_assignments = {
        str(key): str(value)
        for key, value in scene_setup.get("role_assignments", {}).items()
    }
    scene_state.character_presence_constraints = {
        str(key): str(value)
        for key, value in scene_setup.get("character_presence_constraints", {}).items()
    }
    scene_state.character_authority_labels = {
        str(key): str(value)
        for key, value in scene_setup.get("character_authority_labels", {}).items()
        if str(value or "").strip()
    }
    scene_state.sleeping_surface_slots = [
        str(item)
        for item in scene_setup.get("sleeping_surface_slots", [])
        if str(item or "").strip()
    ]
    scene_state.location_entry_slots = [
        str(item)
        for item in scene_setup.get("location_entry_slots", [])
        if str(item or "").strip()
    ]
    if continuity_manager is not None and continuity_manager.scene_state is scene_state:
        continuity_manager.apply_must_remain_presence_from_fn(
            get_must_remain_characters_fn
        )
        return
    must_remain = get_must_remain_characters_fn(scene_state.to_dict())
    for character_name in must_remain:
        if character_name not in scene_state.present_characters:
            scene_state.present_characters.append(character_name)
    scene_state.absent_but_relevant = [
        name for name in scene_state.absent_but_relevant if name not in must_remain
    ]


def enforce_must_remain_presence(
    *,
    st_module: Any,
    get_continuity_manager_fn,
    get_must_remain_characters_fn,
    get_orchestration_state_fn,
) -> None:
    continuity_manager = get_continuity_manager_fn()
    if continuity_manager is not None and continuity_manager.scene_state is not None:
        continuity_manager.apply_must_remain_presence_from_fn(
            get_must_remain_characters_fn
        )

    orchestration_state = get_orchestration_state_fn()
    orchestration_scene_state = orchestration_state.setdefault("scene_state", {})
    must_remain = get_must_remain_characters_fn(orchestration_scene_state)
    present_characters = [
        str(item)
        for item in orchestration_scene_state.get("present_characters", [])
        if str(item or "").strip()
    ]
    for character_name in must_remain:
        if character_name not in present_characters:
            present_characters.append(character_name)
    orchestration_scene_state["present_characters"] = present_characters


def resolve_scene_template_setup(
    *,
    st_module: Any,
    selected_chars: list[str],
    character_names_by_file: dict[str, str],
    scene_template_manager_cls: Any,
    normalize_role_assignments_fn,
    validate_role_assignments_fn,
) -> tuple[dict[str, Any] | None, str]:
    """Resolve template-driven scene_setup from session state.

    ``selected_chars`` is the set of character **file** ids that participate in template role
    validation and ``role_assignments`` (Issue #128: may include the player POV file in addition
    to bot ``selected_chars`` from scene start).
    """
    template_id = st_module.session_state.get("selected_scene_template_id")
    if not template_id:
        return None, ""

    template_manager = scene_template_manager_cls()
    try:
        template = template_manager.load_template(str(template_id))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return None, str(exc)

    raw_assignments = normalize_role_assignments_fn(
        st_module.session_state.get("scene_role_assignments", {})
    )
    _pc = st_module.session_state.get("player_character")
    _player_file = str(_pc).strip() if _pc else None
    issues = validate_role_assignments_fn(
        template,
        selected_chars,
        raw_assignments,
        player_character_file=_player_file or None,
    )
    if issues:
        return None, "; ".join(issues)

    role_assignments: dict[str, str] = {}
    character_presence_constraints: dict[str, str] = {}
    character_authority_labels: dict[str, str] = {}

    for char_file in selected_chars:
        character_name = character_names_by_file.get(char_file, char_file)
        role_name = raw_assignments.get(char_file, "")
        slot = template.get_role_slot(role_name)
        if slot is None:
            continue
        role_assignments[character_name] = slot.role_name
        character_presence_constraints[character_name] = slot.presence_constraint
        if slot.authority:
            character_authority_labels[character_name] = slot.authority

    return {
        "template_id": template.template_id,
        "premise": template.premise,
        "opening_text": template.opening_text,
        "anchor_role_name": template.anchor_role_name,
        "role_assignments": role_assignments,
        "character_presence_constraints": character_presence_constraints,
        "character_authority_labels": character_authority_labels,
        "sleeping_surface_slots": list(template.sleeping_surface_slots),
        "location_entry_slots": list(template.location_entry_slots),
    }, ""
