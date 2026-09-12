"""Derive round-internal critical path and Player-visible latency from execution evidence (#173)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

ATTRIBUTION_PROVEN = "proven"
ATTRIBUTION_BOUNDED_PARTIAL = "bounded_partial"
ATTRIBUTION_UNAVAILABLE = "unavailable"

SCOPE_POST_COMMIT = "post_commit_section"
SCOPE_CHARACTER_TURN = "character_turn"
SCOPE_ROUND_INTERNAL = "round_internal"
SCOPE_PLAYER_VISIBLE = "player_visible_operation"

LIFECYCLE_ROLE = "application_lifecycle"
SPAN_ROLE = "execution_span"
ORCHESTRATION_GRAPH_SCHEMA = "hg_orchestration_graph_v1"

REQUIRED_CHARACTER_TURN_PHASES = (
    "director_phase",
    "character_prep_phase",
    "domain_commit_boundary",
    "post_commit_parallel_group",
)
REQUIRED_ROUND_PHASES = ("round_internal_serial",)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _attempt_timing_ms(attempt: dict[str, Any]) -> int | None:
    timing = (attempt.get("inference_health") or {}).get("timing") or {}
    if timing.get("timing_observed") is not True:
        return None
    wall = timing.get("inference_wall_clock_ms")
    return int(wall) if isinstance(wall, (int, float)) and wall >= 0 else None


def _span_wall_ms(span: dict[str, Any]) -> int | None:
    execution = span.get("execution") or {}
    wall = execution.get("wall_ms")
    return int(wall) if isinstance(wall, (int, float)) and wall >= 0 else None


def _orchestration_graph(span: dict[str, Any]) -> dict[str, Any] | None:
    graph = (span.get("decision") or {}).get("orchestration_graph")
    if not isinstance(graph, dict):
        return None
    if graph.get("schema") != ORCHESTRATION_GRAPH_SCHEMA:
        return None
    return graph


def _span_id(span: dict[str, Any]) -> str | None:
    corr = span.get("correlation") or {}
    return corr.get("span_id") or span.get("evidence_id")


def _phase_id(span: dict[str, Any]) -> str | None:
    corr = span.get("correlation") or {}
    return corr.get("phase_id") or (span.get("decision") or {}).get("phase_id")


def _parent_span_id(span: dict[str, Any]) -> str | None:
    corr = span.get("correlation") or {}
    return corr.get("parent_span_id") or (span.get("decision") or {}).get("parent_span_id")


def _graph_spans(
    attempts: dict[str, dict[str, Any]],
    *,
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    character_turn_index: int | None = None,
) -> list[dict[str, Any]]:
    spans = [
        att for att in attempts.values()
        if (att.get("correlation") or {}).get("role") == SPAN_ROLE and _orchestration_graph(att)
    ]
    if hg_round_id:
        spans = [
            s for s in spans
            if str((s.get("correlation") or {}).get("hg_round_id") or "") == str(hg_round_id)
        ]
    if domain_commit_id:
        spans = [
            s for s in spans
            if _orchestration_graph(s).get("domain_commit_id") == domain_commit_id
            or _phase_id(s) in REQUIRED_CHARACTER_TURN_PHASES
            or _phase_id(s) in ("director_phase", "character_prep_phase", "character_turn_serial")
        ]
    if character_turn_index is not None:
        spans = [
            s for s in spans
            if _orchestration_graph(s).get("character_turn_index") == character_turn_index
            or _phase_id(s) in REQUIRED_ROUND_PHASES
            or _phase_id(s) in ("round_preamble_serial", "storyteller_round_cognition", "plot_cognition_resume")
        ]
    return spans


def _children_by_parent(spans: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_id = {_span_id(s): s for s in spans if _span_id(s)}
    children: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        parent_id = _parent_span_id(span)
        if parent_id and parent_id in by_id:
            children.setdefault(parent_id, []).append(span)
    return children


def _linked_inference_ms(span: dict[str, Any], attempts: dict[str, dict[str, Any]]) -> int:
    evidence_ids = (span.get("associations") or {}).get("evidence_ids") or []
    inference_ms = 0
    for eid in evidence_ids:
        att = attempts.get(eid)
        if not att or not att.get("request"):
            continue
        t = _attempt_timing_ms(att)
        if t is not None:
            inference_ms = max(inference_ms, t)
    return inference_ms


def _serial_leaf_cost(span: dict[str, Any], attempts: dict[str, dict[str, Any]]) -> int:
    span_ms = _span_wall_ms(span) or 0
    infer_ms = _linked_inference_ms(span, attempts)
    if infer_ms > 0 and span_ms > 0:
        return max(span_ms, infer_ms)
    return span_ms or infer_ms


def _lane_duration_ms(lane_span: dict[str, Any], attempts: dict[str, dict[str, Any]]) -> int:
    return _serial_leaf_cost(lane_span, attempts)


def _post_commit_parallel_cost(
    spans: list[dict[str, Any]],
    attempts: dict[str, dict[str, Any]],
) -> tuple[int | None, str | None]:
    groups = [s for s in spans if _orchestration_graph(s).get("node_kind") == "parallel_group"]
    lanes = [s for s in spans if _orchestration_graph(s).get("node_kind") == "lane"]
    joins = [s for s in spans if _orchestration_graph(s).get("node_kind") == "join_barrier"]
    if not groups or not lanes or len(joins) < 1:
        return None, "incomplete_post_commit_graph"
    join_cost = sum(_span_wall_ms(join) or 0 for join in joins)
    max_lane = max(_lane_duration_ms(lane, attempts) for lane in lanes) if lanes else 0
    return max_lane + join_cost, None


def _successors(predecessor_map: dict[str, list[str]], span_ids: set[str]) -> dict[str, list[str]]:
    successors: dict[str, list[str]] = {sid: [] for sid in span_ids}
    for succ, preds in predecessor_map.items():
        for pred in preds:
            if pred in span_ids:
                successors.setdefault(pred, []).append(succ)
    return successors


def _ordered_serial_chain(span_ids: set[str], predecessor_map: dict[str, list[str]]) -> list[str]:
    if not span_ids:
        return []
    successors = _successors(predecessor_map, span_ids)
    roots = [sid for sid in span_ids if not any(p in span_ids for p in predecessor_map.get(sid, []))]
    if not roots:
        roots = sorted(span_ids)
    ordered: list[str] = []
    visited: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        if current in visited or current not in span_ids:
            continue
        visited.add(current)
        ordered.append(current)
        for succ in successors.get(current, []):
            if succ not in visited:
                queue.append(succ)
    for sid in sorted(span_ids):
        if sid not in visited:
            ordered.append(sid)
    return ordered


def _node_cost_ms(
    span: dict[str, Any],
    attempts: dict[str, dict[str, Any]],
    children_by_parent: dict[str, list[dict[str, Any]]],
    span_by_id: dict[str, dict[str, Any]],
) -> int:
    graph = _orchestration_graph(span)
    if not graph:
        return _serial_leaf_cost(span, attempts)
    kind = graph.get("node_kind")
    span_id = _span_id(span)
    children = children_by_parent.get(span_id or "", [])
    graph_children = [c for c in children if _orchestration_graph(c)]

    if kind == "parallel_group":
        cost, _ = _post_commit_parallel_cost([span, *graph_children], attempts)
        return cost or 0
    if kind == "serial_phase" and graph_children:
        predecessor_map = {
            _span_id(c) or "": (_orchestration_graph(c) or {}).get("predecessor_span_ids") or []
            for c in graph_children
        }
        child_ids = {_span_id(c) for c in graph_children if _span_id(c)}
        chain = _ordered_serial_chain(child_ids, predecessor_map)
        return sum(
            _node_cost_ms(span_by_id[cid], attempts, children_by_parent, span_by_id)
            for cid in chain
            if cid in span_by_id
        )
    if kind in ("lane", "join_barrier"):
        return _lane_duration_ms(span, attempts)
    return _serial_leaf_cost(span, attempts)


def _has_phases(spans: list[dict[str, Any]], required: tuple[str, ...]) -> bool:
    present = {_phase_id(s) for s in spans}
    return all(phase in present for phase in required)


def _character_turn_spans(
    spans: list[dict[str, Any]],
    *,
    domain_commit_id: str | None,
    character_turn_index: int | None,
) -> list[dict[str, Any]]:
    turn_spans = [
        s for s in spans
        if _phase_id(s) == "character_turn_serial"
        or (
            domain_commit_id
            and _orchestration_graph(s).get("domain_commit_id") == domain_commit_id
        )
        or (
            character_turn_index is not None
            and _orchestration_graph(s).get("character_turn_index") == character_turn_index
        )
    ]
    if not turn_spans and character_turn_index is not None:
        turn_spans = [
            s for s in spans
            if _orchestration_graph(s).get("character_turn_index") == character_turn_index
        ]
    return turn_spans


def critical_path_attribution(
    attempts: dict[str, dict[str, Any]],
    *,
    attribution_scope: str,
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    character_turn_index: int | None = None,
) -> dict[str, Any]:
    spans = _graph_spans(
        attempts,
        hg_round_id=hg_round_id,
        domain_commit_id=domain_commit_id,
        character_turn_index=character_turn_index,
    )

    if attribution_scope == SCOPE_POST_COMMIT:
        scoped = [
            s for s in spans
            if _orchestration_graph(s).get("node_kind") in ("parallel_group", "lane", "join_barrier")
            and (not domain_commit_id or _orchestration_graph(s).get("domain_commit_id") == domain_commit_id)
        ]
        if not scoped:
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                "attribution_scope": attribution_scope,
                "reason": "incomplete_post_commit_graph",
            }
        total_ms, reason = _post_commit_parallel_cost(scoped, attempts)
        if total_ms is None:
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                "attribution_scope": attribution_scope,
                "reason": reason,
            }
        return {
            "ms": total_ms,
            "attribution_confidence": ATTRIBUTION_PROVEN,
            "attribution_scope": attribution_scope,
            "method": "parallel_max_lane_plus_join_barriers",
        }

    if attribution_scope == SCOPE_CHARACTER_TURN:
        scoped = _character_turn_spans(
            spans,
            domain_commit_id=domain_commit_id,
            character_turn_index=character_turn_index,
        )
        if not _has_phases(scoped, REQUIRED_CHARACTER_TURN_PHASES):
            post_only, _ = _post_commit_parallel_cost(scoped, attempts)
            if post_only is not None and not _has_phases(scoped, ("director_phase", "character_prep_phase")):
                return {
                    "ms": post_only,
                    "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                    "attribution_scope": attribution_scope,
                    "reason": "pre_commit_serial_graph_missing",
                }
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                "attribution_scope": attribution_scope,
                "reason": "incomplete_character_turn_graph",
            }
        turn_roots = [s for s in scoped if _phase_id(s) == "character_turn_serial"]
        if not turn_roots:
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                "attribution_scope": attribution_scope,
                "reason": "missing_character_turn_serial_root",
            }
        span_by_id = {_span_id(s): s for s in scoped if _span_id(s)}
        children_by_parent = _children_by_parent(scoped)
        total = sum(
            _node_cost_ms(root, attempts, children_by_parent, span_by_id)
            for root in turn_roots
        )
        return {
            "ms": total,
            "attribution_confidence": ATTRIBUTION_PROVEN,
            "attribution_scope": attribution_scope,
            "method": "serial_turn_graph_plus_post_commit_parallel",
            "character_turn_index": character_turn_index,
            "domain_commit_id": domain_commit_id,
        }

    if attribution_scope == SCOPE_ROUND_INTERNAL:
        if not _has_phases(spans, REQUIRED_ROUND_PHASES):
            inference_timed = [
                _attempt_timing_ms(att) for att in attempts.values() if att.get("request")
            ]
            if any(ms is not None for ms in inference_timed):
                return {
                    "ms": None,
                    "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                    "attribution_scope": attribution_scope,
                    "reason": "per_attempt_timing_without_round_graph",
                    "inference_attempts_with_timing": sum(1 for ms in inference_timed if ms is not None),
                }
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_UNAVAILABLE,
                "attribution_scope": attribution_scope,
                "reason": "no_timing_or_graph_evidence",
            }

        round_roots = [s for s in spans if _phase_id(s) == "round_internal_serial"]
        turn_serials = [s for s in spans if _phase_id(s) == "character_turn_serial"]
        if not turn_serials:
            return {
                "ms": None,
                "attribution_confidence": ATTRIBUTION_BOUNDED_PARTIAL,
                "attribution_scope": attribution_scope,
                "reason": "incomplete_round_graph_no_character_turns",
            }

        span_by_id = {_span_id(s): s for s in spans if _span_id(s)}
        children_by_parent = _children_by_parent(spans)
        total = 0
        for root in round_roots:
            total += _node_cost_ms(root, attempts, children_by_parent, span_by_id)
        return {
            "ms": total,
            "attribution_confidence": ATTRIBUTION_PROVEN,
            "attribution_scope": attribution_scope,
            "method": "round_serial_graph_with_turn_chaining",
            "character_turn_count": len(turn_serials),
        }

    return {
        "ms": None,
        "attribution_confidence": ATTRIBUTION_UNAVAILABLE,
        "attribution_scope": attribution_scope,
        "reason": "unknown_attribution_scope",
    }


def round_internal_critical_path(
    attempts: dict[str, dict[str, Any]],
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    character_turn_index: int | None = None,
) -> dict[str, Any]:
    if domain_commit_id or character_turn_index is not None:
        return critical_path_attribution(
            attempts,
            attribution_scope=SCOPE_CHARACTER_TURN,
            hg_round_id=hg_round_id,
            domain_commit_id=domain_commit_id,
            character_turn_index=character_turn_index,
        )
    return critical_path_attribution(
        attempts,
        attribution_scope=SCOPE_ROUND_INTERNAL,
        hg_round_id=hg_round_id,
    )


def player_visible_latency(attempts: dict[str, dict[str, Any]], operation_id: str | None) -> dict[str, Any]:
    if not operation_id:
        return {
            "ms": None,
            "attribution_confidence": ATTRIBUTION_UNAVAILABLE,
            "attribution_scope": SCOPE_PLAYER_VISIBLE,
            "reason": "no_application_operation_id",
        }
    milestones: dict[str, dict[str, Any]] = {}
    for att in attempts.values():
        corr = att.get("correlation") or {}
        if corr.get("role") != LIFECYCLE_ROLE:
            continue
        if str(corr.get("operation_id") or "") != str(operation_id):
            continue
        milestone = corr.get("milestone") or (att.get("decision") or {}).get("milestone")
        if milestone:
            milestones[str(milestone)] = att
    began = milestones.get("operation_began")
    terminal = milestones.get("round_terminal_succeeded") or milestones.get("round_terminal_failed")
    if not began or not terminal:
        return {
            "ms": None,
            "attribution_confidence": ATTRIBUTION_UNAVAILABLE,
            "attribution_scope": SCOPE_PLAYER_VISIBLE,
            "reason": "incomplete_application_lifecycle",
        }
    start = _parse_iso(began.get("recorded_at"))
    end = _parse_iso(terminal.get("recorded_at"))
    if not start or not end:
        return {
            "ms": None,
            "attribution_confidence": ATTRIBUTION_UNAVAILABLE,
            "attribution_scope": SCOPE_PLAYER_VISIBLE,
            "reason": "lifecycle_timestamp_missing",
        }
    return {
        "ms": int((end - start).total_seconds() * 1000),
        "attribution_confidence": ATTRIBUTION_PROVEN,
        "attribution_scope": SCOPE_PLAYER_VISIBLE,
        "operation_id": operation_id,
    }


def reconstruct_attribution(
    attempts: dict[str, dict[str, Any]],
    *,
    operation_id: str | None = None,
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    character_turn_index: int | None = None,
) -> dict[str, Any]:
    return {
        "round_internal_critical_path": round_internal_critical_path(
            attempts,
            hg_round_id=hg_round_id,
            domain_commit_id=domain_commit_id,
            character_turn_index=character_turn_index,
        ),
        "post_commit_section": critical_path_attribution(
            attempts,
            attribution_scope=SCOPE_POST_COMMIT,
            hg_round_id=hg_round_id,
            domain_commit_id=domain_commit_id,
            character_turn_index=character_turn_index,
        ),
        "character_turn_critical_path": critical_path_attribution(
            attempts,
            attribution_scope=SCOPE_CHARACTER_TURN,
            hg_round_id=hg_round_id,
            domain_commit_id=domain_commit_id,
            character_turn_index=character_turn_index if character_turn_index is not None else 0,
        ) if domain_commit_id or character_turn_index is not None else None,
        "player_visible_latency": player_visible_latency(attempts, operation_id),
    }
