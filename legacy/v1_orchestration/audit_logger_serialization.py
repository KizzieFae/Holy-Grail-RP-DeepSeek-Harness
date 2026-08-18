from datetime import UTC, datetime
from typing import Any

from character_move_adapters import root_or_flat_action_text, root_or_flat_dialogue_text


def entry_to_full_dict(entry: Any) -> dict[str, Any]:
    out = {
        "timestamp": entry.timestamp,
        "session_owner": entry.session_owner,
        "session_number": entry.session_number,
        "round_number": entry.round_number,
        "turn_number": entry.turn_number,
        "bot_name": entry.bot_name,
        "bot_type": entry.bot_type,
        "input_messages": entry.input_messages,
        "raw_response": entry.raw_response,
        "parsed_output": entry.parsed_output,
        "context_snapshot": entry.context_snapshot,
        "metadata": entry.metadata,
    }
    out["effective_user_trigger"] = getattr(entry, "effective_user_trigger", None)
    md = out.get("metadata") if isinstance(out.get("metadata"), dict) else {}
    for key in (
        "overlay_schedule_mode",
        "overlay_target_actor",
        "overlay_applied",
        "overlay_skipped_reason",
    ):
        if isinstance(md, dict) and key in md:
            out[key] = md.get(key)
    return out


def entry_to_light_dict(entry: Any) -> dict[str, Any]:
    light_inputs = [
        {
            "role": msg.get("role", "unknown"),
            "content_length": len(str(msg.get("content", ""))),
            "content_preview": (
                str(msg.get("content", ""))[:200] + "..."
                if len(str(msg.get("content", ""))) > 200
                else str(msg.get("content", ""))
            ),
        }
        for msg in entry.input_messages
    ]

    po = entry.parsed_output if isinstance(entry.parsed_output, dict) else {}
    light_output = {
        "type": entry.bot_type,
        "has_environment_event": bool(po.get("environment_event")),
        "has_tension_shift": bool(po.get("tension_shift")),
        "key_fields": list(po.keys())[:5],
        "action_preview": str(root_or_flat_action_text(po))[:100],
        "dialogue_preview": str(root_or_flat_dialogue_text(po))[:100],
    }

    out: dict[str, Any] = {
        "timestamp": entry.timestamp,
        "session_owner": entry.session_owner,
        "session_number": entry.session_number,
        "round_number": entry.round_number,
        "turn_number": entry.turn_number,
        "bot_name": entry.bot_name,
        "bot_type": entry.bot_type,
        "input_summary": light_inputs,
        "output_summary": light_output,
        "raw_response_length": len(entry.raw_response),
        "word_count": len(entry.raw_response.split()),
        "metadata_keys": list(entry.metadata.keys()),
    }
    if entry.bot_type in ("character", "character_failure") and isinstance(
        entry.metadata, dict
    ):
        if "has_binding_constraints" in entry.metadata:
            out["has_binding_constraints"] = bool(
                entry.metadata.get("has_binding_constraints")
            )
        bc = entry.metadata.get("scene_binding_constraints_section")
        if isinstance(bc, str) and bc.strip():
            out["scene_binding_constraints_section"] = bc
        im0 = (
            entry.input_messages[0]
            if entry.input_messages
            and isinstance(entry.input_messages[0], dict)
            else None
        )
        if im0 and str(im0.get("role", "")).strip() == "system":
            content = str(im0.get("content", "") or "")
            out["character_system_prompt_length"] = len(content)
            out["character_system_prompt_contains_binding_header"] = (
                "BINDING CONSTRAINTS" in content
            )
    return out


def normalize_string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, item in value.items():
        normalized_key = str(key or "").strip()
        if not normalized_key:
            continue
        normalized[normalized_key] = str(item or "").strip()
    return normalized


def normalize_scene_template_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    return {
        "template_id": str(value.get("template_id", "") or ""),
        "premise": str(value.get("premise", "") or ""),
        "role_assignments": normalize_string_mapping(value.get("role_assignments", {})),
        "character_presence_constraints": normalize_string_mapping(
            value.get("character_presence_constraints", {})
        ),
        "character_authority_labels": normalize_string_mapping(
            value.get("character_authority_labels", {})
        ),
        "location_entry_slots": [
            str(item)
            for item in value.get("location_entry_slots", [])
            if str(item or "").strip()
        ],
    }


def empty_summary_block_visibility() -> dict[str, Any]:
    return {
        "prompt_evaluations": 0,
        "prompt_evaluations_generation_eligible": 0,
        "summary_blocks_generated_total_max": 0,
        "summary_blocks_used_total": 0,
        "prompt_evaluations_with_summary_available": 0,
        "prompt_evaluations_with_summary_injection": 0,
        "first_prompt_with_summary_block": None,
        "prompt_evaluations_where_summary_was_available_but_not_used": [],
        "prompt_evaluations_with_fallback_selection": [],
    }


def normalize_summary_block_metadata(metadata: Any) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None

    return {
        "summary_generation_eligible": bool(
            metadata.get("summary_generation_eligible", False)
        ),
        "summary_blocks_generated_total": int(
            metadata.get("summary_blocks_generated_total", 0) or 0
        ),
        "generated_summary_block_ids": [
            str(item)
            for item in metadata.get("generated_summary_block_ids", [])
            if str(item).strip()
        ],
        "summary_blocks_available_count": int(
            metadata.get("summary_blocks_available_count", 0) or 0
        ),
        "available_summary_block_ids": [
            str(item)
            for item in metadata.get("available_summary_block_ids", [])
            if str(item).strip()
        ],
        "summary_blocks_selected_count": int(
            metadata.get("summary_blocks_selected_count", 0) or 0
        ),
        "selected_summary_block_ids": [
            str(item)
            for item in metadata.get("selected_summary_block_ids", [])
            if str(item).strip()
        ],
        "excluded_summary_block_ids": [
            str(item)
            for item in metadata.get("excluded_summary_block_ids", [])
            if str(item).strip()
        ],
        "selection_reason": str(metadata.get("selection_reason", "") or ""),
        "skipped_reason": str(metadata.get("skipped_reason", "") or ""),
        "fallback_used": bool(metadata.get("fallback_used", False)),
        "summary_limit": metadata.get("summary_limit"),
    }


def prompt_reference(
    round_number: int, turn_number: int, bot_name: str
) -> dict[str, Any]:
    return {
        "round_number": round_number,
        "turn_number": turn_number,
        "bot_name": bot_name,
    }


def append_limited(
    target: list[dict[str, Any]], value: dict[str, Any], limit: int = 20
) -> None:
    if value not in target:
        target.append(value)
        del target[limit:]


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
