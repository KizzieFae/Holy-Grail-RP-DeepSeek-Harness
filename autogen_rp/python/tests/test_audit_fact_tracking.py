"""Tests for audit_fact_tracking (GitHub #58)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_fact_tracking import (
    analyze_fact_tracking,
    fact_spec_sha256,
    run_fact_track_postprocess,
    validate_fact_spec,
)
from audit_support_manifest import build_support_manifest
from issue29_investigation import load_character_audit_rows


def _char_row(
    *,
    rnd: int,
    turn: int,
    name: str,
    prompt: str,
    dialogue: str,
    action: str,
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
        "input_messages": [{"content": prompt}],
        "parsed_output": {"dialogue": dialogue, "action": action},
        "metadata": md,
        "context_snapshot": {},
        "effective_user_trigger": "",
    }


def test_validate_fact_spec_rejects_bad_schema() -> None:
    ok, reason = validate_fact_spec({"schema_version": "wrong"})
    assert not ok
    assert reason == "bad_schema_version"


def test_utilization_failure_when_support_continuous(tmp_path: Path) -> None:
    """Literals stay in prompt; parsed move omits required token at divergence."""
    sess = tmp_path / "session_99999"
    sess.mkdir()
    pl_empty: dict = {}
    rows = [
        _char_row(
            rnd=1,
            turn=1,
            name="A",
            prompt="intro ESTABLISH_KEEP",
            dialogue="x",
            action="y",
            support_manifest=build_support_manifest(pl_empty, "intro ESTABLISH_KEEP"),
        ),
        _char_row(
            rnd=1,
            turn=2,
            name="A",
            prompt="intro ESTABLISH_KEEP more",
            dialogue="missing",
            action="output",
            support_manifest=build_support_manifest(pl_empty, "intro ESTABLISH_KEEP more"),
        ),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_A_turn0{i + 1}_A_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "t_util",
        "actor_scope": {"kind": "character_name", "name": "A"},
        "establishment_rule": {
            "kind": "prompt_literals_all",
            "literals": ["ESTABLISH_KEEP"],
        },
        "support_predicate": {
            "kind": "prompt_literals_all",
            "literals": ["KEEP"],
        },
        "behavior_rule": {
            "kind": "parsed_output_literals_all",
            "literals": ["REQUIRED_OUT"],
        },
    }
    out = analyze_fact_tracking(sess, spec)
    assert out["failure_classification"] == "utilization_failure"
    assert out["support_state_at_divergence"] is True
    assert out["path_manifest_disruption"] is False
    assert out["T_intro"]["turn_number"] == 1
    assert out["T_divergence"]["turn_number"] == 2


def test_support_loss_when_prompt_drops_literal(tmp_path: Path) -> None:
    sess = tmp_path / "session_99998"
    sess.mkdir()
    pl_empty: dict = {}
    rows = [
        _char_row(
            rnd=1,
            turn=1,
            name="A",
            prompt="hold KEEP_TOKEN",
            dialogue="REQUIRED_OUT",
            action="",
            support_manifest=build_support_manifest(pl_empty, "hold KEEP_TOKEN"),
        ),
        _char_row(
            rnd=1,
            turn=2,
            name="A",
            prompt="hold dropped",
            dialogue="no",
            action="REQ",
            support_manifest=build_support_manifest(pl_empty, "hold dropped"),
        ),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_A_turn0{i + 1}_A_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "t_sup",
        "establishment_rule": {
            "kind": "prompt_literals_all",
            "literals": ["KEEP_TOKEN"],
        },
        "support_predicate": {
            "kind": "prompt_literals_all",
            "literals": ["KEEP_TOKEN"],
        },
        "behavior_rule": {
            "kind": "parsed_output_literals_all",
            "literals": ["REQUIRED_OUT"],
        },
    }
    out = analyze_fact_tracking(sess, spec)
    assert out["failure_classification"] == "support_loss"
    assert out["support_state_at_divergence"] is False


def test_manifest_non_envelope_disruption_triggers_support_loss(tmp_path: Path) -> None:
    """Literals unchanged but binding_constraints_section fingerprint jumps (manifest diff)."""
    sess = tmp_path / "session_99997"
    sess.mkdir()
    prompt = "stable LITMARK"
    pl_a = {"scene_binding_constraints_section": "bed=A"}
    pl_b = {"scene_binding_constraints_section": "bed=B"}
    rows = [
        _char_row(
            rnd=1,
            turn=1,
            name="A",
            prompt=prompt,
            dialogue="REQUIRED_OUT",
            action="",
            support_manifest=build_support_manifest(pl_a, prompt),
        ),
        _char_row(
            rnd=1,
            turn=2,
            name="A",
            prompt=prompt,
            dialogue="x",
            action="y",
            support_manifest=build_support_manifest(pl_b, prompt),
        ),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_A_turn0{i + 1}_A_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "t_manif",
        "establishment_rule": {
            "kind": "prompt_literals_all",
            "literals": ["LITMARK"],
        },
        "support_predicate": {
            "kind": "prompt_literals_all",
            "literals": ["LITMARK"],
        },
        "behavior_rule": {
            "kind": "parsed_output_literals_all",
            "literals": ["REQUIRED_OUT"],
        },
    }
    out = analyze_fact_tracking(sess, spec)
    assert out["failure_classification"] == "support_loss"
    assert out["path_manifest_disruption"] is True


def test_fact_spec_sha256_stable() -> None:
    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "p",
        "establishment_rule": {"kind": "prompt_literals_all", "literals": ["a"]},
        "support_predicate": {"kind": "prompt_literals_all", "literals": ["a"]},
        "behavior_rule": {"kind": "parsed_output_literals_all", "literals": ["b"]},
    }
    h1 = fact_spec_sha256(spec)
    h2 = fact_spec_sha256(
        {
            "probe_id": "p",
            "schema_version": "fact_spec.v1",
            "behavior_rule": {"kind": "parsed_output_literals_all", "literals": ["b"]},
            "establishment_rule": {"kind": "prompt_literals_all", "literals": ["a"]},
            "support_predicate": {"kind": "prompt_literals_all", "literals": ["a"]},
        }
    )
    assert h1 == h2


def test_load_character_audit_rows_fixture_order(tmp_path: Path) -> None:
    """Sanity: synthetic layout is readable by shared loader."""
    sess = tmp_path / "session_x"
    sess.mkdir()
    data = _char_row(
        rnd=1,
        turn=3,
        name="Z",
        prompt="p",
        dialogue="d",
        action="a",
    )
    (sess / "round_001_Z_turn03_Z_full.json").write_text(
        json.dumps(data), encoding="utf-8"
    )
    rows = load_character_audit_rows(sess)
    assert len(rows) == 1
    assert rows[0]["bot_name"] == "Z"


def test_run_fact_track_postprocess_writes_companion_and_returns_path(tmp_path: Path) -> None:
    sess = tmp_path / "session_90001"
    sess.mkdir()
    rows = [
        _char_row(
            rnd=1,
            turn=1,
            name="A",
            prompt="intro ESTABLISH_KEEP",
            dialogue="x",
            action="y",
            support_manifest=None,
        ),
        _char_row(
            rnd=1,
            turn=2,
            name="A",
            prompt="intro ESTABLISH_KEEP more",
            dialogue="missing",
            action="output",
            support_manifest=None,
        ),
    ]
    for i, data in enumerate(rows):
        p = sess / f"round_001_A_turn0{i + 1}_A_full.json"
        p.write_text(json.dumps(data), encoding="utf-8")

    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "t_post",
        "actor_scope": {"kind": "character_name", "name": "A"},
        "establishment_rule": {
            "kind": "prompt_literals_all",
            "literals": ["ESTABLISH_KEEP"],
        },
        "support_predicate": {
            "kind": "prompt_literals_all",
            "literals": ["KEEP"],
        },
        "behavior_rule": {
            "kind": "parsed_output_literals_all",
            "literals": ["REQUIRED_OUT"],
        },
    }
    base = analyze_fact_tracking(sess, spec)
    out = run_fact_track_postprocess(sess, spec)
    cap = out.pop("companion_artifact_path", None)
    assert cap is not None
    assert out == base
    p_written = Path(cap)
    assert p_written.is_file()
    assert p_written.parent == sess.resolve()
    assert p_written.name.startswith("fact_track__t_post__")
    disk = json.loads(p_written.read_text(encoding="utf-8"))
    assert disk == base
    assert "companion_artifact_path" not in disk


def test_run_fact_track_postprocess_explicit_out_path(tmp_path: Path) -> None:
    sess = tmp_path / "session_90002"
    sess.mkdir()
    data = _char_row(
        rnd=1,
        turn=1,
        name="A",
        prompt="x",
        dialogue="d",
        action="a",
    )
    (sess / "round_001_A_turn01_A_full.json").write_text(json.dumps(data), encoding="utf-8")
    spec = {
        "schema_version": "fact_spec.v1",
        "probe_id": "p_out",
        "establishment_rule": {"kind": "prompt_literals_all", "literals": ["nope"]},
        "support_predicate": {"kind": "prompt_literals_all", "literals": ["x"]},
        "behavior_rule": {"kind": "parsed_output_literals_all", "literals": ["z"]},
    }
    target = tmp_path / "custom_fact_track.json"
    out = run_fact_track_postprocess(sess, spec, companion_path=target)
    assert out["companion_artifact_path"] == str(target.resolve())
    assert target.is_file()
