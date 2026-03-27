import json
from typing import Any


def build_attempted_post_details(
    raw_response: str = "",
    parsed_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    payload = parsed_output if isinstance(parsed_output, dict) else {}

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
    content = content.strip()

    try:
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif content.startswith("```"):
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None, "No JSON object found"
            json_str = content[start : end + 1]

        data = json.loads(json_str)
        if not isinstance(data, dict):
            return None, "JSON payload must be an object"
        return data, ""
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return None, f"Parse error: {str(e)}"


def parse_character_move(content: str) -> tuple[dict | None, str]:
    data, error = parse_json_payload(content)
    if error or data is None:
        return None, error

    if "action" not in data:
        return None, "Missing 'action' field"

    if "motivation" not in data:
        legacy_intent = str(data.get("intent", "") or "")
        data["motivation"] = {
            "goal": legacy_intent or "advance current objective",
            "tactic": "react in character",
            "emotional_driver": "guarded focus",
            "risk_level": "medium",
        }

    if not isinstance(data.get("motivation"), dict):
        return None, "Field 'motivation' must be an object"

    motivation = data["motivation"]
    motivation.setdefault(
        "goal",
        str(
            data.get("intent", "advance current objective")
            or "advance current objective"
        ),
    )
    motivation.setdefault("tactic", "react in character")
    motivation.setdefault("emotional_driver", "guarded focus")
    motivation.setdefault("risk_level", "medium")
    data["dialogue"] = str(data.get("dialogue", "") or "")

    return data, ""


def parse_director_decision(
    content: str,
    participant_names: list[str],
    available_actors: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    data, error = parse_json_payload(content)
    if error or data is None:
        return None, error

    allowed_actors = (
        available_actors if available_actors is not None else participant_names
    )
    end_round = bool(data.get("end_round"))
    next_actor = data.get("next_actor")
    if end_round and not next_actor:
        next_actor = ""
    if next_actor not in allowed_actors and not (end_round and next_actor == ""):
        return None, f"Invalid next_actor: {next_actor}"

    return {
        "next_actor": next_actor,
        "environment_event": str(data.get("environment_event", "") or ""),
        "tension_shift": str(data.get("tension_shift", "") or ""),
        "reason": str(data.get("reason", data.get("reason_for_choice", "")) or ""),
        "end_round": end_round,
    }, ""
