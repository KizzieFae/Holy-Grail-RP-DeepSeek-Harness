"""Issue #79 Slice 4 — continuity_observability_summary_v1 rollup in _audit_summary.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_audit_origin import CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN
from continuity_manager import ContinuityManager
from continuity_observability_summary import (
    CONTINUITY_OBSERVABILITY_STATUS_REASONS,
    CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
    CONTINUITY_OBSERVABILITY_SUMMARY_V1_SCHEMA_VERSION,
    build_continuity_observability_status_v1_unavailable,
    build_continuity_observability_summary_v1,
)
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from audit_logger import AuditLogger
from audit_logger_summary_report import _enforce_continuity_observability_exclusivity


def _minimal_manager_with_turn_and_mutation() -> ContinuityManager:
    m = ContinuityManager()
    m.initialize_scene(
        location="Lab",
        opening_description="x",
        present_characters=["A", "B"],
    )
    complete_setup_seam_for_test_manager(m, cast=["A", "B"])
    m.process_turn(
        acting_character="A",
        move={
            "action": "speak",
            "dialogue": "hi",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    m.turn_metadata_by_index[1]["continuity_mutation_resolution"] = {"slot": {"x": 1}}
    m.open_excursion(participant_character_ids=["B"], excursion_id="e1")
    m.close_excursion("e1")
    return m


def test_summary_v1_allowed_keys_and_nested_shape() -> None:
    m = _minimal_manager_with_turn_and_mutation()
    s = build_continuity_observability_summary_v1(m)
    assert set(s.keys()) == {
        "beats_with_mutation_resolution",
        "continuity_turn_count_observed",
        "excursion_active_count",
        "excursion_closed_count",
        "excursion_record_count",
        "schema_version",
        "session_audit_origin",
    }
    assert s["schema_version"] == CONTINUITY_OBSERVABILITY_SUMMARY_V1_SCHEMA_VERSION
    assert s["continuity_turn_count_observed"] == 1
    assert s["beats_with_mutation_resolution"] == [1]
    assert s["excursion_record_count"] == 1
    assert s["excursion_active_count"] == 0
    assert s["excursion_closed_count"] == 1
    so = s["session_audit_origin"]
    assert set(so.keys()) == {"bypass_beats", "has_bypass"}
    assert so["has_bypass"] is True
    for row in so["bypass_beats"]:
        assert set(row.keys()) == {"continuity_turn_index", "kind"}
        assert row["kind"] != CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN


def test_enforce_continuity_observability_exclusivity_rejects_both() -> None:
    with pytest.raises(RuntimeError, match="must not both be present"):
        _enforce_continuity_observability_exclusivity(
            {
                "continuity_observability_summary_v1": {"schema_version": 1},
                "continuity_observability_status_v1": {"status": "unavailable"},
            }
        )


def test_status_v1_unavailable_shape_and_enum() -> None:
    assert (
        CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED
        in CONTINUITY_OBSERVABILITY_STATUS_REASONS
    )
    assert len(CONTINUITY_OBSERVABILITY_STATUS_REASONS) == 1
    s = build_continuity_observability_status_v1_unavailable(
        reason=CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
    )
    assert s == {
        "status": "unavailable",
        "reason": CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
    }
    assert list(s.keys()) == ["status", "reason"]


def test_status_v1_rejects_unknown_reason() -> None:
    with pytest.raises(ValueError, match="CONTINUITY_OBSERVABILITY_STATUS_REASONS"):
        build_continuity_observability_status_v1_unavailable(reason="unknown_reason")


def test_bypass_beats_sorted_by_index_then_kind() -> None:
    m = ContinuityManager()
    m.initialize_scene("L", "x", ["A"])
    complete_setup_seam_for_test_manager(m, cast=["A"])
    m.continuity_audit_origin_log = [
        {"continuity_turn_index": 2, "kind": "bypass_raw_location"},
        {"continuity_turn_index": 1, "kind": "bypass_direct_excursion_api"},
        {"continuity_turn_index": 2, "kind": "bypass_direct_excursion_api"},
    ]
    s = build_continuity_observability_summary_v1(m)
    beats = s["session_audit_origin"]["bypass_beats"]
    keys = [(b["continuity_turn_index"], b["kind"]) for b in beats]
    assert keys == sorted(keys)


def test_write_summary_report_replaces_continuity_block(tmp_path: Path) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame"],
        opening_description="x",
        user_name="u",
    )
    base = logger._get_session_path("Ayame", 1)
    report_path = base / "_audit_summary.json"
    report_path.write_text(
        json.dumps(
            {
                "session_owner": "Ayame",
                "continuity_observability_summary_v1": {
                    "stale": True,
                    "full_turn_metadata": {"no": "dupes"},
                },
            }
        ),
        encoding="utf-8",
    )

    m = ContinuityManager()
    m.initialize_scene("L", "x", ["A"])
    complete_setup_seam_for_test_manager(m, cast=["A"])

    out_path = logger.write_summary_report("Ayame", 1, continuity_manager=m)
    data = json.loads(Path(out_path).read_text(encoding="utf-8"))
    cos = data.get("continuity_observability_summary_v1")
    assert isinstance(cos, dict)
    assert "stale" not in cos
    assert "full_turn_metadata" not in cos
    assert cos["schema_version"] == CONTINUITY_OBSERVABILITY_SUMMARY_V1_SCHEMA_VERSION
    assert "continuity_observability_status_v1" not in data


def test_write_summary_report_without_continuity_manager_emits_status_unavailable(
    tmp_path: Path,
) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame"],
        opening_description="x",
        user_name="u",
    )
    out_path = logger.write_summary_report("Ayame", 1)
    data = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert "continuity_observability_summary_v1" not in data
    st = data.get("continuity_observability_status_v1")
    assert st == {
        "status": "unavailable",
        "reason": CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
    }
    assert list(st.keys()) == ["status", "reason"]


def test_merge_retrieval_preserves_continuity_summary(tmp_path: Path) -> None:
    from retrieval_audit_helpers import merge_retrieval_session_into_audit_summary

    p = tmp_path / "_audit_summary.json"
    payload = {
        "session_owner": "X",
        "continuity_observability_summary_v1": {
            "schema_version": 1,
            "continuity_turn_count_observed": 3,
            "beats_with_mutation_resolution": [1, 2],
            "excursion_record_count": 0,
            "excursion_active_count": 0,
            "excursion_closed_count": 0,
            "session_audit_origin": {
                "has_bypass": False,
                "bypass_beats": [],
            },
        },
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    merge_retrieval_session_into_audit_summary(
        str(p), {"retrieval_mode": "off"}
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["continuity_observability_summary_v1"]["continuity_turn_count_observed"] == 3
    assert data["retrieval_session"]["retrieval_mode"] == "off"
