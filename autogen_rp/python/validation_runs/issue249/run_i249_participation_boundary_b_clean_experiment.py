#!/usr/bin/env python3
"""Issue #249 Phase B.2 — clean participation ontology isolation single-turn reruns."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PY / "rp_app"))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.model_context import BufferedChatCompletionContext

from continuity_semantic_proposals import ProposalAuthorityOutcome, evaluate_proposal_legality
from issue240_semantic_evaluation import validate_issue240_semantic_evaluation_ingress
from model_client import MODEL_CONTEXT_BUFFER_SIZE, create_deepseek_client
from prompt_topology_issue240 import (
    ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER,
    ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_CLEAN_MARKER,
    ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_MARKER,
    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,
    apply_issue240_v1_next7_participation_boundary_b_clean_prompt_overrides,
    participation_ontology_contamination_hits,
)
from prompt_topology_manifest import extract_topology_manifest
from response_validation_parsing import parse_character_move

OUT_DIR = Path(__file__).resolve().parent
AUDITS = _PY / "rp_app" / "data" / "rp_audits"
PHASE_A_RESULTS = OUT_DIR / "i249_proposal_schema_experiment_results.json"
PHASE_B_RESULTS = OUT_DIR / "i249_participation_boundary_b_experiment_results.json"
ALLOWED_PROPOSAL_KEYS = frozenset({"kind", "character", "operation"})
FORBIDDEN_KEYS = frozenset(
    {"reason", "description", "rationale", "strategy", "subject", "character_id"}
)

PRIMARY = [
    ("GM3", "session_912", 1, 12, "willow_reeves", "off_focal", "CASE-3"),
    ("GM4", "session_910", 7, 3, "willow_reeves", "off_focal", None),
    ("GM2", "session_912", 1, 9, "willow_reeves", "off_focal_or_reentry", "P04"),
    ("GM2-depart", "session_912", 1, 11, "willow_reeves", "off_focal", "departure"),
]

CONTROLS = [
    ("CTRL-schema", "session_908", 1, 3, "willow_reeves", "covered_change", "M1"),
    ("CTRL-threshold", "session_908", 1, 5, "willow_reeves", "no_covered_change", "P02"),
    ("CTRL-noop", "session_908", 1, 11, "willow_reeves", "no_covered_change", "P05"),
    ("CTRL-malformed-fixed", "session_908", 1, 7, "willow_reeves", "covered_change", "M3"),
]

COMPARATOR = [
    ("C852", "session_852", 1, 8, "hannah_lovelace", "covered_change", "off_focal_accept"),
]

PHASE_A_CASE_MAP = {
    "GM3": "X3",
    "GM4": "M6",
    "GM2": "X2",
    "CTRL-schema": "M1",
    "CTRL-threshold": "M2",
    "CTRL-noop": None,
    "CTRL-malformed-fixed": "M3",
    "C852": "C852",
}


def _parse_raw_response(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def find_committed_artifact(session: str, rnd: int, turn: int, actor: str) -> Path | None:
    d = AUDITS / session / f"round_{rnd:03d}"
    hits = sorted(d.glob(f"*turn{turn:02d}_{actor}_full.json"))
    hits = [p for p in hits if "_parse_retry_" not in p.name and "validation" not in p.name]
    return hits[0] if hits else None


def find_parse_retry_artifact(session: str, rnd: int, turn: int, actor: str) -> Path | None:
    d = AUDITS / session / f"round_{rnd:03d}"
    hits = sorted(d.glob(f"*turn{turn:02d}_{actor}_parse_retry_full.json"))
    return hits[0] if hits else None


def sys_prompt(audit: dict[str, Any]) -> str:
    for msg in audit.get("input_messages") or []:
        if isinstance(msg, dict) and msg.get("role") == "system":
            return str(msg.get("content") or "")
    return ""


def scene_state_from_prompt(prompt: str) -> dict[str, Any]:
    m = re.search(
        r"CURRENT SCENE STATE:\s*(\{.*?\})\s*(?:SCENE TEMPLATE|PARTICIPATION|YOUR SCENE ROLE|RECENT STRUCTURED|FOR THIS BEAT)",
        prompt,
        re.S,
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def proposal_schema_metrics(proposals: list[Any]) -> dict[str, Any]:
    if not proposals:
        return {
            "schema_valid": False,
            "forbidden_keys_found": [],
            "missing_character": True,
        }
    forbidden: list[str] = []
    missing_character = False
    for item in proposals:
        if not isinstance(item, dict):
            return {
                "schema_valid": False,
                "forbidden_keys_found": ["<non_object>"],
                "missing_character": True,
            }
        forbidden.extend(k for k in item if k in FORBIDDEN_KEYS or k not in ALLOWED_PROPOSAL_KEYS)
        if not str(item.get("character") or "").strip():
            missing_character = True
    return {
        "schema_valid": not forbidden and not missing_character,
        "forbidden_keys_found": sorted(set(forbidden)),
        "missing_character": missing_character,
    }


def semantic_eval_from_audit(audit: dict[str, Any]) -> dict[str, Any]:
    po = audit.get("parsed_output")
    if not isinstance(po, dict):
        return {}
    se = po.get("semantic_evaluation")
    return se if isinstance(se, dict) else {}


def attempt_metrics(
    *,
    raw: str | None,
    bot_name: str,
    scene_state: dict[str, Any],
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if raw is None and audit is not None:
        se = semantic_eval_from_audit(audit)
        proposals = se.get("proposals") or []
        schema = proposal_schema_metrics(proposals if isinstance(proposals, list) else [])
        return {
            "parse_ok": True,
            "parse_error": "",
            "ingress_pass": True,
            "ingress_error": "",
            "decision": se.get("decision"),
            "proposals": proposals,
            "schema_valid": schema["schema_valid"] if proposals else None,
            "forbidden_keys_found": schema["forbidden_keys_found"],
            "missing_character": schema["missing_character"],
            "authority_outcome": None,
            "authority_reached": False,
            "proposal_kinds": [
                str(p.get("kind") or "") for p in proposals if isinstance(p, dict)
            ],
        }

    move, parse_error = parse_character_move(str(raw or ""))
    if move is None:
        return {
            "parse_ok": False,
            "parse_error": parse_error,
            "ingress_pass": False,
            "ingress_error": parse_error,
            "decision": None,
            "proposals": [],
            "schema_valid": False,
            "authority_outcome": None,
            "proposal_kinds": [],
        }
    ingress_error = validate_issue240_semantic_evaluation_ingress(move)
    if ingress_error:
        se = move.get("semantic_evaluation") or {}
        proposals = se.get("proposals") or []
        return {
            "parse_ok": True,
            "parse_error": "",
            "ingress_pass": False,
            "ingress_error": ingress_error,
            "decision": se.get("decision"),
            "proposals": proposals,
            "schema_valid": False,
            "authority_outcome": None,
            "proposal_kinds": [
                str(p.get("kind") or "") for p in proposals if isinstance(p, dict)
            ],
        }
    se = move.get("semantic_evaluation") or {}
    proposals = se.get("proposals") or []
    schema = proposal_schema_metrics(proposals if isinstance(proposals, list) else [])
    authority_outcome = None
    if se.get("decision") == "covered_change" and proposals:
        ctx = evaluate_proposal_legality(
            move,
            acting_character=bot_name,
            scene_state=scene_state,
            active_excursion_character_ids=set(),
            excursions=None,
        )
        authority_outcome = ctx.outcome.value if hasattr(ctx.outcome, "value") else str(ctx.outcome)
    return {
        "parse_ok": True,
        "parse_error": "",
        "ingress_pass": True,
        "ingress_error": "",
        "decision": se.get("decision"),
        "proposals": proposals,
        "schema_valid": schema["schema_valid"],
        "forbidden_keys_found": schema["forbidden_keys_found"],
        "missing_character": schema["missing_character"],
        "authority_outcome": authority_outcome,
        "authority_reached": authority_outcome == ProposalAuthorityOutcome.ACCEPT.value,
        "proposal_kinds": [
            str(p.get("kind") or "") for p in proposals if isinstance(p, dict)
        ],
    }


def baseline_first_attempt(session: str, rnd: int, turn: int, actor: str) -> dict[str, Any]:
    path = find_parse_retry_artifact(session, rnd, turn, actor)
    if path is None:
        return {"found": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = _parse_raw_response(data.get("raw_response"))
    se = raw.get("semantic_evaluation") or {}
    proposals = se.get("proposals") or []
    meta = data.get("metadata") or {}
    ingress_error = str(meta.get("failure_reason") or "")
    schema = proposal_schema_metrics(proposals if isinstance(proposals, list) else [])
    return {
        "found": True,
        "artifact": str(path),
        "decision": se.get("decision"),
        "proposals": proposals,
        "ingress_error": ingress_error,
        "ingress_pass": not ingress_error,
        "schema_valid": schema["schema_valid"],
        "forbidden_keys_found": schema["forbidden_keys_found"],
        "proposal_kinds": [
            str(p.get("kind") or "") for p in proposals if isinstance(p, dict)
        ],
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def phase_a_for_case(case_id: str, phase_a: dict[str, Any]) -> dict[str, Any] | None:
    phase_a_id = PHASE_A_CASE_MAP.get(case_id)
    if not phase_a_id:
        return None
    for row in phase_a.get("cases") or []:
        if row.get("case_id") == phase_a_id:
            return row.get("experiment_first_attempt")
    return None


def phase_b_for_case(case_id: str, phase_b: dict[str, Any]) -> dict[str, Any] | None:
    for row in phase_b.get("cases") or []:
        if row.get("case_id") == case_id:
            return row.get("phase_b_boundary_b")
    return None


async def call_character_once(prompt: str, bot_name: str) -> str:
    client = create_deepseek_client()
    agent = AssistantAgent(
        name=re.sub(r"[^A-Za-z0-9_]", "_", bot_name)[:48] or "character",
        description="Character turn replay",
        system_message="",
        model_client=client,
        model_context=BufferedChatCompletionContext(buffer_size=MODEL_CONTEXT_BUFFER_SIZE),
    )
    result = await agent.on_messages(
        [TextMessage(content=prompt, source="system")],
        CancellationToken(),
    )
    return str(result.chat_message.content or "")


async def rerun_case(
    case_id: str,
    session: str,
    rnd: int,
    turn: int,
    actor: str,
    cohort: str,
    expected: str,
    note: str | None,
    phase_a: dict[str, Any],
    phase_b: dict[str, Any],
) -> dict[str, Any]:
    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {
            "case_id": case_id,
            "cohort": cohort,
            "session": session,
            "round": rnd,
            "turn": turn,
            "actor": actor,
            "expected": expected,
            "note": note,
            "status": "artifact_missing",
            "error": f"missing committed artifact {session} R{rnd}T{turn} {actor}",
        }

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt in {committed_path}")

    experimental_prompt = apply_issue240_v1_next7_participation_boundary_b_clean_prompt_overrides(
        original_prompt,
        bot_name,
    )
    contamination = participation_ontology_contamination_hits(experimental_prompt)
    manifest = extract_topology_manifest(experimental_prompt)
    preflight = {
        "schema_marker_present": ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER in experimental_prompt,
        "boundary_marker_present": ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_MARKER
        in experimental_prompt,
        "clean_isolation_marker_present": ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_CLEAN_MARKER
        in experimental_prompt,
        "fuzzy_threshold_absent": ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER not in experimental_prompt,
        "contamination_hits": contamination,
        "contamination_clean": contamination == [],
        "allowed_keys_present": "allowed keys ONLY" in experimental_prompt,
        "forbidden_list_present": "``character_id``" in experimental_prompt,
        "char_name_in_examples": bot_name in experimental_prompt,
        "manifest_schema_marker": manifest.get("markers", {}).get("proposal_schema_teaching_v249_a"),
        "manifest_boundary_marker": manifest.get("markers", {}).get(
            "participation_boundary_teaching_v249_b"
        ),
        "manifest_clean_isolation_marker": manifest.get("markers", {}).get(
            "participation_boundary_clean_isolation_v249_b2"
        ),
        "manifest_participation_arc_absent": not manifest.get("markers", {}).get("participation_arc"),
        "manifest_active_focus_absent": not manifest.get("markers", {}).get("active_focus_capsule"),
        "topology_inferred": manifest.get("topology_inferred"),
    }

    scene_state = scene_state_from_prompt(original_prompt)
    committed = attempt_metrics(raw=None, bot_name=bot_name, scene_state=scene_state, audit=audit)
    baseline = baseline_first_attempt(session, rnd, turn, actor)
    phase_a_attempt = phase_a_for_case(case_id, phase_a)
    phase_b_attempt = phase_b_for_case(case_id, phase_b)

    raw = await call_character_once(experimental_prompt, bot_name)
    phase_b2 = attempt_metrics(raw=raw, bot_name=bot_name, scene_state=scene_state)

    return {
        "case_id": case_id,
        "cohort": cohort,
        "session": session,
        "round": rnd,
        "turn": turn,
        "actor": actor,
        "bot_name": bot_name,
        "expected": expected,
        "note": note,
        "source_artifact": str(committed_path),
        "preflight": preflight,
        "committed_baseline": committed,
        "baseline_first_attempt": baseline,
        "phase_a_schema_a": phase_a_attempt,
        "phase_b_boundary_b": phase_b_attempt,
        "phase_b2_boundary_b_clean": phase_b2,
        "raw_response_excerpt": raw[:2000],
    }


def _emitted(attempt: dict[str, Any] | None) -> bool:
    if not attempt:
        return False
    return attempt.get("decision") == "covered_change" and bool(attempt.get("proposals"))


def _kind_match(attempt: dict[str, Any] | None, expected: str) -> bool | None:
    if not attempt or not _emitted(attempt):
        return None
    kinds = attempt.get("proposal_kinds") or []
    if not kinds:
        return None
    if expected == "off_focal":
        return kinds == ["off_focal"]
    if expected == "off_focal_or_reentry":
        return kinds[0] in {"off_focal", "reentry"}
    if expected == "covered_change":
        return bool(kinds)
    return None


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(rows: list[dict[str, Any]], layer: str, field: str) -> float | None:
        vals: list[bool] = []
        for row in rows:
            if row.get("status") == "artifact_missing":
                continue
            attempt = row.get(layer) or {}
            if layer == "baseline_first_attempt" and not attempt.get("found", True):
                continue
            val = attempt.get(field)
            if isinstance(val, bool):
                vals.append(val)
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    primary = [r for r in results if r.get("cohort") == "primary"]
    controls = [r for r in results if r.get("cohort") == "control"]
    comparator = [r for r in results if r.get("cohort") == "comparator"]

    def emission_rate(layer: str, rows: list[dict[str, Any]]) -> float | None:
        eligible = [r for r in rows if r.get("status") != "artifact_missing"]
        if not eligible:
            return None
        return round(sum(1 for r in eligible if _emitted(r.get(layer))) / len(eligible), 3)

    def over_trigger(layer: str) -> float | None:
        bad = [
            r
            for r in controls
            if r.get("expected") == "no_covered_change" and _emitted(r.get(layer))
        ]
        denom = [r for r in controls if r.get("expected") == "no_covered_change"]
        if not denom:
            return None
        return round(len(bad) / len(denom), 3)

    def off_focal_correct(layer: str, rows: list[dict[str, Any]]) -> float | None:
        eligible = [
            r
            for r in rows
            if r.get("status") != "artifact_missing"
            and r.get("expected") in {"off_focal", "off_focal_or_reentry"}
        ]
        if not eligible:
            return None
        correct = [
            r
            for r in eligible
            if _kind_match(r.get(layer), str(r.get("expected") or "")) is True
        ]
        return round(len(correct) / len(eligible), 3)

    runnable = [r for r in results if r.get("status") != "artifact_missing"]

    return {
        "primary_n": len(primary),
        "control_n": len(controls),
        "comparator_n": len(comparator),
        "committed_emission_rate_primary": emission_rate("committed_baseline", primary),
        "phase_a_emission_rate_primary": emission_rate("phase_a_schema_a", primary),
        "phase_b_emission_rate_primary": emission_rate("phase_b_boundary_b", primary),
        "phase_b2_emission_rate_primary": emission_rate("phase_b2_boundary_b_clean", primary),
        "phase_b2_schema_valid_rate": rate(results, "phase_b2_boundary_b_clean", "schema_valid"),
        "phase_b2_ingress_pass_rate": rate(results, "phase_b2_boundary_b_clean", "ingress_pass"),
        "phase_b2_off_focal_correct_primary": off_focal_correct(
            "phase_b2_boundary_b_clean", primary
        ),
        "phase_b2_malformed_forbidden_key_rate": round(
            sum(
                1
                for r in runnable
                if (r.get("phase_b2_boundary_b_clean") or {}).get("forbidden_keys_found")
            )
            / max(1, len(runnable)),
            3,
        ),
        "phase_b2_over_trigger_rate_controls": over_trigger("phase_b2_boundary_b_clean"),
        "phase_a_over_trigger_rate_controls": over_trigger("phase_a_schema_a"),
        "phase_b_over_trigger_rate_controls": over_trigger("phase_b_boundary_b"),
        "preflight_contamination_clean_rate": round(
            sum(1 for r in runnable if (r.get("preflight") or {}).get("contamination_clean"))
            / max(1, len(runnable)),
            3,
        ),
    }


async def run_all(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    os.environ["RP_ISSUE240_PROMPT_TOPOLOGY"] = "v1_next7_participation_boundary_b_clean"
    phase_a = load_json(PHASE_A_RESULTS)
    phase_b = load_json(PHASE_B_RESULTS)

    cases: list[tuple[Any, ...]] = []
    for row in PRIMARY:
        cases.append((*row[:5], "primary", row[5], row[6]))
    for row in CONTROLS:
        cases.append((*row[:5], "control", row[5], row[6]))
    for row in COMPARATOR:
        cases.append((*row[:5], "comparator", row[5], row[6]))

    results: list[dict[str, Any]] = []
    for case_id, session, rnd, turn, actor, cohort, expected, note in cases:
        print(f"=== {case_id} {session} R{rnd}T{turn} {actor} ===", flush=True)
        if dry_run:
            committed = find_committed_artifact(session, rnd, turn, actor)
            results.append(
                {
                    "case_id": case_id,
                    "cohort": cohort,
                    "dry_run": True,
                    "committed_found": committed is not None,
                    "phase_a_available": phase_a_for_case(case_id, phase_a) is not None,
                    "phase_b_available": phase_b_for_case(case_id, phase_b) is not None,
                }
            )
            continue
        row = await rerun_case(
            case_id,
            session,
            rnd,
            turn,
            actor,
            cohort,
            expected,
            note,
            phase_a,
            phase_b,
        )
        if row.get("status") == "artifact_missing":
            print(f"  SKIP: {row.get('error')}", flush=True)
            results.append(row)
            continue
        pb2 = row["phase_b2_boundary_b_clean"]
        pre = row["preflight"]
        print(
            f"  committed={row['committed_baseline'].get('decision')} "
            f"phase_a={ (row.get('phase_a_schema_a') or {}).get('decision') } "
            f"phase_b={ (row.get('phase_b_boundary_b') or {}).get('decision') } "
            f"phase_b2={pb2.get('decision')} schema={pb2.get('schema_valid')} "
            f"kinds={pb2.get('proposal_kinds')} clean={pre.get('contamination_clean')}",
            flush=True,
        )
        results.append(row)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": "v1_next7_participation_boundary_b_clean",
        "topology_env": os.environ.get("RP_ISSUE240_PROMPT_TOPOLOGY"),
        "dry_run": dry_run,
        "phase_a_source": str(PHASE_A_RESULTS),
        "phase_b_source": str(PHASE_B_RESULTS),
        "cases": results,
        "aggregate": aggregate(results),
    }
    out_path = OUT_DIR / "i249_participation_boundary_b_clean_experiment_results.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve artifacts only (no LLM calls)",
    )
    args = parser.parse_args()
    asyncio.run(run_all(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
