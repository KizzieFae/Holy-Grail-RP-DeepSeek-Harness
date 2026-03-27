from typing import Any


def get_scene_audit_logging_kwargs(scene_state: Any | None) -> dict[str, Any]:
    if scene_state is None:
        return {
            "scene_template_id": None,
            "scene_premise": "",
            "role_assignments": {},
            "character_presence_constraints": {},
            "character_authority_labels": {},
        }

    return {
        "scene_template_id": getattr(scene_state, "scene_template_id", None),
        "scene_premise": str(getattr(scene_state, "scene_premise", "") or ""),
        "role_assignments": dict(getattr(scene_state, "role_assignments", {}) or {}),
        "character_presence_constraints": dict(
            getattr(scene_state, "character_presence_constraints", {}) or {}
        ),
        "character_authority_labels": dict(
            getattr(scene_state, "character_authority_labels", {}) or {}
        ),
    }


def get_character_scene_audit_context(
    character_name: str,
    scene_audit: dict[str, Any] | None,
) -> dict[str, str]:
    audit_payload = scene_audit if isinstance(scene_audit, dict) else {}
    role_assignments = audit_payload.get("role_assignments", {})
    presence_constraints = audit_payload.get("character_presence_constraints", {})
    authority_labels = audit_payload.get("character_authority_labels", {})
    return {
        "character_role": str(role_assignments.get(character_name, "") or ""),
        "character_presence_constraint": str(
            presence_constraints.get(character_name, "") or ""
        ),
        "character_authority_label": str(
            authority_labels.get(character_name, "") or ""
        ),
    }


def serialize_events_for_prompt(
    events: list[Any], character_name: str | None = None
) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for event in events:
        if not hasattr(event, "to_dict"):
            continue
        payload = event.to_dict()
        if character_name is not None and hasattr(event, "knowledge_level_for"):
            payload["knowledge_level"] = event.knowledge_level_for(character_name)
        serialized.append(payload)
    return serialized


def serialize_canon_anchors_for_prompt(anchors: list[Any]) -> list[dict[str, Any]]:
    return [anchor.to_dict() for anchor in anchors if hasattr(anchor, "to_dict")]


def serialize_summary_blocks_for_prompt(
    summary_blocks: list[Any],
) -> list[dict[str, Any]]:
    return [
        summary.to_dict() for summary in summary_blocks if hasattr(summary, "to_dict")
    ]


def get_summary_block_id(summary_block: Any) -> str:
    if hasattr(summary_block, "summary_id"):
        return str(getattr(summary_block, "summary_id", "") or "")
    if isinstance(summary_block, dict):
        return str(summary_block.get("summary_id", "") or "")
    return ""


def build_summary_block_audit_metadata(
    *,
    generated_blocks: list[Any],
    available_blocks: list[Any],
    selected_blocks: list[Any],
    selection_reason: str = "",
    skipped_reason: str = "",
    fallback_used: bool = False,
    summary_generation_eligible: bool = False,
    summary_limit: int | None = None,
) -> dict[str, Any]:
    generated_ids = [
        summary_id
        for summary_id in [get_summary_block_id(block) for block in generated_blocks]
        if summary_id
    ]
    available_ids = [
        summary_id
        for summary_id in [get_summary_block_id(block) for block in available_blocks]
        if summary_id
    ]
    selected_ids = [
        summary_id
        for summary_id in [get_summary_block_id(block) for block in selected_blocks]
        if summary_id
    ]
    excluded_ids = [
        summary_id for summary_id in available_ids if summary_id not in selected_ids
    ]
    return {
        "summary_generation_eligible": bool(summary_generation_eligible),
        "summary_blocks_generated_total": len(generated_ids),
        "generated_summary_block_ids": generated_ids,
        "summary_blocks_available_count": len(available_ids),
        "available_summary_block_ids": available_ids,
        "summary_blocks_selected_count": len(selected_ids),
        "selected_summary_block_ids": selected_ids,
        "excluded_summary_block_ids": excluded_ids,
        "selection_reason": selection_reason,
        "skipped_reason": skipped_reason,
        "fallback_used": bool(fallback_used),
        "summary_limit": summary_limit,
    }
