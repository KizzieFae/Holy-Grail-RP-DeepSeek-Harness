"""Audit session folder identity validation (Holy Grail RP Issue #212).

Ensures ``session_owner`` and ``session_number`` agree across manifest, narrative,
and round index before writes. Cross-run mismatch raises ``AuditSessionIntegrityError``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuditSessionIntegrityError(RuntimeError):
    """Audit artifact identity does not match the active session (Issue #212)."""


def _load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    return raw if isinstance(raw, dict) else None


def _coerce_session_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _expect_identity_match(
    *,
    label: str,
    data: dict[str, Any],
    expected_owner: str,
    expected_number: int,
) -> None:
    exp_owner = str(expected_owner).strip()
    exp_num = int(expected_number)
    got_owner = str(data.get("session_owner", "") or "").strip()
    got_num = _coerce_session_number(data.get("session_number"))
    if got_owner != exp_owner:
        raise AuditSessionIntegrityError(
            f"{label}: session_owner mismatch "
            f"(expected {exp_owner!r}, found {got_owner!r}). Issue #212."
        )
    if got_num != exp_num:
        raise AuditSessionIntegrityError(
            f"{label}: session_number mismatch "
            f"(expected {exp_num}, found {got_num}). Issue #212."
        )


def _validate_round_index_root(
    idx: dict[str, Any],
    *,
    expected_owner: str,
    expected_number: int,
    manifest_exists: bool,
) -> None:
    exp_owner = str(expected_owner).strip()
    exp_num = int(expected_number)
    has_owner_key = "session_owner" in idx
    has_number_key = "session_number" in idx
    if has_owner_key:
        go = str(idx.get("session_owner", "") or "").strip()
        if go != exp_owner:
            raise AuditSessionIntegrityError(
                "_round_index.json: session_owner mismatch "
                f"(expected {exp_owner!r}, found {go!r}). Issue #212."
            )
    if has_number_key:
        gn = _coerce_session_number(idx.get("session_number"))
        if gn != exp_num:
            raise AuditSessionIntegrityError(
                "_round_index.json: session_number mismatch "
                f"(expected {exp_num}, found {gn}). Issue #212."
            )
    rounds = idx.get("rounds") or []
    if (
        isinstance(rounds, list)
        and len(rounds) > 0
        and not has_owner_key
        and not has_number_key
        and not manifest_exists
    ):
        raise AuditSessionIntegrityError(
            "_round_index.json contains rounds but lacks session identity fields and "
            "_manifest.json is missing (Issue #212)."
        )


def validate_audit_session_identity_before_manifest_write(
    session_path: Path,
    *,
    expected_owner: str,
    expected_number: int,
) -> None:
    """Allow manifest write only if existing artifacts do not contradict identity."""

    session_path = Path(session_path)
    manifest_path = session_path / "_manifest.json"
    narrative_path = session_path / "_narrative.json"
    index_path = session_path / "_round_index.json"

    exp_owner = str(expected_owner).strip()
    exp_num = int(expected_number)

    mf = _load_json_optional(manifest_path)
    nf = _load_json_optional(narrative_path)
    idx = _load_json_optional(index_path)

    if nf is not None:
        _expect_identity_match(
            label=str(narrative_path.name),
            data=nf,
            expected_owner=exp_owner,
            expected_number=exp_num,
        )
    if mf is not None:
        _expect_identity_match(
            label=str(manifest_path.name),
            data=mf,
            expected_owner=exp_owner,
            expected_number=exp_num,
        )
    if idx is not None:
        _validate_round_index_root(
            idx,
            expected_owner=exp_owner,
            expected_number=exp_num,
            manifest_exists=mf is not None,
        )


def validate_audit_session_identity_before_append(
    session_path: Path,
    *,
    expected_owner: str,
    expected_number: int,
) -> None:
    """Require coherent identity before narrative/index/turn/manifest-counter writes."""

    validate_audit_session_identity_before_manifest_write(
        session_path,
        expected_owner=expected_owner,
        expected_number=expected_number,
    )
    manifest_path = session_path / "_manifest.json"
    if not manifest_path.exists():
        raise AuditSessionIntegrityError(
            f"{session_path}: _manifest.json is required before narrative, round index, "
            "or per-turn audit writes (Issue #212)."
        )
    mf = _load_json_optional(manifest_path)
    if mf is None:
        raise AuditSessionIntegrityError(
            f"{session_path}: _manifest.json could not be read (Issue #212)."
        )
    _expect_identity_match(
        label=str(manifest_path.name),
        data=mf,
        expected_owner=str(expected_owner).strip(),
        expected_number=int(expected_number),
    )
