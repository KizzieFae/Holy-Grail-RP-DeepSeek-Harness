"""Scene Grounding (MVP): read-only settled facts derived from continuity, for prompts only.

Facts are promoted from deterministic markers attached to public events (see PRD §5.8).
This module does not write continuity or character state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from continuity_state import ConsequenceCategory, DetectedConsequence, PublicEvent

MAX_SCENE_FACTS = 16
SCHEMA_VERSION = 1

# Character prompt: BINDING CONSTRAINTS (subset of settled facts; same rebuild pipeline).
_BINDING_FACT_KEYS: frozenset[tuple[str, str]] = frozenset(
    {
        ("assignment", "sleeping_surface"),
        ("access", "location_entry"),
    }
)


def is_behaviorally_binding_scene_fact(category: str, key: str) -> bool:
    """Facts that must not be contradicted in dialogue/action (prompt enforcement only)."""
    return (str(category or "").strip(), str(key or "").strip()) in _BINDING_FACT_KEYS

# Default priority by category (higher retained first under cap)
_CATEGORY_PRIORITY: dict[str, int] = {
    "access": 78,
    "medical": 85,
    "medical_status": 85,
    "assignment": 80,
    "communication_state": 75,
    "object_state": 70,
}

# Shared deterministic signals for classifier + marker emission (same predicates).
SIGNAL_PHONE_BROKEN = "phone_broken"
SIGNAL_BANDAGE_APPLIED = "bandage_applied"
SIGNAL_WEAPON_ON_TABLE = "weapon_on_table"


def empty_grounding_dict() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "facts": [],
        "last_rebuilt_turn": None,
    }


def _move_text_blob(move: dict[str, Any]) -> str:
    dialogue = str(move.get("dialogue", "") or "").lower()
    action = str(move.get("action", "") or "").lower()
    motivation = move.get("motivation", {})
    goal = (
        str(motivation.get("goal", "") or "").lower()
        if isinstance(motivation, dict)
        else ""
    )
    return f"{dialogue} {action} {goal}"


def grounding_state_signals_from_move(move: dict[str, Any]) -> frozenset[str]:
    """Narrow, deterministic scene-state lexical signals (classifier + markers).

    Same predicates must drive both consequence detection and marker emission.
    """
    text = _move_text_blob(move)
    out: set[str] = set()
    if ("phone" in text or "cell" in text) and (
        "broke" in text
        or "broken" in text
        or "shattered" in text
        or "smashed" in text
    ):
        out.add(SIGNAL_PHONE_BROKEN)
    if ("bandage" in text or "dressing" in text) and (
        "applied" in text
        or "wrapped" in text
        or "taped" in text
        or "secured" in text
    ):
        out.add(SIGNAL_BANDAGE_APPLIED)
    has_weapon_ref = "table" in text and (
        "weapon" in text or "gun" in text or "knife" in text
    )
    padded = f" {text} "
    has_placement_verb = (
        "placed" in text
        or "laid" in text
        or "put down" in text
        or "puts down" in text
        or "set down" in text
        or "sets down" in text
        or "left on" in text
        or "leaves on" in text
        or (
            "on the table" in text
            and any(f" {v} " in padded for v in ("put", "set", "laid", "placed"))
        )
    )
    if has_weapon_ref and has_placement_verb:
        out.add(SIGNAL_WEAPON_ON_TABLE)
    return frozenset(out)


def compute_grounding_markers(
    acting_character: str,
    move: dict[str, Any],
    detected: list[DetectedConsequence],
) -> list[str]:
    """Derive deterministic grounding markers for this turn (no LLM).

    Markers are compact strings: ``category:key|k=v|...`` stored on PublicEvent.
    """
    cats = {d.category for d in detected}
    text = _move_text_blob(move)
    signals = grounding_state_signals_from_move(move)
    markers: list[str] = []

    if ConsequenceCategory.REVELATION in cats:
        if "suppress" in text and (
            "wrong" in text
            or "not a wolf" in text
            or "not built" in text
            or "physiology" in text
            or "formulation" in text
            or "non-wolf" in text
        ):
            subj = str(acting_character or "").strip() or "unknown"
            markers.append(
                f"medical_status:omega_suppressants|formulation=wrong_for_physiology|subject={subj}"
            )

    if SIGNAL_PHONE_BROKEN in signals:
        markers.append("object_state:phone|status=broken")

    if SIGNAL_BANDAGE_APPLIED in signals:
        markers.append("medical_status:wound_dressing|status=applied")

    if SIGNAL_WEAPON_ON_TABLE in signals:
        markers.append("object_state:weapon|location=on_table")

    # communication_state:housing_call is not emitted lexically here. Authoritative
    # promotion is continuity-owned via scene_state_updates.housing_call_outcome
    # (resolved outcome → grounding). Stored markers on older PublicEvents are
    # still honored in rebuild_scene_grounding_from_continuity.

    return markers


def _parse_marker(marker: str) -> tuple[str, str, dict[str, str]] | None:
    marker = str(marker or "").strip()
    if not marker or "|" not in marker and ":" not in marker:
        return None
    head, _, tail = marker.partition("|")
    head = head.strip()
    if ":" not in head:
        return None
    category, _, key = head.partition(":")
    category = category.strip()
    key = key.strip()
    if not category or not key:
        return None
    kv: dict[str, str] = {}
    if tail.strip():
        for part in tail.split("|"):
            part = part.strip()
            if "=" in part:
                k, _, v = part.partition("=")
                kv[k.strip()] = v.strip()
    return category, key, kv


def _humanize_id(name: str) -> str:
    return str(name or "").replace("_", " ").strip() or name


def _build_value_summary(category: str, key: str, kv: dict[str, str]) -> str:
    if category == "assignment" and key == "sleeping_surface":
        who = _humanize_id(kv.get("assignee", "someone"))
        surf = kv.get("surface", "")
        surf_label = surf.replace("_", " ") if surf else surf
        line = f"{who}: sleeping — {surf_label}"
        return line[:120]
    if category == "medical_status" and key == "omega_suppressants":
        who = _humanize_id(kv.get("subject", "omega"))
        form = kv.get("formulation", "")
        if form == "wrong_for_physiology":
            return f"{who}: suppressants wrong for physiology"[:120]
        return f"{who}: suppressants ({form})"[:120]
    if category == "medical" and key == "suppressant_formulation":
        who = _humanize_id(kv.get("subject", "someone"))
        return f"{who}: suppressant formulation {kv.get('status', 'unknown')}"[:120]
    if category == "access" and key == "location_entry":
        who = _humanize_id(kv.get("subject", "someone"))
        location = _humanize_id(kv.get("location", "somewhere"))
        return f"{who}: {location} entry {kv.get('status', 'unknown')}"[:120]
    if category == "object_state" and key == "phone":
        return f"Phone: {kv.get('status', 'unknown')}"[:120]
    if category == "object_state" and key == "weapon":
        loc = kv.get("location", "")
        loc_label = loc.replace("_", " ") if loc else "scene"
        return f"Weapon: {loc_label}"[:120]
    if category == "medical_status" and key == "wound_dressing":
        return f"Wound dressing: {kv.get('status', 'unknown')}"[:120]
    if category == "communication_state" and key == "housing_call":
        return f"Housing call: {kv.get('status', 'unknown')}"[:120]
    return f"{category}/{key}"[:120]


def grounding_markers_event_summary(markers: list[str]) -> str:
    """Deterministic one-line audit/summary when an event is promoted for markers only."""
    parts: list[str] = []
    for m in markers:
        p = _parse_marker(str(m))
        if p:
            cat, key, kv = p
            parts.append(_build_value_summary(cat, key, kv))
        else:
            t = str(m).strip()
            if t:
                parts.append(t[:120])
    if parts:
        return "; ".join(parts)[:280]
    return "Settled scene state updated."


def _build_value_dict(category: str, key: str, kv: dict[str, str]) -> dict[str, str]:
    out = dict(kv)
    out["_category"] = category
    out["_key"] = key
    return out


def _fact_slot_identity(
    category: str,
    key: str,
    kv: dict[str, str],
) -> tuple[str, str, str | None]:
    if category == "assignment" and key == "sleeping_surface":
        assignee = str(
            kv.get("assignee", kv.get("assignee_id", "")) or ""
        ).strip()
        return category, key, assignee or None
    if category == "medical" and key == "suppressant_formulation":
        subject = str(kv.get("subject", kv.get("subject_id", "")) or "").strip()
        return category, key, subject or None
    if category == "access" and key == "location_entry":
        subject = str(kv.get("subject", kv.get("subject_id", "")) or "").strip()
        location = str(kv.get("location", kv.get("location_id", "")) or "").strip()
        slot_subject = subject or ""
        slot_location = location or ""
        return category, key, f"{slot_subject}::{slot_location}" if slot_subject or slot_location else None
    return category, key, None


@dataclass
class SceneFact:
    fact_id: str
    category: str
    key: str
    value: dict[str, str]
    value_summary: str
    source: dict[str, str]
    priority: int
    supersedes: str | None = None
    source_turn_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "category": self.category,
            "key": self.key,
            "value": dict(self.value),
            "value_summary": self.value_summary,
            "source": dict(self.source),
            "priority": self.priority,
            "supersedes": self.supersedes,
            "source_turn_index": self.source_turn_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SceneFact:
        return cls(
            fact_id=str(data.get("fact_id", "")),
            category=str(data.get("category", "")),
            key=str(data.get("key", "")),
            value={
                str(k): str(v)
                for k, v in (data.get("value") or {}).items()
                if isinstance(k, str)
            },
            value_summary=str(data.get("value_summary", "")),
            source={
                str(k): str(v)
                for k, v in (data.get("source") or {}).items()
                if isinstance(k, str)
            },
            priority=int(data.get("priority", 0)),
            supersedes=(
                str(data["supersedes"])
                if data.get("supersedes") is not None
                and str(data.get("supersedes")).strip()
                else None
            ),
            source_turn_index=(
                int(data["source_turn_index"])
                if data.get("source_turn_index") is not None
                else None
            ),
        )


def _marker_to_fact(
    *,
    event: PublicEvent,
    marker: str,
    marker_index: int,
    previous_id: str | None,
) -> SceneFact | None:
    parsed = _parse_marker(marker)
    if not parsed:
        return None
    category, key, kv = parsed
    if category not in _CATEGORY_PRIORITY:
        return None
    allowed_keys = {
        "access": {"location_entry"},
        "medical": {"suppressant_formulation"},
        "assignment": {"sleeping_surface"},
        "medical_status": {"omega_suppressants", "wound_dressing"},
        "object_state": {"phone", "weapon"},
        "communication_state": {"housing_call"},
    }
    if key not in allowed_keys.get(category, set()):
        return None

    fact_id = f"{event.event_id}:{marker_index}"
    value = _build_value_dict(category, key, kv)
    summary = _build_value_summary(category, key, kv)
    priority = _CATEGORY_PRIORITY[category]
    return SceneFact(
        fact_id=fact_id,
        category=category,
        key=key,
        value=value,
        value_summary=summary,
        source={
            "kind": "continuity_event",
            "ref": str(event.event_id or ""),
        },
        priority=priority,
        supersedes=previous_id,
        source_turn_index=event.turn_index,
    )


def _resolved_outcome_to_fact(
    *,
    outcome: Any,
    previous_id: str | None,
) -> SceneFact | None:
    category = str(getattr(outcome, "category", "") or "")
    key = str(getattr(outcome, "key", "") or "")
    value = getattr(outcome, "value", {}) or {}
    if category == "assignment" and key == "sleeping_surface":
        assignee = str(value.get("assignee_id", "") or "").strip()
        surface = str(value.get("surface_id", "") or "").strip()
        if not assignee or not surface:
            return None
        kv = {
            "assignee": assignee,
            "surface": surface,
        }
    elif category == "communication_state" and key == "housing_call":
        status = str(value.get("status", "") or "").strip()
        if not status:
            return None
        kv = {
            "status": status,
        }
    elif category == "medical" and key == "suppressant_formulation":
        subject = str(
            getattr(outcome, "subject_id", "") or value.get("subject_id", "") or ""
        ).strip()
        status = str(value.get("status", "") or "").strip()
        if not subject or not status:
            return None
        kv = {
            "subject": subject,
            "status": status,
        }
    elif category == "access" and key == "location_entry":
        subject = str(
            getattr(outcome, "subject_id", "") or value.get("subject_id", "") or ""
        ).strip()
        location = str(value.get("location_id", "") or value.get("location", "") or "").strip()
        status = str(value.get("status", "") or "").strip()
        if not subject or not location or not status:
            return None
        kv = {
            "subject": subject,
            "location": location,
            "status": status,
        }
    else:
        return None
    return SceneFact(
        fact_id=str(getattr(outcome, "outcome_id", "") or ""),
        category=category,
        key=key,
        value=_build_value_dict(category, key, kv),
        value_summary=_build_value_summary(category, key, kv),
        source={
            "kind": "resolved_outcome",
            "ref": str(
                getattr(outcome, "source_event_id", "")
                or getattr(outcome, "outcome_id", "")
                or ""
            ),
        },
        priority=_CATEGORY_PRIORITY[category],
        supersedes=previous_id,
        source_turn_index=getattr(outcome, "created_turn_index", None),
    )


def rebuild_scene_grounding_from_continuity(manager: Any) -> dict[str, Any]:
    """Rebuild the full grounding snapshot from continuity public events (deterministic)."""
    events: list[PublicEvent] = getattr(manager, "public_events", []) or []
    by_slot: dict[tuple[str, str, str | None], SceneFact] = {}
    for event in events:
        markers = getattr(event, "grounding_markers", None) or []
        if not isinstance(markers, list):
            continue
        for i, marker in enumerate(markers):
            slot_key = _parse_marker(str(marker))
            if not slot_key:
                continue
            cat, k, kv = slot_key
            slot = _fact_slot_identity(cat, k, kv)
            prev = by_slot.get(slot)
            fact = _marker_to_fact(
                event=event,
                marker=str(marker),
                marker_index=i,
                previous_id=prev.fact_id if prev else None,
            )
            if fact is not None:
                by_slot[slot] = fact

    resolved_outcomes = getattr(manager, "resolved_outcomes", []) or []
    for outcome in resolved_outcomes:
        if str(getattr(outcome, "status", "") or "") != "active":
            continue
        category = str(getattr(outcome, "category", "") or "")
        key = str(getattr(outcome, "key", "") or "")
        value = dict(getattr(outcome, "value", {}) or {})
        subject_id = str(getattr(outcome, "subject_id", "") or "").strip()
        if subject_id and "subject_id" not in value:
            value["subject_id"] = subject_id
        slot = _fact_slot_identity(category, key, value)
        prev = by_slot.get(slot)
        fact = _resolved_outcome_to_fact(
            outcome=outcome,
            previous_id=prev.fact_id if prev else None,
        )
        if fact is not None:
            by_slot[slot] = fact

    facts = list(by_slot.values())
    facts.sort(
        key=lambda f: (
            -f.priority,
            -(f.source_turn_index if f.source_turn_index is not None else -1),
            f.category,
            f.key,
            f.fact_id,
        )
    )
    if len(facts) > MAX_SCENE_FACTS:
        facts = facts[:MAX_SCENE_FACTS]

    last_turn = getattr(manager, "turn_counter", None)
    return {
        "schema_version": SCHEMA_VERSION,
        "facts": [f.to_dict() for f in facts],
        "last_rebuilt_turn": int(last_turn) if last_turn is not None else None,
    }


def format_grounding_prompt_prefix(scene_grounding: Any) -> str:
    """Director prefix fragment (plain text, empty if no facts)."""
    block = format_grounding_block_body(scene_grounding)
    if not block.strip():
        return ""
    return (
        "SETTLED SCENE FACTS (established in this scene; do not contradict or "
        "re-open without new in-fiction development):\n"
        f"{block}\n"
    )


def format_grounding_block_body(
    scene_grounding: Any,
    *,
    binding_filter: str | None = None,
) -> str:
    """Bullet lines only (no header).

    binding_filter:
        None — all facts (Director prefix, tests).
        ``"binding"`` — only behaviorally binding categories (sleeping assignment, entry).
        ``"non_binding"`` — exclude those (character SETTLED block; binding lives separately).
    """
    raw = scene_grounding
    if raw is None:
        return ""
    if isinstance(raw, dict):
        facts_data = raw.get("facts", [])
    else:
        facts_data = []
    if not isinstance(facts_data, list) or not facts_data:
        return ""
    lines: list[str] = []
    for item in facts_data:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category", "") or "")
        key = str(item.get("key", "") or "")
        is_binding = is_behaviorally_binding_scene_fact(cat, key)
        if binding_filter == "binding" and not is_binding:
            continue
        if binding_filter == "non_binding" and is_binding:
            continue
        summ = str(item.get("value_summary", "") or "").strip()
        if not summ:
            continue
        lines.append(f"- [{cat}] {summ}")
    return "\n".join(lines)


_BINDING_CONSTRAINTS_PREAMBLE = """## **BINDING CONSTRAINTS (HIGH PRIORITY)**

When the list below is non-empty, these facts override how you may express yourself if there is a conflict: do not deny or nullify them in dialogue or action unless a **new in-scene event** changes them.

The following facts are **true in the world**. You may react emotionally or resist them, but you must **not** state or act as if they are **false** unless a new in-scene event changes them.

**Allowed (examples):** "This is bullshit." / "I'm not agreeing to this." / "I'll call housing and fix this." / "You don't get to decide this long-term."

**Not allowed (examples):** "The couch isn't yours." (when it is assigned) / acting as if no assignment exists / commands that override the assignment or entry permission **without** a new settling event.

**Assertable (must match the list):** declarative statements about world state (who sleeps where, who may enter where). **Performative (allowed):** threats, objections, refusal, attempts to escalate or change the situation.

If your character's instincts conflict with these constraints, **preserve the truth of the constraints** and express resistance through **attitude**, not **contradiction**.
"""


def format_character_binding_constraints_section(scene_grounding: Any) -> str:
    """High-salience binding block for character prompts only; empty if no binding facts."""
    body = format_grounding_block_body(scene_grounding, binding_filter="binding")
    if not body.strip():
        return ""
    return f"{_BINDING_CONSTRAINTS_PREAMBLE}\n{body}\n\n"


def format_character_grounding_section(scene_grounding: Any) -> str:
    body = format_grounding_block_body(scene_grounding, binding_filter="non_binding")
    if not body.strip():
        return ""
    return (
        "SETTLED SCENE FACTS (established in this scene; do not contradict or "
        "re-open without new in-fiction development):\n"
        f"{body}\n\n"
    )


def grounding_dict_from_session_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Restore scene_grounding from saved session metadata (tolerant of missing/old keys)."""
    if not isinstance(metadata, dict):
        return empty_grounding_dict()
    sg = metadata.get("scene_grounding")
    if not isinstance(sg, dict):
        return empty_grounding_dict()
    facts = sg.get("facts", [])
    if not isinstance(facts, list):
        facts = []
    return {
        "schema_version": int(sg.get("schema_version", SCHEMA_VERSION)),
        "facts": [f for f in facts if isinstance(f, dict)],
        "last_rebuilt_turn": sg.get("last_rebuilt_turn"),
    }
