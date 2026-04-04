"""Phase 3.2: episodic candidate pool cache keyed by a deterministic continuity snapshot.

Read-only with respect to continuity: only reads inputs and optional session cache dict.
Invalidation is implicit when the snapshot key changes; explicit clear for session resets.

Wired into character prompt assembly in ``app_turn_prompting.build_character_turn_prompt`` when
``RP_EPISODIC_MEMORY`` is ``1``/``true``/``yes`` (see ``episodic_memory_prompt.is_episodic_memory_enabled``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, MutableMapping, Sequence
from datetime import datetime, timezone
from typing import Any

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    IssueState,
    PublicEvent,
)

from episodic_memory_compile import EpisodicCompiledItem, compile_episodic_candidates

# Single session_state entry to avoid scattering keys.
EPISODIC_CANDIDATE_CACHE_STATE_KEY = "episodic_memory_candidate_cache"


def _dt_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _snapshot_public_event(ev: PublicEvent) -> dict[str, Any]:
    """Fields that affect compile_episodic_candidates for events."""
    return {
        "canon_impact": sorted(str(x) for x in ev.canon_impact if str(x).strip()),
        "event_id": str(ev.event_id or ""),
        "event_type": str(ev.event_type or ""),
        "known_by": sorted(str(x).strip() for x in ev.known_by if str(x).strip()),
        "participants": sorted(str(x).strip() for x in ev.participants if str(x).strip()),
        "significance": str(ev.significance or ""),
        "summary": str(ev.summary or ""),
        "timestamp": _dt_iso(ev.timestamp),
        "turn_index": ev.turn_index,
    }


def _snapshot_interpretation(it: CharacterInterpretation) -> dict[str, Any]:
    return {
        "character_name": str(it.character_name or ""),
        "confidence": str(it.confidence or ""),
        "emotional_reaction": str(it.emotional_reaction or ""),
        "formed_at": _dt_iso(it.formed_at),
        "interpretation": str(it.interpretation or ""),
        "interpretation_id": str(it.interpretation_id or ""),
        "last_reinforced": (
            _dt_iso(it.last_reinforced) if it.last_reinforced is not None else None
        ),
        "subject_id": str(it.subject_id or ""),
        "subject_type": str(it.subject_type or ""),
    }


def _snapshot_issue(isu: IssueState) -> dict[str, Any]:
    st = isu.status
    status_val = st.value if hasattr(st, "value") else str(st)
    return {
        "blocked_characters": sorted(
            str(x).strip() for x in isu.blocked_characters if str(x).strip()
        ),
        "created_at": _dt_iso(isu.created_at),
        "description": str(isu.description or ""),
        "issue_id": str(isu.issue_id or ""),
        "last_turn_index": isu.last_turn_index,
        "last_updated": (
            _dt_iso(isu.last_updated) if isu.last_updated is not None else None
        ),
        "participants": sorted(
            str(x).strip() for x in isu.participants if str(x).strip()
        ),
        "status": status_val,
    }


def _snapshot_anchor(an: CanonAnchor) -> dict[str, Any]:
    return {
        "anchor_id": str(an.anchor_id or ""),
        "category": str(an.category or ""),
        "established_at": _dt_iso(an.established_at),
        "statement": str(an.statement or ""),
        "subject": str(an.subject or ""),
    }


def build_episodic_snapshot_payload(
    *,
    public_events: Sequence[PublicEvent],
    interpretations: Sequence[CharacterInterpretation],
    issues: Sequence[IssueState],
    canon_anchors: Sequence[CanonAnchor],
) -> dict[str, Any]:
    """Canonical JSON-serializable payload (sorted child lists) for hashing."""
    evs = sorted(public_events, key=lambda e: str(e.event_id or ""))
    ints = sorted(interpretations, key=lambda i: str(i.interpretation_id or ""))
    iss = sorted(issues, key=lambda i: str(i.issue_id or ""))
    anc = sorted(canon_anchors, key=lambda a: str(a.anchor_id or ""))
    return {
        "anchors": [_snapshot_anchor(a) for a in anc],
        "events": [_snapshot_public_event(e) for e in evs],
        "interpretations": [_snapshot_interpretation(i) for i in ints],
        "issues": [_snapshot_issue(i) for i in iss],
    }


def compute_episodic_snapshot_key(
    *,
    public_events: Sequence[PublicEvent],
    interpretations: Sequence[CharacterInterpretation],
    issues: Sequence[IssueState],
    canon_anchors: Sequence[CanonAnchor],
) -> str:
    """Deterministic SHA-256 hex digest of continuity inputs relevant to episodic compile."""
    payload = build_episodic_snapshot_payload(
        public_events=public_events,
        interpretations=interpretations,
        issues=issues,
        canon_anchors=canon_anchors,
    )
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def clear_episodic_pool_cache(session_state: MutableMapping[str, Any]) -> None:
    """Remove cached episodic pool (e.g. new scene or session reset)."""
    session_state.pop(EPISODIC_CANDIDATE_CACHE_STATE_KEY, None)


def get_or_compile_episodic_candidate_pool(
    session_state: MutableMapping[str, Any],
    *,
    public_events: Sequence[PublicEvent],
    interpretations: Sequence[CharacterInterpretation],
    issues: Sequence[IssueState],
    canon_anchors: Sequence[CanonAnchor],
) -> tuple[EpisodicCompiledItem, ...]:
    """Return cached pool if snapshot key matches; otherwise compile and store.

    Does not modify continuity. Mutates ``session_state`` only to store cache.
    """
    key = compute_episodic_snapshot_key(
        public_events=public_events,
        interpretations=interpretations,
        issues=issues,
        canon_anchors=canon_anchors,
    )
    raw = session_state.get(EPISODIC_CANDIDATE_CACHE_STATE_KEY)
    if isinstance(raw, Mapping):
        cached_key = raw.get("snapshot_key")
        pool = raw.get("pool")
        if cached_key == key and isinstance(pool, tuple):
            if all(isinstance(x, EpisodicCompiledItem) for x in pool):
                return pool
    pool = compile_episodic_candidates(
        public_events=public_events,
        interpretations=interpretations,
        issues=issues,
        canon_anchors=canon_anchors,
    )
    session_state[EPISODIC_CANDIDATE_CACHE_STATE_KEY] = {
        "pool": pool,
        "snapshot_key": key,
    }
    return pool
