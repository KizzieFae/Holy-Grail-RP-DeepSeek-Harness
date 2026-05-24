"""Deterministic emission-map extraction from audited character turn artifacts (#240 Phase A harness)."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = "emission_map_row.v1"

_EXIT_CUE_RE = re.compile(
    r"\b("
    r"leave|left|exit|exited|step(?:ped|s)?\s+(?:out|into\s+the\s+hall|away)|"
    r"walk(?:ed|s)?\s+out|door(?:way)?|hall(?:way)?|shut\s+the\s+door|"
    r"garage|kitchen(?:\s+doorway)?|workbench|offstage|outside"
    r")\b",
    re.I,
)
_REENTRY_CUE_RE = re.compile(
    r"\b("
    r"re-?enter|return(?:ed|s|ing)?|come\s+back|back\s+through\s+the\s+door|"
    r"rejoin|step(?:ped|s)?\s+back\s+in|doorframe"
    r")\b",
    re.I,
)
_REMOTE_CUE_RE = re.compile(
    r"\b("
    r"phone|call(?:ed|ing|s)?|dial(?:ed|ing|s)?|receiver|cradle|"
    r"wall\s+phone|intercom|line\s+static"
    r")\b",
    re.I,
)
_MOTIVATION_EXIT_RE = re.compile(
    r"\b("
    r"leave|exit|withdraw|distance|remote|phone|hall|garage|"
    r"step\s+out|disengage|without\s+returning|stay\s+out"
    r")\b",
    re.I,
)
_LOCATION_DRIFT_WORDS = frozenset(
    {"hall", "garage", "kitchen", "phone", "doorway", "outside", "workbench"}
)

_SKIP_NAME_PARTS = (
    "director",
    "narrator",
    "parse_retry",
    "validation_",
    "character_failure",
)


@dataclass
class ProbeManifestEntry:
    probe_id: str
    transition_type: str
    target_actor_hint: str
    expected_rubric: str


@dataclass
class EmissionMapRow:
    schema_version: str = SCHEMA_VERSION
    audit_session_number: int | None = None
    session_owner: str = ""
    round_number: int | None = None
    turn_number: int | None = None
    continuity_turn_index: int | None = None
    actor: str = ""
    probe_id: str | None = None
    transition_type: str | None = None
    expected_rubric: str | None = None
    effective_user_trigger: str = ""
    semantic_decision: str | None = None
    proposal_count: int = 0
    proposal_kinds: list[str] = field(default_factory=list)
    spd_authority_outcome: str | None = None
    spd_emitted_present: bool | None = None
    retry_class: str | None = None
    legality_reason_code: str | None = None
    present_characters: list[str] = field(default_factory=list)
    offstage_characters: list[str] = field(default_factory=list)
    character_presence_status: dict[str, str] = field(default_factory=dict)
    active_focus_position: str | None = None
    active_focus_movement: str | None = None
    participation_arc_lines: list[str] = field(default_factory=list)
    transcript_location_hits: dict[str, int] = field(default_factory=dict)
    beats_action_text: str = ""
    beats_dialogue_text: str = ""
    motivation_goal: str = ""
    motivation_tactic: str = ""
    F_exit_cue: bool = False
    F_reentry_cue: bool = False
    F_remote_cue: bool = False
    F_no_proposal: bool = False
    F_focus_in_room: bool = False
    F_location_drift: bool = False
    F_motivation_exit: bool = False
    F_suspect_miss: bool = False
    F_context_drift: bool = False
    rubric_class: str = "unclassified"
    source_artifact: str = ""
    parse_partial: bool = False


def load_probe_manifest(path: str | Path) -> dict[int, ProbeManifestEntry]:
    """Load probe manifest; keys are orchestration turn numbers."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    raw_map = data.get("probes_by_orchestration_turn") or {}
    out: dict[int, ProbeManifestEntry] = {}
    for key, val in raw_map.items():
        if not isinstance(val, dict):
            continue
        turn = int(str(key).strip())
        out[turn] = ProbeManifestEntry(
            probe_id=str(val.get("probe_id") or "").strip(),
            transition_type=str(val.get("transition_type") or "").strip(),
            target_actor_hint=str(val.get("target_actor_hint") or "").strip(),
            expected_rubric=str(val.get("expected_rubric") or "").strip(),
        )
    return out


def _should_skip_artifact(name: str) -> bool:
    lower = name.lower()
    return any(part in lower for part in _SKIP_NAME_PARTS)


def iter_character_full_json_paths(session_dir: Path) -> Iterator[Path]:
    if not session_dir.is_dir():
        return
    for path in sorted(session_dir.rglob("*_full.json")):
        if _should_skip_artifact(path.name):
            continue
        yield path


def _system_prompt(audit_row: dict[str, Any]) -> str:
    for msg in audit_row.get("input_messages") or []:
        if isinstance(msg, dict) and msg.get("role") == "system":
            content = msg.get("content")
            return content if isinstance(content, str) else ""
    return ""


def _extract_section(text: str, header: str, stop_headers: tuple[str, ...]) -> str:
    idx = text.find(header)
    if idx < 0:
        return ""
    start = idx + len(header)
    end = len(text)
    for stop in stop_headers:
        j = text.find(stop, start)
        if j >= 0:
            end = min(end, j)
    return text[idx:end].strip()


def _parse_active_focus(prompt: str) -> tuple[str | None, str | None]:
    block = _extract_section(
        prompt,
        "ACTIVE SCENE FOCUS",
        ("RECENT PARTICIPATION ARC", "YOUR PRIVATE STATE:", "TRIGGER FOR THIS BEAT:"),
    )
    if not block:
        return None, None
    position = None
    movement = None
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Your position:"):
            position = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("- Most recent relevant movement:"):
            movement = stripped.split(":", 1)[-1].strip()
    return position, movement


def _parse_participation_arc(prompt: str) -> list[str]:
    block = _extract_section(
        prompt,
        "RECENT PARTICIPATION ARC",
        ("ACTIVE SCENE FOCUS", "COVERED-CHANGE THRESHOLD", "YOUR PRIVATE STATE:"),
    )
    if not block:
        return []
    lines: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:].strip())
    return lines


def _transcript_location_hits(prompt: str) -> dict[str, int]:
    block = _extract_section(
        prompt,
        "RECENT SCENE TRANSCRIPT",
        (
            "STRUCTURED MOVE HISTORY",
            "RECENT STRUCTURED ACTIONS",
            "ACTIVE ISSUES",
            "YOUR PRIVATE STATE:",
        ),
    )
    lower = block.lower()
    return {word: lower.count(word) for word in _LOCATION_DRIFT_WORDS if word in lower}


def _beats_text(parsed: dict[str, Any]) -> tuple[str, str]:
    actions: list[str] = []
    dialogues: list[str] = []
    for beat in parsed.get("beats") or []:
        if not isinstance(beat, dict):
            continue
        action = str(beat.get("action") or "").strip()
        dialogue = str(beat.get("dialogue") or "").strip()
        if action:
            actions.append(action)
        if dialogue:
            dialogues.append(dialogue)
    return " ".join(actions), " ".join(dialogues)


def _semantic_fields(parsed: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
    sem = parsed.get("semantic_evaluation")
    if not isinstance(sem, dict):
        return None, []
    decision = str(sem.get("decision") or "").strip() or None
    proposals = sem.get("proposals")
    if not isinstance(proposals, list):
        proposals = []
    root = parsed.get("semantic_proposals")
    if isinstance(root, list) and root:
        proposals = root
    return decision, [p for p in proposals if isinstance(p, dict)]


def _motivation_fields(parsed: dict[str, Any]) -> tuple[str, str]:
    mot = parsed.get("motivation")
    if isinstance(mot, dict):
        return (
            str(mot.get("goal") or "").strip(),
            str(mot.get("tactic") or "").strip(),
        )
    if isinstance(mot, str):
        return mot.strip(), ""
    return "", ""


def _spd_fields(metadata: dict[str, Any]) -> tuple[str | None, bool | None, str | None]:
    spd = metadata.get("semantic_proposal_decision") or {}
    if not isinstance(spd, dict):
        return None, None, None
    batch = spd.get("batch") or {}
    authority = batch.get("authority_outcome") if isinstance(batch, dict) else None
    emitted = spd.get("emitted") or {}
    present = emitted.get("present") if isinstance(emitted, dict) else None
    legality = spd.get("pre_commit") or {}
    reason = None
    if isinstance(legality, dict):
        reason = legality.get("legality_reason_code") or legality.get("reason_code")
    return (
        str(authority).strip() if authority else None,
        bool(present) if present is not None else None,
        str(reason).strip() if reason else None,
    )


def _retry_class(metadata: dict[str, Any]) -> str | None:
    te = metadata.get("turn_execution") or {}
    if isinstance(te, dict) and te.get("retry_class"):
        return str(te.get("retry_class")).strip()
    action = str(metadata.get("action") or "").strip()
    if "retry" in action.lower():
        return action
    return None


def _scene_state_after(audit_row: dict[str, Any]) -> dict[str, Any]:
    ctx = audit_row.get("context_snapshot") or {}
    ss = ctx.get("scene_state_after") if isinstance(ctx, dict) else None
    return ss if isinstance(ss, dict) else {}


def _derive_flags(
    *,
    beats_combined: str,
    motivation_combined: str,
    semantic_decision: str | None,
    proposal_count: int,
    active_focus_position: str | None,
    transcript_location_hits: dict[str, int],
    offstage_characters: list[str],
    expected_rubric: str | None,
) -> dict[str, bool]:
    exit_cue = bool(_EXIT_CUE_RE.search(beats_combined))
    reentry_cue = bool(_REENTRY_CUE_RE.search(beats_combined))
    remote_cue = bool(_REMOTE_CUE_RE.search(beats_combined))
    no_proposal = semantic_decision == "no_covered_change" or proposal_count == 0
    focus_in_room = bool(
        active_focus_position
        and "in the room with the live exchange" in active_focus_position.lower()
    )
    beat_lower = beats_combined.lower()
    location_in_beats = any(w in beat_lower for w in _LOCATION_DRIFT_WORDS)
    location_drift = focus_in_room and location_in_beats
    motivation_exit = bool(_MOTIVATION_EXIT_RE.search(motivation_combined))
    expect_covered = expected_rubric == "covered_change"
    suspect_miss = (
        expect_covered
        and no_proposal
        and (exit_cue or reentry_cue or remote_cue)
    )
    context_drift = bool(transcript_location_hits) and not offstage_characters
    return {
        "F_exit_cue": exit_cue,
        "F_reentry_cue": reentry_cue,
        "F_remote_cue": remote_cue,
        "F_no_proposal": no_proposal,
        "F_focus_in_room": focus_in_room,
        "F_location_drift": location_drift,
        "F_motivation_exit": motivation_exit,
        "F_suspect_miss": suspect_miss,
        "F_context_drift": context_drift,
    }


def _classify_rubric(
    *,
    expected_rubric: str | None,
    semantic_decision: str | None,
    proposal_count: int,
    spd_authority: str | None,
    retry_class: str | None,
    flags: dict[str, bool],
) -> str:
    if spd_authority == "reject":
        if retry_class and "legality" in retry_class.lower():
            return "C5_rejected_with_retry"
        return "C4_illegal_emitted"
    if spd_authority == "accept" and proposal_count > 0:
        return "C2_correct_covered_change"
    if semantic_decision == "covered_change" and proposal_count > 0:
        return "C2_correct_covered_change"
    if expected_rubric == "no_covered_change" and flags["F_no_proposal"]:
        return "C1_correct_no_covered_change"
    if flags["F_suspect_miss"]:
        return "C3_missed_covered_change"
    if expected_rubric == "covered_change" and flags["F_no_proposal"]:
        return "C3_missed_covered_change"
    if semantic_decision == "no_covered_change" and (flags["F_exit_cue"] or flags["F_reentry_cue"]):
        return "C8_fiction_denies_transition"
    return "C7_ambiguous"


def extract_row_from_audit_file(
    path: Path,
    *,
    probe_manifest: dict[int, ProbeManifestEntry] | None = None,
    audit_session_number: int | None = None,
) -> EmissionMapRow | None:
    try:
        audit_row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(audit_row, dict):
        return None

    parsed = audit_row.get("parsed_output") or {}
    if not isinstance(parsed, dict):
        parsed = {}
    metadata = audit_row.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    turn_number = audit_row.get("turn_number")
    probe: ProbeManifestEntry | None = None
    if probe_manifest and turn_number is not None:
        probe = probe_manifest.get(int(turn_number))

    prompt = _system_prompt(audit_row)
    position, movement = _parse_active_focus(prompt)
    arc_lines = _parse_participation_arc(prompt)
    loc_hits = _transcript_location_hits(prompt)

    action_text, dialogue_text = _beats_text(parsed)
    beats_combined = f"{action_text} {dialogue_text}".strip()
    mot_goal, mot_tactic = _motivation_fields(parsed)
    motivation_combined = f"{mot_goal} {mot_tactic}".strip()

    decision, proposals = _semantic_fields(parsed)
    kinds = [str(p.get("kind") or "").strip() for p in proposals if p.get("kind")]
    spd_authority, spd_present, legality_reason = _spd_fields(metadata)
    retry_class = _retry_class(metadata)
    ss = _scene_state_after(audit_row)
    present = [str(x) for x in (ss.get("present_characters") or []) if str(x).strip()]
    offstage = [str(x) for x in (ss.get("offstage_characters") or []) if str(x).strip()]
    status_raw = ss.get("character_presence_status") or {}
    status = (
        {str(k): str(v) for k, v in status_raw.items()}
        if isinstance(status_raw, dict)
        else {}
    )

    ctar = metadata.get("ctar") or {}
    ct_index = ctar.get("continuity_turn_index") if isinstance(ctar, dict) else None

    flags = _derive_flags(
        beats_combined=beats_combined,
        motivation_combined=motivation_combined,
        semantic_decision=decision,
        proposal_count=len(proposals),
        active_focus_position=position,
        transcript_location_hits=loc_hits,
        offstage_characters=offstage,
        expected_rubric=probe.expected_rubric if probe else None,
    )
    rubric = _classify_rubric(
        expected_rubric=probe.expected_rubric if probe else None,
        semantic_decision=decision,
        proposal_count=len(proposals),
        spd_authority=spd_authority,
        retry_class=retry_class,
        flags=flags,
    )

    session_num = audit_session_number
    if session_num is None:
        sn = audit_row.get("session_number")
        session_num = int(sn) if sn is not None else None

    row = EmissionMapRow(
        audit_session_number=session_num,
        session_owner=str(audit_row.get("session_owner") or ""),
        round_number=audit_row.get("round_number"),
        turn_number=turn_number,
        continuity_turn_index=int(ct_index) if ct_index is not None else None,
        actor=str(audit_row.get("bot_name") or ""),
        probe_id=probe.probe_id if probe else None,
        transition_type=probe.transition_type if probe else None,
        expected_rubric=probe.expected_rubric if probe else None,
        effective_user_trigger=str(audit_row.get("effective_user_trigger") or ""),
        semantic_decision=decision,
        proposal_count=len(proposals),
        proposal_kinds=kinds,
        spd_authority_outcome=spd_authority,
        spd_emitted_present=spd_present,
        retry_class=retry_class,
        legality_reason_code=legality_reason,
        present_characters=present,
        offstage_characters=offstage,
        character_presence_status=status,
        active_focus_position=position,
        active_focus_movement=movement,
        participation_arc_lines=arc_lines,
        transcript_location_hits=loc_hits,
        beats_action_text=action_text[:2000],
        beats_dialogue_text=dialogue_text[:2000],
        motivation_goal=mot_goal[:500],
        motivation_tactic=mot_tactic[:500],
        rubric_class=rubric,
        source_artifact=str(path),
        parse_partial=not bool(beats_combined),
        **flags,
    )
    return row


def extract_session(
    session_dir: str | Path,
    *,
    probe_manifest_path: str | Path | None = None,
    audit_session_number: int | None = None,
) -> list[EmissionMapRow]:
    session_path = Path(session_dir)
    manifest: dict[int, ProbeManifestEntry] = {}
    if probe_manifest_path:
        manifest = load_probe_manifest(probe_manifest_path)

    if audit_session_number is None:
        name = session_path.name
        m = re.search(r"session_(\d+)", name)
        if m:
            audit_session_number = int(m.group(1))

    rows: list[EmissionMapRow] = []
    for artifact in iter_character_full_json_paths(session_path):
        row = extract_row_from_audit_file(
            artifact,
            probe_manifest=manifest or None,
            audit_session_number=audit_session_number,
        )
        if row is not None:
            rows.append(row)
    rows.sort(
        key=lambda r: (
            r.turn_number or 0,
            r.round_number or 0,
            r.actor.casefold(),
            r.source_artifact,
        )
    )
    return rows


def write_jsonl(rows: list[EmissionMapRow], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_csv(rows: list[EmissionMapRow], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    dict_rows = [asdict(r) for r in rows]
    fieldnames = list(dict_rows[0].keys())
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for dr in dict_rows:
            for key, val in dr.items():
                if isinstance(val, (list, dict)):
                    dr[key] = json.dumps(val, ensure_ascii=False)
            writer.writerow(dr)


def summarize_rows(rows: list[EmissionMapRow]) -> dict[str, Any]:
    probe_rows = [r for r in rows if r.probe_id]
    by_class: dict[str, int] = {}
    by_probe: dict[str, str] = {}
    for r in rows:
        by_class[r.rubric_class] = by_class.get(r.rubric_class, 0) + 1
        if r.probe_id and r.probe_id not in by_probe:
            by_probe[r.probe_id] = r.rubric_class
    suspect = sum(1 for r in probe_rows if r.F_suspect_miss)
    emitted = sum(1 for r in probe_rows if r.proposal_count > 0)
    return {
        "total_character_rows": len(rows),
        "probe_attributed_rows": len(probe_rows),
        "distinct_probes_seen": len(by_probe),
        "suspect_miss_count": suspect,
        "probe_emitted_proposal_count": emitted,
        "rubric_class_counts": by_class,
        "probe_first_actor_class": by_probe,
    }
