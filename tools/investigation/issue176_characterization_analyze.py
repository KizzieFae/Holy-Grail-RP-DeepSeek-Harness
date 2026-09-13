#!/usr/bin/env python3
"""Analyze Issue #176 characterization campaign execution evidence."""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestration_critical_path import (  # noqa: E402
    ATTRIBUTION_PROVEN,
    critical_path_attribution,
    player_visible_latency,
)


def load_session(evidence_root: Path, session_id: str) -> tuple[dict, dict[str, dict]]:
    base = evidence_root / session_id
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    attempts: dict[str, dict] = {}
    for eid in index.get("attempt_ids", []):
        p = base / "attempts" / f"{eid}.json"
        if p.exists():
            attempts[eid] = json.loads(p.read_text(encoding="utf-8"))
    return index, attempts


def attempt_wall(att: dict) -> int | None:
    timing = (att.get("inference_health") or {}).get("timing") or {}
    if timing.get("timing_observed") is not True:
        return None
    wall = timing.get("inference_wall_clock_ms")
    return int(wall) if isinstance(wall, (int, float)) and wall >= 0 else None


def inference_kind(att: dict) -> str | None:
    return (att.get("correlation") or {}).get("inference_kind")


def graph_spans(attempts: dict[str, dict]) -> list[dict]:
    out = []
    for att in attempts.values():
        corr = att.get("correlation") or {}
        if corr.get("role") != "execution_span":
            continue
        graph = (att.get("decision") or {}).get("orchestration_graph")
        if isinstance(graph, dict) and graph.get("schema") == "hg_orchestration_graph_v1":
            out.append(att)
    return out


def phase_id(span: dict) -> str | None:
    corr = span.get("correlation") or {}
    return corr.get("phase_id") or (span.get("decision") or {}).get("phase_id")


def turn_index(span: dict) -> int | None:
    corr = span.get("correlation") or {}
    if corr.get("character_turn_index") is not None:
        return int(corr["character_turn_index"])
    graph = (span.get("decision") or {}).get("orchestration_graph") or {}
    idx = graph.get("character_turn_index")
    return int(idx) if idx is not None else None


def span_id(span: dict) -> str | None:
    corr = span.get("correlation") or {}
    return corr.get("span_id") or span.get("evidence_id")


def linked_evidence_ids(span: dict) -> list[str]:
    ids = list((span.get("associations") or {}).get("evidence_ids") or [])
    ids.extend((span.get("execution") or {}).get("evidence_ids") or [])
    return list(dict.fromkeys(ids))


def round_id(span: dict) -> str | None:
    return (span.get("correlation") or {}).get("hg_round_id")


_INFERENCE_TURN_RE = re.compile(r"inf-character-(\d+)-")


def inference_turn_key(att: dict) -> tuple[str | None, int | None]:
    corr = att.get("correlation") or {}
    rid = corr.get("hg_round_id")
    if corr.get("character_turn_index") is not None:
        return rid, int(corr["character_turn_index"])
    inf = corr.get("inference_id") or ""
    match = _INFERENCE_TURN_RE.search(inf)
    if match:
        return rid, int(match.group(1))
    return rid, None


def collect_inference_by_turn(attempts: dict[str, dict]) -> dict[tuple[str | None, int], list[str]]:
    out: dict[tuple[str | None, int], list[str]] = {}
    for eid, att in attempts.items():
        if not att.get("request"):
            continue
        rid, turn_idx = inference_turn_key(att)
        if turn_idx is None:
            continue
        out.setdefault((rid, turn_idx), []).append(eid)
    return out


def collect_prep_spans(spans: list[dict]) -> dict[int, dict]:
    by_turn: dict[int, dict] = {}
    for span in spans:
        if phase_id(span) != "character_prep_phase":
            continue
        idx = turn_index(span)
        if idx is None:
            continue
        by_turn[idx] = span
    return by_turn


def linked_inference_by_prep(spans: list[dict], attempts: dict[str, dict]) -> dict[str, list[str]]:
    prep_ids = {span_id(s) for s in spans if phase_id(s) == "character_prep_phase" and span_id(s)}
    out: dict[str, list[str]] = {pid: [] for pid in prep_ids}
    for span in spans:
        if phase_id(span) != "character_prep_inference":
            continue
        parent = (span.get("correlation") or {}).get("parent_span_id")
        if parent not in out:
            continue
        for eid in linked_evidence_ids(span):
            if eid not in out[parent]:
                out[parent].append(eid)
    # Fallback: direct associations on prep span
    for span in spans:
        if phase_id(span) != "character_prep_phase":
            continue
        pid = span_id(span)
        if not pid:
            continue
        for eid in linked_evidence_ids(span):
            if eid not in out.setdefault(pid, []):
                out[pid].append(eid)
    return out


def analyze_run(run_manifest_path: Path) -> dict:
    manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    session_id = manifest["hg_session_id"]
    evidence_root = Path(manifest["execution_evidence_dir"])
    _, attempts = load_session(evidence_root, session_id)
    spans = graph_spans(attempts)
    link_map = linked_inference_by_prep(spans, attempts)
    inference_by_turn = collect_inference_by_turn(attempts)

    prep_spans = [s for s in spans if phase_id(s) == "character_prep_phase"]
    character_turns = []
    for prep_span in sorted(
        prep_spans,
        key=lambda s: (
            round_id(s) or "",
            turn_index(s) if turn_index(s) is not None else -1,
        ),
    ):
        corr = prep_span.get("correlation") or {}
        turn_idx = turn_index(prep_span)
        hg_round_id = round_id(prep_span)
        prep_wall = (prep_span.get("execution") or {}).get("wall_ms")
        linked = list(link_map.get(span_id(prep_span) or "", []))
        attribution_method = "span_linked" if linked else "inference_id_turn_key"
        if not linked and hg_round_id is not None and turn_idx is not None:
            linked = inference_by_turn.get((hg_round_id, turn_idx), [])

        layer_b_wall = 0
        layer_b_count = 0
        regen_wall = 0
        regen_count = 0
        prep_inference_sum = 0
        orient_med_wall = 0
        for eid in linked:
            att = attempts.get(eid)
            if not att:
                continue
            kind = inference_kind(att)
            wall = attempt_wall(att) or 0
            prep_inference_sum += wall
            if kind == "plot_cognition_epistemic_eval":
                layer_b_count += 1
                layer_b_wall += wall
            if kind == "character_advisory_generation":
                regen_count += 1
                regen_wall += wall
            if kind in ("character_orientation", "librarian_mediation"):
                orient_med_wall += wall

        domain_commit_id = (
            (prep_span.get("decision") or {}).get("orchestration_graph") or {}
        ).get("domain_commit_id")
        turn_cp = critical_path_attribution(
            attempts,
            attribution_scope="character_turn",
            hg_round_id=hg_round_id,
            domain_commit_id=domain_commit_id,
            character_turn_index=turn_idx,
        )
        prep_share = (layer_b_wall / prep_wall) if prep_wall and layer_b_wall else None
        turn_cp_share = (layer_b_wall / turn_cp["ms"]) if turn_cp.get("ms") and layer_b_wall else None
        # Serial prep scheduling: elapsed Layer B wall time is on the prep critical path when present.
        layer_b_cp_ms = layer_b_wall if layer_b_wall else 0
        hypothetical_overlap_savings = (
            min(layer_b_wall, orient_med_wall) if layer_b_wall and orient_med_wall else 0
        )

        character_turns.append({
            "hg_round_id": hg_round_id,
            "character_turn_index": turn_idx,
            "domain_commit_id": domain_commit_id,
            "character_prep_phase_wall_ms": prep_wall,
            "character_prep_linked_inference_sum_ms": prep_inference_sum,
            "layer_b_eval_count": layer_b_count,
            "layer_b_elapsed_wall_ms": layer_b_wall,
            "layer_b_share_of_prep_phase_wall": prep_share,
            "layer_b_share_of_turn_cp": turn_cp_share,
            "layer_b_on_character_prep_critical_path_ms": layer_b_cp_ms,
            "layer_b_attribution_method": attribution_method if linked else "none",
            "character_turn_cp_ms": turn_cp.get("ms"),
            "character_turn_cp_confidence": turn_cp.get("attribution_confidence"),
            "regen_eval_count": regen_count,
            "regen_elapsed_wall_ms": regen_wall,
            "hypothetical_overlap_savings_ms": hypothetical_overlap_savings,
        })

    player_turns = []
    for ut in manifest.get("user_turns", []):
        op = ut.get("client_operation_id")
        pv = player_visible_latency(attempts, op)
        # Layer B in same round via hg_round_id
        rid = ut.get("hg_round_id")
        round_layer_b = 0
        round_layer_b_n = 0
        if rid:
            for att in attempts.values():
                corr = att.get("correlation") or {}
                if corr.get("hg_round_id") != rid:
                    continue
                if inference_kind(att) == "plot_cognition_epistemic_eval":
                    round_layer_b_n += 1
                    round_layer_b += attempt_wall(att) or 0
        share = None
        if pv.get("ms") and round_layer_b:
            share = round_layer_b / pv["ms"]
        player_turns.append({
            "turn_index": ut.get("turn_index"),
            "client_operation_id": op,
            "hg_round_id": rid,
            "player_visible_ms": pv.get("ms"),
            "player_visible_confidence": pv.get("attribution_confidence"),
            "round_layer_b_wall_ms": round_layer_b,
            "round_layer_b_eval_count": round_layer_b_n,
            "layer_b_share_of_player_visible": share,
            "orchestrator_wall_ms": ut.get("wall_ms"),
        })

    round_cp = critical_path_attribution(attempts, attribution_scope="round_internal")
    graph_count = len(spans)
    proven_turns = sum(1 for t in character_turns if t["character_turn_cp_confidence"] == ATTRIBUTION_PROVEN)
    proven_player_turns = sum(
        1 for t in player_turns if t.get("player_visible_confidence") == ATTRIBUTION_PROVEN
    )

    return {
        "run_manifest": str(run_manifest_path),
        "condition_id": manifest.get("condition_id"),
        "repetition": manifest.get("repetition"),
        "hg_session_id": session_id,
        "orchestration_span_count": graph_count,
        "proven_character_turn_count": proven_turns,
        "proven_player_turn_count": proven_player_turns,
        "character_turn_count": len(character_turns),
        "round_internal_cp": round_cp,
        "character_turns": character_turns,
        "player_turns": player_turns,
    }


def summarize(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    vals = sorted(values)
    n = len(vals)
    def pct(p: float) -> float:
        if n == 1:
            return vals[0]
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        return vals[f] + (vals[c] - vals[f]) * (k - f)
    return {
        "n": n,
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "min": vals[0],
        "max": vals[-1],
        "p25": pct(0.25),
        "p75": pct(0.75),
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: issue176_characterization_analyze.py <campaign_root>")
        return 2
    campaign_root = Path(argv[0])
    run_manifests = sorted(campaign_root.glob("*/*/rep-*/**/run_manifest.json"))
    if not run_manifests:
        run_manifests = sorted(campaign_root.glob("**/run_manifest.json"))
    analyses = [analyze_run(p) for p in run_manifests]

    by_condition: dict[str, list[dict]] = {}
    for a in analyses:
        by_condition.setdefault(a["condition_id"], []).append(a)

    aggregate = {"conditions": {}, "overall": {}}
    all_lb_share_pv = []
    all_lb_share_turn_cp = []
    all_lb_prep_ms = []

    for cond, runs in by_condition.items():
        shares_pv = [
            t["layer_b_share_of_player_visible"]
            for r in runs for t in r["player_turns"]
            if t.get("layer_b_share_of_player_visible") is not None
        ]
        shares_prep = [
            t["layer_b_share_of_prep_phase_wall"]
            for r in runs for t in r["character_turns"]
            if t.get("layer_b_share_of_prep_phase_wall") is not None
        ]
        shares_cp = [
            t["layer_b_share_of_turn_cp"]
            for r in runs for t in r["character_turns"]
            if t.get("layer_b_share_of_turn_cp") is not None
        ]
        prep_ms = [
            t["layer_b_elapsed_wall_ms"]
            for r in runs for t in r["character_turns"]
            if t.get("layer_b_elapsed_wall_ms")
        ]
        turns_with_lb = sum(
            1 for r in runs for t in r["character_turns"] if t.get("layer_b_eval_count")
        )
        aggregate["conditions"][cond] = {
            "run_count": len(runs),
            "character_turn_count": sum(r["character_turn_count"] for r in runs),
            "character_turns_with_layer_b": turns_with_lb,
            "proven_character_turn_count": sum(r["proven_character_turn_count"] for r in runs),
            "layer_b_share_of_player_visible": summarize(shares_pv),
            "layer_b_share_of_prep_phase_wall": summarize(shares_prep),
            "layer_b_share_of_turn_cp": summarize(shares_cp),
            "layer_b_elapsed_wall_ms_per_turn_with_layer_b": summarize([float(x) for x in prep_ms]),
        }
        all_lb_share_pv.extend(shares_pv)
        all_lb_share_turn_cp.extend(shares_cp)
        all_lb_prep_ms.extend(prep_ms)

    all_lb_share_prep = [
        t["layer_b_share_of_prep_phase_wall"]
        for a in analyses for t in a["character_turns"]
        if t.get("layer_b_share_of_prep_phase_wall") is not None
    ]
    turns_with_lb = sum(
        1 for a in analyses for t in a["character_turns"] if t.get("layer_b_eval_count")
    )
    aggregate["overall"] = {
        "run_count": len(analyses),
        "character_turn_count": sum(a["character_turn_count"] for a in analyses),
        "character_turns_with_layer_b": turns_with_lb,
        "layer_b_share_of_player_visible": summarize(all_lb_share_pv),
        "layer_b_share_of_prep_phase_wall": summarize(all_lb_share_prep),
        "layer_b_share_of_turn_cp": summarize(all_lb_share_turn_cp),
        "layer_b_elapsed_wall_ms_per_turn_with_layer_b": summarize(
            [float(x) for x in all_lb_prep_ms if x]
        ),
    }

    report = {
        "schema": "issue176_characterization_analysis_v1",
        "campaign_root": str(campaign_root),
        "runs": analyses,
        "aggregate": aggregate,
    }
    out_path = campaign_root / "characterization_analysis.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"analysis_path": str(out_path), "run_count": len(analyses)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
