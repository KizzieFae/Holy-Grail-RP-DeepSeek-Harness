"""Issue #183 Character-prep span linkage attribution tests."""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from issue176_characterization_analyze import (  # noqa: E402
    graph_spans,
    linked_inference_by_prep,
    phase_id,
    span_id,
)

ORCHESTRATION_GRAPH_SCHEMA = "hg_orchestration_graph_v1"


def _prep_phase_span(prep_span_id: str, *, with_rollup: bool, linked_ids: list[str]) -> dict:
    return {
        "evidence_id": prep_span_id,
        "correlation": {
            "role": "execution_span",
            "span_id": prep_span_id,
            "phase_id": "character_prep_phase",
            "hg_round_id": "round-1",
            "character_turn_index": 0,
        },
        "decision": {
            "phase_id": "character_prep_phase",
            "orchestration_graph": {
                "schema": ORCHESTRATION_GRAPH_SCHEMA,
                "node_kind": "serial_phase",
                "graph_id": "graph-1",
                "character_turn_index": 0,
            },
        },
        "associations": {"evidence_ids": linked_ids if with_rollup else []},
        "execution": {"wall_ms": 5000},
    }


def _prep_inference_span(child_span_id: str, parent_span_id: str, evidence_id: str, *, with_graph: bool) -> dict:
    decision = {"phase_id": "character_prep_inference"}
    if with_graph:
        decision["orchestration_graph"] = {
            "schema": ORCHESTRATION_GRAPH_SCHEMA,
            "node_kind": "inference_reference",
            "graph_id": "graph-1",
            "character_turn_index": 0,
            "predecessor_span_ids": [parent_span_id],
        }
    return {
        "evidence_id": child_span_id,
        "correlation": {
            "role": "execution_span",
            "span_id": child_span_id,
            "parent_span_id": parent_span_id,
            "phase_id": "character_prep_inference",
            "hg_round_id": "round-1",
            "character_turn_index": 0,
        },
        "decision": decision,
        "associations": {"evidence_ids": [evidence_id]},
    }


def _layer_b_attempt(evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "request": {"schema": "hg_assembled_request_v1"},
        "correlation": {
            "hg_round_id": "round-1",
            "character_turn_index": 0,
            "inference_kind": "plot_cognition_epistemic_eval",
            "inference_id": "inf-character-0-layerb",
        },
        "inference_health": {
            "timing": {
                "timing_observed": True,
                "inference_wall_clock_ms": 2200,
            },
        },
    }


def _attribution_method(spans: list[dict], attempts: dict[str, dict], prep_span: dict) -> str:
    link_map = linked_inference_by_prep(spans, attempts)
    linked = list(link_map.get(span_id(prep_span) or "", []))
    return "span_linked" if linked else "inference_id_turn_key"


def test_repaired_prep_evidence_uses_span_linked_attribution():
    prep_span_id = "prep-span-1"
    layer_b_id = "layer-b-ev-1"
    child_span_id = "prep-inf-1"
    attempts = {
        layer_b_id: _layer_b_attempt(layer_b_id),
        prep_span_id: _prep_phase_span(prep_span_id, with_rollup=True, linked_ids=[layer_b_id]),
        child_span_id: _prep_inference_span(child_span_id, prep_span_id, layer_b_id, with_graph=True),
    }
    spans = graph_spans(attempts)
    prep_span = next(span for span in spans if phase_id(span) == "character_prep_phase")
    assert _attribution_method(spans, attempts, prep_span) == "span_linked"


def test_legacy_incomplete_prep_evidence_falls_back_to_inference_id_turn_key():
    prep_span_id = "prep-span-legacy"
    layer_b_id = "layer-b-ev-legacy"
    child_span_id = "prep-inf-legacy"
    attempts = {
        layer_b_id: _layer_b_attempt(layer_b_id),
        prep_span_id: _prep_phase_span(prep_span_id, with_rollup=False, linked_ids=[]),
        child_span_id: _prep_inference_span(child_span_id, prep_span_id, layer_b_id, with_graph=False),
    }
    spans = graph_spans(attempts)
    prep_span = next(span for span in spans if phase_id(span) == "character_prep_phase")
    assert _attribution_method(spans, attempts, prep_span) == "inference_id_turn_key"
