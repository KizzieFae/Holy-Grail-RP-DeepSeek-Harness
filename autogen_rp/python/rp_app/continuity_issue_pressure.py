"""Pressure kinds, markers, and turn/issue profile construction for continuity issues."""

from __future__ import annotations

import re
from typing import Any, Optional

from continuity_state import IssueState, PublicEvent

PRESSURE_KIND_CONTROL = "control_conflict"
PRESSURE_KIND_ACCESS = "access_conflict"
PRESSURE_KIND_PRESENCE = "presence_conflict"
PRESSURE_KIND_PLAN = "plan_execution"
PRESSURE_KIND_INFORMATION = "information_gap"
PRESSURE_KIND_SAFETY = "safety_risk"

CONTROL_CONSEQUENCE_TAGS = {
    "authority_asserted",
    "authority_challenged",
    "mediation_attempted",
    "interception",
}
ACCESS_CONSEQUENCE_TAGS = {"access_denied", "access_granted"}
PRESENCE_CONSEQUENCE_TAGS = {
    "arrival",
    "exit",
    "repositioning",
    "territorial_claim",
    "territorial_denial",
}
PLAN_CONSEQUENCE_TAGS = {
    "refusal",
    "agreement",
    "commitment",
    "decision_made",
    "plan_committed",
    "dependency_advanced",
}
INFORMATION_CONSEQUENCE_TAGS = {"revelation", "concealment"}
CONTESTED_PRESENCE_TAGS = {
    "territorial_claim",
    "territorial_denial",
    "authority_asserted",
    "authority_challenged",
    "access_denied",
    "escalation",
}

CONTROL_TEXT_MARKERS = (
    "control",
    "authority",
    "command",
    "order",
    "submit",
    "defy",
    "challenge",
    "accus",
    "dominan",
)
ACCESS_TEXT_MARKERS = (
    "access",
    "permission",
    "allow",
    "blocked",
    "denied",
    "entry",
    "gate",
)
PRESENCE_TEXT_MARKERS = (
    "stay",
    "remain",
    "leave",
    "enter",
    "arrival",
    "exit",
    "presence",
    "position",
    "space",
)
PLAN_TEXT_MARKERS = (
    "plan",
    "decision",
    "offer",
    "deal",
    "course",
    "agree",
    "accept",
    "refuse",
    "commit",
    "obligation",
    "next step",
)
INFORMATION_TEXT_MARKERS = (
    "truth",
    "answer",
    "explain",
    "reveal",
    "conceal",
    "confess",
    "clarify",
    "whether",
    "know",
)
SAFETY_TEXT_MARKERS = (
    "injur",
    "wound",
    "bleed",
    "safe",
    "safety",
    "stabil",
    "protective step",
    "exposure",
    "pain",
    "collapse",
    "responsive",
    "tracked",
    "danger",
    "threat",
)
PLAN_COMPLETION_TEXT_MARKERS = (
    "completed",
    "finished",
    "done",
    "settled",
    "carried out",
    "secured",
)
SAFETY_SETTLED_TEXT_MARKERS = (
    "stable",
    "stabilized",
    "responsive",
    "safe for now",
    "breathing steady",
    "bleeding stopped",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    return [
        item for item in dict.fromkeys(_clean_text(value) for value in values) if item
    ]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _issue_source_text(
    *,
    move: dict[str, Any],
    state_changes: list[str],
    actionable_implications: list[str],
    event: Optional[PublicEvent],
) -> str:
    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    values = [
        _clean_text(move.get("action", "")),
        _clean_text(move.get("dialogue", "")),
        _clean_text(motivation.get("goal", "")),
        _clean_text(motivation.get("tactic", "")),
        *[_clean_text(item) for item in state_changes],
        *[_clean_text(item) for item in actionable_implications],
    ]
    if event is not None:
        values.append(_clean_text(event.summary))
    return " ".join(value for value in values if value)


def _extract_issue_participants(
    *, manager: Any, acting_character: str, move: dict[str, Any]
) -> list[str]:
    if manager.scene_state is None:
        return [acting_character]
    present = [
        _clean_text(item)
        for item in manager.scene_state.present_characters
        if _clean_text(item)
    ]
    if not present:
        return [acting_character]

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    combined = " ".join(
        [
            _clean_text(move.get("action", "")),
            _clean_text(move.get("dialogue", "")),
            _clean_text(motivation.get("goal", "")),
            _clean_text(motivation.get("tactic", "")),
        ]
    ).lower()

    participants = [acting_character]
    for name in present:
        if name == acting_character:
            continue
        if re.search(rf"\b{re.escape(name.lower())}\b", combined):
            participants.append(name)

    if len(participants) == 1:
        return present[:] if len(present) <= 3 else [acting_character]
    return _dedupe_strings(participants)


def _infer_pressure_kind(*, consequence_tags: set[str], source_text: str) -> str:
    tags = {str(item).strip().lower() for item in consequence_tags if _clean_text(item)}
    lowered = source_text.lower()

    if _contains_any(
        lowered, ("establish whether", "determine whether", "clarify whether")
    ):
        return PRESSURE_KIND_INFORMATION
    if tags.intersection(INFORMATION_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_INFORMATION
    if _contains_any(lowered, SAFETY_TEXT_MARKERS):
        return PRESSURE_KIND_SAFETY
    if tags.intersection(ACCESS_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_ACCESS
    if tags.intersection(CONTROL_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_CONTROL
    if tags.intersection(PRESENCE_CONSEQUENCE_TAGS) and (
        tags.intersection(CONTESTED_PRESENCE_TAGS)
        or _contains_any(lowered, CONTROL_TEXT_MARKERS + ACCESS_TEXT_MARKERS)
    ):
        return PRESSURE_KIND_PRESENCE
    if tags.intersection(PLAN_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_PLAN
    if _contains_any(lowered, ACCESS_TEXT_MARKERS):
        return PRESSURE_KIND_ACCESS
    if _contains_any(lowered, CONTROL_TEXT_MARKERS):
        return PRESSURE_KIND_CONTROL
    if _contains_any(lowered, PRESENCE_TEXT_MARKERS) and _contains_any(
        lowered, CONTROL_TEXT_MARKERS + ACCESS_TEXT_MARKERS
    ):
        return PRESSURE_KIND_PRESENCE
    if _contains_any(lowered, PLAN_TEXT_MARKERS):
        return PRESSURE_KIND_PLAN
    if _contains_any(lowered, INFORMATION_TEXT_MARKERS):
        return PRESSURE_KIND_INFORMATION
    return ""


def _default_blocked_what(pressure_kind: str) -> str:
    if pressure_kind == PRESSURE_KIND_CONTROL:
        return "Clear control of the immediate interaction"
    if pressure_kind == PRESSURE_KIND_ACCESS:
        return "Access to the relevant person, place, or action"
    if pressure_kind == PRESSURE_KIND_PRESENCE:
        return "Stable presence or positioning in the scene"
    if pressure_kind == PRESSURE_KIND_PLAN:
        return "Progress on the current decision or obligation"
    if pressure_kind == PRESSURE_KIND_INFORMATION:
        return "Confidence about what is true and what can be done next"
    if pressure_kind == PRESSURE_KIND_SAFETY:
        return "Immediate safety and room to act without worsening danger"
    return "Unresolved scene pressure"


def _derive_blocked_what(
    *, pressure_kind: str, candidate_description: str, source_text: str
) -> str:
    if pressure_kind == PRESSURE_KIND_INFORMATION and candidate_description:
        return candidate_description.rstrip(".")
    if pressure_kind == PRESSURE_KIND_PLAN:
        lowered = source_text.lower()
        if "refus" in lowered or "reject" in lowered:
            return "The current proposed course of action"
        if any(token in lowered for token in ("agree", "accept", "commit")):
            return "Execution of the newly agreed course of action"
    return _default_blocked_what(pressure_kind)


def _default_required_next_step(pressure_kind: str) -> str:
    if pressure_kind == PRESSURE_KIND_CONTROL:
        return "The challenged party must respond, yield, or reassert control."
    if pressure_kind == PRESSURE_KIND_ACCESS:
        return "Someone must grant access, apply leverage, or choose another route."
    if pressure_kind == PRESSURE_KIND_PRESENCE:
        return "The cast must settle who can remain, move, or take space."
    if pressure_kind == PRESSURE_KIND_PLAN:
        return "Someone must decide the next move or carry the obligation forward."
    if pressure_kind == PRESSURE_KIND_INFORMATION:
        return "Someone must clarify the uncertainty or act on the new information."
    if pressure_kind == PRESSURE_KIND_SAFETY:
        return "The cast must reduce the immediate risk or choose the safest next step."
    return "A concrete next move is still required."


def _default_escalation_signals(
    pressure_kind: str, consequence_tags: set[str]
) -> list[str]:
    defaults = {
        PRESSURE_KIND_CONTROL: ["challenge", "defy", "command", "authority"],
        PRESSURE_KIND_ACCESS: ["deny", "block", "refuse access", "locked"],
        PRESSURE_KIND_PRESENCE: ["leave", "stay", "move", "territory"],
        PRESSURE_KIND_PLAN: ["refuse", "delay", "block", "demand"],
        PRESSURE_KIND_INFORMATION: ["conceal", "evade", "withhold", "unclear"],
        PRESSURE_KIND_SAFETY: ["danger", "risk", "worse", "threat"],
    }
    return sorted(
        {
            *[str(item).strip() for item in consequence_tags if _clean_text(item)],
            *defaults.get(pressure_kind, []),
            "pressure",
        }
    )


def _default_resolution_signals(pressure_kind: str) -> list[str]:
    defaults = {
        PRESSURE_KIND_CONTROL: ["yield", "agree", "settled"],
        PRESSURE_KIND_ACCESS: ["allow", "open", "granted"],
        PRESSURE_KIND_PRESENCE: ["settled", "left", "remained"],
        PRESSURE_KIND_PLAN: ["completed", "done", "carried out"],
        PRESSURE_KIND_INFORMATION: ["answer", "clarified", "revealed"],
        PRESSURE_KIND_SAFETY: ["stable", "safe for now", "secured"],
    }
    return defaults.get(pressure_kind, [])


def _build_pressure_description(*, blocked_what: str, required_next_step: str) -> str:
    description = _clean_text(blocked_what) or "Unresolved scene pressure"
    if description[-1:] not in ".!?":
        description += "."
    if required_next_step and required_next_step.lower() not in description.lower():
        description += f" Required next move: {required_next_step}"
    return description


def _build_turn_pressure_profile(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    event: Optional[PublicEvent],
    consequence_tags: set[str],
    state_changes: list[str],
    actionable_implications: list[str],
) -> dict[str, Any]:
    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    candidate_description = (
        next((item for item in state_changes if _clean_text(item)), "")
        or _clean_text(motivation.get("goal", ""))
        or _clean_text(move.get("dialogue", ""))[:160]
        or _clean_text(move.get("action", ""))[:160]
    )
    source_text = _issue_source_text(
        move=move,
        state_changes=state_changes,
        actionable_implications=actionable_implications,
        event=event,
    )
    pressure_kind = _infer_pressure_kind(
        consequence_tags=consequence_tags,
        source_text=source_text,
    )
    blocked_what = _derive_blocked_what(
        pressure_kind=pressure_kind,
        candidate_description=candidate_description,
        source_text=source_text,
    )
    required_next_step = next(
        (item for item in actionable_implications if _clean_text(item)), ""
    ) or _default_required_next_step(pressure_kind)
    last_change = (
        next((item for item in state_changes if _clean_text(item)), "")
        or _clean_text(event.summary if event is not None else "")
        or candidate_description
    )
    participants = _extract_issue_participants(
        manager=manager,
        acting_character=acting_character,
        move=move,
    )
    should_track = bool(
        pressure_kind
        and (
            candidate_description
            or state_changes
            or actionable_implications
            or consequence_tags
        )
    )
    return {
        "pressure_kind": pressure_kind,
        "blocked_what": blocked_what,
        "blocked_characters": participants[:],
        "last_change": last_change,
        "required_next_step": required_next_step,
        "description": _build_pressure_description(
            blocked_what=blocked_what,
            required_next_step=required_next_step,
        ),
        "participants": participants,
        "should_track": should_track,
        "source_text": source_text,
    }


def _build_issue_profile_from_issue(issue: IssueState) -> dict[str, Any]:
    source_text = " ".join(
        value
        for value in [
            _clean_text(issue.description),
            _clean_text(issue.status_reason),
            *[_clean_text(item) for item in issue.escalation_signals],
            *[_clean_text(item) for item in issue.resolution_signals],
        ]
        if value
    )
    pressure_kind = issue.pressure_kind or _infer_pressure_kind(
        consequence_tags=set(),
        source_text=source_text,
    )
    blocked_what = (
        _clean_text(issue.blocked_what)
        or _clean_text(issue.description)
        or _default_blocked_what(pressure_kind)
    )
    required_next_step = _clean_text(
        issue.required_next_step
    ) or _default_required_next_step(pressure_kind)
    return {
        "pressure_kind": pressure_kind,
        "blocked_what": blocked_what,
        "blocked_characters": issue.blocked_characters[:] or issue.participants[:],
        "last_change": _clean_text(issue.last_change)
        or _clean_text(issue.status_reason),
        "required_next_step": required_next_step,
        "description": _clean_text(issue.description)
        or _build_pressure_description(
            blocked_what=blocked_what,
            required_next_step=required_next_step,
        ),
        "participants": issue.participants[:],
    }
