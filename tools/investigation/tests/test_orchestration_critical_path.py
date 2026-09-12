"""Unit tests for orchestration critical-path attribution (#173)."""

from orchestration_critical_path import (
    ATTRIBUTION_BOUNDED_PARTIAL,
    ATTRIBUTION_PROVEN,
    ATTRIBUTION_UNAVAILABLE,
    SCOPE_CHARACTER_TURN,
    SCOPE_POST_COMMIT,
    SCOPE_ROUND_INTERNAL,
    critical_path_attribution,
    player_visible_latency,
    reconstruct_attribution,
    round_internal_critical_path,
)


def test_player_latency_unavailable_without_operation_id():
    result = player_visible_latency({}, None)
    assert result["attribution_confidence"] == ATTRIBUTION_UNAVAILABLE
    assert result["attribution_scope"] == "player_visible_operation"


def test_bounded_partial_without_graph():
    attempts = {
        "a1": {
            "request": {"schema": "hg_assembled_request_v1"},
            "inference_health": {
                "timing": {
                    "timing_observed": True,
                    "inference_wall_clock_ms": 100,
                },
            },
        },
    }
    result = round_internal_critical_path(attempts)
    assert result["attribution_confidence"] == ATTRIBUTION_BOUNDED_PARTIAL
    assert result["attribution_scope"] == SCOPE_ROUND_INTERNAL


def _post_commit_fixture():
    return {
        "lane-a": {
            "correlation": {"role": "execution_span", "span_id": "lane-a", "hg_round_id": "r1"},
            "execution": {"wall_ms": 50},
            "decision": {
                "phase_id": "post_commit_lane_librarian",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "lane",
                    "graph_id": "g1",
                    "lane": "librarian",
                    "domain_commit_id": "c1",
                    "character_turn_index": 0,
                },
            },
            "associations": {"evidence_ids": []},
        },
        "lane-b": {
            "correlation": {"role": "execution_span", "span_id": "lane-b", "hg_round_id": "r1"},
            "execution": {"wall_ms": 80},
            "decision": {
                "phase_id": "post_commit_lane_narrator",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "lane",
                    "graph_id": "g1",
                    "lane": "narrator",
                    "domain_commit_id": "c1",
                    "character_turn_index": 0,
                },
            },
            "associations": {"evidence_ids": []},
        },
        "group": {
            "correlation": {"role": "execution_span", "span_id": "group", "hg_round_id": "r1"},
            "execution": {"wall_ms": 90},
            "decision": {
                "phase_id": "post_commit_parallel_group",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "parallel_group",
                    "graph_id": "g1",
                    "domain_commit_id": "c1",
                    "character_turn_index": 0,
                },
            },
        },
        "join": {
            "correlation": {"role": "execution_span", "span_id": "join", "hg_round_id": "r1"},
            "execution": {"wall_ms": 10},
            "decision": {
                "phase_id": "post_commit_join_narrator",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "join_barrier",
                    "graph_id": "g1",
                    "barrier_index": 1,
                    "domain_commit_id": "c1",
                    "character_turn_index": 0,
                },
            },
        },
    }


def test_proven_post_commit_scope_only():
    attempts = _post_commit_fixture()
    result = critical_path_attribution(
        attempts,
        attribution_scope=SCOPE_POST_COMMIT,
        hg_round_id="r1",
        domain_commit_id="c1",
    )
    assert result["attribution_confidence"] == ATTRIBUTION_PROVEN
    assert result["attribution_scope"] == SCOPE_POST_COMMIT
    assert result["ms"] == 90


def test_post_commit_only_not_proven_for_character_turn():
    attempts = _post_commit_fixture()
    result = critical_path_attribution(
        attempts,
        attribution_scope=SCOPE_CHARACTER_TURN,
        hg_round_id="r1",
        domain_commit_id="c1",
        character_turn_index=0,
    )
    assert result["attribution_confidence"] == ATTRIBUTION_BOUNDED_PARTIAL
    assert result["attribution_scope"] == SCOPE_CHARACTER_TURN


def test_proven_character_turn_with_serial_graph():
    attempts = {
        **_post_commit_fixture(),
        "turn": {
            "correlation": {
                "role": "execution_span",
                "span_id": "turn",
                "hg_round_id": "r1",
                "parent_span_id": None,
            },
            "execution": {"wall_ms": 200},
            "decision": {
                "phase_id": "character_turn_serial",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "serial_phase",
                    "graph_id": "turn-g1",
                    "character_turn_index": 0,
                    "predecessor_span_ids": [],
                },
            },
        },
        "director": {
            "correlation": {
                "role": "execution_span",
                "span_id": "director",
                "hg_round_id": "r1",
                "parent_span_id": "turn",
            },
            "execution": {"wall_ms": 40},
            "decision": {
                "phase_id": "director_phase",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "serial_phase",
                    "graph_id": "turn-g1",
                    "character_turn_index": 0,
                    "predecessor_span_ids": ["turn"],
                },
            },
            "associations": {"evidence_ids": ["dir-ev"]},
        },
        "prep": {
            "correlation": {
                "role": "execution_span",
                "span_id": "prep",
                "hg_round_id": "r1",
                "parent_span_id": "turn",
            },
            "execution": {"wall_ms": 60},
            "decision": {
                "phase_id": "character_prep_phase",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "serial_phase",
                    "graph_id": "turn-g1",
                    "character_turn_index": 0,
                    "predecessor_span_ids": ["director"],
                },
            },
            "associations": {"evidence_ids": ["char-ev"]},
        },
        "commit": {
            "correlation": {
                "role": "execution_span",
                "span_id": "commit",
                "hg_round_id": "r1",
                "parent_span_id": "turn",
            },
            "execution": {"wall_ms": 5},
            "decision": {
                "phase_id": "domain_commit_boundary",
                "orchestration_graph": {
                    "schema": "hg_orchestration_graph_v1",
                    "node_kind": "serial_phase",
                    "graph_id": "turn-g1",
                    "domain_commit_id": "c1",
                    "character_turn_index": 0,
                    "predecessor_span_ids": ["prep"],
                },
            },
        },
        "dir-ev": {
            "request": {"schema": "hg_assembled_request_v1"},
            "inference_health": {"timing": {"timing_observed": True, "inference_wall_clock_ms": 35}},
        },
        "char-ev": {
            "request": {"schema": "hg_assembled_request_v1"},
            "inference_health": {"timing": {"timing_observed": True, "inference_wall_clock_ms": 55}},
        },
    }
    attempts["group"]["correlation"]["parent_span_id"] = "turn"
    attempts["group"]["decision"]["orchestration_graph"]["predecessor_span_ids"] = ["commit"]

    result = critical_path_attribution(
        attempts,
        attribution_scope=SCOPE_CHARACTER_TURN,
        hg_round_id="r1",
        domain_commit_id="c1",
        character_turn_index=0,
    )
    assert result["attribution_confidence"] == ATTRIBUTION_PROVEN
    assert result["attribution_scope"] == SCOPE_CHARACTER_TURN
    assert result["ms"] >= 90


def test_reconstruct_attribution_exposes_scopes():
    attempts = _post_commit_fixture()
    payload = reconstruct_attribution(attempts, hg_round_id="r1", domain_commit_id="c1")
    assert payload["post_commit_section"]["attribution_confidence"] == ATTRIBUTION_PROVEN
    assert payload["character_turn_critical_path"]["attribution_confidence"] == ATTRIBUTION_BOUNDED_PARTIAL
