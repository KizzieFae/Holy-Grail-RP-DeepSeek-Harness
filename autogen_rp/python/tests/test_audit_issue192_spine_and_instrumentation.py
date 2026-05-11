"""Issue #192 PR-TECH: audit spine invariants + instrumentation stderr mirror (deterministic)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit_instrumentation import audit_instrumentation_enabled, log_audit_warning
from audit_logger_summary_output_continuity import count_indexed_turns
from audit_logger_summary_prep import scan_audit_artifact_gaps


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_audit_spine_index_narrative_and_round_dirs(tmp_path: Path) -> None:
    """Minimal coherent tree: index turn count matches narrative; indexed rounds have dirs."""
    session = tmp_path / "sessionfixture"
    session.mkdir()

    index = {
        "rounds": [
            {
                "round_number": 1,
                "turns": [{"acting_character": "Alpha"}],
            },
            {
                "round_number": 2,
                "turns": [{"acting_character": "Beta"}],
            },
        ]
    }
    narrative = {
        "turns": [
            {"character": "Alpha"},
            {"character": "Beta"},
        ]
    }
    _write_json(session / "_round_index.json", index)
    _write_json(session / "_narrative.json", narrative)
    _write_json(session / "_manifest.json", {"session_number": 1})
    _write_json(session / "_audit_summary.json", {"schema_version": "audit_summary.v0"})

    loaded_index = json.loads((session / "_round_index.json").read_text(encoding="utf-8"))
    loaded_narr = json.loads((session / "_narrative.json").read_text(encoding="utf-8"))

    assert count_indexed_turns(loaded_index.get("rounds", [])) == len(
        loaded_narr.get("turns") or []
    )

    for re in loaded_index.get("rounds", []):
        rn = int(re.get("round_number", 0) or 0)
        if rn <= 0:
            continue
        rdir = session / f"round_{rn:03d}"
        rdir.mkdir()
        (rdir / "owner_session001_round001_turn01_char_full.json").write_text(
            "{}", encoding="utf-8"
        )

    for re in loaded_index.get("rounds", []):
        rn = int(re.get("round_number", 0) or 0)
        if rn <= 0:
            continue
        assert (session / f"round_{rn:03d}").is_dir()


def test_scan_audit_artifact_gaps_stderr_mirror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Indexed turns with empty narrative triggers warning on stderr when instrumentation ON."""
    monkeypatch.setenv("RP_AUDIT_INSTRUMENTATION", "1")
    assert audit_instrumentation_enabled() is True

    session = tmp_path / "gap_session"
    session.mkdir()
    index = {
        "rounds": [
            {"round_number": 1, "turns": [{"acting_character": "X"}]},
        ]
    }
    narrative: dict = {"turns": []}

    scan_audit_artifact_gaps(session, index, narrative)
    err = capsys.readouterr().err
    assert "gap_session" in err
    assert "_round_index" in err
    assert "_narrative.json" in err


def test_log_audit_warning_no_stderr_when_instrumentation_off(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("RP_AUDIT_INSTRUMENTATION", raising=False)
    assert audit_instrumentation_enabled() is False
    log_audit_warning("should not appear")
    assert capsys.readouterr().err == ""

