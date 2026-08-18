"""Deterministic authored-index selection and pre-merge caps (Issue #166)."""

from __future__ import annotations

import hashlib
import re

from authored_retrieval_index import AuthoredIndexChunk, AuthoredRetrievalIndex
from runtime_packet_types import RetrievedContextBundle, RetrievedItem


def _normalize_for_hash(text: str) -> str:
    s = str(text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _text_hash(text: str) -> str:    return hashlib.sha256(_normalize_for_hash(text).encode("utf-8")).hexdigest()


def _truncate_lore_for_prompt(text: str) -> str:
    """Selection-time only; compiled index stores full lore text."""
    import retrieved_context_select as rcs

    m = rcs.MAX_KIND_LORE_CHARS
    if len(text) <= m:
        return text
    if m <= 1:
        return "…"
    return text[: m - 1] + "…"


def _chunk_to_item(
    ch: AuthoredIndexChunk,
    *,
    from_other_character: str | None,
    apply_lore_truncation: bool = False,
) -> RetrievedItem:
    text = ch.text
    if apply_lore_truncation and ch.source_kind == "lore":
        text = _truncate_lore_for_prompt(text)
    return RetrievedItem(
        text=text,
        source_kind=ch.source_kind,
        source_ref=ch.source_ref,
        scope=ch.scope,
        relevance_tags=ch.relevance_tags,
        priority=ch.priority,
        non_authoritative=True,
        from_other_character=from_other_character,
    )


def _lore_matches_scene(ch: AuthoredIndexChunk, tid: str) -> bool:
    if ch.source_kind != "lore" or ch.scope != "world_lore":
        return False
    if not tid.strip():
        return False
    if ch.template_id == tid:
        return True
    return f"template:{tid}" in ch.relevance_tags


def _trim_kind_subcap(items: list[RetrievedItem], cap: int) -> list[RetrievedItem]:
    if cap <= 0:
        return []
    s = sorted(items, key=lambda x: (-x.priority, x.source_ref))
    return s[:cap]


def _apply_source_kind_subcaps(items: list[RetrievedItem]) -> list[RetrievedItem]:
    import retrieved_context_select as rcs

    lore_l = [x for x in items if x.source_kind == "lore"]
    tpl_l = [x for x in items if x.source_kind == "scene_template"]
    setup_l = [x for x in items if x.source_kind == "setup_note"]
    self_l = [
        x
        for x in items
        if x.source_kind == "character_card" and x.from_other_character is None
    ]
    cross_l = [x for x in items if x.from_other_character is not None]
    return (
        _trim_kind_subcap(tpl_l, rcs.MAX_KIND_SCENE_TEMPLATE_ITEMS)
        + _trim_kind_subcap(setup_l, rcs.MAX_KIND_SETUP_NOTE_ITEMS)
        + _trim_kind_subcap(lore_l, rcs.MAX_KIND_LORE_ITEMS)
        + _trim_kind_subcap(self_l, rcs.MAX_KIND_CHARACTER_CARD_ITEMS)
        + cross_l
    )


def _dedupe_items(candidates: list[RetrievedItem]) -> list[RetrievedItem]:
    seen_refs: set[str] = set()
    seen_hashes: set[str] = set()
    kept: list[RetrievedItem] = []

    for item in candidates:
        if item.source_ref in seen_refs:
            continue
        h = _text_hash(item.text)
        if h in seen_hashes:
            continue
        seen_refs.add(item.source_ref)
        seen_hashes.add(h)
        kept.append(item)

    # Substring fallback: drop item if it is a strict substring of another (keeper wins by priority)
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
            if tin in otx:
                if other.priority > item.priority or (
                    other.priority == item.priority and other.source_ref < item.source_ref
                ):
                    drop = True
                    break
        if not drop:
            final.append(item)
    return final


def _dedupe_against_authority(items: list[RetrievedItem], snippets: list[str]) -> list[RetrievedItem]:
    norm_snips = [_normalize_for_hash(s) for s in snippets if str(s or "").strip()]
    out: list[RetrievedItem] = []
    for item in items:
        nt = _normalize_for_hash(item.text)
        skip = False
        for sn in norm_snips:
            if not sn:
                continue
            if nt == sn or nt in sn or sn in nt:
                skip = True
                break
        if not skip:
            out.append(item)
    return out


def _apply_caps(items: list[RetrievedItem]) -> list[RetrievedItem]:
    import retrieved_context_select as rcs

    if not items:
        return []
    pool = list(items)

    def is_cross(it: RetrievedItem) -> bool:
        return it.from_other_character is not None

    def sort_drop_key(it: RetrievedItem) -> tuple[int, int, str]:
        # Lower tuple = removed first: cross-character (0) before primary (1); lower priority value; ref
        tier = 0 if is_cross(it) else 1
        return (tier, it.priority, it.source_ref)

    def total_chars(lst: list[RetrievedItem]) -> int:
        return sum(len(it.text) for it in lst)

    while (
        len(pool) > rcs.MAX_RETRIEVED_ITEMS
        or total_chars(pool) > rcs.MAX_RETRIEVED_CHARS
    ):
        if not pool:
            break
        victim = min(pool, key=sort_drop_key)
        pool.remove(victim)
    return pool


def select_authored_retrieved_items_pre_global_cap(
    *,
    index: AuthoredRetrievalIndex | None,
    char_name: str,
    scene_template_id: str,
    relationship_focus_names: tuple[str, ...],
    cast: tuple[str, ...],
    dedup_against_texts: tuple[str, ...],
) -> list[RetrievedItem]:
    """Authored lane after subcaps and dedupe, before ``_apply_caps``."""
    if index is None:
        return []
    tid = str(scene_template_id or "").strip()
    primary_ordered: list[RetrievedItem] = []

    if tid and tid in index.templates:
        for ch in index.templates[tid]:
            primary_ordered.append(
                _chunk_to_item(ch, from_other_character=None, apply_lore_truncation=False)
            )

    if tid:
        for note in index.setup_notes:
            match = note.template_id == tid or f"template:{tid}" in note.relevance_tags
            if match:
                primary_ordered.append(
                    _chunk_to_item(note, from_other_character=None, apply_lore_truncation=False)
                )

    for ch in index.lore:
        if _lore_matches_scene(ch, tid):
            primary_ordered.append(
                _chunk_to_item(ch, from_other_character=None, apply_lore_truncation=True)
            )

    self_chunks = index.characters.get(char_name, ())
    for ch in self_chunks:
        if ch.scope != "character_local":
            continue
        primary_ordered.append(
            _chunk_to_item(ch, from_other_character=None, apply_lore_truncation=False)
        )

    cross_ordered: list[RetrievedItem] = []
    eligible_others = sorted(
        frozenset(relationship_focus_names) & frozenset(cast) - {char_name}
    )
    for other in eligible_others:
        ochunks = index.characters.get(other, ())
        rel = [c for c in ochunks if c.relationship_relevant]
        if not rel:
            continue
        best = max(rel, key=lambda c: (c.priority, c.source_ref))
        cross_ordered.append(
            _chunk_to_item(best, from_other_character=other, apply_lore_truncation=False)
        )

    ordered = primary_ordered + cross_ordered
    deduped = _dedupe_items(ordered)
    filtered = _dedupe_against_authority(deduped, list(dedup_against_texts))
    return _apply_source_kind_subcaps(filtered)


def select_retrieved_context_bundle(
    *,
    index: AuthoredRetrievalIndex | None,
    char_name: str,
    scene_template_id: str,
    relationship_focus_names: tuple[str, ...],
    cast: tuple[str, ...],
    dedup_against_texts: tuple[str, ...],
) -> RetrievedContextBundle:
    """Pure deterministic selection (authored index only)."""
    if index is None:
        return RetrievedContextBundle()
    subcapped = select_authored_retrieved_items_pre_global_cap(
        index=index,
        char_name=char_name,
        scene_template_id=scene_template_id,
        relationship_focus_names=relationship_focus_names,
        cast=cast,
        dedup_against_texts=dedup_against_texts,
    )
    capped = _apply_caps(subcapped)
    return RetrievedContextBundle(items=tuple(capped))
