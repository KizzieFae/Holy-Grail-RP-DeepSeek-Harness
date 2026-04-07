"""Progression Stress Audit replay (deterministic, no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_stress_audit_replay import (  # noqa: E402
    compute_is1,
    levenshtein_distance,
    merge_issue_updates_into_H,
    motivation_sig,
    post_turn_issue_H,
    run_progression_stress_audit_replay,
    similarity_sim,
    issues_H_from_before_payload,
)


def test_levenshtein_and_similarity() -> None:
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("a", "b") == 1
    assert similarity_sim("", "") == 1.0
    assert similarity_sim("hello", "hello") == 1.0
    # punctuation-only delta after normalization
    assert similarity_sim("hello", "hello!") >= 0.90


def test_motivation_sig_sorts_keys() -> None:
    assert motivation_sig({"b": 1, "a": 2}) == motivation_sig({"a": 2, "b": 1})


def test_compute_is1_requires_same_motivation_and_tau() -> None:
    move = {"action": "walks", "dialogue": "Hi", "motivation": {"x": 1}}
    prior: list[tuple[str, dict[str, Any]]] = [
        ("Bob", {"action": "walks", "dialogue": "Hi", "motivation": {"x": 1}}),
    ]
    assert compute_is1(speaker="Bob", move=move, prior_moves=prior) is True
    move2 = dict(move)
    move2["dialogue"] = "Hello there friend"  # likely still >= tau vs Hi? maybe not
    # different motivation breaks
    move3 = {**move, "motivation": {"x": 2}}
    assert compute_is1(speaker="Bob", move=move3, prior_moves=prior) is False


def test_merge_issue_updates_into_H() -> None:
    base = [("i1", "active", ("A",), "r0")]
    upd = [{"issue_id": "i1", "status": "escalating", "participants": ["A"], "status_reason": "r1"}]
    out = merge_issue_updates_into_H(base, upd)
    assert out == [("i1", "escalating", ("A",), "r1")]


def test_issues_H_from_character_audit_v1() -> None:
    cav1 = {
        "observed": {
            "issues_before": {
                "issues": [
                    {
                        "issue_id": "z",
                        "status": "active",
                        "participants": ["B", "A"],
                        "status_reason_excerpt": "sr",
                    }
                ]
            }
        }
    }
    h = issues_H_from_before_payload(cav1)
    assert h == [("z", "active", ("A", "B"), "sr")]


def _char_row(
    *,
    rnd: int,
    tn: int,
    ts: str,
    name: str,
    action: str,
    dialogue: str,
    phase: str,
    tension: str,
    consequences: list[str],
    cav1: dict | None,
    issue_updates: list | None = None,
) -> dict:
    md: dict = {
        "consequences": consequences,
        "progression_advisory": {"stall_score": 0.5},
        "turn_execution": {},
        "issue_updates": issue_updates or [],
    }
    if cav1 is not None:
        md["character_audit_v1"] = cav1
    return {
        "bot_type": "character",
        "round_number": rnd,
        "turn_number": tn,
        "timestamp": ts,
        "bot_name": name,
        "parsed_output": {
            "action": action,
            "dialogue": dialogue,
            "motivation": {},
        },
        "metadata": md,
        "context_snapshot": {
            "scene_state_after": {
                "phase": phase,
                "current_tension_level": tension,
            }
        },
    }


def test_run_replay_minimal(tmp_path: Path) -> None:
    sess = tmp_path / "session_001"
    sess.mkdir()
    ib = {
        "observed": {
            "issues_before": {
                "issues": [
                    {
                        "issue_id": "i1",
                        "status": "active",
                        "participants": ["A"],
                        "status_reason_excerpt": "x",
                    }
                ]
            }
        }
    }
    for i, ts in enumerate(
        ["2026-01-01T00:00:0%dZ" % (i + 1) for i in range(3)],
    ):
        row = _char_row(
            rnd=1,
            tn=i + 1,
            ts=ts,
            name="A",
            action="act",
            dialogue="line",
            phase="opening",
            tension="high",
            consequences=["c"],
            cav1=ib,
        )
        (sess / f"r1_t{i}_A_full.json").write_text(
            json.dumps(row, ensure_ascii=False),
            encoding="utf-8",
        )

    se = {
        "scenario_id": "test",
        "metrics": {},
        "sim_progression_metrics_events": [
            {
                "kind": "accepted_turn",
                "continuity_turn_index": j + 1,
                "qualifies": True,
                "gate_active": False,
                "enforcement_effective": False,
                "round_number": 1,
                "orchestration_turn_number": j + 1,
                "next_actor": "A",
            }
            for j in range(3)
        ],
    }
    se_path = tmp_path / "eval.json"
    se_path.write_text(json.dumps(se), encoding="utf-8")

    log = (
        "[beat_shift] set active reason=progression_stall stall_score=0.7 "
        "components={} source_turn_id=user_round_1\n"
        "[beat_shift] consumed and cleared (was reason=progression_stall source_turn_id=None)\n"
    )
    log_path = tmp_path / "run.log"
    log_path.write_text(log, encoding="utf-8")

    r = run_progression_stress_audit_replay(
        session_dir=sess,
        structured_eval_path=se_path,
        log_path=log_path,
    )
    assert len(r.per_turn) == 3
    assert r.per_turn[2]["is2"] is True
    assert r.per_turn[1]["is3"] is True
    assert r.per_run_summary["beat_shift"]["status"] == "ok"
    assert r.per_run_summary["beat_shift"]["window_a_ctks"] == []


def test_post_turn_issue_H_last_row_merge(tmp_path: Path) -> None:
    """Last CTK uses merge(issues_before, issue_updates)."""
    rows_data = [
        _char_row(
            rnd=1,
            tn=1,
            ts="2026-01-01T00:00:01Z",
            name="A",
            action="a",
            dialogue="d",
            phase="x",
            tension="low",
            consequences=[],
            cav1={
                "observed": {
                    "issues_before": {
                        "issues": [
                            {
                                "issue_id": "i1",
                                "status": "active",
                                "participants": [],
                                "status_reason_excerpt": "old",
                            }
                        ]
                    }
                }
            },
        ),
        _char_row(
            rnd=1,
            tn=2,
            ts="2026-01-01T00:00:02Z",
            name="A",
            action="a",
            dialogue="d",
            phase="x",
            tension="low",
            consequences=[],
            cav1={
                "observed": {
                    "issues_before": {
                        "issues": [
                            {
                                "issue_id": "i1",
                                "status": "active",
                                "participants": [],
                                "status_reason_excerpt": "old",
                            }
                        ]
                    }
                }
            },
            issue_updates=[
                {"issue_id": "i1", "status": "resolved", "participants": [], "status_reason": "new"}
            ],
        ),
    ]
    from progression_stress_audit_replay import load_character_audit_rows

    sess = tmp_path / "s2"
    sess.mkdir()
    for i, row in enumerate(rows_data):
        (sess / f"f{i}_full.json").write_text(json.dumps(row), encoding="utf-8")
    loaded = load_character_audit_rows(sess)
    h_last = post_turn_issue_H(loaded, 1)
    assert h_last is not None
    assert h_last[0][1] == "resolved"
    assert h_last[0][3] == "new"
