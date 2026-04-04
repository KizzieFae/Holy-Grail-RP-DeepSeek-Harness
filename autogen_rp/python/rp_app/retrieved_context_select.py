"""Phase 2: deterministic authored-index retrieval for RetrievedContextBundle.

No transcript ingestion, vectors, or graph. Selection runs only from app_turn_prompting.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from episodic_memory_compile import EpisodicCompiledItem
from runtime_packets import RetrievedContextBundle, RetrievedItem

_LOG = logging.getLogger("rp_app.retrieved_context")
_EPISODIC_SUPPRESS_LOG = logging.getLogger("rp_app.episodic_prompt")

MAX_RETRIEVED_ITEMS = 8
MAX_RETRIEVED_CHARS = 8000

# Phase 3.1: per-source_kind subcaps (trim: priority DESC, source_ref ASC, keep head).
MAX_KIND_LORE_ITEMS = 1
MAX_KIND_LORE_CHARS = 600
MAX_KIND_SCENE_TEMPLATE_ITEMS = 3
MAX_KIND_SETUP_NOTE_ITEMS = 2
MAX_KIND_CHARACTER_CARD_ITEMS = 4

NonAuthoritative = Literal[True]


def _normalize_for_hash(text: str) -> str:
    s = str(text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _text_hash(text: str) -> str:
    return hashlib.sha256(_normalize_for_hash(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthoredIndexChunk:
    source_ref: str
    text: str
    priority: int
    source_kind: str
    scope: str
    relevance_tags: frozenset[str]
    relationship_relevant: bool
    template_id: str | None = None


@dataclass(frozen=True)
class AuthoredRetrievalIndex:
    version: int
    schema_version: int
    characters: dict[str, tuple[AuthoredIndexChunk, ...]]
    templates: dict[str, tuple[AuthoredIndexChunk, ...]]
    setup_notes: tuple[AuthoredIndexChunk, ...]
    lore: tuple[AuthoredIndexChunk, ...]


def load_authored_retrieval_index(path: str | None) -> AuthoredRetrievalIndex | None:
    if not path or not str(path).strip():
        return None
    p = Path(path)
    if not p.is_file():
        _LOG.warning("retrieval index path not found: %s", path)
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _LOG.warning("retrieval index load failed: %s", e)
        return None
    if not isinstance(raw, dict):
        return None
    ver = int(raw.get("version", 1))
    schema_ver = int(raw.get("schema_version", 1))
    chars: dict[str, tuple[AuthoredIndexChunk, ...]] = {}
    raw_chars = raw.get("characters") or {}
    if isinstance(raw_chars, dict):
        for name, chunks in sorted(raw_chars.items(), key=lambda x: str(x[0])):
            parsed: list[AuthoredIndexChunk] = []
            if isinstance(chunks, list):
                for c in chunks:
                    ch = _parse_chunk(c)
                    if ch:
                        parsed.append(ch)
            chars[str(name)] = tuple(sorted(parsed, key=lambda x: x.source_ref))
    templates: dict[str, tuple[AuthoredIndexChunk, ...]] = {}
    raw_tpl = raw.get("templates") or {}
    if isinstance(raw_tpl, dict):
        for tid, chunks in sorted(raw_tpl.items(), key=lambda x: str(x[0])):
            parsed = []
            if isinstance(chunks, list):
                for c in chunks:
                    ch = _parse_chunk(c)
                    if ch:
                        parsed.append(ch)
            templates[str(tid)] = tuple(sorted(parsed, key=lambda x: x.source_ref))
    setup_list: list[AuthoredIndexChunk] = []
    raw_setup = raw.get("setup_notes") or []
    if isinstance(raw_setup, list):
        for c in raw_setup:
            ch = _parse_chunk(c)
            if ch:
                setup_list.append(ch)
    setup_list.sort(key=lambda x: x.source_ref)
    lore_list: list[AuthoredIndexChunk] = []
    raw_lore = raw.get("lore") or []
    if isinstance(raw_lore, list):
        for c in raw_lore:
            ch = _parse_chunk(c)
            if ch:
                lore_list.append(ch)
    lore_list.sort(key=lambda x: x.source_ref)
    return AuthoredRetrievalIndex(
        version=ver,
        schema_version=schema_ver,
        characters=chars,
        templates=templates,
        setup_notes=tuple(setup_list),
        lore=tuple(lore_list),
    )


def _parse_chunk(c: Any) -> AuthoredIndexChunk | None:
    if not isinstance(c, dict):
        return None
    ref = str(c.get("source_ref", "") or "").strip()
    text = str(c.get("text", "") or "").strip()
    if not ref or not text:
        return None
    tags_raw = c.get("relevance_tags") or []
    tags: set[str] = set()
    if isinstance(tags_raw, list):
        for t in tags_raw:
            s = str(t or "").strip()
            if s:
                tags.add(s)
    tpl = str(c.get("template_id", "") or "").strip() or None
    return AuthoredIndexChunk(
        source_ref=ref,
        text=text,
        priority=int(c.get("priority", 0)),
        source_kind=str(c.get("source_kind", "authored") or "authored"),
        scope=str(c.get("scope", "character_local") or "character_local"),
        relevance_tags=frozenset(tags),
        relationship_relevant=bool(c.get("relationship_relevant", False)),
        template_id=tpl,
    )


def _truncate_lore_for_prompt(text: str) -> str:
    """Selection-time only; compiled index stores full lore text."""
    m = MAX_KIND_LORE_CHARS
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
        _trim_kind_subcap(tpl_l, MAX_KIND_SCENE_TEMPLATE_ITEMS)
        + _trim_kind_subcap(setup_l, MAX_KIND_SETUP_NOTE_ITEMS)
        + _trim_kind_subcap(lore_l, MAX_KIND_LORE_ITEMS)
        + _trim_kind_subcap(self_l, MAX_KIND_CHARACTER_CARD_ITEMS)
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

    while len(pool) > MAX_RETRIEVED_ITEMS or total_chars(pool) > MAX_RETRIEVED_CHARS:
        if not pool:
            break
        victim = min(pool, key=sort_drop_key)
        pool.remove(victim)
    return pool


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
    """Like ``_dedupe_items`` but on priority tie, substring containment drops episodic before authored."""
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


def _apply_global_cap_merged(items: list[RetrievedItem]) -> list[RetrievedItem]:
    """Global item/char cap: drop lowest priority first; on priority tie, episodic before authored cross before primary."""
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

    while len(pool) > MAX_RETRIEVED_ITEMS or total_chars(pool) > MAX_RETRIEVED_CHARS:
        if not pool:
            break
        min_pri = min(x.priority for x in pool)
        layer = [x for x in pool if x.priority == min_pri]
        victim = min(layer, key=tie_break_worse)
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
    episodic_items = filter_episodic_items_by_structured_prompt_overlap(
        episodic_items,
        prompt_issue_ids=pi,
        prompt_public_event_ids=pe,
        prompt_interpretation_ids=pn,
    )
    if not episodic_items:
        return RetrievedContextBundle(items=tuple(_apply_caps(authored)))

    episodic_ri = [episodic_compiled_to_retrieved_item(x) for x in episodic_items]
    merged = authored + episodic_ri
    deduped = _dedupe_merged_retrieval_items(merged)
    filtered = _dedupe_against_authority(deduped, list(dedup_against_texts))
    capped = _apply_global_cap_merged(filtered)
    return RetrievedContextBundle(items=tuple(capped))


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


def get_index_path_from_env() -> str | None:
    v = os.environ.get("RP_RETRIEVED_CONTEXT_INDEX", "")
    s = str(v or "").strip()
    return s or None


def log_retrieval_if_active(bundle: RetrievedContextBundle, *, char_name: str) -> None:
    if not bundle.items:
        return
    refs = [it.source_ref for it in bundle.items]
    n_chars = sum(len(it.text) for it in bundle.items)
    _LOG.info(
        "retrieved_context char=%s items=%d chars=%d source_refs=%s",
        char_name,
        len(bundle.items),
        n_chars,
        refs,
    )
