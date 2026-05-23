"""Tests for Issue #243-B semantic_proposal_eval_v1."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from semantic_eval_boundary_signals import dorm_studio_boundary_signals  # noqa: E402
from semantic_proposal_eval_v1 import (  # noqa: E402
    CORRECTED_CATEGORIES,
    EvalCaseInput,
    corpus_case_to_eval_input,
    evaluate_case,
    evaluate_corpus,
    model_alignment_success,
)
from semantic_eval_profiles import load_profile_registry, resolve_evaluation_profile  # noqa: E402

_DATA = Path(__file__).resolve().parent.parent / "data"
_WILLOW = _DATA / "issue240" / "adjudication_corpus_willow_v1.json"
_FINAL = _DATA / "issue240" / "adjudication_corpus_final_viability_v1.json"


def test_dorm_in_room_not_exec_depart() -> None:
    beats = "crossed to my bunk and sat down on the edge with a sketchbook"
    signals = dorm_studio_boundary_signals(beats)
    assert signals["in_room_only"] is True
    assert signals["exec_depart"] is False


def test_generic_profile_does_not_use_in_room_semantics() -> None:
    inp = EvalCaseInput(
        case_id="synthetic",
        scenario_id="cert_i234_proposal_accept_off_focal",
        beats_text="crossed to my bunk and sat on the couch",
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        profile_id="generic_net_state_v1",
        profile_resolution="default",
    )
    j = evaluate_case(inp)
    assert j["profile_id"] == "generic_net_state_v1"
    assert "no dorm/studio ontology" in " ".join(j["limitations"]).lower()


def test_dorm_in_room_success_not_true_miss() -> None:
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
        raw_case={"classifier_primary": "F7", "classifier_secondary": ["honest_no_covered_change"]},
    )
    assert j["corrected_category"] == "success"
    assert j["legacy_classifier_misflag"] is True
    assert j["legacy_lane"]["legacy_f_code"] == "F7"


def test_ambiguity_preserved_generic_exec_depart() -> None:
    inp = EvalCaseInput(
        case_id="synthetic_ambig",
        scenario_id="cert_i234_proposal_accept_off_focal",
        beats_text="walked through the open doorway into the hall and kept going",
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        overlay_applied=False,
        profile_id="generic_net_state_v1",
        profile_resolution="default",
    )
    j = evaluate_case(inp)
    assert j["corrected_category"] == "ambiguous_threshold"


def test_multi_room_stub_emits_limitations() -> None:
    inp = EvalCaseInput(
        case_id="stub",
        scenario_id="audit_i214_offstage_continuity_tier_b",
        beats_text="left the room",
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        profile_id="multi_room_excursion_v1",
        profile_resolution="manifest",
    )
    j = evaluate_case(inp)
    assert j["corrected_category"] == "ambiguous_threshold"
    assert any("stub" in x.lower() for x in j["limitations"])


def test_willow_corpus_eval_all_success() -> None:
    import json

    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    report = evaluate_corpus(corpus)
    counts = report["corrected_category_counts"]
    assert counts.get("success") == 14
    assert counts.get("true_semantic_miss", 0) == 0
    assert counts.get("ambiguous_threshold", 0) == 0


def test_final_viability_human_alignment() -> None:
    import json

    corpus = json.loads(_FINAL.read_text(encoding="utf-8"))
    report = evaluate_corpus(corpus)
    for j in report["judgments"]:
        assert model_alignment_success(j)
    assert report["corrected_category_counts"]["success"] == 10


def test_profile_resolution_manifest_over_registry() -> None:
    reg = load_profile_registry()
    pid, src = resolve_evaluation_profile(
        "audit_i225_willow_must_remain_v2_offstage_cycles",
        manifest_profile="generic_net_state_v1",
        registry=reg,
    )
    assert pid == "generic_net_state_v1"
    assert src == "manifest"


def test_corpus_case_to_eval_input_willow_profile() -> None:
    import json

    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    case = corpus["cases"][0]
    inp = corpus_case_to_eval_input(case)
    assert inp.profile_id == "dorm_studio_single_space"


def test_corrected_categories_closed_set() -> None:
    assert "ambiguous_threshold" in CORRECTED_CATEGORIES
    assert "evaluator_defect" in CORRECTED_CATEGORIES


def test_boundary_adjacent_choreography_ambiguous_not_success() -> None:
    beats = "walked past her through the open doorway into the hall and kept going"
    inp = EvalCaseInput(
        case_id="probe_boundary_adjacent",
        scenario_id="emotional_loop_2char",
        beats_text=beats,
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        overlay_applied=True,
        profile_id="dorm_studio_single_space",
        profile_resolution="scenario_registry",
    )
    j = evaluate_case(inp)
    assert j["corrected_category"] == "ambiguous_threshold"
    assert j["corrected_category"] != "true_semantic_miss"
    assert any("boundary_adjacent" in x for x in j["limitations"])


def test_willow_in_room_still_success_after_choreography_tuning() -> None:
    import json

    corpus = json.loads(_WILLOW.read_text(encoding="utf-8"))
    report = evaluate_corpus(corpus)
    assert report["corrected_category_counts"]["success"] == 14
    assert report["corrected_category_counts"].get("ambiguous_threshold", 0) == 0


def test_final_viability_no_anchor_preserves_ambiguity() -> None:
    import json

    corpus = json.loads(_FINAL.read_text(encoding="utf-8"))
    ambiguous_ids = {
        "848_t3_celina_baseline",
        "855_t3_ayame",
        "856_t3_celina",
        "856_t6_ayame",
        "856_t4_ayame",
        "856_t10_ayame",
        "856_t12_ayame",
        "857_t6_ayame",
        "857_t8_ayame",
    }
    for raw in corpus["cases"]:
        if raw["case_id"] not in ambiguous_ids:
            continue
        inp = EvalCaseInput(
            case_id="synthetic_no_anchor",
            scenario_id=str(raw["scenario_id"]),
            beats_text=str(raw.get("beats_text") or ""),
            semantic_decision=str(raw.get("semantic_decision") or ""),
            proposals_emitted=[],
            overlay_applied=bool(raw.get("overlay_applied")),
            profile_id="dorm_studio_single_space"
            if "emotional_loop" in str(raw.get("scenario_id"))
            else "generic_net_state_v1",
            profile_resolution="scenario_registry",
        )
        j = evaluate_case(inp, raw_case=raw)
        assert j["corrected_category"] == "ambiguous_threshold", raw["case_id"]
        assert j["corrected_category"] != "true_semantic_miss"


def test_generic_profile_unchanged_on_exec_depart() -> None:
    inp = EvalCaseInput(
        case_id="generic_ambig",
        scenario_id="cert_i234_proposal_accept_off_focal",
        beats_text="walked through the open doorway into the hall and kept going",
        semantic_decision="no_covered_change",
        proposals_emitted=[],
        overlay_applied=False,
        profile_id="generic_net_state_v1",
        profile_resolution="default",
    )
    j = evaluate_case(inp)
    assert j["corrected_category"] == "ambiguous_threshold"
