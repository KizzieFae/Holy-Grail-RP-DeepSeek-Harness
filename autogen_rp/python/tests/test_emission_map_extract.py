"""Unit tests for emission_map_extract (deterministic, no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from emission_map_extract import (  # noqa: E402
    extract_row_from_audit_file,
    load_probe_manifest,
    summarize_rows,
)


@pytest.fixture
def manifest_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "data"
        / "issue240"
        / "i240_emission_probe_manifest_v1.json"
    )


def test_load_probe_manifest(manifest_path: Path) -> None:
    probes = load_probe_manifest(manifest_path)
    assert probes[2].probe_id == "T01"
    assert probes[7].transition_type == "remote_phone"
    assert probes[9].expected_rubric == "no_covered_change"


def test_extract_flags_suspect_miss(tmp_path: Path, manifest_path: Path) -> None:
    probes = load_probe_manifest(manifest_path)
    audit = {
        "session_number": 999,
        "round_number": 1,
        "turn_number": 2,
        "bot_name": "Celina",
        "effective_user_trigger": "Traveler: Celina, leave the living room now.",
        "input_messages": [
            {
                "role": "system",
                "content": (
                    "ACTIVE SCENE FOCUS (this beat only):\n"
                    "- Your position: You are in the room with the live exchange.\n"
                    "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):\n"
                    "Earlier in the hall.\n"
                ),
            }
        ],
        "parsed_output": {
            "semantic_evaluation": {"decision": "no_covered_change"},
            "beats": [
                {
                    "type": "action",
                    "action": "Walked out into the hall and shut the door behind her.",
                }
            ],
            "motivation": {
                "goal": "Leave without drama",
                "tactic": "Step out quietly",
            },
        },
        "metadata": {
            "semantic_proposal_decision": {
                "batch": {"authority_outcome": "no_proposal"},
                "emitted": {"present": False, "count": 0},
            },
            "ctar": {"continuity_turn_index": 3},
        },
        "context_snapshot": {
            "scene_state_after": {
                "present_characters": ["Ayame", "Celina"],
                "offstage_characters": [],
                "character_presence_status": {"Celina": "onstage"},
            }
        },
    }
    path = tmp_path / "row_full.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    row = extract_row_from_audit_file(
        path,
        probe_manifest=probes,
        audit_session_number=999,
    )
    assert row is not None
    assert row.probe_id == "T01"
    assert row.F_exit_cue is True
    assert row.F_no_proposal is True
    assert row.F_focus_in_room is True
    assert row.F_location_drift is True
    assert row.F_suspect_miss is True
    assert row.rubric_class == "C3_missed_covered_change"


def test_extract_correct_no_covered_change_control(tmp_path: Path, manifest_path: Path) -> None:
    probes = load_probe_manifest(manifest_path)
    audit = {
        "session_number": 999,
        "turn_number": 9,
        "bot_name": "Celina",
        "input_messages": [{"role": "system", "content": ""}],
        "parsed_output": {
            "semantic_evaluation": {"decision": "no_covered_change"},
            "beats": [
                {
                    "type": "action",
                    "action": "Stayed at the side table and sorted papers without looking up.",
                }
            ],
        },
        "metadata": {},
        "context_snapshot": {"scene_state_after": {}},
    }
    path = tmp_path / "control_full.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    row = extract_row_from_audit_file(path, probe_manifest=probes)
    assert row is not None
    assert row.probe_id == "T07"
    assert row.rubric_class == "C1_correct_no_covered_change"
    assert row.F_suspect_miss is False


def test_extract_legality_reject_class(tmp_path: Path) -> None:
    audit = {
        "turn_number": 5,
        "bot_name": "Harley_Quinn",
        "input_messages": [{"role": "system", "content": ""}],
        "parsed_output": {
            "semantic_evaluation": {
                "decision": "covered_change",
                "proposals": [{"kind": "off_focal", "character": "Harley_Quinn"}],
            },
            "beats": [{"type": "action", "action": "Turned away from the phone."}],
        },
        "metadata": {
            "semantic_proposal_decision": {
                "batch": {"authority_outcome": "reject"},
                "pre_commit": {"legality_reason_code": "must_remain_off_focal"},
            },
            "turn_execution": {"retry_class": "proposal_legality"},
        },
        "context_snapshot": {"scene_state_after": {}},
    }
    path = tmp_path / "reject_full.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    row = extract_row_from_audit_file(path)
    assert row is not None
    assert row.rubric_class == "C5_rejected_with_retry"
    assert row.proposal_count == 1


def test_summarize_rows_counts() -> None:
    from emission_map_extract import EmissionMapRow

    rows = [
        EmissionMapRow(probe_id="T01", rubric_class="C3_missed_covered_change", F_suspect_miss=True),
        EmissionMapRow(probe_id="T07", rubric_class="C1_correct_no_covered_change"),
    ]
    summary = summarize_rows(rows)
    assert summary["suspect_miss_count"] == 1
    assert summary["rubric_class_counts"]["C3_missed_covered_change"] == 1
