"""Episodic merge lane and global cap after authored selection (Issue #166)."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from authored_retrieval_index import AuthoredRetrievalIndex
from episodic_memory_compile import EpisodicCompiledItem
from retrieved_selection_authored import (
    _apply_caps,
    select_authored_retrieved_items_pre_global_cap,
)
from runtime_packet_types import RetrievedContextBundle, RetrievedItem

_EPISODIC_SUPPRESS_LOG = logging.getLogger("rp_app.episodic_prompt")


def _is_episodic_retrieved_item(it: RetrievedItem) -> bool:
    return str(it.source_kind or "").startswith("episodic")


def episodic_compiled_to_retrieved_item(ep: EpisodicCompiledItem) -> RetrievedItem:
    """Map episodic compile row to bundle item (non-authoritative)."""
    return RetrievedItem(
        text=ep.summary_text,
        source_kind=f"episodic:{ep.memory_type}",
        source_ref=ep.source_ref,
        scope="session_episodic",
        relevance_tags=frozenset(),
        priority=int(ep.salience),
        non_authoritative=True,
        from_other_character=None,
    )


def structured_prompt_id_sets_for_episodic_suppression(
    *,
    active_issues: Sequence[Mapping[str, Any]],
    recent_public_events: Sequence[Mapping[str, Any]],
    my_interpretations: Sequence[Mapping[str, Any]],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """IDs present in this character's structured prompt JSON (exact match for merge-time suppression)."""
    issue_ids: set[str] = set()
    for row in active_issues:
        if not isinstance(row, Mapping):
            continue
        iid = str(row.get("issue_id", "") or "").strip()
        if iid:
            issue_ids.add(iid)
    event_ids: set[str] = set()
    for row in recent_public_events:
        if not isinstance(row, Mapping):
            continue
        eid = str(row.get("event_id", "") or "").strip()
        if eid:
            event_ids.add(eid)
    interp_ids: set[str] = set()
    for row in my_interpretations:
        if not isinstance(row, Mapping):
            continue
        nid = str(row.get("interpretation_id", "") or "").strip()
        if nid:
            interp_ids.add(nid)
    return frozenset(issue_ids), frozenset(event_ids), frozenset(interp_ids)


def filter_episodic_items_by_structured_prompt_overlap(
    episodic_items: tuple[EpisodicCompiledItem, ...],
    *,
    prompt_issue_ids: frozenset[str],
    prompt_public_event_ids: frozenset[str],
    prompt_interpretation_ids: frozenset[str],
) -> tuple[EpisodicCompiledItem, ...]:
    """Drop episodic rows whose source id already appears in structured prompt sections (exact id only)."""
    kept: list[EpisodicCompiledItem] = []
    for ep in episodic_items:
        mt = str(ep.memory_type or "")
        ref = str(ep.source_ref or "").strip()
        if not ref:
            kept.append(ep)
            continue
        if mt == "issue" and ref in prompt_issue_ids:
            _EPISODIC_SUPPRESS_LOG.debug(
                "episodic suppress id=%s type=issue reason=already present in ACTIVE ISSUES",
                ref,
            )
            continue
        if mt == "public_event" and ref in prompt_public_event_ids:
            _EPISODIC_SUPPRESS_LOG.debug(
                "episodic suppress id=%s type=public_event reason=already present in RECENT PUBLIC EVENTS",
                ref,
            )
            continue
        if mt == "interpretation" and ref in prompt_interpretation_ids:
            _EPISODIC_SUPPRESS_LOG.debug(
                "episodic suppress id=%s type=interpretation reason=already present in YOUR RECENT INTERPRETATIONS",
                ref,
            )
            continue
        kept.append(ep)
    return tuple(kept)


def _dedupe_merged_retrieval_items(items: list[RetrievedItem]) -> list[RetrievedItem]:
    """Like authored _dedupe_items but on priority tie, substring containment drops episodic before authored."""
    from retrieved_selection_authored import _text_hash

    seen_refs: set[str] = set()
    seen_hashes: set[str] = set()
    kept: list[RetrievedItem] = []

    for item in items:
        if item.source_ref in seen_refs:
            continue
        h = _text_hash(item.text)
        if h in seen_hashes:
            continue
        seen_refs.add(item.source_ref)
        seen_hashes.add(h)
        kept.append(item)

    final: list[RetrievedItem] = []
    for item in kept:
        tin = item.text.strip()
        drop = False
        for other in kept:
            if other is item:
                continue
            otx = other.text.strip()
            if not tin or not otx or tin == otx:
                continue
            if tin not in otx:
                continue
            if other.priority > item.priority:
                drop = True
                break
            if other.priority < item.priority:
                continue
            ie = _is_episodic_retrieved_item(item)
            oe = _is_episodic_retrieved_item(other)
            if ie and not oe:
                drop = True
                break
            if oe and not ie:
                continue
            if other.source_ref < item.source_ref:
                drop = True
                break
        if not drop:
            final.append(item)
    return final


def _dedupe_against_authority(items: list[RetrievedItem], snippets: list[str]) -> list[RetrievedItem]:
    from retrieved_selection_authored import _dedupe_against_authority as _daa

    return _daa(items, snippets)


def _apply_global_cap_merged(items: list[RetrievedItem]) -> list[RetrievedItem]:
    """Global item/char cap: drop lowest priority first; on priority tie, episodic before authored cross before primary."""
    import retrieved_context_select as rcs

    pool = list(items)

    def total_chars(lst: list[RetrievedItem]) -> int:
        return sum(len(it.text) for it in lst)

    def tie_break_worse(it: RetrievedItem) -> tuple[int, str]:
        if _is_episodic_retrieved_item(it):
            lane = 0
        elif it.from_other_character is not None:
            lane = 1
        else:
            lane = 2
        return (lane, it.source_ref)

    while (
        len(pool) > rcs.MAX_RETRIEVED_ITEMS or total_chars(pool) > rcs.MAX_RETRIEVED_CHARS
    ):
        if not pool:
            break
        min_pri = min(x.priority for x in pool)
        layer = [x for x in pool if x.priority == min_pri]
        victim = min(layer, key=tie_break_worse)
        pool.remove(victim)
    return pool


def merge_retrieved_context_with_episodic(
    *,
    index: AuthoredRetrievalIndex | None,
    char_name: str,
    scene_template_id: str,
    relationship_focus_names: tuple[str, ...],
    cast: tuple[str, ...],
    dedup_against_texts: tuple[str, ...],
    episodic_items: tuple[EpisodicCompiledItem, ...],
    structured_prompt_issue_ids: frozenset[str] | None = None,
    structured_prompt_public_event_ids: frozenset[str] | None = None,
    structured_prompt_interpretation_ids: frozenset[str] | None = None,
) -> RetrievedContextBundle:
    """Merge authored (pre–global-cap pipeline) with episodic items; one global cap; deterministic order.

    Ordering: authored segment (existing relative order) then episodic segment; survivors keep that order
    after dedupe and cap removals. On equal minimum ``priority`` under global cap, episodic is dropped
    before authored; among authored at that priority, cross-character before primary.
    """
    authored = select_authored_retrieved_items_pre_global_cap(
        index=index,
        char_name=char_name,
        scene_template_id=scene_template_id,
        relationship_focus_names=relationship_focus_names,
        cast=cast,
        dedup_against_texts=dedup_against_texts,
    )
    pi = structured_prompt_issue_ids or frozenset()
    pe = structured_prompt_public_event_ids or frozenset()
    pn = structured_prompt_interpretation_ids or frozenset()
    filtered_episodic = filter_episodic_items_by_structured_prompt_overlap(
        episodic_items,
        prompt_issue_ids=pi,
        prompt_public_event_ids=pe,
        prompt_interpretation_ids=pn,
    )
    if not filtered_episodic:
        return RetrievedContextBundle(items=tuple(_apply_caps(authored)))

    episodic_ri = [episodic_compiled_to_retrieved_item(x) for x in filtered_episodic]
    merged = authored + episodic_ri
    deduped = _dedupe_merged_retrieval_items(merged)
    filtered = _dedupe_against_authority(deduped, list(dedup_against_texts))
    capped = _apply_global_cap_merged(filtered)
    return RetrievedContextBundle(items=tuple(capped))
