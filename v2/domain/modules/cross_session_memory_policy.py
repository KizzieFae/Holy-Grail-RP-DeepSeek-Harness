"""Thin policy layer for cross-session memory: env toggles, promotion filter, audit/log helpers."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)

# RP_CROSS_SESSION_MEMORY=0 disables load/apply (card-only for aggregation layer).
# RP_CROSS_SESSION_PROMOTE_FILTER=0 disables aggregation-time promotion filter (keep all strings).
_ENV_TRUTHY = {"1", "true", "yes", "on"}
_ENV_FALSY = {"0", "false", "no", "off"}


def is_cross_session_memory_enabled() -> bool:
    raw = os.environ.get("RP_CROSS_SESSION_MEMORY", "1").strip().lower()
    if raw in _ENV_FALSY:
        return False
    return True


def is_cross_session_promote_filter_enabled() -> bool:
    raw = os.environ.get("RP_CROSS_SESSION_PROMOTE_FILTER", "1").strip().lower()
    if raw in _ENV_FALSY:
        return False
    return True


_INTERACTION_MARKERS = (
    " said ",
    " did ",
    " refused ",
    " agreed ",
    " learned ",
    " promised ",
    " told ",
    " asked ",
    " answered ",
    " challenged ",
    " denied ",
    " revealed ",
    " left ",
    " arrived ",
    " attacked ",
    " escaped ",
    "traveler said or signaled:",
    " said or signaled:",
    "goal=",
    "tactic=",
)


def should_promote_cross_session(text: str, memory_type: str) -> bool:
    """Keep lines with an interaction/consequence signal; drop purely descriptive text.

    World facts, user preferences, and session summaries are always promoted.
    """
    if not is_cross_session_promote_filter_enabled():
        return True
    mt = (memory_type or "").strip().lower()
    if mt in (
        "persistent_world_fact",
        "user_preference",
        "session_summary",
        "relationship_snapshot",
        "relationship_trend",
    ):
        return True
    raw = str(text or "").strip()
    if not raw:
        return False
    padded = f" {raw.lower()} "
    return any(marker in padded for marker in _INTERACTION_MARKERS)


def empty_cross_session_payload(character_names: list[str]) -> dict[str, Any]:
    names = [str(n) for n in character_names if str(n).strip()]
    return {
        "session_summaries": [],
        "persistent_world_facts": [],
        "user_preferences": [],
        "character_user_memories": {name: [] for name in names},
        "cross_session_relationships": {name: {} for name in names},
        "relationship_trends": {name: {} for name in names},
        "indexed_session_count": 0,
        "_cross_session_enabled": False,
    }


def new_injection_report(
    *,
    cross_session_memory_enabled: bool,
    exclude_session_id: str | None,
    indexed_session_count: int,
) -> dict[str, Any]:
    return {
        "version": 1,
        "persistence_scope": "cross_session",
        "cross_session_memory_enabled": cross_session_memory_enabled,
        "exclude_session_id": exclude_session_id,
        "indexed_session_count": indexed_session_count,
        "load_items": [],
        "load_items_filtered": [],
        "apply_items": [],
    }


def append_load_item(
    report: dict[str, Any],
    *,
    memory_type: str,
    injection_reason: str,
    source_session_id: str,
    target_character: str | None,
    preview: str,
    prompt_destination: list[str],
    promoted: bool,
) -> None:
    entry: dict[str, Any] = {
        "memory_type": memory_type,
        "injection_reason": injection_reason,
        "source_session_id": source_session_id,
        "target_character": target_character,
        "preview": preview[:240],
        "prompt_destination": list(prompt_destination),
        "persistence_scope": "cross_session",
        "stage": "load",
        "promoted": promoted,
    }
    if promoted:
        report.setdefault("load_items", []).append(entry)
    else:
        report.setdefault("load_items_filtered", []).append(entry)


def append_apply_item(
    report: dict[str, Any],
    *,
    memory_type: str,
    injection_reason: str,
    source_session_id: str | None,
    target_character: str | None,
    preview: str,
    prompt_destination: list[str],
) -> None:
    report.setdefault("apply_items", []).append(
        {
            "memory_type": memory_type,
            "injection_reason": injection_reason,
            "source_session_id": source_session_id,
            "target_character": target_character,
            "preview": preview[:240],
            "prompt_destination": list(prompt_destination),
            "persistence_scope": "cross_session",
            "stage": "apply",
            "promoted": True,
        }
    )


def compact_report_for_audit(
    report: dict[str, Any],
    *,
    max_items_per_section: int = 40,
    preview_len: int = 96,
) -> dict[str, Any]:
    """Smaller payload for audit JSON."""

    def _trim_items(items: list[Any]) -> list[Any]:
        out = []
        for item in items[:max_items_per_section]:
            if not isinstance(item, dict):
                continue
            d = dict(item)
            prev = str(d.get("preview", "") or "")
            if len(prev) > preview_len:
                d["preview"] = prev[:preview_len] + "…"
            out.append(d)
        return out

    return {
        "version": report.get("version"),
        "persistence_scope": report.get("persistence_scope"),
        "cross_session_memory_enabled": report.get("cross_session_memory_enabled"),
        "exclude_session_id": report.get("exclude_session_id"),
        "indexed_session_count": report.get("indexed_session_count"),
        "load_item_count": len(report.get("load_items") or []),
        "load_filtered_count": len(report.get("load_items_filtered") or []),
        "apply_item_count": len(report.get("apply_items") or []),
        "load_items": _trim_items(list(report.get("load_items") or [])),
        "load_items_filtered": _trim_items(list(report.get("load_items_filtered") or [])),
        "apply_items": _trim_items(list(report.get("apply_items") or [])),
    }


def log_cross_session_report(report: dict[str, Any]) -> None:
    try:
        payload = compact_report_for_audit(report, max_items_per_section=25, preview_len=80)
        _logger.info("[cross_session] %s", json.dumps(payload, ensure_ascii=False))
    except (TypeError, ValueError):
        _logger.info("[cross_session] report_logging_failed")
