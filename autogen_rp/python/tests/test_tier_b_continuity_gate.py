"""Unit tests for Tier B continuity deterministic gate (GitHub #214; no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from tier_b_continuity_gate import (  # noqa: E402
    TierBContinuityGateError,
    validate_tier_b_continuity_grounded_session,
    validate_tier_b_continuity_grounded_session_report_only,
)


def _write_manifest(
    dstdir: Path,
    *,
    excursion_id: str = "ex1",
    participant: str = "Hannah_Lovelace",
) -> None:
    dstdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "audit_scenario_metadata": {
            "audit_validation_tier": "tier_b_continuity_grounded",
            "audit_program_issue": "214",
            "tier_b_continuity_gate": {
                "excursion_id": excursion_id,
                "excursion_participant_agent": participant,
            },
        }
    }
    (dstdir / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_char_row(
    dstdir: Path,
    filename: str,
    *,
    rn: int,
    tn: int,
    digest: list[dict[str, str]] | None,
    present: list[str],
    pipeline_turn: bool = True,
) -> None:
    rnd = dstdir / f"round_{rn:03d}"
    rnd.mkdir(parents=True, exist_ok=True)
    md: dict = {}
    if digest is not None:
        md["excursion_audit_digest_v1"] = digest
    if pipeline_turn:
        md["continuity_audit_origin"] = {"kind": "pipeline_turn"}
    payload = {
        "round_number": rn,
        "turn_number": tn,
        "bot_type": "character",
        "bot_name": "ayame",
        "context_snapshot": {"scene_state_after": {"present_characters": present}},
        "metadata": md,
        "parsed_output": {},
    }
    (rnd / filename).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_gate_passes_lifecycle_and_presence(tmp_path: Path) -> None:
    root = tmp_path / "sess"
    _write_manifest(root)
    _write_char_row(
        root,
        "audit_x_session_round001_turn01_ayame_full.json",
        rn=1,
        tn=1,
        digest=[{"excursion_id": "ex1", "status": "active"}],
        present=["Ayame", "Celina"],
        pipeline_turn=True,
    )
    _write_char_row(
        root,
        "audit_x_session_round001_turn02_celina_full.json",
        rn=1,
        tn=2,
        digest=[{"excursion_id": "ex1", "status": "closed"}],
        present=["Ayame", "Celina", "Hannah_Lovelace"],
        pipeline_turn=True,
    )
    rep = validate_tier_b_continuity_grounded_session(root)
    assert rep["ok"] is True
    assert rep["digest_status_timeline"] == ["active", "closed"]


def test_gate_fails_perception_only_no_digest(tmp_path: Path) -> None:
    root = tmp_path / "sess"
    _write_manifest(root)
    _write_char_row(
        root,
        "audit_x_session_round001_turn01_ayame_full.json",
        rn=1,
        tn=1,
        digest=None,
        present=["Ayame"],
        pipeline_turn=True,
    )
    with pytest.raises(TierBContinuityGateError, match="excursion_audit_digest"):
        validate_tier_b_continuity_grounded_session(root)


def test_gate_fails_closed_without_restored_participation(tmp_path: Path) -> None:
    root = tmp_path / "sess"
    _write_manifest(root)
    _write_char_row(
        root,
        "audit_x_session_round001_turn01_ayame_full.json",
        rn=1,
        tn=1,
        digest=[{"excursion_id": "ex1", "status": "active"}],
        present=["Ayame", "Celina"],
        pipeline_turn=True,
    )
    _write_char_row(
        root,
        "audit_x_session_round001_turn02_celina_full.json",
        rn=1,
        tn=2,
        digest=[{"excursion_id": "ex1", "status": "closed"}],
        present=["Ayame", "Celina"],
        pipeline_turn=True,
    )
    with pytest.raises(TierBContinuityGateError, match="participant not in present_characters"):
        validate_tier_b_continuity_grounded_session(root)


def test_report_only_never_raises(tmp_path: Path) -> None:
    root = tmp_path / "sess"
    _write_manifest(root)
    rep = validate_tier_b_continuity_grounded_session_report_only(root)
    assert rep["ok"] is False
    assert rep["errors"]
