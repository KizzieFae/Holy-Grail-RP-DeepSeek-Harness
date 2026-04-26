"""User callout review store (GitHub #125)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import user_callout_review_store as rs
import user_callouts as uc
from user_callout_review_store import (
    UserCalloutReviewStoreError,
    dismiss_callout,
    find_user_callouts_path_for_callout,
    list_unresolved,
    record_issue_promotion,
    rebuild_review_state,
    review_index_path,
    save_issue_links,
    save_review_index,
    upsert_review_row_after_new_callout,
)


def _raw_record(cid: str, sn: int = 1) -> dict:
    return {
        "callout_id": cid,
        "created_at_utc": "2026-01-15T12:00:00Z",
        "audit_session_owner": "o",
        "audit_session_number": sn,
        "runtime_session_id": None,
        "scene_template_id": None,
        "audit_round_number": 1,
        "audit_turn_number": 1,
        "continuity_turn_index": 0,
        "note": None,
        "artifact_refs": {
            "round_path": "x/r",
            "primary_full_path": None,
            "audit_summary_path": "x/s",
            "session_state_path": None,
        },
    }


def test_keyed_index_roundtrip(tmp_path: Path) -> None:
    monkey = pytest.MonkeyPatch()
    monkey.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "ad"
    base.mkdir()
    p = review_index_path(base_dir=base)
    root = {
        "schema": rs.REVIEW_INDEX_SCHEMA,
        "schema_version": 1,
        "rows": {
            "a1": {
                "audit_session_number": 1,
                "session_path_hint": "ad/session_001",
                "created_at_utc": "2026-01-01T00:00:00Z",
                "audit_round_number": 1,
                "audit_turn_number": 1,
                "continuity_turn_index": 0,
                "review_disposition": "unreviewed",
            }
        },
    }
    save_review_index(p, root)
    got = rs.load_review_index(p)
    assert got["rows"]["a1"]["review_disposition"] == "unreviewed"


def test_issue_links_sole_promotion_and_duplicate_rejected(tmp_path: Path) -> None:
    save_issue_links(
        rs.issue_links_path(base_dir=tmp_path),
        {
            "schema": rs.ISSUE_LINKS_SCHEMA,
            "schema_version": 1,
            "links": {
                "c1": {
                    "issue_number": 99,
                    "issue_url": "https://x/y/99",
                    "linked_at_utc": "2026-01-01T00:00:00Z",
                }
            },
        },
    )
    with pytest.raises(ValueError, match="already has an issue link"):
        record_issue_promotion(
            base_dir=tmp_path,
            callout_id="c1",
            issue_number=100,
            issue_url="https://x",
        )


def test_dismiss_forbidden_when_promoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    save_issue_links(
        rs.issue_links_path(base_dir=tmp_path),
        {
            "schema": rs.ISSUE_LINKS_SCHEMA,
            "schema_version": 1,
            "links": {
                "c1": {
                    "issue_number": 1,
                    "issue_url": "u",
                    "linked_at_utc": "t",
                }
            },
        },
    )
    ip = review_index_path(base_dir=tmp_path)
    save_review_index(
        ip,
        {
            "schema": rs.REVIEW_INDEX_SCHEMA,
            "schema_version": 1,
            "rows": {
                "c1": {
                    "audit_session_number": 1,
                    "session_path_hint": "x",
                    "created_at_utc": "t",
                    "audit_round_number": 1,
                    "audit_turn_number": 1,
                    "continuity_turn_index": None,
                    "review_disposition": "unreviewed",
                }
            },
        },
    )
    with pytest.raises(ValueError, match="promoted"):
        dismiss_callout(base_dir=tmp_path, callout_id="c1")


def test_rebuild_merges_raw_links_preserves_dismissed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "rp"
    sdir = base / "session_001"
    sdir.mkdir(parents=True)
    uc.append_callout(
        sdir / "user_callouts_v1.json",
        _raw_record("call-a", 1),
    )
    # dismissed in old index, not in links — should keep dismissed
    save_review_index(
        review_index_path(base_dir=base),
        {
            "schema": rs.REVIEW_INDEX_SCHEMA,
            "schema_version": 1,
            "rows": {
                "call-a": {
                    "audit_session_number": 1,
                    "session_path_hint": "rp/session_001",
                    "created_at_utc": "2026-01-15T12:00:00Z",
                    "audit_round_number": 1,
                    "audit_turn_number": 1,
                    "continuity_turn_index": 0,
                    "review_disposition": "dismissed",
                }
            },
        },
    )
    rebuild_review_state(base_dir=base)
    data = rs.load_review_index(review_index_path(base_dir=base))
    assert data["rows"]["call-a"]["review_disposition"] == "dismissed"


def test_upsert_after_new_callout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "rp"
    sdir = base / "session_001"
    sdir.mkdir(parents=True)
    path = sdir / "user_callouts_v1.json"
    rec = _raw_record("new-uuid-1111-1111-1111-111111111111", 1)
    uc.append_callout(path, rec)
    upsert_review_row_after_new_callout(base_dir=base, record=rec)
    idx = rs.load_review_index(review_index_path(base_dir=base))
    assert idx["rows"]["new-uuid-1111-1111-1111-111111111111"]["review_disposition"] == "unreviewed"


def test_corrupt_review_index_raises(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text("{", encoding="utf-8")
    with pytest.raises(UserCalloutReviewStoreError):
        rs.load_review_index(p)


def test_find_user_callouts_path_for_callout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "rp"
    sdir = base / "session_001"
    sdir.mkdir(parents=True)
    cid = "11111111-1111-1111-1111-111111111111"
    uc.append_callout(
        sdir / "user_callouts_v1.json",
        _raw_record(cid, 1),
    )
    got = find_user_callouts_path_for_callout(base_dir=base, callout_id=cid)
    assert got is not None
    assert got.name == "user_callouts_v1.json"


def test_list_unresolved_excludes_dismissed_and_promoted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "rp"
    sdir = base / "session_001"
    sdir.mkdir(parents=True)
    uc.append_callout(
        sdir / "user_callouts_v1.json",
        _raw_record("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 1),
    )
    uc.append_callout(
        sdir / "user_callouts_v1.json",
        _raw_record("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", 1),
    )
    r1 = _raw_record("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 1)
    r2 = _raw_record("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", 1)
    upsert_review_row_after_new_callout(base_dir=base, record=r1)
    upsert_review_row_after_new_callout(base_dir=base, record=r2)
    # promote b
    save_issue_links(
        rs.issue_links_path(base_dir=base),
        {
            "schema": rs.ISSUE_LINKS_SCHEMA,
            "schema_version": 1,
            "links": {
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb": {
                    "issue_number": 1,
                    "issue_url": "https://x/1",
                    "linked_at_utc": "t",
                }
            },
        },
    )
    # dismiss a via file manipulation: load index, set dismissed for a
    pidx = review_index_path(base_dir=base)
    data = rs.load_review_index(pidx)
    ar = data["rows"]["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    ar["review_disposition"] = "dismissed"
    data["rows"]["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"] = ar
    save_review_index(pidx, data)
    u = list_unresolved(base_dir=base)
    assert u == []


def test_list_unresolved_includes_unreviewed_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "PATH_ANCHOR", tmp_path, raising=False)
    monkeypatch.setattr(uc, "_PATH_ANCHOR", tmp_path, raising=False)
    base = tmp_path / "rp"
    sdir = base / "session_001"
    sdir.mkdir(parents=True)
    r0 = _raw_record("cccccccc-cccc-cccc-cccc-cccccccccccc", 1)
    uc.append_callout(sdir / "user_callouts_v1.json", r0)
    upsert_review_row_after_new_callout(base_dir=base, record=r0)
    u = list_unresolved(base_dir=base)
    assert len(u) == 1
    assert u[0][0] == "cccccccc-cccc-cccc-cccc-cccccccccccc"
