"""User Callouts (Issue #55) — append-only triage annotations for audit-backed runs.

``user_callouts_v1.json`` is the authoritative per-audit-session store. It is
non-runtime: nothing in the director / continuity / validation path imports
this module.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from audit_logger_paths import get_session_path

USER_CALLOUTS_SCHEMA = "user_callouts.v1"
USER_CALLOUTS_SCHEMA_VERSION = 1
USER_CALLOUTS_FILENAME = "user_callouts_v1.json"

# Paths in ``artifact_refs`` are relative to ``autogen_rp/python/`` (parent of ``rp_app``).
_PATH_ANCHOR: Path = Path(__file__).resolve().parent.parent


class UserCalloutDocumentError(ValueError):
    """Invalid or corrupt ``user_callouts_v1.json`` (strict: do not auto-repair)."""


def path_relative_to_python_dir(abs_path: Path) -> str:
    """Stable repo-relative string (forward slashes) from ``autogen_rp/python/``."""
    return str(abs_path.resolve().relative_to(_PATH_ANCHOR)).replace("\\", "/")


def get_user_callouts_path(*, base_dir: Path, audit_session_number: int) -> Path:
    session_dir = get_session_path(base_dir=base_dir, session_number=audit_session_number)
    return session_dir / USER_CALLOUTS_FILENAME


RE_FULL_TURN = re.compile(
    r"_turn(?P<turn>\d{2})_(?P<bot>.+?)_full\.json$", re.IGNORECASE
)


def pick_primary_full_path(
    round_dir: Path, *, audit_turn_number: int
) -> Path | None:
    """Choose one ``*_full.json`` for this round/turn, or None if none exist.

    Precedence: character (not director/narrator) → narrator → director;
    multiple in a bucket: lexicographic by path name.
    """
    if not round_dir.is_dir():
        return None
    turn_s = f"{int(audit_turn_number):02d}"
    char: list[Path] = []
    narr: list[Path] = []
    dirc: list[Path] = []
    for p in round_dir.iterdir():
        if not p.is_file():
            continue
        m = RE_FULL_TURN.search(p.name)
        if not m or m.group("turn") != turn_s:
            continue
        bot = m.group("bot").strip().lower()
        if bot == "director":
            dirc.append(p)
        elif bot == "narrator":
            narr.append(p)
        else:
            char.append(p)
    if char:
        return sorted(char, key=lambda x: x.name)[0]
    if narr:
        return sorted(narr, key=lambda x: x.name)[0]
    if dirc:
        return sorted(dirc, key=lambda x: x.name)[0]
    return None


@dataclass(frozen=True, slots=True)
class ArtifactRefInputs:
    base_dir: Path
    audit_session_number: int
    audit_round_number: int
    audit_turn_number: int
    primary_full: Path | None
    session_state_json: Path | None


def build_artifact_refs(inputs: ArtifactRefInputs) -> dict[str, Any]:
    """Build ``artifact_refs`` with repo-relative path strings and nullables."""
    sn = int(inputs.audit_session_number)
    rr = int(inputs.audit_round_number)
    session_dir = get_session_path(base_dir=inputs.base_dir, session_number=sn)
    round_dir = session_dir / f"round_{rr:03d}"
    round_path = path_relative_to_python_dir(round_dir)
    audit_summary_path = path_relative_to_python_dir(session_dir / "_audit_summary.json")
    session_state: str | None
    if inputs.session_state_json is not None and inputs.session_state_json.is_file():
        session_state = path_relative_to_python_dir(inputs.session_state_json)
    else:
        session_state = None
    primary: str | None
    if inputs.primary_full is not None and inputs.primary_full.is_file():
        primary = path_relative_to_python_dir(inputs.primary_full)
    else:
        primary = None
    return {
        "round_path": round_path,
        "primary_full_path": primary,
        "audit_summary_path": audit_summary_path,
        "session_state_path": session_state,
    }


def empty_document_root() -> dict[str, Any]:
    return {
        "schema": USER_CALLOUTS_SCHEMA,
        "schema_version": USER_CALLOUTS_SCHEMA_VERSION,
        "records": [],
    }


def load_document(path: Path) -> dict[str, Any]:
    """Load and validate; missing file => empty root. Existing corrupt => raise."""
    if not path.is_file():
        return empty_document_root()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserCalloutDocumentError(f"cannot read: {path}: {exc}") from exc
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserCalloutDocumentError(
            f"invalid JSON in {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise UserCalloutDocumentError("root must be a JSON object")
    if str(data.get("schema", "")) != USER_CALLOUTS_SCHEMA or int(
        data.get("schema_version", -1)
    ) != USER_CALLOUTS_SCHEMA_VERSION:
        raise UserCalloutDocumentError("schema or schema_version mismatch")
    rec = data.get("records")
    if not isinstance(rec, list):
        raise UserCalloutDocumentError("records must be a JSON array")
    for i, item in enumerate(rec):
        if not isinstance(item, dict):
            raise UserCalloutDocumentError(f"records[{i}] must be an object")
    return data


def validate_callout_record(rec: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty if valid)."""
    errors: list[str] = []
    required_top = (
        "callout_id",
        "created_at_utc",
        "audit_session_owner",
        "audit_session_number",
        "runtime_session_id",
        "scene_template_id",
        "audit_round_number",
        "audit_turn_number",
        "continuity_turn_index",
        "note",
        "artifact_refs",
    )
    for key in required_top:
        if key not in rec:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    if not isinstance(rec.get("callout_id"), str) or not str(rec.get("callout_id")):
        errors.append("callout_id must be a non-empty string")
    if not isinstance(rec.get("created_at_utc"), str):
        errors.append("created_at_utc must be a string")
    if not isinstance(rec.get("audit_session_owner"), str):
        errors.append("audit_session_owner must be a string")
    if not isinstance(rec.get("audit_session_number"), int):
        errors.append("audit_session_number must be an integer")
    if rec.get("runtime_session_id") is not None and not isinstance(
        rec.get("runtime_session_id"), str
    ):
        errors.append("runtime_session_id must be string or null")
    stid = rec.get("scene_template_id")
    if stid is not None and not isinstance(stid, str):
        errors.append("scene_template_id must be string or null")
    for ak in ("audit_round_number", "audit_turn_number"):
        if not isinstance(rec.get(ak), int):
            errors.append(f"{ak} must be an integer")
    cti = rec.get("continuity_turn_index")
    if cti is not None and not isinstance(cti, int):
        errors.append("continuity_turn_index must be int or null")
    note = rec.get("note")
    if note is not None and not isinstance(note, str):
        errors.append("note must be string or null")
    refs = rec.get("artifact_refs")
    if not isinstance(refs, dict):
        errors.append("artifact_refs must be an object")
    else:
        for rk, nullable in (
            ("round_path", False),
            ("primary_full_path", True),
            ("audit_summary_path", False),
            ("session_state_path", True),
        ):
            if rk not in refs:
                errors.append(f"artifact_refs missing {rk}")
            else:
                val = refs.get(rk)
                if val is None and nullable:
                    continue
                if not isinstance(val, str) or not str(val).strip():
                    errors.append(f"artifact_refs.{rk} must be a non-empty string or null")
    return errors


def append_callout(
    path: Path,
    record: dict[str, Any],
) -> None:
    """Append one record. Strict: if ``path`` exists and is invalid, raise; never truncate."""
    errs = validate_callout_record(record)
    if errs:
        raise ValueError("invalid record: " + "; ".join(errs))
    if path.is_file():
        document = load_document(path)
    else:
        document = empty_document_root()
    records = list(document.get("records", []))
    records.append(record)
    out = {
        "schema": USER_CALLOUTS_SCHEMA,
        "schema_version": USER_CALLOUTS_SCHEMA_VERSION,
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp"
    tmp.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def build_callout_record(
    *,
    audit_session_owner: str,
    audit_session_number: int,
    audit_round_number: int,
    audit_turn_number: int,
    runtime_session_id: str | None,
    scene_template_id: str | None,
    continuity_turn_index: int | None,
    note: str | None,
    artifact_inputs: ArtifactRefInputs,
) -> dict[str, Any]:
    return {
        "callout_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "audit_session_owner": str(audit_session_owner).strip(),
        "audit_session_number": int(audit_session_number),
        "runtime_session_id": runtime_session_id,
        "scene_template_id": scene_template_id,
        "audit_round_number": int(audit_round_number),
        "audit_turn_number": int(audit_turn_number),
        "continuity_turn_index": continuity_turn_index,
        "note": note,
        "artifact_refs": build_artifact_refs(artifact_inputs),
    }


def new_callout(
    *,
    base_dir: Path,
    path: Path,
    audit_session_owner: str,
    audit_session_number: int,
    audit_round_number: int,
    audit_turn_number: int,
    runtime_session_id: str | None,
    scene_template_id: str | None,
    continuity_turn_index: int | None,
    note: str | None,
    session_state_json: Path | None,
) -> dict[str, Any]:
    """Build record and append. Returns the record (includes ``callout_id``)."""
    session_dir = get_session_path(
        base_dir=base_dir, session_number=audit_session_number
    )
    round_dir = session_dir / f"round_{int(audit_round_number):03d}"
    primary = pick_primary_full_path(
        round_dir, audit_turn_number=audit_turn_number
    )
    inputs = ArtifactRefInputs(
        base_dir=base_dir,
        audit_session_number=audit_session_number,
        audit_round_number=audit_round_number,
        audit_turn_number=audit_turn_number,
        primary_full=primary,
        session_state_json=session_state_json,
    )
    record = build_callout_record(
        audit_session_owner=audit_session_owner,
        audit_session_number=audit_session_number,
        audit_round_number=audit_round_number,
        audit_turn_number=audit_turn_number,
        runtime_session_id=runtime_session_id,
        scene_template_id=scene_template_id,
        continuity_turn_index=continuity_turn_index,
        note=(note or "").strip() or None,
        artifact_inputs=inputs,
    )
    append_callout(path, record)
    return record
