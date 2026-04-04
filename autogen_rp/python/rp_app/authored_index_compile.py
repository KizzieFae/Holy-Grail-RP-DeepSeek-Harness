"""Offline deterministic compiler: manifest → Phase 3 retrieval index JSON (schema v2 or v3).

Lossy: only allowlisted flavor fields become chunks. No LLM, no timestamps in output.

schema_version 2: legacy chunk shape only (runtime retrieval unchanged).

schema_version 3: each chunk adds canonical primary fields; legacy fields remain a
backward-compatible projection. See canonical_compile_adapters.py for mapping table.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from canonical_compile_adapters import (
    ALLOWED_DECOMPOSITION_STRATEGIES,
    AdapterRow,
    apply_dense_narrative_cap,
    clamp_authority_to_ceiling,
    resolve_adapter_row,
)

MAX_COMPILE_CHUNK_CHARS = 1200

DEFAULT_PRIORITY = {"character_card": 50, "scene_template": 45, "setup_note": 35, "lore": 25}

OOC_BLOCKLIST = frozenset({"ooc_notes_for_model"})

ALLOWED_SCHEMA_VERSIONS: frozenset[int] = frozenset({2, 3})

REQUIRED_CANONICAL_KEYS: frozenset[str] = frozenset(
    {
        "knowledge_id",
        "knowledge_type",
        "authority_class",
        "visibility",
        "subject_scope",
    }
)


def _normalize_for_dedup(text: str) -> str:
    s = str(text or "").strip().lower()
    return re.sub(r"\s+", " ", s)


def _dedup_hash(text: str) -> str:
    return hashlib.sha256(_normalize_for_dedup(text).encode("utf-8")).hexdigest()


def compute_knowledge_id(*, source_ref: str, text: str, knowledge_type: str) -> str:
    """Stable id: source_ref + normalized text + knowledge_type only (no authority / policy)."""
    norm = _normalize_for_dedup(text)
    payload = f"v1|{source_ref}|{norm}|{knowledge_type}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def _subject_scope_dict(
    *,
    visibility: str,
    character_id: str | None,
    template_id: str | None,
) -> dict[str, str]:
    if visibility == "character_scoped":
        if not character_id or not str(character_id).strip():
            raise ValueError("character_scoped visibility requires character_id in compile context")
        return {"character_id": str(character_id).strip()}
    if visibility == "template_participants":
        if not template_id or not str(template_id).strip():
            raise ValueError("template_participants visibility requires template_id in compile context")
        return {"template_id": str(template_id).strip()}
    if visibility == "public":
        return {}
    raise ValueError(f"unsupported visibility for compile: {visibility!r}")


def _validate_subject_scope(scope: dict[str, Any]) -> None:
    if not isinstance(scope, dict):
        raise ValueError("subject_scope must be a JSON object")
    for k, v in scope.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError(f"invalid subject_scope key: {k!r}")
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"subject_scope values must be non-empty strings: {k!r}")


def _validate_decomposition(row: AdapterRow) -> None:
    if row.decomposition not in ALLOWED_DECOMPOSITION_STRATEGIES:
        raise ValueError(f"unsupported decomposition {row.decomposition!r}")


def _normalized_json_object(obj: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def _nested_object_leaf_pieces(parent_ref: str, obj: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for k in sorted(obj.keys()):
        v = obj[k]
        ref = f"{parent_ref}.{k}"
        if isinstance(v, str):
            t = v.strip()
            if t:
                out.append((ref, t))
        elif isinstance(v, list):
            if not v:
                continue
            if not all(isinstance(x, str) for x in v):
                raise ValueError(f"list at {ref} must contain only strings")
            for i, x in enumerate(v):
                xs = str(x).strip()
                if xs:
                    out.append((f"{ref}#{i}", xs))
        elif isinstance(v, dict):
            out.extend(_nested_object_leaf_pieces(ref, v))
        else:
            raise ValueError(f"unsupported value type at {ref}: {type(v).__name__}")
    return out


def _role_slots_pieces(base_ref: str, val: Any) -> list[tuple[str, str, dict[str, Any]]]:
    if not isinstance(val, list):
        raise ValueError(f"role_slots must be a list at {base_ref}")
    slots: list[dict[str, Any]] = []
    for item in val:
        if not isinstance(item, dict):
            raise ValueError(f"role_slots entries must be objects at {base_ref}")
        slots.append(item)
    slots.sort(key=lambda d: str(d.get("role_name", "")))
    out: list[tuple[str, str, dict[str, Any]]] = []
    for slot in slots:
        rn = str(slot.get("role_name", "") or "").strip()
        if not rn:
            raise ValueError(f"role_slot missing role_name under {base_ref}")
        ref = f"{base_ref}:role_slot:{rn}"
        text = json.dumps(slot, ensure_ascii=False, sort_keys=True)
        out.append((ref, text, _normalized_json_object(slot)))
    return out


def _pieces_from_value(
    val: Any,
    *,
    row: AdapterRow,
    base_ref: str,
    used_fallback: bool,
) -> list[tuple[str, str, Any]]:
    """Return (source_ref, text, structured_payload|None) atomic rows (already length-chunked)."""
    strat = row.decomposition
    if strat == "emit_zero_chunks":
        return []
    if used_fallback and isinstance(val, (dict, list)):
        dumped = json.dumps(val, ensure_ascii=False, sort_keys=True)
        acc: list[tuple[str, str, Any]] = []
        for ref, txt in _chunk_string(dumped, base_ref):
            acc.append((ref, txt, None))
        return acc
    if strat == "whole_value_single_row":
        if not isinstance(val, str):
            raise ValueError(f"expected string at {base_ref}, got {type(val).__name__}")
        acc2: list[tuple[str, str, Any]] = []
        for ref, txt in _chunk_string(val.strip(), base_ref):
            acc2.append((ref, txt, None))
        return acc2
    if strat == "one_row_per_string_list_item":
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            raise ValueError(f"expected list[str] at {base_ref}")
        acc3: list[tuple[str, str, Any]] = []
        for i, s in enumerate(val):
            s2 = str(s).strip()
            if not s2:
                continue
            sub = f"{base_ref}#{i}"
            for ref, txt in _chunk_string(s2, sub):
                acc3.append((ref, txt, None))
        return acc3
    if strat == "nested_object_leaf_strings":
        if not isinstance(val, dict):
            raise ValueError(f"expected object at {base_ref}")
        acc4: list[tuple[str, str, Any]] = []
        for ref, txt in _nested_object_leaf_pieces(base_ref, val):
            for r2, t2 in _chunk_string(txt, ref):
                acc4.append((r2, t2, None))
        return acc4
    if strat == "role_slots_array_rows":
        return _role_slots_pieces(base_ref, val)
    raise ValueError(f"unhandled decomposition {strat!r}")


def _strip_compile_ctx(chunk: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in chunk.items() if k != "_compile_ctx"}


def _attach_canonical_fields(
    chunk: dict[str, Any],
    *,
    compile_metadata: dict[str, Any],
) -> dict[str, Any]:
    ctx = chunk.get("_compile_ctx")
    if not isinstance(ctx, dict):
        raise ValueError("v3 chunk missing _compile_ctx")

    etype = str(ctx.get("etype", "") or "")
    key_path = str(ctx.get("key_path", "") or "")
    character_id = ctx.get("character_id")
    template_id = ctx.get("template_id")
    dense = bool(ctx.get("dense_narrative", False))
    structured = ctx.get("structured_payload")

    row, used_fallback = resolve_adapter_row(etype, key_path)
    _validate_decomposition(row)

    knowledge_type = row.knowledge_type
    authority_class = row.authority_class
    visibility = row.visibility

    if used_fallback:
        compile_metadata.setdefault("fallback_uses", 0)
        compile_metadata["fallback_uses"] = int(compile_metadata["fallback_uses"]) + 1
        w = compile_metadata.setdefault("warnings", [])
        w.append(f"strict_fallback:{etype}:{key_path}:{chunk.get('source_ref', '')}")

    pre_clamp = authority_class
    authority_class = clamp_authority_to_ceiling(authority_class, knowledge_type)
    if authority_class != pre_clamp:
        compile_metadata.setdefault("authority_clamps", 0)
        compile_metadata["authority_clamps"] = int(compile_metadata["authority_clamps"]) + 1

    if dense:
        pre_dense = authority_class
        authority_class = apply_dense_narrative_cap(authority_class)
        if authority_class != pre_dense:
            compile_metadata.setdefault("dense_caps", 0)
            compile_metadata["dense_caps"] = int(compile_metadata["dense_caps"]) + 1

    subject_scope = _subject_scope_dict(
        visibility=visibility,
        character_id=str(character_id).strip() if character_id else None,
        template_id=str(template_id).strip() if template_id else None,
    )
    _validate_subject_scope(subject_scope)

    text = str(chunk.get("text", "") or "")
    source_ref = str(chunk.get("source_ref", "") or "").strip()
    if not source_ref:
        raise ValueError("chunk missing source_ref for v3")

    kid = compute_knowledge_id(source_ref=source_ref, text=text, knowledge_type=knowledge_type)

    legacy = _strip_compile_ctx(chunk)
    out = {
        **legacy,
        "knowledge_id": kid,
        "knowledge_type": knowledge_type,
        "authority_class": authority_class,
        "visibility": visibility,
        "subject_scope": subject_scope,
        "temporal_scope": {},
        "structured_payload": structured if structured is not None else None,
    }
    for req in REQUIRED_CANONICAL_KEYS:
        if req not in out:
            raise ValueError(f"v3 chunk missing required canonical field {req!r}")
        if req != "subject_scope" and (out[req] is None or out[req] == ""):
            raise ValueError(f"v3 chunk has empty canonical field {req!r}")
    return out


def compile_authored_index(
    manifest_path: Path,
    output_path: Path,
    *,
    schema_version: int = 2,
) -> dict[str, Any]:
    """Compile manifest into index JSON at output_path.

    schema_version 2: legacy-only chunks (default; unchanged behavior from pre-v3).
    schema_version 3: canonical fields + legacy projection per chunk.
    """
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        raise ValueError(f"schema_version must be one of {sorted(ALLOWED_SCHEMA_VERSIONS)}, got {schema_version}")

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
        dense_narrative = bool(ent.get("dense_narrative", False))

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
                base_ref = f"char:{cid}:{key}"
                row, used_fb = resolve_adapter_row("character", key)
                pieces = _pieces_from_value(val, row=row, base_ref=base_ref, used_fallback=used_fb)
                rel_flag = key in rel_keys
                prio = DEFAULT_PRIORITY["character_card"]
                for ref, chunk_text, spl in pieces:
                    ctx: dict[str, Any] = {
                        "etype": "character",
                        "key_path": key,
                        "character_id": cid,
                        "template_id": None,
                        "dense_narrative": dense_narrative,
                    }
                    if spl is not None:
                        ctx["structured_payload"] = spl
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "character_card",
                        "scope": "character_local",
                        "relevance_tags": [],
                        "relationship_relevant": rel_flag,
                        "_compile_ctx": ctx,
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
                base_ref = f"tpl:{tid}:{key}"
                row, used_fb = resolve_adapter_row("template", key)
                pieces = _pieces_from_value(val, row=row, base_ref=base_ref, used_fallback=used_fb)
                prio = DEFAULT_PRIORITY["scene_template"]
                for ref, chunk_text, spl in pieces:
                    ctx = {
                        "etype": "template",
                        "key_path": key,
                        "character_id": None,
                        "template_id": tid,
                        "dense_narrative": dense_narrative,
                    }
                    if spl is not None:
                        ctx["structured_payload"] = spl
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "scene_template",
                        "scope": "scene_shared",
                        "relevance_tags": [tag],
                        "relationship_relevant": False,
                        "_compile_ctx": ctx,
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
                base_ref = f"setup:{tid}:{key}"
                row, used_fb = resolve_adapter_row("setup", key)
                pieces = _pieces_from_value(val, row=row, base_ref=base_ref, used_fallback=used_fb)
                prio = DEFAULT_PRIORITY["setup_note"]
                for ref, chunk_text, spl in pieces:
                    ctx = {
                        "etype": "setup",
                        "key_path": key,
                        "character_id": None,
                        "template_id": tid,
                        "dense_narrative": dense_narrative,
                    }
                    if spl is not None:
                        ctx["structured_payload"] = spl
                    chunk = {
                        "source_ref": ref,
                        "text": chunk_text,
                        "priority": prio,
                        "source_kind": "setup_note",
                        "scope": "scene_shared",
                        "relevance_tags": [tag],
                        "template_id": tid,
                        "relationship_relevant": False,
                        "_compile_ctx": ctx,
                    }
                    setup_notes.append(chunk)
                    all_chunks.append(chunk)

        elif etype == "initial_message":
            data = _load_json(src_path)
            if not isinstance(data, dict):
                raise ValueError(f"initial_message file must be object: {src_path}")
            text = data.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"initial_message requires non-empty string 'text': {src_path}")
            tid = str(ent.get("template_id", "") or "").strip() or None
            stem = src_path.stem
            base_ref = f"imsg:{stem}:text"
            row, used_fb = resolve_adapter_row("initial_message", "__body__")
            pieces = _pieces_from_value(text.strip(), row=row, base_ref=base_ref, used_fallback=used_fb)
            prio = DEFAULT_PRIORITY["setup_note"]
            tags = [f"template:{tid}"] if tid else []
            for ref, chunk_text, spl in pieces:
                ctx = {
                    "etype": "initial_message",
                    "key_path": "__body__",
                    "character_id": None,
                    "template_id": tid,
                    "dense_narrative": dense_narrative,
                }
                if spl is not None:
                    ctx["structured_payload"] = spl
                chunk = {
                    "source_ref": ref,
                    "text": chunk_text,
                    "priority": prio,
                    "source_kind": "setup_note",
                    "scope": "scene_shared",
                    "relevance_tags": tags,
                    "relationship_relevant": False,
                    "_compile_ctx": ctx,
                }
                if tid:
                    chunk["template_id"] = tid
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
                chunk = {
                    "source_ref": ref,
                    "text": text.strip(),
                    "priority": prio,
                    "source_kind": "lore",
                    "scope": "world_lore",
                    "relevance_tags": tags,
                    "relationship_relevant": False,
                    "_compile_ctx": {
                        "etype": "lore_file",
                        "key_path": "__chunk__",
                        "character_id": None,
                        "template_id": tpl_id,
                        "dense_narrative": dense_narrative,
                    },
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

    compile_metadata: dict[str, Any] = {
        "schema_version_target": schema_version,
        "warnings": [],
        "fallback_uses": 0,
        "authority_clamps": 0,
        "dense_caps": 0,
    }

    if schema_version == 3:

        def _map_chunk(ch: dict[str, Any]) -> dict[str, Any]:
            return _attach_canonical_fields(ch, compile_metadata=compile_metadata)

        for cid in characters:
            characters[cid] = [_map_chunk(c) for c in characters[cid]]
        for tid in templates:
            templates[tid] = [_map_chunk(c) for c in templates[tid]]
        setup_notes[:] = [_map_chunk(c) for c in setup_notes]
        lore[:] = [_map_chunk(c) for c in lore]
        out_obj: dict[str, Any] = {
            "schema_version": 3,
            "version": 3,
            "characters": characters,
            "templates": templates,
            "setup_notes": setup_notes,
            "lore": lore,
            "compile_metadata": compile_metadata,
        }
    else:
        for cid in characters:
            characters[cid] = [_strip_compile_ctx(c) for c in characters[cid]]
        for tid in templates:
            templates[tid] = [_strip_compile_ctx(c) for c in templates[tid]]
        setup_notes[:] = [_strip_compile_ctx(c) for c in setup_notes]
        lore[:] = [_strip_compile_ctx(c) for c in lore]
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
        "schema_version": schema_version,
        "compile_metadata": compile_metadata if schema_version == 3 else {},
    }
