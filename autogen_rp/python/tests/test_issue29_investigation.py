"""Issue #29 machine-lane analysis (no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from issue29_investigation import (  # noqa: E402
    analyze_issue29_session,
    parse_audit_session_from_stdout,
)


def _row(
    rnd: int,
    tn: int,
    bot: str,
    content: str,
    po: dict,
    trig: str = "",
    sm: dict | None = None,
) -> dict:
    base_sm = sm or {
        "schema_version": "support_manifest.v1",
        "units": [
            {
                "type": "retrieval_aggregate",
                "id": "retr:agg:v1",
                "content_fp": "sha256:" + "a" * 64,
            },
            {
                "type": "prompt_envelope",
                "id": "prompt:envelope:character:v1",
                "content_fp": "sha256:" + "b" * 64,
            },
        ],
    }
    ctx = {
        "continuity_event": {},
        "scene_state_after": {"issue29_negotiation_carry": "ISSUE29_NEGOT_TERMS_V1"},
    }
    return {
        "bot_type": "character",
        "round_number": rnd,
        "turn_number": tn,
        "bot_name": bot,
        "input_messages": [{"role": "system", "content": content}],
        "parsed_output": po,
        "context_snapshot": ctx,
        "effective_user_trigger": trig,
        "metadata": {"support_manifest": base_sm},
    }


def test_parse_audit_session_from_stdout() -> None:
    text = "blah\n* **Audit session:** `436`\n"
    assert parse_audit_session_from_stdout(text) == 436


@pytest.mark.parametrize(
    "scenario_id",
    [
        "investigate_i29_negotiation_harley_kizzie_ayame",
        "investigate_i29_cross_scene_carry",
    ],
)
def test_scenario_loads_with_investigation_block(scenario_id: str) -> None:
    from progression_simulation_scenarios import load_scenario

    raw = load_scenario(scenario_id)
    assert isinstance(raw.get("investigation"), dict)
    assert raw["investigation"].get("min_character_rows")


def test_analyze_synthetic_negotiation_baseline(tmp_path: Path) -> None:
    # Minimal session: establishment has tokens; recall turn 20 fails second token
    sess = tmp_path / "session_synth"
    sess.mkdir()
    rows = [
        _row(
            1,
            1,
            "A",
            "x ISSUE29_NEGOT_TERMS_V1 ISSUE29_ROLE_ANCHOR_AY",
            {"dialogue": "ok", "action": ""},
        ),
        _row(
            1,
            2,
            "B",
            "y ISSUE29_NEGOT_TERMS_V1 ISSUE29_ROLE_ANCHOR_AY",
            {"dialogue": "ok", "action": ""},
        ),
        _row(
            1,
            3,
            "A",
            "z ISSUE29_NEGOT_TERMS_V1 ISSUE29_ROLE_ANCHOR_AY",
            {"dialogue": "ok", "action": ""},
        ),
        _row(
            1,
            20,
            "B",
            "only ISSUE29_NEGOT_TERMS_V1 dropped other",
            {"dialogue": "ISSUE29_NEGOT_TERMS_V1", "action": ""},
        ),
    ]
    for i, data in enumerate(rows):
        p = sess / f"r_round001_t{i:02d}_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    out = analyze_issue29_session(
        sess, "investigate_i29_negotiation_harley_kizzie_ayame"
    )
    assert out["baseline_valid"] is True
    assert out["T_sup"] is not None
    assert out["T_sup"]["reason"] == "token_dropped_consecutive"
    assert out["T_beh"] is not None
    assert out["integrity_support_manifest_all_rows"] is True
    assert out["incomplete_run"] is True  # only 4 rows < 25


def test_user_trigger_schedule_cross_scene_max() -> None:
    from user_trigger_schedule import load_user_trigger_schedule

    p = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "issue29_investigation_schedules"
        / "cross_scene_50.json"
    )
    schedule = load_user_trigger_schedule(p, max_orchestration_turn=50)
    by_turn = schedule.by_orchestration_turn
    assert 16 in by_turn and 31 in by_turn
