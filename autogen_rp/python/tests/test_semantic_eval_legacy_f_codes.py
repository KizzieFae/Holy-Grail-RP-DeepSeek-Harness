"""Tests for Issue #243-C legacy F-code taxonomy lane."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from semantic_eval_legacy_f_codes import (  # noqa: E402
    LEGACY_F_CODE_LABELS,
    attach_legacy_lane,
    classify_legacy_turn,
    legacy_f_code_counts_from_corpus,
    map_legacy_f_code_to_corrected,
    resolve_legacy_f_code,
)
from semantic_proposal_eval_v1 import EvalCaseInput, evaluate_case, evaluate_corpus  # noqa: E402

_DATA = Path(__file__).resolve().parent.parent / "data"
_WILLOW = _DATA / "issue240" / "adjudication_corpus_willow_v1.json"
_FINAL = _DATA / "issue240" / "adjudication_corpus_final_viability_v1.json"


def test_legacy_f_code_labels_cover_known_codes() -> None:
    for code in ("F0", "F1", "F2", "F3", "F4", "F7"):
        assert code in LEGACY_F_CODE_LABELS


def test_willow_stored_legacy_replay_preserves_f7_counts() -> None:
    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    summary = legacy_f_code_counts_from_corpus(corpus, replay=False)
    assert summary["legacy_f_code_counts"] == {"F7": 14}
    assert summary["legacy_resolution_sources"]["stored"] == 14


def test_dorm_in_room_f7_maps_success_with_misflag() -> None:
    mapped, limits, misflag = map_legacy_f_code_to_corrected(
        "F7",
        ["honest_no_covered_change"],
        semantic_decision="no_covered_change",
        boundary_signals={"in_room_only": True, "info_boundary_only": True, "exec_depart": False},
        overlay_applied=True,
        has_proposals=False,
        profile_id="dorm_studio_single_space",
    )
    assert mapped == "success"
    assert misflag is True


def test_overlay_exec_depart_does_not_map_to_true_miss() -> None:
    mapped, limits, misflag = map_legacy_f_code_to_corrected(
        "F7",
        ["prose_implies_covered"],
        semantic_decision="no_covered_change",
        boundary_signals={"exec_depart": True, "exec_return": False},
        overlay_applied=True,
        has_proposals=False,
        profile_id="dorm_studio_single_space",
    )
    assert mapped == "ambiguous_threshold"
    assert misflag is False
    assert any("overlay" in x.lower() for x in limits)


def test_f2_covered_change_without_proposals_maps_true_miss() -> None:
    mapped, _, misflag = map_legacy_f_code_to_corrected(
        "F2",
        ["covered_change_without_proposals"],
        semantic_decision="covered_change",
        boundary_signals={},
        overlay_applied=True,
        has_proposals=False,
        profile_id="generic_net_state_v1",
    )
    assert mapped == "true_semantic_miss"
    assert misflag is False


def test_generic_profile_no_dorm_in_room_mapping() -> None:
    mapped, limits, misflag = map_legacy_f_code_to_corrected(
        "F7",
        [],
        semantic_decision="no_covered_change",
        boundary_signals={"in_room_only": True, "exec_depart": False},
        overlay_applied=False,
        has_proposals=False,
        profile_id="generic_net_state_v1",
    )
    assert mapped == "success"
    assert misflag is False
    assert not any("in-room" in x.lower() for x in limits)


def test_evaluate_case_nests_legacy_lane_secondary() -> None:
    inp = EvalCaseInput(
        case_id="synthetic_willow",
        scenario_id="audit_i225_willow_must_remain_v2_offstage_cycles",
        beats_text="crossed to my bunk. Bathroom's third door down.",
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        overlay_applied=True,
        profile_id="dorm_studio_single_space",
        profile_resolution="scenario_registry",
    )
    j = evaluate_case(
        inp,
        raw_case={
            "classifier_primary": "F7",
            "classifier_secondary": ["honest_no_covered_change"],
            "semantic_decision": "no_covered_change",
            "overlay_applied": True,
        },
    )
    assert j["corrected_category"] == "success"
    assert "legacy_lane" in j
    assert j["legacy_lane"]["legacy_f_code"] == "F7"
    assert j["legacy_lane"]["legacy_taxonomy_status"] in {"superseded", "compatible", "ambiguous"}
    assert j["legacy_classifier_misflag"] is True
    assert j["legacy_lane"]["legacy_f_code_label"] == LEGACY_F_CODE_LABELS["F7"]


def test_f1_mapping_ambiguous_scope() -> None:
    mapped, limits, _ = map_legacy_f_code_to_corrected(
        "F1",
        ["schema_syntax"],
        semantic_decision="",
        boundary_signals={},
        overlay_applied=False,
        has_proposals=False,
        profile_id="generic_net_state_v1",
    )
    assert mapped == "evaluator_defect"
    assert any("schema" in x.lower() for x in limits)


def test_classify_legacy_turn_replay_from_corpus_fields() -> None:
    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    case = corpus["cases"][0]
    f_code, _, source = resolve_legacy_f_code(case, replay=True)
    assert f_code in LEGACY_F_CODE_LABELS
    assert source in {"replayed", "stored", "stored_replay_mismatch"}


def test_evaluate_corpus_includes_legacy_counts_without_changing_corrected() -> None:
    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    report = evaluate_corpus(corpus)
    assert report["corrected_category_counts"]["success"] == 14
    assert report["legacy_f_code_counts"] == {"F7": 14}
    for j in report["judgments"]:
        assert "legacy_lane" in j
        assert j["legacy_lane"]["legacy_not_runtime_truth"] is True
