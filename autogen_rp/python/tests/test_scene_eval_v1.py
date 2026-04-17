"""Tests for scene_eval_v1 (GitHub Issue #66 v1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_support_manifest import build_support_manifest
from scene_eval_v1 import (
    PREDICATE_INTEGRITY,
    PREDICATE_PAIRWISE,
    PREDICATE_STRUCT,
    run_scene_eval_v1,
)


def _minimal_prompt_layer_audit(**kwargs: object) -> dict:
    base = {
        "summary_generation_eligible": False,
        "summary_blocks_generated_total": 0,
        "generated_summary_block_ids": [],
        "summary_blocks_available_count": 0,
        "available_summary_block_ids": [],
        "summary_blocks_selected_count": 0,
        "selected_summary_block_ids": [],
        "excluded_summary_block_ids": [],
        "selection_reason": "",
        "skipped_reason": "",
        "fallback_used": False,
        "summary_limit": None,
        "has_binding_constraints": False,
        "scene_binding_constraints_section": "",
        "retrieval_summary": {
            "retrieved_block_present": False,
            "retrieved_item_count": 0,
            "retrieved_char_count": 0,
            "retrieved_source_refs": [],
        },
    }
    base.update(kwargs)
    return base


def _char_row(
    *,
    rnd: int,
    turn: int,
    name: str,
    support_manifest: dict | None = None,
) -> dict:
    md: dict = {}
    if support_manifest is not None:
        md["support_manifest"] = support_manifest
    return {
        "bot_type": "character",
        "round_number": rnd,
        "turn_number": turn,
        "bot_name": name,
        "input_messages": [{"content": "p"}],
        "parsed_output": {"dialogue": "d", "action": "a"},
        "metadata": md,
        "context_snapshot": {"ignored_by_scene_eval_v1": True},
        "effective_user_trigger": "",
    }


def test_integrity_when_no_character_rows(tmp_path: Path) -> None:
    sess = tmp_path / "session_empty"
    sess.mkdir()
    out = run_scene_eval_v1(sess)
    assert out["scene_eval_version"] == "1"
    integrity = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_INTEGRITY]
    assert len(integrity) == 1
    assert integrity[0]["result"] == "inconclusive"
    pairwise = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_PAIRWISE]
    assert not pairwise


def test_pairwise_clear_identical_manifests(tmp_path: Path) -> None:
    sess = tmp_path / "session_1"
    sess.mkdir()
    pl = _minimal_prompt_layer_audit()
    m = build_support_manifest(pl, "same")
    rows = [
        _char_row(rnd=1, turn=1, name="A", support_manifest=m),
        _char_row(rnd=1, turn=2, name="A", support_manifest=dict(m)),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_x_turn0{i + 1}_A_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    out = run_scene_eval_v1(sess)
    pw = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_PAIRWISE]
    assert len(pw) == 1
    assert pw[0]["result"] == "clear"
    assert pw[0]["subject"]["bot_name"] == "A"


def test_pairwise_fired_non_envelope_diff(tmp_path: Path) -> None:
    sess = tmp_path / "session_2"
    sess.mkdir()
    pl1 = _minimal_prompt_layer_audit(selected_summary_block_ids=["x"])
    pl2 = _minimal_prompt_layer_audit(selected_summary_block_ids=["y"])
    m1 = build_support_manifest(pl1, "p")
    m2 = build_support_manifest(pl2, "p")
    rows = [
        _char_row(rnd=1, turn=1, name="B", support_manifest=m1),
        _char_row(rnd=1, turn=2, name="B", support_manifest=m2),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_x_turn0{i + 1}_B_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    out = run_scene_eval_v1(sess)
    pw = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_PAIRWISE]
    assert len(pw) == 1
    assert pw[0]["result"] == "fired"


def test_pairwise_inconclusive_missing_manifest(tmp_path: Path) -> None:
    sess = tmp_path / "session_3"
    sess.mkdir()
    pl = _minimal_prompt_layer_audit()
    m = build_support_manifest(pl, "p")
    rows = [
        _char_row(rnd=1, turn=1, name="C", support_manifest=m),
        _char_row(rnd=1, turn=2, name="C", support_manifest=None),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_x_turn0{i + 1}_C_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    out = run_scene_eval_v1(sess)
    pw = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_PAIRWISE]
    assert len(pw) == 1
    assert pw[0]["result"] == "inconclusive"


def test_structured_eval_inconclusive_when_omitted(tmp_path: Path) -> None:
    sess = tmp_path / "session_4"
    sess.mkdir()
    pl = _minimal_prompt_layer_audit()
    m = build_support_manifest(pl, "p")
    data = _char_row(rnd=1, turn=1, name="D", support_manifest=m)
    (sess / "round_001_x_turn01_D_full.json").write_text(json.dumps(data), encoding="utf-8")

    out = run_scene_eval_v1(sess, structured_eval_path=None)
    st = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_STRUCT]
    assert len(st) == 1
    assert st[0]["result"] == "inconclusive"


def test_structured_eval_fired_with_metrics(tmp_path: Path) -> None:
    sess = tmp_path / "session_5"
    sess.mkdir()
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "metrics": {"progression_retries_triggered": 2},
                "sim_progression_metrics_events": [
                    {"kind": "progression_retry"},
                    {"kind": "progression_retry"},
                    {"kind": "accepted_turn"},
                ],
            }
        ),
        encoding="utf-8",
    )
    out = run_scene_eval_v1(sess, structured_eval_path=metrics_path)
    st = [j for j in out["judgments"] if j["predicate_id"] == PREDICATE_STRUCT]
    assert len(st) == 1
    assert st[0]["result"] == "fired"
    assert "progression_retries_triggered" in st[0]["summary"]
    assert "2" in st[0]["summary"]
