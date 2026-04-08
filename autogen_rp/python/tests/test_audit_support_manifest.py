"""Tests for audit-side support manifests (GitHub #28)."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_support_manifest import (
    SUPPORT_MANIFEST_SCHEMA_VERSION,
    build_support_manifest,
    diff_support_manifests,
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


def test_identical_inputs_identical_manifests() -> None:
    audit = _minimal_prompt_layer_audit(
        selected_summary_block_ids=["b", "a"],
        retrieval_summary={
            "retrieved_block_present": True,
            "retrieved_item_count": 1,
            "retrieved_char_count": 10,
            "retrieved_source_refs": ["doc/x#1"],
        },
    )
    m1 = build_support_manifest(audit, "hello")
    m2 = build_support_manifest(dict(audit), "hello")
    assert m1 == m2
    assert m1["schema_version"] == SUPPORT_MANIFEST_SCHEMA_VERSION


def test_summary_id_list_ordering_does_not_affect_manifest() -> None:
    audit1 = _minimal_prompt_layer_audit(selected_summary_block_ids=["z", "a", "m"])
    audit2 = _minimal_prompt_layer_audit(selected_summary_block_ids=["a", "m", "z"])
    assert build_support_manifest(audit1, "p") == build_support_manifest(audit2, "p")


def test_units_sorted_by_type_then_id() -> None:
    audit = _minimal_prompt_layer_audit(
        selected_summary_block_ids=["x"],
        excluded_summary_block_ids=["y"],
        scene_binding_constraints_section="B",
    )
    m = build_support_manifest(audit, "z")
    types_ids = [(u["type"], u["id"]) for u in m["units"]]
    assert types_ids == sorted(types_ids, key=lambda x: (x[0], x[1]))


def test_missing_fields_deterministic() -> None:
    m = build_support_manifest({}, "")
    assert m["schema_version"] == SUPPORT_MANIFEST_SCHEMA_VERSION
    types = {u["type"] for u in m["units"]}
    # Always: aggregate, binding (possibly empty text), envelope; never orphan types
    assert types == {
        "retrieval_aggregate",
        "binding_constraints_section",
        "prompt_envelope",
    }
    assert len(m["units"]) == 3
    # No summary/ref units when lists missing
    assert not any(u["type"] == "summary_block_selected" for u in m["units"])
    assert not any(u["type"] == "retrieval_source_ref" for u in m["units"])
    bind = next(u for u in m["units"] if u["type"] == "binding_constraints_section")
    assert bind["id"] == "bind:v1"


def test_non_list_summary_and_retrieval_skipped_safely() -> None:
    audit = _minimal_prompt_layer_audit(
        selected_summary_block_ids="not-a-list",  # type: ignore[arg-type]
        retrieval_summary="bad",  # type: ignore[arg-type]
    )
    m = build_support_manifest(audit, "x")
    assert not any(u["type"] == "summary_block_selected" for u in m["units"])
    agg = next(u for u in m["units"] if u["type"] == "retrieval_aggregate")
    assert agg["id"] == "retr:agg:v1"


def test_retrieval_ref_position_matters() -> None:
    a1 = _minimal_prompt_layer_audit(
        retrieval_summary={
            "retrieved_block_present": True,
            "retrieved_item_count": 2,
            "retrieved_char_count": 4,
            "retrieved_source_refs": ["same", "same"],
        }
    )
    a2 = _minimal_prompt_layer_audit(
        retrieval_summary={
            "retrieved_block_present": True,
            "retrieved_item_count": 2,
            "retrieved_char_count": 4,
            "retrieved_source_refs": ["same", "same"],
        }
    )
    assert build_support_manifest(a1, "") == build_support_manifest(a2, "")

    a3 = _minimal_prompt_layer_audit(
        retrieval_summary={
            "retrieved_block_present": True,
            "retrieved_item_count": 2,
            "retrieved_char_count": 4,
            "retrieved_source_refs": ["b", "a"],
        }
    )
    a4 = _minimal_prompt_layer_audit(
        retrieval_summary={
            "retrieved_block_present": True,
            "retrieved_item_count": 2,
            "retrieved_char_count": 4,
            "retrieved_source_refs": ["a", "b"],
        }
    )
    assert build_support_manifest(a3, "") != build_support_manifest(a4, "")


def test_diff_support_manifests() -> None:
    prev = build_support_manifest(
        _minimal_prompt_layer_audit(selected_summary_block_ids=["keep", "gone"]),
        "p1",
    )
    curr = build_support_manifest(
        _minimal_prompt_layer_audit(selected_summary_block_ids=["keep", "new"]),
        "p2",
    )
    d = diff_support_manifests(prev, curr)
    absent_ids = {(x["type"], x["id"]) for x in d["support_absent"]}
    new_ids = {(x["type"], x["id"]) for x in d["support_new"]}
    assert ("summary_block_selected", "summary:sel:gone") in absent_ids
    assert ("summary_block_selected", "summary:sel:new") in new_ids
    assert any(
        x["type"] == "prompt_envelope" for x in d["support_changed"]
    ), "prompt text changed"


def test_diff_empty_previous() -> None:
    curr = build_support_manifest(_minimal_prompt_layer_audit(), "")
    d = diff_support_manifests(None, curr)
    assert d["support_absent"] == []
    assert len(d["support_new"]) >= 1
