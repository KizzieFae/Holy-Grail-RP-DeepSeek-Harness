"""Deterministic promotion policy for durable scope knowledge."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_state_canon import CanonAnchor  # noqa: E402

from .scope_knowledge_repository import (  # noqa: E402
    LEARNED_WORLD_KNOWLEDGE,
    USER_PROFILE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)

ALLOWED_USER_PROFILE_KEYS = frozenset(
    {
        "preferred_name",
        "interaction_preference",
    }
)


def _visibility_for_world_anchor(
    anchor: CanonAnchor,
    *,
    character_file_ids: dict[str, str],
) -> tuple[str, str | None]:
    subject = str(anchor.subject or "").strip()
    if subject and subject in character_file_ids:
        return "character_scoped", character_file_ids[subject]
    return "scope_global", None


def build_learned_world_records(
    fixture: Any,
    *,
    source_domain_commit_id: str,
) -> list[ScopeKnowledgeRecord]:
    scope_id = str(getattr(fixture, "memory_scope_id", "") or "").strip()
    if not scope_id:
        return []

    mgr = fixture.manager
    anchors = list(getattr(mgr, "canon_anchors", []) or [])
    character_file_ids = dict(getattr(fixture, "character_file_ids", {}) or {})
    records: list[ScopeKnowledgeRecord] = []

    for anchor in anchors:
        if not isinstance(anchor, CanonAnchor):
            continue
        if str(anchor.category or "").strip() != "world_fact":
            continue
        statement = str(anchor.statement or "").strip()
        if not statement:
            continue
        visibility, subject_file_id = _visibility_for_world_anchor(
            anchor,
            character_file_ids=character_file_ids,
        )
        knowledge_id = ScopeKnowledgeRepository.make_knowledge_id(
            parts=[
                scope_id,
                LEARNED_WORLD_KNOWLEDGE,
                str(anchor.anchor_id),
            ]
        )
        records.append(
            ScopeKnowledgeRecord(
                knowledge_id=knowledge_id,
                scope_id=scope_id,
                knowledge_kind=LEARNED_WORLD_KNOWLEDGE,
                content=statement,
                authority_class="suggestive",
                visibility=visibility,
                subject_character_file_id=subject_file_id,
                source_kind="canon_anchor",
                source_session_id=fixture.hg_session_id,
                source_domain_commit_id=source_domain_commit_id,
                source_continuity_anchor_id=str(anchor.anchor_id),
                created_at=ScopeKnowledgeRepository.now_iso(),
                provenance={
                    "knowledge_lane": "learned_world_knowledge",
                    "anchor_category": anchor.category,
                    "anchor_subject": anchor.subject,
                    "anchor_source": anchor.source,
                    "authority_note": "reference_derived_from_continuity_not_independent_canon",
                },
            )
        )
    return records


def build_user_profile_record(
    fixture: Any,
    *,
    profile_key: str,
    content: str,
    user_persona_id: str,
) -> ScopeKnowledgeRecord:
    scope_id = str(getattr(fixture, "memory_scope_id", "") or "").strip()
    if not scope_id:
        raise ValueError("memory_scope_id is required for user profile facts")
    key = str(profile_key or "").strip()
    if key not in ALLOWED_USER_PROFILE_KEYS:
        raise ValueError(f"unsupported user profile key: {key}")
    text = str(content or "").strip()
    if not text:
        raise ValueError("user profile content is required")
    persona = str(user_persona_id or "").strip()
    if not persona:
        raise ValueError("user_persona_id is required")

    knowledge_id = ScopeKnowledgeRepository.make_knowledge_id(
        parts=[scope_id, USER_PROFILE, key, persona]
    )
    return ScopeKnowledgeRecord(
        knowledge_id=knowledge_id,
        scope_id=scope_id,
        knowledge_kind=USER_PROFILE,
        content=text,
        authority_class="suggestive",
        visibility="scope_global",
        source_kind="explicit_user_profile",
        source_session_id=fixture.hg_session_id,
        profile_key=key,
        user_persona_id=persona,
        created_at=ScopeKnowledgeRepository.now_iso(),
        provenance={
            "knowledge_lane": "user_profile",
            "profile_key": key,
            "authority_note": "user_profile_not_world_canon",
        },
    )


def anchor_still_active(anchor: CanonAnchor, record: ScopeKnowledgeRecord) -> bool:
    statement = str(anchor.statement or "").strip()
    return statement == str(record.content or "").strip()


def filter_active_learned_world_records(
    fixture: Any,
    records: list[ScopeKnowledgeRecord],
) -> list[ScopeKnowledgeRecord]:
    mgr = fixture.manager
    anchors = {
        str(anchor.anchor_id): anchor
        for anchor in getattr(mgr, "canon_anchors", []) or []
        if isinstance(anchor, CanonAnchor)
    }
    active: list[ScopeKnowledgeRecord] = []
    for record in records:
        anchor_id = record.source_continuity_anchor_id
        if not anchor_id:
            continue
        anchor = anchors.get(anchor_id)
        if anchor is None:
            active.append(record)
            continue
        if not anchor_still_active(anchor, record):
            continue
        active.append(record)
    return active


def upsert_canon_anchor_for_test(
    manager: Any,
    *,
    anchor_id: str,
    statement: str,
    subject: str = "Scene",
    category: str = "world_fact",
) -> CanonAnchor:
    from continuity_canon_anchors import upsert_canon_anchor

    anchor = CanonAnchor(
        anchor_id=anchor_id,
        category=category,
        subject=subject,
        statement=statement,
        source="domain_commit",
        established_at=datetime.now(timezone.utc),
    )
    upsert_canon_anchor(manager, anchor)
    return anchor
