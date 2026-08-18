"""User callout review index and issue links (GitHub #125); non-runtime.

- ``_user_callout_review_index_v1.json``: lightweight keyed map for queue state.
- ``_user_callout_issue_links_v1.json``: sole authority for ``callout_id`` → GitHub issue.

Raw ``user_callouts_v1.json`` per session remains evidence authority (Issue #55).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from audit_logger_paths import resolve_base_dir
from user_callouts import USER_CALLOUTS_FILENAME, load_document as load_user_callouts_doc

REVIEW_INDEX_SCHEMA = "user_callout_review_index.v1"
REVIEW_INDEX_SCHEMA_VERSION = 1
REVIEW_INDEX_FILENAME = "_user_callout_review_index_v1.json"

ISSUE_LINKS_SCHEMA = "user_callout_issue_links.v1"
ISSUE_LINKS_SCHEMA_VERSION = 1
ISSUE_LINKS_FILENAME = "_user_callout_issue_links_v1.json"

from legacy.v1_orchestration.paths import autogen_python_dir

PATH_ANCHOR = autogen_python_dir()

ReviewDisposition = Literal["unreviewed", "dismissed"]


class UserCalloutReviewStoreError(ValueError):
    """Invalid or corrupt review index or issue links file."""


def path_relative_to_python_dir(abs_path: Path) -> str:
    """Repo-relative (forward slashes) from ``autogen_rp/python/``."""
    return str(abs_path.resolve().relative_to(PATH_ANCHOR)).replace("\\", "/")


def review_index_path(*, base_dir: Path) -> Path:
    return base_dir / REVIEW_INDEX_FILENAME


def issue_links_path(*, base_dir: Path) -> Path:
    return base_dir / ISSUE_LINKS_FILENAME


def session_path_hint(*, base_dir: Path, audit_session_number: int) -> str:
    """Lightweight string for navigation (under ``autogen_rp/python/``). Does not mkdir."""
    sn = int(audit_session_number)
    session_dir = base_dir / f"session_{sn:03d}"
    return path_relative_to_python_dir(session_dir)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically (temp + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp"
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _empty_review_index_root() -> dict[str, Any]:
    return {
        "schema": REVIEW_INDEX_SCHEMA,
        "schema_version": REVIEW_INDEX_SCHEMA_VERSION,
        "rows": {},
    }


def _empty_issue_links_root() -> dict[str, Any]:
    return {
        "schema": ISSUE_LINKS_SCHEMA,
        "schema_version": ISSUE_LINKS_SCHEMA_VERSION,
        "links": {},
    }


def load_review_index(path: Path) -> dict[str, Any]:
    """Load review index; missing file => empty. Corrupt => raise."""
    if not path.is_file():
        return _empty_review_index_root()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserCalloutReviewStoreError(f"cannot read: {path}: {exc}") from exc
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserCalloutReviewStoreError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise UserCalloutReviewStoreError("root must be a JSON object")
    if str(data.get("schema", "")) != REVIEW_INDEX_SCHEMA or int(
        data.get("schema_version", -1)
    ) != REVIEW_INDEX_SCHEMA_VERSION:
        raise UserCalloutReviewStoreError("schema or schema_version mismatch")
    rows = data.get("rows")
    if not isinstance(rows, dict):
        raise UserCalloutReviewStoreError("rows must be a JSON object (keyed map)")
    for k, v in rows.items():
        if not isinstance(k, str) or not k.strip():
            raise UserCalloutReviewStoreError("row keys must be non-empty strings")
        if not isinstance(v, dict):
            raise UserCalloutReviewStoreError(f"rows[{k!r}] must be an object")
        _validate_review_row(v, callout_id=k)
    return data


def _validate_review_row(row: dict[str, Any], *, callout_id: str) -> None:
    required = (
        "audit_session_number",
        "session_path_hint",
        "created_at_utc",
        "audit_round_number",
        "audit_turn_number",
        "continuity_turn_index",
        "review_disposition",
    )
    for key in required:
        if key not in row:
            raise UserCalloutReviewStoreError(f"rows[{callout_id!r}] missing {key}")
    if not isinstance(row.get("audit_session_number"), int):
        raise UserCalloutReviewStoreError("audit_session_number must be int")
    if not isinstance(row.get("session_path_hint"), str) or not row.get(
        "session_path_hint", ""
    ):
        raise UserCalloutReviewStoreError("session_path_hint must be a non-empty string")
    if not isinstance(row.get("created_at_utc"), str):
        raise UserCalloutReviewStoreError("created_at_utc must be a string")
    for ak in ("audit_round_number", "audit_turn_number"):
        if not isinstance(row.get(ak), int):
            raise UserCalloutReviewStoreError(f"{ak} must be an integer")
    cti = row.get("continuity_turn_index")
    if cti is not None and not isinstance(cti, int):
        raise UserCalloutReviewStoreError("continuity_turn_index must be int or null")
    disp = row.get("review_disposition")
    if disp not in ("unreviewed", "dismissed"):
        raise UserCalloutReviewStoreError("review_disposition must be unreviewed|dismissed")


def load_issue_links(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty_issue_links_root()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserCalloutReviewStoreError(f"cannot read: {path}: {exc}") from exc
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserCalloutReviewStoreError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise UserCalloutReviewStoreError("root must be a JSON object")
    if str(data.get("schema", "")) != ISSUE_LINKS_SCHEMA or int(
        data.get("schema_version", -1)
    ) != ISSUE_LINKS_SCHEMA_VERSION:
        raise UserCalloutReviewStoreError("schema or schema_version mismatch")
    links = data.get("links")
    if not isinstance(links, dict):
        raise UserCalloutReviewStoreError("links must be a JSON object (keyed map)")
    for k, v in links.items():
        if not isinstance(k, str) or not k.strip():
            raise UserCalloutReviewStoreError("link keys must be non-empty strings")
        if not isinstance(v, dict):
            raise UserCalloutReviewStoreError(f"links[{k!r}] must be an object")
        for fk in ("issue_number", "issue_url", "linked_at_utc"):
            if fk not in v:
                raise UserCalloutReviewStoreError(f"links[{k!r}] missing {fk}")
        if not isinstance(v.get("issue_number"), int):
            raise UserCalloutReviewStoreError("issue_number must be int")
        if not isinstance(v.get("issue_url"), str) or not v.get("issue_url", "").strip():
            raise UserCalloutReviewStoreError("issue_url must be a non-empty string")
        if not isinstance(v.get("linked_at_utc"), str):
            raise UserCalloutReviewStoreError("linked_at_utc must be a string")
    return data


def save_review_index(path: Path, data: dict[str, Any]) -> None:
    rows = data.get("rows", {})
    if not isinstance(rows, dict):
        raise UserCalloutReviewStoreError("rows must be a dict")
    for k, v in rows.items():
        if isinstance(v, dict):
            _validate_review_row(v, callout_id=k)
    out = {
        "schema": REVIEW_INDEX_SCHEMA,
        "schema_version": REVIEW_INDEX_SCHEMA_VERSION,
        "rows": dict(rows),
    }
    atomic_write_json(path, out)


def _validate_link_map(links: dict[str, Any]) -> None:
    for k, v in links.items():
        if not isinstance(k, str) or not k.strip():
            raise UserCalloutReviewStoreError("link keys must be non-empty strings")
        if not isinstance(v, dict):
            raise UserCalloutReviewStoreError(f"links[{k!r}] must be an object")
        for fk in ("issue_number", "issue_url", "linked_at_utc"):
            if fk not in v:
                raise UserCalloutReviewStoreError(f"links[{k!r}] missing {fk}")
        if not isinstance(v.get("issue_number"), int):
            raise UserCalloutReviewStoreError("issue_number must be int")
        if not isinstance(v.get("issue_url"), str) or not v.get("issue_url", "").strip():
            raise UserCalloutReviewStoreError("issue_url must be a non-empty string")
        if not isinstance(v.get("linked_at_utc"), str):
            raise UserCalloutReviewStoreError("linked_at_utc must be a string")


def save_issue_links(path: Path, data: dict[str, Any]) -> None:
    links = data.get("links", {})
    if not isinstance(links, dict):
        raise UserCalloutReviewStoreError("links must be a dict")
    _validate_link_map(links)
    atomic_write_json(
        path,
        {
            "schema": ISSUE_LINKS_SCHEMA,
            "schema_version": ISSUE_LINKS_SCHEMA_VERSION,
            "links": dict(links),
        },
    )


def review_row_from_raw_record(
    *,
    base_dir: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Build a lightweight index row (no artifact_refs) from a raw #55 record."""
    sn = int(record["audit_session_number"])
    return {
        "audit_session_number": sn,
        "session_path_hint": session_path_hint(
            base_dir=base_dir, audit_session_number=sn
        ),
        "created_at_utc": str(record["created_at_utc"]),
        "audit_round_number": int(record["audit_round_number"]),
        "audit_turn_number": int(record["audit_turn_number"]),
        "continuity_turn_index": record.get("continuity_turn_index"),
        "review_disposition": "unreviewed",
    }


def upsert_review_row_after_new_callout(
    *,
    base_dir: Path,
    record: dict[str, Any],
) -> None:
    """Add or update review index row for a new raw callout (post-append)."""
    path = review_index_path(base_dir=base_dir)
    data = load_review_index(path)
    rows: dict[str, Any] = dict(data.get("rows", {}))
    cid = str(record["callout_id"])
    rows[cid] = review_row_from_raw_record(base_dir=base_dir, record=record)
    data["rows"] = rows
    save_review_index(path, data)


def is_promoted(*, base_dir: Path, callout_id: str) -> bool:
    path = issue_links_path(base_dir=base_dir)
    data = load_issue_links(path)
    return callout_id in (data.get("links") or {})


def dismiss_callout(*, base_dir: Path, callout_id: str) -> None:
    """Set review_disposition to dismissed. Forbidden if callout is promoted (has link)."""
    if is_promoted(base_dir=base_dir, callout_id=callout_id):
        raise ValueError(
            "dismissing a promoted callout is not allowed in v1 (callout has an issue link)"
        )
    path = review_index_path(base_dir=base_dir)
    data = load_review_index(path)
    rows: dict[str, Any] = dict(data.get("rows", {}))
    if callout_id not in rows:
        raise ValueError(f"unknown callout_id in index: {callout_id!r}")
    row = dict(rows[callout_id])
    row["review_disposition"] = "dismissed"
    rows[callout_id] = row
    data["rows"] = rows
    save_review_index(path, data)


def sync_index_entries_from_raw(*, base_dir: Path) -> int:
    """Add review rows for raw callouts missing from the index. Returns count added."""
    raw_map = load_raw_map_from_disk(base_dir=base_dir)
    path = review_index_path(base_dir=base_dir)
    data = load_review_index(path)
    rows: dict[str, Any] = dict(data.get("rows", {}))
    added = 0
    for cid, rec in raw_map.items():
        if cid not in rows:
            rows[cid] = review_row_from_raw_record(
                base_dir=base_dir, record=rec
            )
            added += 1
    if added:
        data["rows"] = rows
        save_review_index(path, data)
    return added


def record_issue_promotion(
    *,
    base_dir: Path,
    callout_id: str,
    issue_number: int,
    issue_url: str,
    replace: bool = False,
) -> None:
    """Record promotion: issue link map is sole authority.

    Rejects duplicate ``callout_id`` unless ``replace`` is True (e.g. reconciling
    a link to a different GitHub issue while keeping the same callout_id).
    """
    links_p = issue_links_path(base_dir=base_dir)
    ldata = load_issue_links(links_p)
    links: dict[str, Any] = dict(ldata.get("links", {}))
    if callout_id in links and not replace:
        raise ValueError(
            f"callout_id {callout_id!r} already has an issue link; duplicate promotion rejected"
        )
    if replace and callout_id in links:
        now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        links[callout_id] = {
            "issue_number": int(issue_number),
            "issue_url": str(issue_url).strip(),
            "linked_at_utc": now,
        }
        ldata["links"] = links
        save_issue_links(links_p, ldata)
        return
    idx_p = review_index_path(base_dir=base_dir)
    idata = load_review_index(idx_p)
    rows: dict[str, Any] = dict(idata.get("rows", {}))
    if callout_id not in rows:
        raw = find_raw_record(base_dir=base_dir, callout_id=callout_id)
        if raw is None:
            raise ValueError(
                f"callout_id {callout_id!r} not in index and not found in session callout files"
            )
        rows[callout_id] = review_row_from_raw_record(
            base_dir=base_dir, record=raw
        )
    elif rows[callout_id].get("review_disposition") == "dismissed":
        r = dict(rows[callout_id])
        r["review_disposition"] = "unreviewed"
        rows[callout_id] = r
    now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    links[callout_id] = {
        "issue_number": int(issue_number),
        "issue_url": str(issue_url).strip(),
        "linked_at_utc": now,
    }
    ldata["links"] = links
    save_issue_links(links_p, ldata)
    idata["rows"] = rows
    save_review_index(idx_p, idata)


def _iter_session_callout_paths(base_dir: Path) -> list[Path]:
    out: list[Path] = []
    for session_dir in sorted(base_dir.glob("session_*")):
        if not session_dir.is_dir():
            continue
        p = session_dir / USER_CALLOUTS_FILENAME
        if p.is_file():
            out.append(p)
    return out


def load_raw_map_from_disk(*, base_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all callout_id -> raw record (last wins if duplicate id across files)."""
    by_id: dict[str, dict[str, Any]] = {}
    for path in _iter_session_callout_paths(base_dir):
        try:
            doc = load_user_callouts_doc(path)
        except Exception:
            continue
        for rec in doc.get("records", []):
            if not isinstance(rec, dict) or "callout_id" not in rec:
                continue
            cid = str(rec["callout_id"])
            by_id[cid] = rec
    return by_id


def find_raw_record(*, base_dir: Path, callout_id: str) -> dict[str, Any] | None:
    m = load_raw_map_from_disk(base_dir=base_dir)
    return m.get(callout_id)


def resolve_default_audit_base_dir(
    base_dir: Path | str | None = None,
) -> Path:
    """Default ``data/rp_audits`` (same as audit logger) unless ``base_dir`` is set."""
    if base_dir is not None:
        return Path(base_dir).resolve()
    return resolve_base_dir(file_path=str(Path(__file__).resolve()), base_dir=None)


def find_user_callouts_path_for_callout(
    *, base_dir: Path, callout_id: str
) -> Path | None:
    """Path to the ``user_callouts_v1.json`` file containing this ``callout_id``, if any."""
    for p in _iter_session_callout_paths(base_dir):
        try:
            doc = load_user_callouts_doc(p)
        except Exception:
            continue
        for rec in doc.get("records", []):
            if isinstance(rec, dict) and str(rec.get("callout_id")) == str(callout_id):
                return p
    return None


def get_issue_link_for_callout(
    *, base_dir: Path, callout_id: str
) -> dict[str, Any] | None:
    ldata = load_issue_links(issue_links_path(base_dir=base_dir))
    link = (ldata.get("links") or {}).get(callout_id)
    return link if isinstance(link, dict) else None


@dataclass
class RebuildResult:
    review_rows_written: int
    link_keys: int
    orphan_index_ids: list[str] = field(default_factory=list)
    orphan_link_ids: list[str] = field(default_factory=list)
    inconsistency_dismissed_with_link: list[str] = field(default_factory=list)


def rebuild_review_state(*, base_dir: Path) -> RebuildResult:
    """
    Rebuild review index from raw callouts, overlaying issue links, preserving index-only rows.

    Precedence: raw -> links (promotion) -> reconcile dispositions.
    """
    raw_map = load_raw_map_from_disk(base_dir=base_dir)
    idx_p = review_index_path(base_dir=base_dir)
    l_p = issue_links_path(base_dir=base_dir)
    try:
        old_data = load_review_index(idx_p)
    except UserCalloutReviewStoreError:
        old_data = _empty_review_index_root()
    old_rows: dict[str, Any] = dict(old_data.get("rows", {}))
    ldata = load_issue_links(l_p)
    links: dict[str, Any] = dict(ldata.get("links", {}))

    new_rows: dict[str, Any] = {}
    inconsistency: list[str] = []

    for cid, rec in raw_map.items():
        row = review_row_from_raw_record(base_dir=base_dir, record=rec)
        if cid in old_rows and isinstance(old_rows[cid], dict):
            o = old_rows[cid]
            disp = o.get("review_disposition")
            if disp in ("unreviewed", "dismissed"):
                row["review_disposition"] = disp
        if cid in links and row.get("review_disposition") == "dismissed":
            inconsistency.append(cid)
            row["review_disposition"] = "unreviewed"
        new_rows[cid] = row

    orphan_index: list[str] = []
    for cid, orow in old_rows.items():
        if cid not in new_rows and isinstance(orow, dict):
            new_rows[cid] = orow
            orphan_index.append(cid)

    orphan_links: list[str] = [cid for cid in links if cid not in raw_map]

    out = {
        "schema": REVIEW_INDEX_SCHEMA,
        "schema_version": REVIEW_INDEX_SCHEMA_VERSION,
        "rows": new_rows,
    }
    save_review_index(idx_p, out)

    return RebuildResult(
        review_rows_written=len(new_rows),
        link_keys=len(links),
        orphan_index_ids=orphan_index,
        orphan_link_ids=orphan_links,
        inconsistency_dismissed_with_link=inconsistency,
    )


def list_unresolved(
    *, base_dir: Path
) -> list[tuple[str, dict[str, Any]]]:
    """Queue: not promoted (no link) and not dismissed; sorted by created_at_utc desc."""
    idx = load_review_index(review_index_path(base_dir=base_dir))
    ldata = load_issue_links(issue_links_path(base_dir=base_dir))
    links: dict[str, Any] = dict(ldata.get("links", {}))
    rows: dict[str, Any] = dict(idx.get("rows", {}))
    out: list[tuple[str, dict[str, Any]]] = []
    for cid, row in rows.items():
        if not isinstance(row, dict):
            continue
        if row.get("review_disposition") == "dismissed":
            continue
        if cid in links:
            continue
        out.append((cid, row))
    out.sort(key=lambda t: t[1].get("created_at_utc", ""), reverse=True)
    return out
