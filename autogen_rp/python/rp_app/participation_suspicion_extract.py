"""Issue #246 — deterministic C3 suspicion extraction (offline only).

Wraps existing emission/cohesion extract rows. C3 rubric classes become
``participation_suspicion.v1`` records — suspicion, not validation failure.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Iterator

from emission_map_extract import EmissionMapRow, write_jsonl

SCHEMA_VERSION: Final[str] = "participation_suspicion.v1"
POSITIVE_SUSPICION_RUBRIC_CLASSES: Final[frozenset[str]] = frozenset(
    {"C3_missed_covered_change"}
)

_FLAG_KEYS = (
    "F_exit_cue",
    "F_reentry_cue",
    "F_remote_cue",
    "F_no_proposal",
    "F_focus_in_room",
    "F_location_drift",
    "F_motivation_exit",
    "F_suspect_miss",
    "F_context_drift",
    "F_rebound_cue",
    "F_tether_cue",
    "F_filler_cue",
    "F_in_room_focus",
    "F_fiction_roster_drift",
)


@dataclass
class ParticipationSuspicionRecord:
    schema_version: str = SCHEMA_VERSION
    suspicion_id: str = ""
    source_artifact: str = ""
    audit_session_number: int | None = None
    turn_number: int | None = None
    actor: str = ""
    probe_id: str | None = None
    transition_type: str | None = None
    deterministic_rubric_class: str = ""
    expected_rubric: str | None = None
    deterministic_flags: dict[str, bool] = field(default_factory=dict)
    cohesion_flags: dict[str, bool] = field(default_factory=dict)
    semantic_decision: str | None = None
    proposal_count: int = 0
    spd_authority_outcome: str | None = None
    scene_snapshot_before: dict[str, Any] = field(default_factory=dict)
    scene_snapshot_after: dict[str, Any] = field(default_factory=dict)
    suspicion_reason_codes: list[str] = field(default_factory=list)
    suspicion_emitted_at: str = ""
    adjudication_status: str = "pending"
    effective_user_trigger: str = ""


def make_suspicion_id(
    *,
    audit_session_number: int | None,
    turn_number: int | None,
    actor: str,
    probe_id: str | None,
) -> str:
    return ":".join(
        [
            str(audit_session_number or ""),
            str(turn_number or ""),
            str(actor or ""),
            str(probe_id or ""),
        ]
    )


def _reason_codes_from_row(row: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    if row.get("expected_rubric") == "covered_change" and row.get("F_no_proposal"):
        codes.append("expect_covered_no_proposal")
    if row.get("F_suspect_miss"):
        codes.append("suspect_miss_heuristic")
    if row.get("F_exit_cue"):
        codes.append("exit_cue")
    if row.get("F_reentry_cue"):
        codes.append("reentry_cue")
    if row.get("F_remote_cue"):
        codes.append("remote_cue")
    if row.get("F_tether_cue"):
        codes.append("tether_cue")
    if row.get("F_rebound_cue"):
        codes.append("rebound_cue")
    if row.get("F_in_room_focus"):
        codes.append("in_room_focus")
    if row.get("F_fiction_roster_drift"):
        codes.append("fiction_roster_drift")
    return codes


def _compact_scene_snapshot(row: dict[str, Any], *, after: bool = False) -> dict[str, Any]:
    if after:
        return {
            "present_characters": list(row.get("present_characters") or []),
            "offstage_characters": list(row.get("offstage_characters") or []),
            "character_presence_status": dict(row.get("character_presence_status") or {}),
        }
    return {
        "target_presence_constraint": row.get("target_presence_constraint"),
        "target_in_present": row.get("target_in_present"),
        "target_in_offstage": row.get("target_in_offstage"),
        "target_status": row.get("target_status"),
    }


def row_dict_to_suspicion(row: dict[str, Any], *, emitted_at: str | None = None) -> ParticipationSuspicionRecord | None:
    rubric = str(row.get("rubric_class") or "").strip()
    if rubric not in POSITIVE_SUSPICION_RUBRIC_CLASSES:
        return None
    flags = {k: bool(row.get(k)) for k in _FLAG_KEYS if k in row}
    cohesion_keys = (
        "F_rebound_cue",
        "F_tether_cue",
        "F_filler_cue",
        "F_in_room_focus",
        "F_fiction_roster_drift",
    )
    cohesion = {k: bool(row.get(k)) for k in cohesion_keys if k in row}
    sid = make_suspicion_id(
        audit_session_number=row.get("audit_session_number"),
        turn_number=row.get("turn_number"),
        actor=str(row.get("actor") or ""),
        probe_id=row.get("probe_id"),
    )
    ts = emitted_at or datetime.now(timezone.utc).isoformat()
    return ParticipationSuspicionRecord(
        suspicion_id=sid,
        source_artifact=str(row.get("source_artifact") or ""),
        audit_session_number=row.get("audit_session_number"),
        turn_number=row.get("turn_number"),
        actor=str(row.get("actor") or ""),
        probe_id=row.get("probe_id"),
        transition_type=row.get("transition_type"),
        deterministic_rubric_class=rubric,
        expected_rubric=row.get("expected_rubric"),
        deterministic_flags={k: flags[k] for k in _FLAG_KEYS[:9] if k in flags},
        cohesion_flags=cohesion,
        semantic_decision=row.get("semantic_decision"),
        proposal_count=int(row.get("proposal_count") or 0),
        spd_authority_outcome=row.get("spd_authority_outcome"),
        scene_snapshot_before=_compact_scene_snapshot(row, after=False),
        scene_snapshot_after=_compact_scene_snapshot(row, after=True),
        suspicion_reason_codes=_reason_codes_from_row(row),
        suspicion_emitted_at=ts,
        effective_user_trigger=str(row.get("effective_user_trigger") or "")[:500],
    )


def emission_row_to_suspicion(row: EmissionMapRow, *, emitted_at: str | None = None) -> ParticipationSuspicionRecord | None:
    return row_dict_to_suspicion(asdict(row), emitted_at=emitted_at)


def suspicions_from_row_dicts(
    rows: list[dict[str, Any]],
    *,
    emitted_at: str | None = None,
) -> list[ParticipationSuspicionRecord]:
    out: list[ParticipationSuspicionRecord] = []
    for row in rows:
        rec = row_dict_to_suspicion(row, emitted_at=emitted_at)
        if rec is not None:
            out.append(rec)
    return out


def load_jsonl_rows(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def extract_suspicions_from_jsonl(path: str | Path, *, emitted_at: str | None = None) -> list[ParticipationSuspicionRecord]:
    return suspicions_from_row_dicts(load_jsonl_rows(path), emitted_at=emitted_at)


def write_suspicion_jsonl(records: list[ParticipationSuspicionRecord], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def suspicion_from_dict(row: dict[str, Any]) -> ParticipationSuspicionRecord:
    fields = {f.name for f in ParticipationSuspicionRecord.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    payload = {k: row[k] for k in row if k in fields}
    return ParticipationSuspicionRecord(**payload)


def iter_suspicion_records(path: str | Path) -> Iterator[ParticipationSuspicionRecord]:
    for row in load_jsonl_rows(path):
        if row.get("schema_version") == SCHEMA_VERSION:
            yield suspicion_from_dict(row)
            continue
        rec = row_dict_to_suspicion(row)
        if rec is not None:
            yield rec
