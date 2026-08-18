"""Deterministic Willow departure experiment extraction (#227 anchor-only must_remain)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from emission_map_extract import (
    EmissionMapRow,
    ProbeManifestEntry,
    extract_row_from_audit_file,
    load_probe_manifest,
    summarize_rows,
)

WILLOW_NAME_RE = re.compile(r"willow", re.I)
REBOUND_RE = re.compile(
    r"\b(forgot|keys|excuse|come\s+back|right\s+back|returned|rejoin|same\s+beat)\b",
    re.I,
)
TETHER_RE = re.compile(
    r"\b(phone|call(?:ed|ing|s)?|garage|hall(?:way)?|through\s+the\s+door|"
    r"open\s+door|still\s+talk|yell(?:ed|ing|s)?\s+back)\b",
    re.I,
)
IN_ROOM_FOCUS_RE = re.compile(r"in the room with the live exchange", re.I)
OFFSTAGE_FOCUS_RE = re.compile(r"currently offstage", re.I)
WITHDRAWN_FOCUS_RE = re.compile(r"partially withdrawn", re.I)

_SCHEMA = "willow_departure_row.v1"


@dataclass
class WillowDepartureRow(EmissionMapRow):
    schema_version: str = _SCHEMA
    willow_presence_constraint: str | None = None
    willow_in_present: bool | None = None
    willow_in_offstage: bool | None = None
    willow_status: str | None = None
    F_rebound_cue: bool = False
    F_tether_cue: bool = False
    F_in_room_focus: bool = False
    F_offstage_focus: bool = False
    F_fiction_roster_drift: bool = False
    trigger_redacted: bool = False


def _willow_actor_name(actor: str) -> bool:
    return bool(WILLOW_NAME_RE.search(str(actor or "")))


def _willow_constraint_from_prompt(prompt: str) -> str | None:
    idx = prompt.find("SCENE ROLES:")
    if idx < 0:
        return None
    block = prompt[idx : idx + 4000]
    for line in block.splitlines():
        if "Willow" not in line and "willow" not in line.lower():
            continue
        if "presence_constraint" in line and "must_remain" in line:
            return "must_remain"
        if "presence_constraint" in line and "flexible" in line:
            return "flexible"
    # JSON block parsing fallback
    try:
        start = block.find("[")
        end = block.find("]", start)
        if start >= 0 and end > start:
            arr = json.loads(block[start : end + 1])
            if isinstance(arr, list):
                for item in arr:
                    if not isinstance(item, dict):
                        continue
                    char = str(item.get("character") or "")
                    if _willow_actor_name(char):
                        return str(item.get("presence_constraint") or "") or None
    except json.JSONDecodeError:
        pass
    return None


def enrich_willow_row(row: EmissionMapRow, *, prompt: str) -> WillowDepartureRow:
    beats = f"{row.beats_action_text} {row.beats_dialogue_text}".strip()
    mot = f"{row.motivation_goal} {row.motivation_tactic}".strip()
    combined = f"{beats} {mot}"
    willow_present = any(_willow_actor_name(x) for x in row.present_characters)
    willow_off = any(_willow_actor_name(x) for x in row.offstage_characters)
    willow_status = None
    for k, v in row.character_presence_status.items():
        if _willow_actor_name(k):
            willow_status = v
            break
    focus_blob = f"{row.active_focus_position or ''} {row.active_focus_movement or ''}"
    in_room = bool(IN_ROOM_FOCUS_RE.search(prompt) or IN_ROOM_FOCUS_RE.search(focus_blob))
    off_focus = bool(OFFSTAGE_FOCUS_RE.search(prompt) or WITHDRAWN_FOCUS_RE.search(focus_blob))
    exit_fiction = bool(row.F_exit_cue or row.F_remote_cue)
    roster_drift = exit_fiction and willow_present and not willow_off and in_room
    trig = row.effective_user_trigger or ""
    data = asdict(row)
    data.update(
        {
            "schema_version": _SCHEMA,
            "willow_presence_constraint": _willow_constraint_from_prompt(prompt),
            "willow_in_present": willow_present if _willow_actor_name(row.actor) else None,
            "willow_in_offstage": willow_off if _willow_actor_name(row.actor) else None,
            "willow_status": willow_status if _willow_actor_name(row.actor) else None,
            "F_rebound_cue": bool(REBOUND_RE.search(combined)),
            "F_tether_cue": bool(TETHER_RE.search(combined)),
            "F_in_room_focus": in_room,
            "F_offstage_focus": off_focus,
            "F_fiction_roster_drift": roster_drift,
            "trigger_redacted": "omitted" in trig.lower(),
        }
    )
    return WillowDepartureRow(**data)


def extract_session(
    session_dir: Path,
    *,
    probe_manifest_path: Path | None = None,
    audit_session_number: int | None = None,
) -> list[WillowDepartureRow]:
    manifest: dict[int, ProbeManifestEntry] = {}
    if probe_manifest_path is not None:
        manifest = load_probe_manifest(probe_manifest_path)
    rows: list[WillowDepartureRow] = []
    from emission_map_extract import iter_character_full_json_paths

    for path in iter_character_full_json_paths(session_dir):
        base = extract_row_from_audit_file(
            path,
            probe_manifest=manifest or None,
            audit_session_number=audit_session_number,
        )
        if base is None:
            continue
        if not _willow_actor_name(base.actor):
            continue
        try:
            audit_row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prompt = ""
        for msg in audit_row.get("input_messages") or []:
            if isinstance(msg, dict) and msg.get("role") == "system":
                prompt = str(msg.get("content") or "")
                break
        rows.append(enrich_willow_row(base, prompt=prompt))
    return rows


def summarize_willow_rows(rows: list[WillowDepartureRow]) -> dict[str, Any]:
    base = summarize_rows(rows)
    probe_rows = [r for r in rows if r.probe_id]
    by_probe: dict[str, dict[str, Any]] = {}
    for r in probe_rows:
        if r.probe_id and r.probe_id not in by_probe:
            by_probe[r.probe_id] = {
                "rubric_class": r.rubric_class,
                "semantic_decision": r.semantic_decision,
                "proposal_count": r.proposal_count,
                "proposal_kinds": r.proposal_kinds,
                "spd_authority_outcome": r.spd_authority_outcome,
                "legality_reason_code": r.legality_reason_code,
                "retry_class": r.retry_class,
                "F_rebound_cue": r.F_rebound_cue,
                "F_tether_cue": r.F_tether_cue,
                "F_in_room_focus": r.F_in_room_focus,
                "F_fiction_roster_drift": r.F_fiction_roster_drift,
                "willow_status": r.willow_status,
                "willow_in_offstage": r.willow_in_offstage,
            }
    return {
        **base,
        "willow_probe_detail": by_probe,
        "willow_rebound_probe_count": sum(1 for r in probe_rows if r.F_rebound_cue),
        "willow_tether_probe_count": sum(1 for r in probe_rows if r.F_tether_cue),
        "willow_in_room_focus_probe_count": sum(1 for r in probe_rows if r.F_in_room_focus),
        "willow_fiction_roster_drift_count": sum(
            1 for r in probe_rows if r.F_fiction_roster_drift
        ),
        "willow_presence_constraint_seen": next(
            (r.willow_presence_constraint for r in rows if r.willow_presence_constraint),
            None,
        ),
    }
