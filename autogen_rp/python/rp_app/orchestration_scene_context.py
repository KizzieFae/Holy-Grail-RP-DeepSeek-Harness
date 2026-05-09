"""Recent scene context for narrator path (Issue #164)."""

from __future__ import annotations

from typing import Any, Callable

from summary_audit_helpers import build_summary_block_audit_metadata


def build_recent_scene_context(
    *,
    chat_history: list[dict[str, Any]],
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    build_recent_dialogue_history_fn: Callable[
        [list[dict[str, Any]], int], list[dict[str, str]]
    ],
    limit: int = 6,
) -> tuple[str, dict[str, Any]]:
    continuity_snapshot = (
        continuity_manager.get_snapshot() if continuity_manager is not None else None
    )
    orchestration_continuity_context = (
        continuity_manager.get_orchestration_context(
            active_issue_limit=3,
            recent_event_limit=3,
            summary_limit=2,
        )
        if continuity_manager is not None
        else None
    )
    generated_summary_blocks = (
        continuity_manager.summary_blocks[:] if continuity_manager is not None else []
    )
    available_summary_blocks = (
        continuity_manager.retrieve_summary_blocks(limit=0)
        if continuity_manager is not None
        else []
    )
    selected_summary_blocks = (
        orchestration_continuity_context.get("summary_blocks", [])
        if orchestration_continuity_context is not None
        else []
    )
    summary_block_audit = build_summary_block_audit_metadata(
        generated_blocks=generated_summary_blocks,
        available_blocks=available_summary_blocks,
        selected_blocks=selected_summary_blocks,
        selection_reason=(
            "ranked deterministic retrieval for narrator scene context"
            if selected_summary_blocks
            else ""
        ),
        skipped_reason=(
            "Continuity manager unavailable"
            if continuity_manager is None
            else (
                "No summary blocks generated yet"
                if not generated_summary_blocks
                else (
                    "No narrator summary blocks available after retrieval"
                    if not selected_summary_blocks
                    else ""
                )
            )
        ),
        summary_generation_eligible=(
            continuity_manager is not None
            and continuity_manager.summary_interval > 0
            and continuity_manager.turn_counter >= continuity_manager.summary_interval
        ),
        summary_limit=2,
    )
    scene_state = (
        continuity_snapshot.scene_state.to_dict()
        if continuity_snapshot is not None
        else orchestration_state.get("scene_state", {})
    )
    parts: list[str] = []

    opening_description = str(scene_state.get("opening_description", "") or "").strip()
    if opening_description:
        parts.append(f"OPENING DESCRIPTION:\n{opening_description}")

    location = str(scene_state.get("location", "") or "").strip()
    if location:
        parts.append(f"LOCATION:\n{location}")

    environment_description = str(
        scene_state.get("environment_description", "") or ""
    ).strip()
    if environment_description:
        parts.append(f"CURRENT ENVIRONMENT:\n{environment_description}")

    recent_environment_events = scene_state.get("recent_environment_events", [])[-3:]
    if recent_environment_events:
        parts.append(
            "RECENT ENVIRONMENT EVENTS:\n"
            + "\n".join(str(item) for item in recent_environment_events)
        )

    recent_tension = scene_state.get("tension_history", [])[-3:]
    if not recent_tension:
        current_tension_level = str(
            scene_state.get("current_tension_level", "") or ""
        ).strip()
        if current_tension_level:
            recent_tension = [current_tension_level]
    if recent_tension:
        parts.append(
            "RECENT TENSION SHIFTS:\n" + "\n".join(str(item) for item in recent_tension)
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("active_issues")
    ):
        parts.append(
            "ACTIVE ISSUES:\n"
            + "\n".join(
                issue.description
                for issue in orchestration_continuity_context.get("active_issues", [])
            )
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("recent_public_events")
    ):
        parts.append(
            "RECENT PUBLIC EVENTS:\n"
            + "\n".join(
                event.summary
                for event in orchestration_continuity_context.get(
                    "recent_public_events", []
                )
            )
        )

    if (
        orchestration_continuity_context is not None
        and orchestration_continuity_context.get("summary_blocks")
    ):
        parts.append(
            "OLDER CONTINUITY SUMMARY BLOCKS:\n"
            + "\n".join(
                "; ".join(summary.key_events)
                for summary in orchestration_continuity_context.get(
                    "summary_blocks", []
                )
            )
        )

    if orchestration_continuity_context is not None:
        scene_canon_anchors = orchestration_continuity_context.get(
            "scene_canon_anchors", []
        )[:4]
        if scene_canon_anchors:
            parts.append(
                "SCENE CANON:\n"
                + "\n".join(anchor.statement for anchor in scene_canon_anchors)
            )

    recent_dialogue = build_recent_dialogue_history_fn(chat_history, limit)
    if recent_dialogue:
        transcript = "\n".join(
            f"{item['speaker']}: {item['content']}" for item in recent_dialogue
        )
        parts.append(f"RECENT TRANSCRIPT:\n{transcript}")

    return "\n\n".join(parts), summary_block_audit
