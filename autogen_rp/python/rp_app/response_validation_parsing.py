import json
from typing import Any

from character_move_adapters import (
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)
from character_move_ingress import (
    load_json_object_duplicate_safe,
    parse_character_move_content_to_v2,
    unwrap_fenced_json_object,
)


def build_attempted_post_details(
    raw_response: str = "",
    parsed_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    payload = parsed_output if isinstance(parsed_output, dict) else {}

    if int(str(payload.get("move_schema_version", 0) or 0) or 0) == 2:
        action = str(legacy_flat_action_text(payload) or "").strip()
        dialogue = str(legacy_flat_dialogue_text(payload) or "").strip()
    else:
        action = str(payload.get("action", "") or "").strip()
        dialogue = str(payload.get("dialogue", "") or "").strip()
    motivation = payload.get("motivation", {})
    if not isinstance(motivation, dict):
        motivation = {}

    if action:
        details["action"] = action
    if dialogue:
        details["dialogue"] = dialogue
    if motivation:
        details["motivation"] = motivation

    human_readable_parts: list[str] = []
    if action:
        human_readable_parts.append(f"Action: {action}")
    if dialogue:
        human_readable_parts.append(f'Dialogue: "{dialogue}"')
    if motivation:
        goal = str(motivation.get("goal", "") or "").strip()
        tactic = str(motivation.get("tactic", "") or "").strip()
        emotional_driver = str(motivation.get("emotional_driver", "") or "").strip()
        risk_level = str(motivation.get("risk_level", "") or "").strip()
        motivation_parts = [
            part
            for part in [
                f"goal={goal}" if goal else "",
                f"tactic={tactic}" if tactic else "",
                (f"emotional_driver={emotional_driver}" if emotional_driver else ""),
                f"risk_level={risk_level}" if risk_level else "",
            ]
            if part
        ]
        if motivation_parts:
            human_readable_parts.append("Motivation: " + "; ".join(motivation_parts))

    raw = str(raw_response or "").strip()
    if raw:
        details["raw_response"] = raw

    if human_readable_parts:
        details["attempted_message"] = "\n".join(human_readable_parts)

    return details


def parse_json_payload(content: str) -> tuple[dict[str, Any] | None, str]:
    """Parse a single JSON object (director, etc.): fenced unwrap + duplicate-key–safe load."""
    json_str, uerr = unwrap_fenced_json_object(content)
    if uerr:
        return None, uerr
    try:
        data = load_json_object_duplicate_safe(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"Invalid JSON: {e}"
    except Exception as e:
        return None, f"Parse error: {e}"
    if not isinstance(data, dict):
        return None, "JSON payload must be an object"
    return data, ""


def parse_character_move(content: str) -> tuple[dict | None, str]:
    """Canonical v2 only on success (legacy v1 at ingress is normalized in-place)."""
    return parse_character_move_content_to_v2(content)


def _resolve_next_actor_to_allowed(
    next_actor: Any, allowed_actors: list[str]
) -> str | None:
    """If ``next_actor`` is an exact allowed key, or equals ``make_agent_identifier``
    of an allowed key, or ``make_agent_identifier(next_actor)`` is in allowed, return
    that allowed key. Otherwise None. No fuzzy matching."""
    from character_loader import make_agent_identifier

    na = str(next_actor or "").strip()
    if not na:
        return None
    allowed = [str(a).strip() for a in allowed_actors if (a or "").strip()]
    if not allowed:
        return None
    if na in allowed:
        return na
    derived = make_agent_identifier(na)
    if derived in allowed:
        return derived
    return None


def parse_director_decision(
    content: str,
    participant_names: list[str],
    available_actors: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    data, error = parse_json_payload(content)
    if error or data is None:
        return None, error

    allowed_actors = [
        str(a).strip()
        for a in (
            available_actors
            if available_actors is not None
            else participant_names
        )
        if (a or "").strip()
    ]
    end_round = bool(data.get("end_round"))
    raw_next = data.get("next_actor")
    if end_round and not raw_next:
        next_actor = ""
    else:
        canonical = _resolve_next_actor_to_allowed(raw_next, allowed_actors)
        if canonical is None:
            return None, f"Invalid next_actor: {raw_next!r}"
        next_actor = canonical

    if next_actor not in allowed_actors and not (end_round and next_actor == ""):
        return None, f"Invalid next_actor: {next_actor!r}"

    return {
        "next_actor": next_actor,
        "environment_event": str(data.get("environment_event", "") or ""),
        "tension_shift": str(data.get("tension_shift", "") or ""),
        "reason": str(data.get("reason", data.get("reason_for_choice", "")) or ""),
        "end_round": end_round,
    }, ""
