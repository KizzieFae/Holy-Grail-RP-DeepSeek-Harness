"""Support-window observability for audits (GitHub #28).

Pure projection from prompt_layer_audit + task_prompt. Does not import prompt assembly,
retrieval, or continuity. See issue: non-authoritative, deterministic manifests only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

SUPPORT_MANIFEST_SCHEMA_VERSION: Final[str] = "support_manifest.v1"

SUPPORT_UNIT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "summary_block_selected",
        "summary_block_excluded",
        "retrieval_source_ref",
        "retrieval_aggregate",
        "binding_constraints_section",
        "prompt_envelope",
    }
)


def _canonical_json(obj: Any) -> str:
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def _content_fp_json(obj: Any) -> str:
    payload = _canonical_json(obj).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _content_fp_utf8(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _canonical_segment(value: Any) -> str:
    return str(value).strip()


def _retrieval_summary_dict(prompt_layer_audit: dict[str, Any]) -> dict[str, Any]:
    raw = prompt_layer_audit.get("retrieval_summary")
    return raw if isinstance(raw, dict) else {}


def _binding_section_text(prompt_layer_audit: dict[str, Any]) -> str:
    raw = prompt_layer_audit.get("scene_binding_constraints_section")
    if raw is None:
        return ""
    return str(raw)


def _string_id_list(key: str, prompt_layer_audit: dict[str, Any]) -> list[str]:
    raw = prompt_layer_audit.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        seg = _canonical_segment(item)
        if seg:
            out.append(seg)
    return out


def build_support_manifest(
    prompt_layer_audit: dict[str, Any], task_prompt: str
) -> dict[str, Any]:
    """Build a SupportManifest from the character prompt_layer_audit dict and task_prompt.

    Operates only on the provided dict and string; does not parse prompt text into facets.
    """
    audit = prompt_layer_audit if isinstance(prompt_layer_audit, dict) else {}
    prompt = task_prompt if isinstance(task_prompt, str) else str(task_prompt or "")

    units: list[dict[str, str]] = []

    for sid in sorted(set(_string_id_list("selected_summary_block_ids", audit))):
        units.append(
            {
                "type": "summary_block_selected",
                "id": f"summary:sel:{sid}",
                "content_fp": _content_fp_json({"id": sid}),
            }
        )

    for sid in sorted(set(_string_id_list("excluded_summary_block_ids", audit))):
        units.append(
            {
                "type": "summary_block_excluded",
                "id": f"summary:exc:{sid}",
                "content_fp": _content_fp_json({"id": sid}),
            }
        )

    rs = _retrieval_summary_dict(audit)
    refs = rs.get("retrieved_source_refs")
    if not isinstance(refs, list):
        refs = []
    for i, ref in enumerate(refs):
        if not isinstance(ref, str):
            continue
        seg = _canonical_segment(ref)
        if not seg:
            continue
        units.append(
            {
                "type": "retrieval_source_ref",
                "id": f"retr:ref:{seg}:i{i}",
                "content_fp": _content_fp_json({"ref": seg, "list_index": i}),
            }
        )

    agg_payload = {
        "retrieved_block_present": rs.get("retrieved_block_present", False)
        if isinstance(rs.get("retrieved_block_present"), bool)
        else False,
        "retrieved_item_count": rs.get("retrieved_item_count", 0)
        if type(rs.get("retrieved_item_count")) is int
        else 0,
        "retrieved_char_count": rs.get("retrieved_char_count", 0)
        if type(rs.get("retrieved_char_count")) is int
        else 0,
        "retrieved_source_refs": refs
        if isinstance(refs, list)
        and all(isinstance(x, str) for x in refs)
        else [],
    }
    units.append(
        {
            "type": "retrieval_aggregate",
            "id": "retr:agg:v1",
            "content_fp": _content_fp_json(agg_payload),
        }
    )

    bind_text = _binding_section_text(audit)
    units.append(
        {
            "type": "binding_constraints_section",
            "id": "bind:v1",
            "content_fp": _content_fp_json({"text": bind_text}),
        }
    )

    units.append(
        {
            "type": "prompt_envelope",
            "id": "prompt:envelope:character:v1",
            "content_fp": _content_fp_utf8(prompt),
        }
    )

    units.sort(key=lambda u: (u["type"], u["id"]))

    for u in units:
        if u["type"] not in SUPPORT_UNIT_TYPES:
            raise ValueError(f"invalid unit type: {u['type']!r}")

    return {
        "schema_version": SUPPORT_MANIFEST_SCHEMA_VERSION,
        "units": units,
    }


def _manifest_unit_index(
    manifest: dict[str, Any],
) -> dict[tuple[str, str], str]:
    if not isinstance(manifest, dict):
        return {}
    if manifest.get("schema_version") != SUPPORT_MANIFEST_SCHEMA_VERSION:
        return {}
    raw_units = manifest.get("units")
    if not isinstance(raw_units, list):
        return {}
    out: dict[tuple[str, str], str] = {}
    for u in raw_units:
        if not isinstance(u, dict):
            continue
        t = u.get("type")
        i = u.get("id")
        fp = u.get("content_fp")
        if not isinstance(t, str) or not isinstance(i, str) or not isinstance(fp, str):
            continue
        out[(t, i)] = fp
    return out


def diff_support_manifests(
    previous: dict[str, Any] | None, current: dict[str, Any] | None
) -> dict[str, Any]:
    """Deterministic diff between two SupportManifest dicts (audit-side helper).

    Keys: support_absent, support_new, support_changed — each a sorted list of
    ``{"type", "id"}`` dicts (changed includes content_fp_prev/content_fp_curr).
    """
    prev_m = _manifest_unit_index(previous or {})
    curr_m = _manifest_unit_index(current or {})

    prev_keys = frozenset(prev_m)
    curr_keys = frozenset(curr_m)

    absent = sorted(
        ({"type": k[0], "id": k[1]} for k in prev_keys - curr_keys),
        key=lambda x: (x["type"], x["id"]),
    )
    new = sorted(
        ({"type": k[0], "id": k[1]} for k in curr_keys - prev_keys),
        key=lambda x: (x["type"], x["id"]),
    )
    changed: list[dict[str, str]] = []
    for k in sorted(prev_keys & curr_keys, key=lambda x: (x[0], x[1])):
        if prev_m[k] != curr_m[k]:
            changed.append(
                {
                    "type": k[0],
                    "id": k[1],
                    "content_fp_prev": prev_m[k],
                    "content_fp_curr": curr_m[k],
                }
            )

    return {
        "support_absent": absent,
        "support_new": new,
        "support_changed": changed,
    }
