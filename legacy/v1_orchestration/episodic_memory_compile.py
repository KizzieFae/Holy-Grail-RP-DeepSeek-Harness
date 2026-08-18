"""Phase 3.2: deterministic episodic memory candidate compilation (read-only).

Compiles non-authoritative recall lines from explicit continuity rows only:
PublicEvent, CharacterInterpretation, IssueState, CanonAnchor.

No continuity writes, no LLM usage, no inference beyond fixed templates.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    IssueState,
    IssueStatus,
    PublicEvent,
)

_ORIGIN_EVENT: Literal["event"] = "event"
_ORIGIN_INTERPRETATION: Literal["interpretation"] = "interpretation"
_ORIGIN_ISSUE: Literal["issue"] = "issue"
_ORIGIN_ANCHOR: Literal["anchor"] = "anchor"

EpisodicOriginType = Literal["event", "interpretation", "issue", "anchor"]

_MAX_SUMMARY_CHARS = 240


def _utc_ts(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _truncate_field(text: str, *, max_chars: int = _MAX_SUMMARY_CHARS) -> str:
    s = " ".join(str(text or "").split())
    if len(s) <= max_chars:
        return s
    if max_chars <= 3:
        return s[:max_chars]
    return s[: max_chars - 3].rstrip() + "..."


def _event_salience(event: PublicEvent) -> int:
    sig = str(event.significance or "minor").strip().lower()
    if sig == "pivotal":
        return 60
    if sig == "major":
        return 40
    return 20


def _event_recency_key(event: PublicEvent) -> int:
    ti = event.turn_index if event.turn_index is not None else -1
    return ti * 1_000_000_000 + _utc_ts(event.timestamp)


def _issue_salience(issue: IssueState) -> int:
    st = issue.status
    if st in (IssueStatus.ACTIVE, IssueStatus.ESCALATING):
        return 80
    if st == IssueStatus.STALLED:
        return 50
    return 20


def _issue_recency_key(issue: IssueState) -> int:
    ti = issue.last_turn_index if issue.last_turn_index is not None else -1
    base = issue.last_updated or issue.created_at
    return ti * 1_000_000_000 + _utc_ts(base)


def _interpretation_salience(interp: CharacterInterpretation) -> int:
    c = str(interp.confidence or "tentative").strip().lower()
    if c == "certain":
        return 45
    if c == "confident":
        return 35
    return 25


def _interpretation_recency_key(interp: CharacterInterpretation) -> int:
    base = interp.last_reinforced or interp.formed_at
    return _utc_ts(base)


def _anchor_salience(_anchor: CanonAnchor) -> int:
    return 55


def _anchor_recency_key(anchor: CanonAnchor) -> int:
    return _utc_ts(anchor.established_at)


def _memory_id(
    *,
    origin_type: str,
    source_ref: str,
    summary_text: str,
    salience: int,
    recency_key: int,
) -> str:
    payload = "\x1e".join(
        [origin_type, source_ref, summary_text, str(salience), str(recency_key)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _visible_for_public_event(event: PublicEvent) -> frozenset[str] | None:
    known = frozenset(str(x).strip() for x in event.known_by if str(x).strip())
    if not known:
        return None
    return known


def _visible_for_interpretation(interp: CharacterInterpretation) -> frozenset[str] | None:
    name = str(interp.character_name or "").strip()
    if not name:
        return None
    return frozenset({name})


def _visible_for_issue(issue: IssueState) -> frozenset[str] | None:
    names: set[str] = set()
    for item in issue.participants:
        s = str(item).strip()
        if s:
            names.add(s)
    for item in issue.blocked_characters:
        s = str(item).strip()
        if s:
            names.add(s)
    if not names:
        return None
    return frozenset(names)


def _visible_for_anchor(anchor: CanonAnchor) -> frozenset[str] | None:
    cat = str(anchor.category or "").strip().lower()
    subj = str(anchor.subject or "").strip()
    if not subj:
        return None
    if cat == "character_trait":
        return frozenset({subj})
    if cat == "relationship":
        parts = [p.strip() for p in subj.split(",") if p.strip()]
        if not parts:
            return None
        return frozenset(parts)
    return None


def _template_public_event(event: PublicEvent) -> str:
    et = str(event.event_type or "action").strip()
    sig = str(event.significance or "minor").strip()
    body = _truncate_field(event.summary)
    return f"Public event ({et}, {sig}): {body}"


def _template_interpretation(interp: CharacterInterpretation) -> str:
    st = str(interp.subject_type or "event").strip()
    sid = str(interp.subject_id or "").strip()
    interp_txt = _truncate_field(interp.interpretation, max_chars=160)
    emo = _truncate_field(interp.emotional_reaction, max_chars=80)
    return f"Interpretation ({st} {sid}): {interp_txt}; felt: {emo}"


def _template_issue(issue: IssueState) -> str:
    st = issue.status.value if isinstance(issue.status, IssueStatus) else str(issue.status)
    desc = _truncate_field(issue.description)
    return f"Issue {issue.issue_id} ({st}): {desc}"


def _template_anchor(anchor: CanonAnchor) -> str:
    cat = str(anchor.category or "").strip()
    stmt = _truncate_field(anchor.statement)
    return f"Canon ({cat}): {stmt}"


def _involved_from_event(event: PublicEvent) -> tuple[str, ...]:
    names = {str(p).strip() for p in event.participants if str(p).strip()}
    return tuple(sorted(names))


def _involved_from_interpretation(interp: CharacterInterpretation) -> tuple[str, ...]:
    names = {str(interp.character_name or "").strip()}
    sid = str(interp.subject_id or "").strip()
    if sid and str(interp.subject_type or "") == "character":
        names.add(sid)
    names.discard("")
    return tuple(sorted(names))


def _involved_from_issue(issue: IssueState) -> tuple[str, ...]:
    names = {str(p).strip() for p in issue.participants if str(p).strip()}
    return tuple(sorted(names))


def _involved_from_anchor(anchor: CanonAnchor) -> tuple[str, ...]:
    vis = _visible_for_anchor(anchor)
    if vis is None:
        return ()
    return tuple(sorted(vis))


@dataclass(frozen=True)
class EpisodicCompiledItem:
    """Single episodic recall candidate (non-authoritative)."""

    memory_id: str
    origin_type: EpisodicOriginType
    source_ref: str
    memory_type: str
    visible_to: frozenset[str]
    involved_characters: tuple[str, ...]
    summary_text: str
    salience: int
    recency_key: int
    non_authoritative: Literal[True]


def compile_episodic_candidates(
    *,
    public_events: Sequence[PublicEvent],
    interpretations: Sequence[CharacterInterpretation],
    issues: Sequence[IssueState],
    canon_anchors: Sequence[CanonAnchor],
) -> tuple[EpisodicCompiledItem, ...]:
    """Build the full candidate pool from explicit continuity rows (read-only).

    Ordering: descending salience, then descending recency_key, then origin_type,
    then source_ref (lexicographic).
    """
    items: list[EpisodicCompiledItem] = []

    for event in public_events:
        eid = str(event.event_id or "").strip()
        if not eid:
            continue
        if not str(event.summary or "").strip():
            continue
        if event.canon_impact:
            continue
        vis = _visible_for_public_event(event)
        if vis is None:
            continue
        summary_text = _template_public_event(event)
        sal = _event_salience(event)
        rk = _event_recency_key(event)
        mid = _memory_id(
            origin_type=_ORIGIN_EVENT,
            source_ref=eid,
            summary_text=summary_text,
            salience=sal,
            recency_key=rk,
        )
        items.append(
            EpisodicCompiledItem(
                memory_id=mid,
                origin_type=_ORIGIN_EVENT,
                source_ref=eid,
                memory_type="public_event",
                visible_to=vis,
                involved_characters=_involved_from_event(event),
                summary_text=summary_text,
                salience=sal,
                recency_key=rk,
                non_authoritative=True,
            )
        )

    for interp in interpretations:
        iid = str(interp.interpretation_id or "").strip()
        if not iid:
            continue
        if not str(interp.interpretation or "").strip():
            continue
        vis = _visible_for_interpretation(interp)
        if vis is None:
            continue
        summary_text = _template_interpretation(interp)
        sal = _interpretation_salience(interp)
        rk = _interpretation_recency_key(interp)
        mid = _memory_id(
            origin_type=_ORIGIN_INTERPRETATION,
            source_ref=iid,
            summary_text=summary_text,
            salience=sal,
            recency_key=rk,
        )
        items.append(
            EpisodicCompiledItem(
                memory_id=mid,
                origin_type=_ORIGIN_INTERPRETATION,
                source_ref=iid,
                memory_type="interpretation",
                visible_to=vis,
                involved_characters=_involved_from_interpretation(interp),
                summary_text=summary_text,
                salience=sal,
                recency_key=rk,
                non_authoritative=True,
            )
        )

    for issue in issues:
        iid = str(issue.issue_id or "").strip()
        if not iid:
            continue
        if not str(issue.description or "").strip():
            continue
        vis = _visible_for_issue(issue)
        if vis is None:
            continue
        summary_text = _template_issue(issue)
        sal = _issue_salience(issue)
        rk = _issue_recency_key(issue)
        mid = _memory_id(
            origin_type=_ORIGIN_ISSUE,
            source_ref=iid,
            summary_text=summary_text,
            salience=sal,
            recency_key=rk,
        )
        items.append(
            EpisodicCompiledItem(
                memory_id=mid,
                origin_type=_ORIGIN_ISSUE,
                source_ref=iid,
                memory_type="issue",
                visible_to=vis,
                involved_characters=_involved_from_issue(issue),
                summary_text=summary_text,
                salience=sal,
                recency_key=rk,
                non_authoritative=True,
            )
        )

    for anchor in canon_anchors:
        aid = str(anchor.anchor_id or "").strip()
        if not aid:
            continue
        if not str(anchor.statement or "").strip():
            continue
        vis = _visible_for_anchor(anchor)
        if vis is None:
            continue
        summary_text = _template_anchor(anchor)
        sal = _anchor_salience(anchor)
        rk = _anchor_recency_key(anchor)
        mid = _memory_id(
            origin_type=_ORIGIN_ANCHOR,
            source_ref=aid,
            summary_text=summary_text,
            salience=sal,
            recency_key=rk,
        )
        items.append(
            EpisodicCompiledItem(
                memory_id=mid,
                origin_type=_ORIGIN_ANCHOR,
                source_ref=aid,
                memory_type="anchor",
                visible_to=vis,
                involved_characters=_involved_from_anchor(anchor),
                summary_text=summary_text,
                salience=sal,
                recency_key=rk,
                non_authoritative=True,
            )
        )

    origin_rank = {"anchor": 0, "event": 1, "interpretation": 2, "issue": 3}

    def sort_key(it: EpisodicCompiledItem) -> tuple[int, int, int, str]:
        return (
            -it.salience,
            -it.recency_key,
            origin_rank.get(it.origin_type, 9),
            it.source_ref,
        )

    items.sort(key=sort_key)
    return tuple(items)
