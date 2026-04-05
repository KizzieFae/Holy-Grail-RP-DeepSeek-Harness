"""Lightweight retrieval observability for audits and structured_eval (Phase 4A).

Does not implement selection or prompt formatting — only summarizes bundles and env state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from retrieved_context_select import get_index_path_from_env
from runtime_packets import RetrievedContextBundle

_RETRIEVED_SOURCE_REFS_CAP = 12


def build_retrieval_summary_for_audit(bundle: RetrievedContextBundle) -> dict[str, Any]:
    """Per-turn stats from the bundle (no full text)."""
    items = tuple(bundle.items)
    n = len(items)
    chars = sum(len(it.text) for it in items)
    refs = [it.source_ref for it in items[:_RETRIEVED_SOURCE_REFS_CAP]]
    return {
        "retrieved_block_present": n > 0,
        "retrieved_item_count": n,
        "retrieved_char_count": chars,
        "retrieved_source_refs": refs,
    }


def retrieval_index_fingerprint(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        if not p.is_file():
            return f"missing|{path}"
        st = p.stat()
        return f"{path}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        return f"unreadable|{path}"


def build_retrieval_session_audit(*, saw_nonempty_bundle: bool) -> dict[str, Any]:
    """Run-level retrieval fields from env + whether any character turn had bundle items."""
    path = get_index_path_from_env()
    mode = "on" if path else "off"
    verified = mode == "on" and bool(saw_nonempty_bundle)
    return {
        "retrieval_mode": mode,
        "retrieval_index_path": path,
        "retrieval_verified_active": verified,
        "retrieval_index_fingerprint": retrieval_index_fingerprint(path),
    }


def verify_retrieval_strict_or_raise(
    session: dict[str, Any], *, scene_template_id: str | None
) -> None:
    """If retrieval is ON and the scene has a template id, require a non-empty bundle on some turn."""
    if session.get("retrieval_mode") != "on":
        return
    if not str(scene_template_id or "").strip():
        return
    if session.get("retrieval_verified_active"):
        return
    raise ValueError(
        "Retrieval is ON (RP_RETRIEVED_CONTEXT_INDEX set) and scene_template_id is set, "
        "but no character turn produced a non-empty retrieved bundle. "
        "Check the index path, manifest, cast, and scene_template_id alignment."
    )


def merge_retrieval_session_into_audit_summary(
    report_path: str | None, session: dict[str, Any]
) -> None:
    """Append retrieval_session to existing _audit_summary.json (headless / Streamlit)."""
    if not report_path:
        return
    p = Path(report_path)
    if not p.is_file():
        return
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    out = dict(data)
    out["retrieval_session"] = dict(session)
    p.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
