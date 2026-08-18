"""Authored retrieval JSON index types and loader (Issue #166)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOG = logging.getLogger("rp_app.retrieved_context")


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
