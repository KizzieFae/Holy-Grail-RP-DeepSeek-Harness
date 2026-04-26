"""User Callouts (Issue #55) — append store and strict document validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import user_callouts as uc
from user_callouts import (
    UserCalloutDocumentError,
    append_callout,
    build_related_artifact_ref_entries,
    get_user_callouts_path,
    load_document,
    new_callout,
    path_relative_to_python_dir,
    pick_primary_full_path,
    validate_callout_record,
)


def test_empty_round_dir_returns_no_primary(tmp_path: Path) -> None:
    rd = tmp_path / "round_001"
    rd.mkdir()
    assert pick_primary_full_path(rd, audit_turn_number=1) is None


def test_primary_prefers_character_over_narrator(tmp_path: Path) -> None:
    rd = tmp_path / "r"
    rd.mkdir()
    (rd / "o_session001_round001_turn01_narrator_full.json").write_text("{}", encoding="utf-8")
    (rd / "o_session001_round001_turn01_celina_full.json").write_text("{}", encoding="utf-8")
    got = pick_primary_full_path(rd, audit_turn_number=1)
    assert got is not None
    assert "celina" in got.name.lower()


def test_path_relative_to_python_dir_roundtrip(tmp_path: Path) -> None:
    anchor = Path(uc.__file__).resolve().parent.parent
    p = anchor / "data" / "x.txt"
    rel = path_relative_to_python_dir(p)
    assert rel.replace("\\", "/") == "data/x.txt"


def test_append_creates_file_and_second_append(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "audits"
    base.mkdir()
    sdir = base / "session_001" / "round_001"
    sdir.mkdir(parents=True)
    (sdir / "a_session001_round001_turn01_ayame_full.json").write_text("{}", encoding="utf-8")

    path = get_user_callouts_path(base_dir=base, audit_session_number=1)
    rec1 = {
        "callout_id": "c1",
        "created_at_utc": "2026-01-01T00:00:00Z",
        "audit_session_owner": "a",
        "audit_session_number": 1,
        "runtime_session_id": None,
        "scene_template_id": None,
        "audit_round_number": 1,
        "audit_turn_number": 1,
        "continuity_turn_index": 0,
        "note": None,
        "artifact_refs": {
            "round_path": "t/r",
            "primary_full_path": None,
            "audit_summary_path": "t/s",
            "session_state_path": None,
        },
    }
    assert validate_callout_record(rec1) == []
    append_callout(path, rec1)
    rec2 = dict(rec1)
    rec2["callout_id"] = "c2"
    append_callout(path, rec2)
    data = load_document(path)
    assert len(data["records"]) == 2


def test_corrupt_file_strict_failure(tmp_path: Path) -> None:
    p = tmp_path / "user_callouts_v1.json"
    p.write_text("not json {{{", encoding="utf-8")
    with pytest.raises(UserCalloutDocumentError):
        load_document(p)
    with pytest.raises(UserCalloutDocumentError):
        append_callout(
            p,
            {
                "callout_id": "x",
                "created_at_utc": "2026-01-01T00:00:00Z",
                "audit_session_owner": "a",
                "audit_session_number": 1,
                "runtime_session_id": None,
                "scene_template_id": None,
                "audit_round_number": 1,
                "audit_turn_number": 1,
                "continuity_turn_index": None,
                "note": None,
                "artifact_refs": {
                    "round_path": "a/b",
                    "primary_full_path": None,
                    "audit_summary_path": "a/s",
                    "session_state_path": None,
                },
            },
        )
    # File unchanged on failed append
    assert p.read_text(encoding="utf-8") == "not json {{{"


def test_new_callout_writes_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "ad"
    sdir = base / "session_001" / "round_001"
    sdir.mkdir(parents=True)
    (sdir / "a_session001_round001_turn01_ayame_full.json").write_text("{}", encoding="utf-8")
    path = get_user_callouts_path(base_dir=base, audit_session_number=1)
    rec = new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="testowner",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id="tid",
        continuity_turn_index=3,
        note="hello",
        session_state_json=None,
    )
    assert rec["callout_id"]
    out = load_document(path)
    assert len(out["records"]) == 1
    ar = out["records"][0]["artifact_refs"]
    assert ar["round_path"] == "ad/session_001/round_001"
    assert ar["primary_full_path"] and "ayame" in ar["primary_full_path"].lower()
    assert ar["session_state_path"] is None
    assert "related_artifact_refs" not in ar


def test_new_callout_related_sibling_full_only_excludes_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "ad"
    sdir = base / "session_001" / "round_001"
    sdir.mkdir(parents=True)
    (sdir / "o_s001_r001_round001_turn01_celina_full.json").write_text("{}", encoding="utf-8")
    (sdir / "o_s001_r001_round001_turn01_narrator_full.json").write_text("{}", encoding="utf-8")
    (sdir / "o_s001_r001_round001_turn01_director_full.json").write_text("{}", encoding="utf-8")
    path = get_user_callouts_path(base_dir=base, audit_session_number=1)
    rec = new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="o",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id=None,
        continuity_turn_index=0,
        note="n",
        session_state_json=None,
    )
    ar = rec["artifact_refs"]
    rel = ar.get("related_artifact_refs", [])
    assert len(rel) == 2
    names = {Path(x["path"]).name for x in rel}
    assert "o_s001_r001_round001_turn01_celina_full.json" not in names
    assert "o_s001_r001_round001_turn01_narrator_full.json" in names
    assert "o_s001_r001_round001_turn01_director_full.json" in names
    assert ar["primary_full_path"] and "celina" in ar["primary_full_path"]


def test_new_callout_ignores_other_turn_and_light(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "ad"
    sdir = base / "session_001" / "round_001"
    sdir.mkdir(parents=True)
    (sdir / "o_s001_r001_round001_turn01_ayame_full.json").write_text("{}", encoding="utf-8")
    (sdir / "o_s001_r001_round001_turn01_ayame_light.json").write_text("{}", encoding="utf-8")
    (sdir / "o_s001_r001_round001_turn02_ayame_full.json").write_text("{}", encoding="utf-8")
    path = get_user_callouts_path(base_dir=base, audit_session_number=1)
    new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="o",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id=None,
        continuity_turn_index=0,
        note=None,
        session_state_json=None,
    )
    out = load_document(path)
    ar = out["records"][0]["artifact_refs"]
    assert "related_artifact_refs" not in ar
    (sdir / "o_s001_r001_round001_turn01_mira_full.json").write_text("{}", encoding="utf-8")
    new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="o",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id=None,
        continuity_turn_index=0,
        note="second",
        session_state_json=None,
    )
    last = load_document(path)["records"][-1]
    r2 = last["artifact_refs"].get("related_artifact_refs", [])
    rel_names = {Path(x["path"]).name for x in r2}
    assert "o_s001_r001_round001_turn01_ayame_light.json" not in rel_names
    assert "o_s001_r001_round001_turn02_ayame_full.json" not in rel_names
    assert "o_s001_r001_round001_turn01_mira_full.json" in rel_names
    assert "o_s001_r001_round001_turn01_ayame_full.json" not in rel_names


def test_validate_related_missing_path() -> None:
    rec = {
        "callout_id": "c1",
        "created_at_utc": "2026-01-01T00:00:00Z",
        "audit_session_owner": "a",
        "audit_session_number": 1,
        "runtime_session_id": None,
        "scene_template_id": None,
        "audit_round_number": 1,
        "audit_turn_number": 1,
        "continuity_turn_index": 0,
        "note": None,
        "artifact_refs": {
            "round_path": "r/r",
            "primary_full_path": None,
            "audit_summary_path": "r/s",
            "session_state_path": None,
            "related_artifact_refs": [{"label": "x"}],
        },
    }
    err = validate_callout_record(rec)
    assert any("path" in e.lower() for e in err)


def test_validate_related_unknown_key_tolerated() -> None:
    rec = {
        "callout_id": "c1",
        "created_at_utc": "2026-01-01T00:00:00Z",
        "audit_session_owner": "a",
        "audit_session_number": 1,
        "runtime_session_id": None,
        "scene_template_id": None,
        "audit_round_number": 1,
        "audit_turn_number": 1,
        "continuity_turn_index": 0,
        "note": None,
        "artifact_refs": {
            "round_path": "r/r",
            "primary_full_path": None,
            "audit_summary_path": "r/s",
            "session_state_path": None,
            "related_artifact_refs": [
                {"path": "rp_app/x.json", "future_field": 123, "ref_kind": "nope"}
            ],
        },
    }
    assert validate_callout_record(rec) == []


def test_append_only_preserves_first_record_with_related(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "ad"
    sdir = base / "session_001" / "round_001"
    sdir.mkdir(parents=True)
    (sdir / "a_session001_round001_turn01_ayame_full.json").write_text("{}", encoding="utf-8")
    (sdir / "a_session001_round001_turn01_zoe_full.json").write_text("{}", encoding="utf-8")
    path = get_user_callouts_path(base_dir=base, audit_session_number=1)
    new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="a",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id=None,
        continuity_turn_index=0,
        note="first",
        session_state_json=None,
    )
    snapshot = json.loads(
        json.dumps(load_document(path)["records"][0], sort_keys=True)
    )
    new_callout(
        base_dir=base,
        path=path,
        audit_session_owner="a",
        audit_session_number=1,
        audit_round_number=1,
        audit_turn_number=1,
        runtime_session_id=None,
        scene_template_id=None,
        continuity_turn_index=0,
        note="second",
        session_state_json=None,
    )
    out = load_document(path)
    assert len(out["records"]) == 2
    first = out["records"][0]
    second = out["records"][1]
    assert first["callout_id"] != second["callout_id"]
    assert first["note"] == "first"
    rfirst = first["artifact_refs"]
    rsecond = second["artifact_refs"]
    assert "related_artifact_refs" in rfirst
    assert "related_artifact_refs" in rsecond
    assert "path" in rfirst["related_artifact_refs"][0]
    assert json.loads(json.dumps(first, sort_keys=True)) == snapshot


def test_build_related_entries_empty_when_solo_primary(tmp_path: Path) -> None:
    rd = tmp_path / "round_001"
    rd.mkdir()
    (rd / "x_round001_turn01_ayame_full.json").write_text("{}", encoding="utf-8")
    primary = pick_primary_full_path(rd, audit_turn_number=1)
    assert primary is not None
    assert build_related_artifact_ref_entries(
        rd, audit_turn_number=1, primary_full=primary
    ) == []
