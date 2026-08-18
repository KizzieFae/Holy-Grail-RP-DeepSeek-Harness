"""Deterministic cohesion-slate extraction (#227 broad validation)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from emission_map_extract import (
    EmissionMapRow,
    ProbeManifestEntry,
    extract_row_from_audit_file,
    load_probe_manifest,
    summarize_rows,
)

REBOUND_RE = re.compile(
    r"\b(forgot|keys|excuse|come\s+back|right\s+back|returned|rejoin|same\s+beat|pudding|ledger)\b",
    re.I,
)
TETHER_RE = re.compile(
    r"\b(phone|call(?:ed|ing|s)?|garage|hall(?:way)?|through\s+the\s+door|"
    r"open\s+door|still\s+talk|yell(?:ed|ing|s)?\s+back|doorway|serving\s+line|foyer)\b",
    re.I,
)
FILLER_RE = re.compile(
    r"\b(offscreen|elsewhere|meanwhile|from\s+another\s+room|murmur(?:ed|ing)?\s+from)\b",
    re.I,
)
IN_ROOM_FOCUS_RE = re.compile(r"in the room with the live exchange", re.I)
OFFSTAGE_FOCUS_RE = re.compile(r"currently offstage|partially withdrawn", re.I)

_SCHEMA = "cohesion_slate_row.v1"


@dataclass
class CohesionSlateRow(EmissionMapRow):
    schema_version: str = _SCHEMA
    probe_target_actor: str | None = None
    target_presence_constraint: str | None = None
    target_in_present: bool | None = None
    target_in_offstage: bool | None = None
    target_status: str | None = None
    F_rebound_cue: bool = False
    F_tether_cue: bool = False
    F_filler_cue: bool = False
    F_in_room_focus: bool = False
    F_fiction_roster_drift: bool = False
    trigger_redacted: bool = False


def _actor_matches(actor: str, hint: str) -> bool:
    if not hint:
        return True
    a = str(actor or "").lower().replace("_", " ")
    h = str(hint or "").lower().replace("_", " ")
    return h in a or a in h or h.split()[0] in a


def _presence_constraint_from_prompt(prompt: str, actor: str) -> str | None:
    actor_first = str(actor or "").split("_")[0].lower()
    for label in ("YOUR SCENE ROLE:", "character_presence_constraints"):
        idx = prompt.find(label)
        if idx < 0:
            continue
        block = prompt[idx : idx + 2500]
        if label.startswith("character_presence"):
            try:
                start = block.find("{")
                end = block.find("}", start)
                if start >= 0 and end > start:
                    constraints = json.loads(block[start : end + 1])
                    if isinstance(constraints, dict):
                        for k, v in constraints.items():
                            if _actor_matches(k, actor):
                                return str(v)
            except json.JSONDecodeError:
                pass
        else:
            try:
                start = block.find("{")
                end = block.find("}", start)
                if start >= 0 and end > start:
                    role = json.loads(block[start : end + 1])
                    if isinstance(role, dict) and _actor_matches(
                        str(role.get("character") or ""), actor
                    ):
                        return str(role.get("presence_constraint") or "") or None
            except json.JSONDecodeError:
                pass
    return None


def enrich_cohesion_row(row: EmissionMapRow, *, prompt: str, actor: str) -> CohesionSlateRow:
    beats = f"{row.beats_action_text} {row.beats_dialogue_text}".strip()
    mot = f"{row.motivation_goal} {row.motivation_tactic}".strip()
    combined = f"{beats} {mot}"
    target_present = any(_actor_matches(x, actor) for x in row.present_characters)
    target_off = any(_actor_matches(x, actor) for x in row.offstage_characters)
    target_status = None
    for k, v in row.character_presence_status.items():
        if _actor_matches(k, actor):
            target_status = v
            break
    focus_blob = f"{row.active_focus_position or ''} {row.active_focus_movement or ''}"
    in_room = bool(IN_ROOM_FOCUS_RE.search(prompt) or IN_ROOM_FOCUS_RE.search(focus_blob))
    exit_fiction = bool(row.F_exit_cue or row.F_remote_cue)
    roster_drift = exit_fiction and target_present and not target_off and in_room
    trig = row.effective_user_trigger or ""
    data = asdict(row)
    data.update(
        {
            "schema_version": _SCHEMA,
            "probe_target_actor": actor,
            "target_presence_constraint": _presence_constraint_from_prompt(prompt, actor),
            "target_in_present": target_present,
            "target_in_offstage": target_off,
            "target_status": target_status,
            "F_rebound_cue": bool(REBOUND_RE.search(combined)),
            "F_tether_cue": bool(TETHER_RE.search(combined)),
            "F_filler_cue": bool(FILLER_RE.search(combined)),
            "F_in_room_focus": in_room,
            "F_fiction_roster_drift": roster_drift,
            "trigger_redacted": "omitted" in trig.lower(),
        }
    )
    return CohesionSlateRow(**data)


def _resolve_probe_actor(
    manifest_entry: ProbeManifestEntry | None,
    default_actor: str,
) -> str:
    if manifest_entry and manifest_entry.target_actor_hint:
        return manifest_entry.target_actor_hint
    return default_actor


def extract_session(
    session_dir: Path,
    *,
    probe_manifest_path: Path | None = None,
    default_probe_actor: str,
    audit_session_number: int | None = None,
) -> list[CohesionSlateRow]:
    manifest: dict[int, ProbeManifestEntry] = {}
    if probe_manifest_path is not None:
        manifest = load_probe_manifest(probe_manifest_path)
    probe_turns = set(manifest.keys())
    rows: list[CohesionSlateRow] = []
    from emission_map_extract import iter_character_full_json_paths

    for path in iter_character_full_json_paths(session_dir):
        base = extract_row_from_audit_file(
            path,
            probe_manifest=manifest or None,
            audit_session_number=audit_session_number,
        )
        if base is None:
            continue
        if base.turn_number not in probe_turns and not base.probe_id:
            continue
        manifest_entry = manifest.get(int(base.turn_number or 0))
        expected_actor = _resolve_probe_actor(manifest_entry, default_probe_actor)
        if not _actor_matches(base.actor, expected_actor):
            continue
        if base.parse_partial:
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
        rows.append(enrich_cohesion_row(base, prompt=prompt, actor=expected_actor))
    return rows


def summarize_cohesion_rows(rows: list[CohesionSlateRow]) -> dict[str, Any]:
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
                "F_filler_cue": r.F_filler_cue,
                "F_in_room_focus": r.F_in_room_focus,
                "F_fiction_roster_drift": r.F_fiction_roster_drift,
                "target_status": r.target_status,
                "target_in_offstage": r.target_in_offstage,
                "target_presence_constraint": r.target_presence_constraint,
            }
    covered_expected = [
        r for r in probe_rows if r.expected_rubric == "covered_change" and r.probe_id
    ]
    covered_first = {r.probe_id: r for r in covered_expected}.values()
    return {
        **base,
        "probe_detail": by_probe,
        "covered_change_probe_count": sum(
            1 for r in covered_first if r.rubric_class == "C2_correct_covered_change"
        ),
        "covered_change_probe_total": len(set(r.probe_id for r in covered_expected)),
        "covered_change_emitted_count": sum(
            1
            for r in covered_first
            if int(r.proposal_count or 0) > 0 and r.spd_authority_outcome == "accept"
        ),
        "fiction_roster_drift_count": sum(1 for r in probe_rows if r.F_fiction_roster_drift),
        "tether_probe_count": sum(1 for r in probe_rows if r.F_tether_cue),
        "rebound_probe_count": sum(1 for r in probe_rows if r.F_rebound_cue),
        "filler_probe_count": sum(1 for r in probe_rows if r.F_filler_cue),
        "in_room_focus_probe_count": sum(1 for r in probe_rows if r.F_in_room_focus),
    }
