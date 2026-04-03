"""Phase 2: deterministic authored-index retrieval for RetrievedContextBundle.

No transcript ingestion, vectors, or graph. Selection runs only from app_turn_prompting.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from runtime_packets import RetrievedContextBundle, RetrievedItem

_LOG = logging.getLogger("rp_app.retrieved_context")

MAX_RETRIEVED_ITEMS = 8
MAX_RETRIEVED_CHARS = 8000

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
    characters: dict[str, tuple[AuthoredIndexChunk, ...]]
    templates: dict[str, tuple[AuthoredIndexChunk, ...]]
    setup_notes: tuple[AuthoredIndexChunk, ...]


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
    return AuthoredRetrievalIndex(
        version=ver,
        characters=chars,
        templates=templates,
        setup_notes=tuple(setup_list),
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


def _chunk_to_item(
    ch: AuthoredIndexChunk,
    *,
    from_other_character: str | None,
) -> RetrievedItem:
    return RetrievedItem(
        text=ch.text,
        source_kind=ch.source_kind,
        source_ref=ch.source_ref,
        scope=ch.scope,
        relevance_tags=ch.relevance_tags,
        priority=ch.priority,
        non_authoritative=True,
        from_other_character=from_other_character,
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
    tid = str(scene_template_id or "").strip()
    primary_ordered: list[RetrievedItem] = []

    if tid and tid in index.templates:
        for ch in index.templates[tid]:
            primary_ordered.append(_chunk_to_item(ch, from_other_character=None))

    self_chunks = index.characters.get(char_name, ())
    for ch in self_chunks:
        primary_ordered.append(_chunk_to_item(ch, from_other_character=None))

    if tid:
        for note in index.setup_notes:
            match = note.template_id == tid or f"template:{tid}" in note.relevance_tags
            if match:
                primary_ordered.append(_chunk_to_item(note, from_other_character=None))

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
        cross_ordered.append(_chunk_to_item(best, from_other_character=other))

    ordered = primary_ordered + cross_ordered

    deduped = _dedupe_items(ordered)
    filtered = _dedupe_against_authority(deduped, list(dedup_against_texts))
    capped = _apply_caps(filtered)
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
