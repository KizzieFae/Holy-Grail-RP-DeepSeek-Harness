"""Unit tests for Tier A perception deterministic gate (GitHub #214; no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from tier_a_perception_gate import (  # noqa: E402
    TierAPerceptionGateError,
    validate_tier_a_perception_smoke_session,
    validate_tier_a_perception_smoke_session_report_only,
)


def _write_full(
    dstdir: Path,
    name: str,
    *,
    bot_type: str,
    parsed: dict,
) -> None:
    dstdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "bot_type": bot_type,
        "parsed_output": parsed,
    }
    (dstdir / name).write_text(json.dumps(payload), encoding="utf-8")


def test_gate_passes_directed_with_audience(tmp_path: Path) -> None:
    r = tmp_path / "session_x"
    _write_full(
        r / "round_001",
        "audit_fake_session_round001_turn01_celina_full.json",
        bot_type="character",
        parsed={
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Hey.", "audibility": "directed", "audience": ["Ayame"]}
            ],
            "motivation": {},
        },
    )
    rep = validate_tier_a_perception_smoke_session(r, bounded_token=None)
    assert rep["ok"] is True
    assert rep["speech_beats_scanned"] == 1


def test_gate_fails_public_only(tmp_path: Path) -> None:
    r = tmp_path / "session_x"
    _write_full(
        r,
        "audit_fake_session_round001_turn01_ayame_full.json",
        bot_type="character",
        parsed={
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Hello everyone.", "audibility": "public", "audience": []}
            ],
            "motivation": {},
        },
    )
    with pytest.raises(TierAPerceptionGateError, match="directed"):
        validate_tier_a_perception_smoke_session(r)


def test_gate_fails_private_empty_audience(tmp_path: Path) -> None:
    r = tmp_path / "session_x"
    _write_full(
        r,
        "audit_fake_session_round001_turn01_ayame_full.json",
        bot_type="character",
        parsed={
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Secret.", "audibility": "private", "audience": []}
            ],
            "motivation": {},
        },
    )
    with pytest.raises(TierAPerceptionGateError, match="audience"):
        validate_tier_a_perception_smoke_session(r)


def test_report_only_never_raises(tmp_path: Path) -> None:
    r = tmp_path / "session_x"
    _write_full(
        r,
        "audit_fake_session_round001_turn01_x_full.json",
        bot_type="character",
        parsed={"move_schema_version": 2, "beats": [], "motivation": {}},
    )
    rep = validate_tier_a_perception_smoke_session_report_only(r)
    assert rep["ok"] is False
    assert rep["errors"]
