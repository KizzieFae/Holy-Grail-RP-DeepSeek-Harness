#!/usr/bin/env python3
"""Issue #249 Phase A — proposal schema teaching single-turn reruns."""

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
    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,
    apply_issue240_v1_next7_proposal_schema_a_prompt_overrides,
)
from prompt_topology_manifest import extract_topology_manifest
from response_validation_parsing import parse_character_move

OUT_DIR = Path(__file__).resolve().parent
AUDITS = _PY / "rp_app" / "data" / "rp_audits"
ALLOWED_PROPOSAL_KEYS = frozenset({"kind", "character", "operation"})
FORBIDDEN_KEYS = frozenset(
    {"reason", "description", "rationale", "strategy", "subject", "character_id"}
)

MALFORMED = [
    ("M1", "session_908", 1, 3, "willow_reeves", "reason", "off_focal"),
    ("M2", "session_908", 1, 5, "willow_reeves", "reason", "reentry"),
    ("M3", "session_908", 1, 7, "willow_reeves", "reason", "off_focal"),
    ("M4", "session_908", 1, 9, "willow_reeves", "character_id+reason", "reentry"),
    ("M5", "session_910", 5, 3, "willow_reeves", "description", "reentry"),
    ("M6", "session_910", 7, 3, "willow_reeves", "strategy+rationale", "off_focal"),
    ("M7", "session_912", 1, 10, "kizzie", "subject", "off_focal"),
]

MISSED = [
    ("X1", "session_911", 1, 3, "willow_reeves", "P01"),
    ("X2", "session_912", 1, 9, "willow_reeves", "P04"),
    ("X3", "session_912", 1, 12, "willow_reeves", "CASE-3"),
]

COMPARATOR = [
    ("C852", "session_852", 1, 8, "hannah_lovelace", "off_focal_accept"),
]


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
        "missing_character": schema["missing_character"],
    }


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


def evaluate_attempt(
    *,
    raw: str,
    bot_name: str,
    scene_state: dict[str, Any],
) -> dict[str, Any]:
    move, parse_error = parse_character_move(raw)
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
        }
    ingress_error = validate_issue240_semantic_evaluation_ingress(move)
    if ingress_error:
        return {
            "parse_ok": True,
            "parse_error": "",
            "ingress_pass": False,
            "ingress_error": ingress_error,
            "decision": (move.get("semantic_evaluation") or {}).get("decision"),
            "proposals": (move.get("semantic_evaluation") or {}).get("proposals") or [],
            "schema_valid": False,
            "authority_outcome": None,
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
    }


async def rerun_case(case_id: str, session: str, rnd: int, turn: int, actor: str, **meta: Any) -> dict[str, Any]:
    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        raise FileNotFoundError(f"{case_id}: missing committed artifact {session} R{rnd}T{turn} {actor}")

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt in {committed_path}")

    experimental_prompt = apply_issue240_v1_next7_proposal_schema_a_prompt_overrides(
        original_prompt,
        bot_name,
    )
    manifest = extract_topology_manifest(experimental_prompt)
    preflight = {
        "schema_marker_present": ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER in experimental_prompt,
        "allowed_keys_present": "allowed keys ONLY" in experimental_prompt,
        "forbidden_list_present": "``character_id``" in experimental_prompt,
        "char_name_in_examples": bot_name in experimental_prompt,
        "manifest_marker": manifest.get("markers", {}).get("proposal_schema_teaching_v249_a"),
        "topology_inferred": manifest.get("topology_inferred"),
    }

    baseline = baseline_first_attempt(session, rnd, turn, actor)
    scene_state = scene_state_from_prompt(original_prompt)

    raw = await call_character_once(experimental_prompt, bot_name)
    after = evaluate_attempt(raw=raw, bot_name=bot_name, scene_state=scene_state)

    return {
        "case_id": case_id,
        "cohort": meta.get("cohort", "unknown"),
        "session": session,
        "round": rnd,
        "turn": turn,
        "actor": actor,
        "bot_name": bot_name,
        "source_artifact": str(committed_path),
        "meta": {k: v for k, v in meta.items() if k != "cohort"},
        "preflight": preflight,
        "baseline_first_attempt": baseline,
        "experiment_first_attempt": after,
        "raw_response_excerpt": raw[:2000],
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    def _rate(rows: list[dict[str, Any]], layer: str, field: str) -> float | None:
        vals = []
        for row in rows:
            attempt = row.get(layer) or {}
            if not attempt.get("found", True):
                continue
            val = attempt.get(field)
            if isinstance(val, bool):
                vals.append(val)
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    malformed = [r for r in results if r.get("cohort") == "malformed"]
    missed = [r for r in results if r.get("cohort") == "missed"]
    comparator = [r for r in results if r.get("cohort") == "comparator"]

    missed_baseline_covered = [
        1
        for row in missed
        if (row.get("baseline_first_attempt") or {}).get("decision") == "covered_change"
    ]
    missed_experiment_covered = [
        1
        for row in missed
        if (row.get("experiment_first_attempt") or {}).get("decision") == "covered_change"
    ]

    return {
        "malformed_n": len(malformed),
        "baseline_schema_valid_rate": _rate(malformed, "baseline_first_attempt", "schema_valid"),
        "experiment_schema_valid_rate": _rate(malformed, "experiment_first_attempt", "schema_valid"),
        "baseline_ingress_pass_rate": _rate(malformed, "baseline_first_attempt", "ingress_pass"),
        "experiment_ingress_pass_rate": _rate(malformed, "experiment_first_attempt", "ingress_pass"),
        "experiment_authority_reached_rate": _rate(
            malformed, "experiment_first_attempt", "authority_reached"
        ),
        "missed_baseline_covered_emission_rate": round(len(missed_baseline_covered) / len(missed), 3)
        if missed
        else None,
        "missed_experiment_covered_emission_rate": round(len(missed_experiment_covered) / len(missed), 3)
        if missed
        else None,
        "comparator_experiment_ingress_pass_rate": _rate(
            comparator, "experiment_first_attempt", "ingress_pass"
        ),
        "comparator_experiment_authority_reached_rate": _rate(
            comparator, "experiment_first_attempt", "authority_reached"
        ),
    }


async def run_all(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    os.environ["RP_ISSUE240_PROMPT_TOPOLOGY"] = "v1_next7_proposal_schema_a"

    cases: list[tuple[Any, ...]] = []
    for row in MALFORMED:
        cases.append((*row, {"cohort": "malformed", "invalid_fields": row[5], "expected_kind": row[6]}))
    for row in MISSED:
        cases.append((*row, {"cohort": "missed", "probe": row[5]}))
    for row in COMPARATOR:
        cases.append((*row, {"cohort": "comparator", "note": row[5]}))

    results: list[dict[str, Any]] = []
    for case_id, session, rnd, turn, actor, *rest in cases:
        meta = rest[-1] if isinstance(rest[-1], dict) else {}
        print(f"=== {case_id} {session} R{rnd}T{turn} {actor} ===", flush=True)
        if dry_run:
            committed = find_committed_artifact(session, rnd, turn, actor)
            baseline = baseline_first_attempt(session, rnd, turn, actor)
            results.append(
                {
                    "case_id": case_id,
                    "cohort": meta.get("cohort"),
                    "dry_run": True,
                    "committed_found": committed is not None,
                    "baseline_first_attempt": baseline,
                }
            )
            continue
        row = await rerun_case(case_id, session, rnd, turn, actor, **meta)
        results.append(row)
        print(
            f"  baseline ingress={row['baseline_first_attempt'].get('ingress_pass')} "
            f"schema={row['baseline_first_attempt'].get('schema_valid')} -> "
            f"experiment ingress={row['experiment_first_attempt'].get('ingress_pass')} "
            f"schema={row['experiment_first_attempt'].get('schema_valid')}",
            flush=True,
        )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": "v1_next7_proposal_schema_a",
        "topology_env": os.environ.get("RP_ISSUE240_PROMPT_TOPOLOGY"),
        "dry_run": dry_run,
        "cases": results,
        "aggregate": aggregate(results),
    }
    out_path = OUT_DIR / "i249_proposal_schema_experiment_results.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve artifacts and baseline metrics only (no LLM calls)",
    )
    args = parser.parse_args()
    asyncio.run(run_all(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
