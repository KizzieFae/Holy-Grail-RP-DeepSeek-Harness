"""Initialization source snapshot gathering for Plot Cognition (#60)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .plot_cognition_initialization_contract import (
    INITIALIZATION_SOURCE_SNAPSHOT_SCHEMA,
    InitializationSourceSnapshot,
    OpeningCompleteness,
    new_snapshot_id,
)
from .session_state import LiveSession


def _opening_entry(fixture: LiveSession) -> dict[str, Any] | None:
    entry_id = f"opening-{fixture.hg_session_id}"
    for item in fixture.rp_history:
        if item.get("entry_id") == entry_id or item.get("kind") == "opening":
            return dict(item)
    return None


def resolve_opening_completeness(
    opening_mode: str,
    *,
    opening_entry: dict[str, Any] | None,
) -> OpeningCompleteness:
    mode = str(opening_mode or "minimal").strip().lower()
    if mode == "generated":
        return "prose_present" if opening_entry is not None else "prose_pending"
    if mode in {"custom", "template"}:
        return "prose_present" if opening_entry is not None else "prose_not_expected"
    return "prose_not_expected"


def initialization_sources_complete(opening_completeness: OpeningCompleteness) -> bool:
    return opening_completeness != "prose_pending"


def _character_source_digest(display_name: str, card: dict[str, Any], state: Any) -> dict[str, Any]:
    relationships = card.get("relationships") or {}
    if hasattr(state, "relationships"):
        relationships = getattr(state, "relationships", relationships)
    return {
        "display_name": display_name,
        "file_id": None,
        "description_digest": _digest_text(card.get("description")),
        "personality_digest": _digest_text(card.get("personality")),
        "goals_digest": _digest_text(card.get("goals")),
        "medium_term_goal_digest": _digest_text(card.get("medium_term_goal")),
        "core_goals_digest": _digest_json(card.get("core_goals")),
        "relationships_digest": _digest_json(relationships),
        "state_goals_digest": _digest_text(getattr(state, "long_term_goal", "")),
        "state_medium_term_goal_digest": _digest_text(getattr(state, "medium_term_goal", "")),
        "state_core_goals_digest": _digest_json(getattr(state, "core_goals", [])),
    }


def _digest_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_json(value: Any) -> str:
    if value is None:
        return ""
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _continuity_digest(fixture: LiveSession) -> dict[str, Any]:
    mgr = fixture.manager
    scene_state = getattr(mgr, "scene_state", None)
    issues = getattr(mgr, "issues", {}) or {}
    issue_ids = sorted(str(key) for key in issues.keys())
    return {
        "location": str(getattr(scene_state, "location", "") or ""),
        "opening_description_digest": _digest_text(
            getattr(scene_state, "opening_description", "")
        ),
        "present_characters": sorted(
            str(name) for name in (getattr(scene_state, "present_characters", None) or fixture.cast)
        ),
        "initial_issue_ids": issue_ids,
    }


def build_canonical_source_body(fixture: LiveSession) -> dict[str, Any]:
    snapshot = dict(fixture.setup_snapshot or {})
    opening_meta = dict(snapshot.get("opening") or {})
    opening_mode = str(opening_meta.get("mode", "minimal") or "minimal").strip().lower()
    opening_entry = _opening_entry(fixture)
    opening_completeness = resolve_opening_completeness(
        opening_mode,
        opening_entry=opening_entry,
    )

    cards = dict(snapshot.get("character_cards") or {})
    characters: list[dict[str, Any]] = []
    for display_name in fixture.cast:
        file_id = fixture.character_file_ids.get(display_name)
        card = dict(cards.get(file_id or "", {}) or {})
        state = fixture.character_states.get(display_name)
        digest = _character_source_digest(display_name, card, state)
        digest["file_id"] = file_id
        characters.append(digest)

    scene_template = dict(snapshot.get("scene_template") or {})
    opening_body: dict[str, Any] | None = None
    if opening_entry is not None:
        opening_body = {
            "entry_id": str(opening_entry.get("entry_id") or ""),
            "presentation_status": str(opening_entry.get("presentation_status") or ""),
            "content_digest": _digest_text(opening_entry.get("content")),
        }

    return {
        "plot_cognition_scope_id": str(fixture.plot_cognition_scope_id or ""),
        "session_id": fixture.hg_session_id,
        "opening_mode": opening_mode,
        "opening_completeness": opening_completeness,
        "opening_entry_id": opening_body.get("entry_id") if opening_body else None,
        "template_id": str(snapshot.get("scene_template_id") or scene_template.get("template_id") or ""),
        "premise_digest": _digest_text(scene_template.get("premise")),
        "location": str(snapshot.get("location") or ""),
        "characters": characters,
        "continuity": _continuity_digest(fixture),
        "opening": opening_body,
    }


def compute_source_fingerprint(canonical_body: dict[str, Any]) -> str:
    payload = json.dumps(canonical_body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def gather_initialization_sources(fixture: LiveSession) -> InitializationSourceSnapshot:
    canonical_body = build_canonical_source_body(fixture)
    fingerprint = compute_source_fingerprint(canonical_body)
    return InitializationSourceSnapshot(
        schema=INITIALIZATION_SOURCE_SNAPSHOT_SCHEMA,
        snapshot_id=new_snapshot_id(),
        fingerprint=fingerprint,
        plot_cognition_scope_id=str(fixture.plot_cognition_scope_id or ""),
        session_id=fixture.hg_session_id,
        opening_mode=str(canonical_body.get("opening_mode") or "minimal"),
        opening_completeness=str(canonical_body.get("opening_completeness") or "prose_not_expected"),  # type: ignore[arg-type]
        opening_entry_id=canonical_body.get("opening_entry_id"),
        canonical_body=canonical_body,
    )
