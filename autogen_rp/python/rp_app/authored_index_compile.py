"""Offline deterministic compiler: manifest → Phase 3 retrieval index JSON (schema v2).

Lossy: only allowlisted flavor fields become chunks. No LLM, no timestamps in output.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

MAX_COMPILE_CHUNK_CHARS = 1200

DEFAULT_PRIORITY = {"character_card": 50, "scene_template": 45, "setup_note": 35, "lore": 25}

OOC_BLOCKLIST = frozenset({"ooc_notes_for_model"})


def _normalize_for_dedup(text: str) -> str:
    s = str(text or "").strip().lower()
    return re.sub(r"\s+", " ", s)


def _dedup_hash(text: str) -> str:
    return hashlib.sha256(_normalize_for_dedup(text).encode("utf-8")).hexdigest()


def _chunk_string(text: str, base_ref: str) -> list[tuple[str, str]]:
    t = str(text or "").strip()
    if not t:
        return []
    if len(t) <= MAX_COMPILE_CHUNK_CHARS:
        return [(base_ref, t)]
    parts: list[str] = []
    for para in re.split(r"\n\s*\n", t):
        p = para.strip()
        if not p:
            continue
        if len(p) <= MAX_COMPILE_CHUNK_CHARS:
            parts.append(p)
            continue
        for line in p.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(line) <= MAX_COMPILE_CHUNK_CHARS:
                parts.append(line)
                continue
            for i in range(0, len(line), MAX_COMPILE_CHUNK_CHARS):
                parts.append(line[i : i + MAX_COMPILE_CHUNK_CHARS])
    out: list[tuple[str, str]] = []
    for i, chunk_text in enumerate(parts):
        suffix = f"#{i}" if len(parts) > 1 else ""
        out.append((f"{base_ref}{suffix}", chunk_text))
    return out


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_authored_index(manifest_path: Path, output_path: Path) -> dict[str, Any]:
    """Compile manifest into schema_version 2 index JSON at output_path."""
    manifest_path = manifest_path.resolve()
    base_dir = manifest_path.parent
    raw_m = _load_json(manifest_path)
    if not isinstance(raw_m, dict):
        raise ValueError("manifest must be a JSON object")
    entries = raw_m.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest.entries must be a non-empty list")

    characters: dict[str, list[dict[str, Any]]] = {}
    templates: dict[str, list[dict[str, Any]]] = {}
    setup_notes: list[dict[str, Any]] = []
    lore: list[dict[str, Any]] = []
    all_chunks: list[dict[str, Any]] = []

    sorted_entries = sorted(
        entries,
        key=lambda e: (
            str((e or {}).get("type", "")),
            str((e or {}).get("path", "")),
        ),
    )

    for ent in sorted_entries:
        if not isinstance(ent, dict):
            continue
        etype = str(ent.get("type", "") or "").strip()
        rel_path = str(ent.get("path", "") or "").strip()
        if not rel_path:
            raise ValueError(f"manifest entry missing path: {ent!r}")
        src_path = (base_dir / rel_path).resolve()
        if not src_path.is_file():
            raise FileNotFoundError(f"source not found: {src_path}")

        if etype == "character":
            cid = str(ent.get("character_id", "") or "").strip()
            if not cid:
                raise ValueError("character entry requires character_id")
            allow = ent.get("allowlist_keys")
            if not isinstance(allow, list) or not allow:
                raise ValueError(f"character {cid}: allowlist_keys required")
            rel_keys = frozenset(str(x) for x in ent.get("relationship_keys", []) if str(x).strip())
            data = _load_json(src_path)
            if not isinstance(data, dict):
                raise ValueError(f"character file must be object: {src_path}")
            keys = sorted(
                str(k)
                for k in allow
                if str(k).strip() and str(k) not in OOC_BLOCKLIST
            )
            for key in keys:
                if key not in data:
                    continue
                val = data[key]
                text = val if isinstance(val, str) else str(val)
                base_ref = f"char:{cid}:{key}"
                rel_flag = key in rel_keys
                prio = DEFAULT_PRIORITY["character_card"]
                for ref, chunk_text in _chunk_string(text, base_ref):
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "character_card",
                        "scope": "character_local",
                        "relevance_tags": [],
                        "relationship_relevant": rel_flag,
                    }
                    characters.setdefault(cid, []).append(chunk)
                    all_chunks.append(chunk)

        elif etype == "template":
            tid = str(ent.get("template_id", "") or "").strip()
            if not tid:
                raise ValueError("template entry requires template_id")
            allow = ent.get("allowlist_keys")
            if not isinstance(allow, list) or not allow:
                raise ValueError(f"template {tid}: allowlist_keys required")
            data = _load_json(src_path)
            if not isinstance(data, dict):
                raise ValueError(f"template file must be object: {src_path}")
            keys = sorted(
                str(k)
                for k in allow
                if str(k).strip() and str(k) not in OOC_BLOCKLIST
            )
            tag = f"template:{tid}"
            for key in keys:
                if key not in data:
                    continue
                val = data[key]
                text = val if isinstance(val, str) else str(val)
                base_ref = f"tpl:{tid}:{key}"
                prio = DEFAULT_PRIORITY["scene_template"]
                for ref, chunk_text in _chunk_string(text, base_ref):
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "scene_template",
                        "scope": "scene_shared",
                        "relevance_tags": [tag],
                        "relationship_relevant": False,
                    }
                    templates.setdefault(tid, []).append(chunk)
                    all_chunks.append(chunk)

        elif etype == "setup":
            tid = str(ent.get("template_id", "") or "").strip()
            if not tid:
                raise ValueError("setup entry requires template_id")
            allow = ent.get("allowlist_keys")
            if not isinstance(allow, list) or not allow:
                raise ValueError("setup: allowlist_keys required")
            data = _load_json(src_path)
            if not isinstance(data, dict):
                raise ValueError(f"setup file must be object: {src_path}")
            keys = sorted(
                str(k)
                for k in allow
                if str(k).strip() and str(k) not in OOC_BLOCKLIST
            )
            tag = f"template:{tid}"
            for key in keys:
                if key not in data:
                    continue
                val = data[key]
                text = val if isinstance(val, str) else str(val)
                base_ref = f"setup:{tid}:{key}"
                prio = DEFAULT_PRIORITY["setup_note"]
                for ref, chunk_text in _chunk_string(text, base_ref):
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "setup_note",
                        "scope": "scene_shared",
                        "relevance_tags": [tag],
                        "template_id": tid,
                        "relationship_relevant": False,
                    }
                    setup_notes.append(chunk)
                    all_chunks.append(chunk)

        elif etype == "lore_file":
            data = _load_json(src_path)
            default_tags: list[str] = []
            dt = ent.get("default_tags")
            if isinstance(dt, list):
                default_tags = [str(x).strip() for x in dt if str(x).strip()]
            stem = src_path.stem
            chunks_raw = None
            if isinstance(data, dict) and isinstance(data.get("chunks"), list):
                chunks_raw = data["chunks"]
            elif isinstance(data, list):
                chunks_raw = data
            else:
                raise ValueError(f"lore_file must have chunks array or be array: {src_path}")
            if not isinstance(chunks_raw, list):
                raise ValueError(f"lore_file chunks invalid: {src_path}")
            for i, c in enumerate(chunks_raw):
                if not isinstance(c, dict):
                    continue
                lid = str(c.get("local_id", "") or "").strip() or str(i)
                text = c.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                tags = list(default_tags)
                rt = c.get("relevance_tags")
                if isinstance(rt, list):
                    tags.extend(str(x).strip() for x in rt if str(x).strip())
                tags = sorted(frozenset(tags))
                tpl_id = str(c.get("template_id", "") or "").strip() or None
                prio = int(c.get("priority", DEFAULT_PRIORITY["lore"]))
                ref = f"lore:{stem}:{lid}"
                # Full text stored; truncation at selection time only.
                chunk = {
                    "source_ref": ref,
                    "text": text.strip(),
                    "priority": prio,
                    "source_kind": "lore",
                    "scope": "world_lore",
                    "relevance_tags": tags,
                    "relationship_relevant": False,
                }
                if tpl_id:
                    chunk["template_id"] = tpl_id
                lore.append(chunk)
                all_chunks.append(chunk)
        else:
            raise ValueError(f"unknown manifest entry type: {etype!r}")

    # Compile-time dedup by text hash (keep higher priority, then lexicographic source_ref)
    by_hash: dict[str, dict[str, Any]] = {}
    for ch in sorted(all_chunks, key=lambda x: (-int(x.get("priority", 0)), str(x.get("source_ref", "")))):
        h = _dedup_hash(str(ch.get("text", "")))
        existing = by_hash.get(h)
        if existing is None:
            by_hash[h] = ch
            continue
        if int(ch.get("priority", 0)) > int(existing.get("priority", 0)):
            by_hash[h] = ch
        elif int(ch.get("priority", 0)) == int(existing.get("priority", 0)):
            if str(ch.get("source_ref", "")) < str(existing.get("source_ref", "")):
                by_hash[h] = ch

    surviving_refs = {str(c.get("source_ref", "")) for c in by_hash.values()}

    def _filter_surviving(lst: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [x for x in lst if str(x.get("source_ref", "")) in surviving_refs]

    for cid in list(characters.keys()):
        characters[cid] = _filter_surviving(characters[cid])
        characters[cid].sort(key=lambda x: str(x.get("source_ref", "")))
        if not characters[cid]:
            del characters[cid]
    for tid in list(templates.keys()):
        templates[tid] = _filter_surviving(templates[tid])
        templates[tid].sort(key=lambda x: str(x.get("source_ref", "")))
        if not templates[tid]:
            del templates[tid]
    setup_notes[:] = _filter_surviving(setup_notes)
    setup_notes.sort(key=lambda x: str(x.get("source_ref", "")))
    lore[:] = _filter_surviving(lore)
    lore.sort(key=lambda x: str(x.get("source_ref", "")))

    out_obj = {
        "schema_version": 2,
        "version": 2,
        "characters": characters,
        "templates": templates,
        "setup_notes": setup_notes,
        "lore": lore,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(out_obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "characters": len(characters),
        "templates": len(templates),
        "setup_notes": len(setup_notes),
        "lore": len(lore),
        "chunks": len(surviving_refs),
    }
