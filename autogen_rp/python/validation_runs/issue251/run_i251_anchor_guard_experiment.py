#!/usr/bin/env python3
"""Issue #251 — anchor + guard matrix (baseline v1_next7 vs awareness_clean treatment)."""

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.model_context import BufferedChatCompletionContext

from continuity_semantic_proposals import ProposalAuthorityOutcome, evaluate_proposal_legality
from i251_metrics import enrich_attempt_metrics, false_off_focal
from issue240_semantic_evaluation import validate_issue240_semantic_evaluation_ingress
from model_client import MODEL_CONTEXT_BUFFER_SIZE, create_deepseek_client
from prompt_topology_issue240 import (
    ISSUE251_AWARENESS_CLEAN_MARKER,
    ISSUE251_AWARENESS_DOCTRINE_MARKER,
    ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER,
    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,
    apply_baseline_v1_next7_replay_prompt_overrides,
    apply_issue251_awareness_clean_prompt_overrides,
    issue251_awareness_contamination_hits,
)
from prompt_topology_manifest import extract_topology_manifest
from response_validation_parsing import parse_character_move

OUT_DIR = Path(__file__).resolve().parent
AUDITS = _PY / "rp_app" / "data" / "rp_audits"
ALLOWED_PROPOSAL_KEYS = frozenset({"kind", "character", "operation"})
FORBIDDEN_KEYS = frozenset(
    {"reason", "description", "rationale", "strategy", "subject", "character_id"}
)
ANCHOR_N = 3

ANCHORS = [
    ("GM3", "session_912", 1, 12, "willow_reeves", "off_focal", "CASE-3"),
    ("908-P01", "session_908", 1, 3, "willow_reeves", "off_focal", "P01"),
]

GUARDS = [
    ("P02", "session_908", 1, 5, "willow_reeves", "no_covered_change", "threshold"),
    ("P05", "session_908", 1, 11, "willow_reeves", "no_covered_change", "present_disengaged"),
    ("P04", "session_908", 1, 9, "willow_reeves", "no_covered_change", "rebound"),
    ("P03", "session_908", 1, 7, "willow_reeves", "no_covered_change", "remote_phone_override"),
    ("CTRL-GM2", "session_912", 1, 9, "willow_reeves", "no_covered_change", "legacy_gm2"),
    ("911-P01", "session_911", 1, 3, "willow_reeves", "no_covered_change", "in_room_logistics"),
]

OBSERVATIONAL = [
    ("GM4", "session_910", 7, 3, "willow_reeves", "off_focal", "S1S2_only"),
    ("GM2-depart", "session_912", 1, 11, "willow_reeves", "off_focal", "departure"),
]

DEFERRED_GUARDS = [
    ("AUD-01", "doorway_continuity", "phase_1b_no_replay"),
    ("AUD-02", "hallway_audible_continuity", "phase_1b_no_replay"),
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
        forbidden.extend(
            k for k in item if k in FORBIDDEN_KEYS or k not in ALLOWED_PROPOSAL_KEYS
        )
        if not str(item.get("character") or "").strip():
            missing_character = True
    return {
        "schema_valid": not forbidden and not missing_character,
        "forbidden_keys_found": sorted(set(forbidden)),
        "missing_character": missing_character,
    }


def attempt_metrics(
    *,
    raw: str | None,
    bot_name: str,
    scene_state: dict[str, Any],
) -> dict[str, Any]:
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
            "authority_reached": False,
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
            "authority_reached": False,
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
        authority_outcome = (
            ctx.outcome.value if hasattr(ctx.outcome, "value") else str(ctx.outcome)
        )
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


def apply_arm_prompt(prompt: str, char_name: str, arm: str) -> str:
    if arm == "baseline":
        return apply_baseline_v1_next7_replay_prompt_overrides(prompt, char_name)
    if arm == "treatment":
        return apply_issue251_awareness_clean_prompt_overrides(prompt, char_name)
    raise ValueError(f"unknown arm: {arm}")


def preflight(prompt: str, arm: str) -> dict[str, Any]:
    manifest = extract_topology_manifest(prompt)
    base = {
        "arm": arm,
        "schema_marker_present": ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER in prompt,
        "topology_inferred": manifest.get("topology_inferred"),
    }
    if arm == "treatment":
        base.update(
            {
                "awareness_doctrine_marker": ISSUE251_AWARENESS_DOCTRINE_MARKER in prompt,
                "awareness_clean_marker": ISSUE251_AWARENESS_CLEAN_MARKER in prompt,
                "fuzzy_threshold_absent": ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER
                not in prompt,
                "contamination_hits": issue251_awareness_contamination_hits(prompt),
                "contamination_clean": issue251_awareness_contamination_hits(prompt) == [],
                "manifest_awareness_doctrine": manifest.get("markers", {}).get(
                    "participation_awareness_doctrine_issue251_v1"
                ),
                "manifest_awareness_clean": manifest.get("markers", {}).get(
                    "participation_awareness_clean_isolation_v251"
                ),
            }
        )
    else:
        base["fuzzy_or_margin_present"] = (
            ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER in prompt
            or "margin withdrawal/rejoin" in prompt
        )
    return base


async def run_sample(
    *,
    case_id: str,
    session: str,
    rnd: int,
    turn: int,
    actor: str,
    cohort: str,
    doctrine_expected: str,
    note: str | None,
    arm: str,
    sample_index: int,
) -> dict[str, Any]:
    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {
            "case_id": case_id,
            "cohort": cohort,
            "arm": arm,
            "sample_index": sample_index,
            "status": "artifact_missing",
            "error": f"missing {session} R{rnd}T{turn} {actor}",
        }
    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt")
    arm_prompt = apply_arm_prompt(original_prompt, bot_name, arm)
    scene_state = scene_state_from_prompt(original_prompt)
    raw = await call_character_once(arm_prompt, bot_name)
    attempt = enrich_attempt_metrics(
        attempt_metrics(raw=raw, bot_name=bot_name, scene_state=scene_state),
        doctrine_expected,
    )
    return {
        "case_id": case_id,
        "cohort": cohort,
        "arm": arm,
        "sample_index": sample_index,
        "session": session,
        "round": rnd,
        "turn": turn,
        "actor": actor,
        "bot_name": bot_name,
        "doctrine_expected": doctrine_expected,
        "note": note,
        "source_artifact": str(committed_path),
        "preflight": preflight(arm_prompt, arm),
        "first_attempt": attempt,
        "raw_response_excerpt": raw[:2000],
    }


def aggregate_anchor_guard(
    anchor_rows: list[dict[str, Any]], guard_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    def s1_rate(rows: list[dict], arm: str) -> float | None:
        vals = [
            r["first_attempt"]["S1_semantic_intent_correct"]
            for r in rows
            if r.get("status") != "artifact_missing"
            and r.get("arm") == arm
            and r.get("first_attempt")
        ]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 3)

    def false_off_rate(rows: list[dict], arm: str) -> float | None:
        eligible = [
            r
            for r in rows
            if r.get("cohort") == "guard"
            and r.get("arm") == arm
            and r.get("status") != "artifact_missing"
        ]
        if not eligible:
            return None
        bad = sum(1 for r in eligible if false_off_focal(r.get("first_attempt")))
        return round(bad / len(eligible), 3)

    anchor_only = [r for r in anchor_rows if r.get("cohort") == "anchor"]
    guard_only = [r for r in guard_rows if r.get("cohort") == "guard"]

    gm3_t = [
        r
        for r in anchor_only
        if r.get("case_id") == "GM3"
        and r.get("arm") == "treatment"
        and r.get("status") != "artifact_missing"
    ]
    p01_t = [
        r
        for r in anchor_only
        if r.get("case_id") == "908-P01"
        and r.get("arm") == "treatment"
        and r.get("status") != "artifact_missing"
    ]

    def pass_n_of_3(rows: list[dict]) -> bool | None:
        if len(rows) < ANCHOR_N:
            return None
        ok = sum(
            1
            for r in rows
            if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
        )
        return ok >= 2

    return {
        "anchor_s1_rate_baseline": s1_rate(anchor_only, "baseline"),
        "anchor_s1_rate_treatment": s1_rate(anchor_only, "treatment"),
        "guard_false_off_focal_baseline": false_off_rate(guard_only, "baseline"),
        "guard_false_off_focal_treatment": false_off_rate(guard_only, "treatment"),
        "gm3_treatment_pass_2_of_3": pass_n_of_3(gm3_t),
        "p01_treatment_pass_2_of_3": pass_n_of_3(p01_t),
    }


async def run_all(*, dry_run: bool = False, anchors_only: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    anchor_results: list[dict[str, Any]] = []
    guard_results: list[dict[str, Any]] = []
    obs_results: list[dict[str, Any]] = []

    for case_id, session, rnd, turn, actor, expected, note in ANCHORS:
        for arm in ("baseline", "treatment"):
            for sample_index in range(ANCHOR_N):
                print(
                    f"=== anchor {case_id} {arm} sample {sample_index + 1}/{ANCHOR_N} ===",
                    flush=True,
                )
                if dry_run:
                    anchor_results.append(
                        {
                            "case_id": case_id,
                            "cohort": "anchor",
                            "arm": arm,
                            "sample_index": sample_index,
                            "dry_run": True,
                            "artifact_found": find_committed_artifact(
                                session, rnd, turn, actor
                            )
                            is not None,
                        }
                    )
                    continue
                row = await run_sample(
                    case_id=case_id,
                    session=session,
                    rnd=rnd,
                    turn=turn,
                    actor=actor,
                    cohort="anchor",
                    doctrine_expected=expected,
                    note=note,
                    arm=arm,
                    sample_index=sample_index,
                )
                fa = row.get("first_attempt") or {}
                print(
                    f"  S1={fa.get('S1_semantic_intent_correct')} "
                    f"S2={fa.get('S2_structural_legality_pass')} "
                    f"decision={fa.get('decision')} kinds={fa.get('proposal_kinds')}",
                    flush=True,
                )
                anchor_results.append(row)

    if not anchors_only:
        for case_id, session, rnd, turn, actor, expected, note in GUARDS:
            for arm in ("baseline", "treatment"):
                print(f"=== guard {case_id} {arm} ===", flush=True)
                if dry_run:
                    guard_results.append(
                        {
                            "case_id": case_id,
                            "cohort": "guard",
                            "arm": arm,
                            "dry_run": True,
                            "artifact_found": find_committed_artifact(
                                session, rnd, turn, actor
                            )
                            is not None,
                        }
                    )
                    continue
                row = await run_sample(
                    case_id=case_id,
                    session=session,
                    rnd=rnd,
                    turn=turn,
                    actor=actor,
                    cohort="guard",
                    doctrine_expected=expected,
                    note=note,
                    arm=arm,
                    sample_index=0,
                )
                fa = row.get("first_attempt") or {}
                print(
                    f"  S1={fa.get('S1_semantic_intent_correct')} "
                    f"false_off_focal={false_off_focal(fa)}",
                    flush=True,
                )
                guard_results.append(row)

        for case_id, session, rnd, turn, actor, expected, note in OBSERVATIONAL:
            for arm in ("baseline", "treatment"):
                if dry_run:
                    obs_results.append(
                        {
                            "case_id": case_id,
                            "cohort": "observational",
                            "arm": arm,
                            "dry_run": True,
                            "artifact_found": find_committed_artifact(
                                session, rnd, turn, actor
                            )
                            is not None,
                        }
                    )
                    continue
                row = await run_sample(
                    case_id=case_id,
                    session=session,
                    rnd=rnd,
                    turn=turn,
                    actor=actor,
                    cohort="observational",
                    doctrine_expected=expected,
                    note=note,
                    arm=arm,
                    sample_index=0,
                )
                obs_results.append(row)

    agg = aggregate_anchor_guard(anchor_results, guard_results)
    payload_common = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": "issue251_awareness_clean_v1",
        "dry_run": dry_run,
        "aggregate": agg,
        "deferred_guards": DEFERRED_GUARDS,
    }
    anchor_path = OUT_DIR / "i251_anchor_matrix.json"
    anchor_path.write_text(
        json.dumps({**payload_common, "samples": anchor_results}, indent=2),
        encoding="utf-8",
    )
    guard_path = OUT_DIR / "i251_guard_matrix.json"
    guard_path.write_text(
        json.dumps(
            {**payload_common, "samples": guard_results, "observational": obs_results},
            indent=2,
        ),
        encoding="utf-8",
    )
    metrics_path = OUT_DIR / "i251_aggregate_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                **payload_common,
                "anchor_matrix": str(anchor_path),
                "guard_matrix": str(guard_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {anchor_path}, {guard_path}, {metrics_path}", flush=True)
    return payload_common


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--anchors-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_all(dry_run=args.dry_run, anchors_only=args.anchors_only))


if __name__ == "__main__":
    main()
