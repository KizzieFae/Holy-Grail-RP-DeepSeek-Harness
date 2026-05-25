#!/usr/bin/env python3
"""Issue #249 Phase A — schema teaching generalization validation matrix."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from collections import defaultdict
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
PHASE_A_PRIOR = OUT_DIR / "i249_proposal_schema_experiment_results.json"
ALLOWED_PROPOSAL_KEYS = frozenset({"kind", "character", "operation"})
FORBIDDEN_KEYS = frozenset(
    {"reason", "description", "rationale", "strategy", "subject", "character_id"}
)

# category tags per matrix row (multiple rows may share the same audit turn)
MATRIX_ROWS: list[dict[str, Any]] = [
    # A — clean exits
    {"case_id": "A1", "category": "A_clean_exit", "session": "session_908", "round": 1, "turn": 3, "actor": "willow_reeves", "expected_decision": "covered_change", "expected_kind": "off_focal", "note": "room departure / door shut"},
    {"case_id": "A2", "category": "A_clean_exit", "session": "session_852", "round": 1, "turn": 8, "actor": "hannah_lovelace", "expected_decision": "covered_change", "expected_kind": "off_focal", "note": "Hannah exit accept comparator"},
    {"case_id": "A3", "category": "A_clean_exit", "session": "session_853", "round": 1, "turn": 10, "actor": "hannah_lovelace", "expected_decision": "covered_change", "expected_kind": "off_focal", "note": "hall exit tier-b"},
    # B — reentries
    {"case_id": "B1", "category": "B_reentry", "session": "session_908", "round": 1, "turn": 9, "actor": "willow_reeves", "expected_decision": "covered_change", "expected_kind": "reentry", "note": "P04 return to room"},
    {"case_id": "B2", "category": "B_reentry", "session": "session_910", "round": 5, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "reentry", "note": "door return reentry malformed baseline"},
    # C — temporary practical
    {"case_id": "C1", "category": "C_temp_movement", "session": "session_912", "round": 1, "turn": 12, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "note": "garage/latch temporary (#251 miss probe)"},
    {"case_id": "C2", "category": "C_temp_movement", "session": "session_908", "round": 1, "turn": 8, "actor": "kizzie", "expected_decision": "no_covered_change", "expected_kind": None, "note": "in-room reposition"},
    # D — tethered
    {"case_id": "D1", "category": "D_tether", "session": "session_908", "round": 1, "turn": 5, "actor": "willow_reeves", "expected_decision": "no_covered_change", "expected_kind": None, "note": "P02 doorway tether", "stochastic_passes": 3},
    {"case_id": "D2", "category": "D_tether", "session": "session_908", "round": 1, "turn": 11, "actor": "willow_reeves", "expected_decision": "no_covered_change", "expected_kind": None, "note": "P05 noop tether", "stochastic_passes": 3},
    {"case_id": "D3", "category": "D_tether", "session": "session_911", "round": 1, "turn": 5, "actor": "marlene_fletcher", "expected_decision": "no_covered_change", "expected_kind": None, "note": "P02 variant session"},
    {"case_id": "D4", "category": "D_tether", "session": "session_912", "round": 1, "turn": 11, "actor": "marlene_fletcher", "expected_decision": "no_covered_change", "expected_kind": None, "note": "P05 variant session"},
    # E — emotional
    {"case_id": "E1", "category": "E_emotional", "session": "session_910", "round": 7, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "note": "flirtation margin exit", "stochastic_passes": 3},
    {"case_id": "E2", "category": "E_emotional", "session": "session_910", "round": 12, "turn": 1, "actor": "marlene_fletcher", "expected_decision": "monitor", "expected_kind": None, "note": "R12T1 rationale malformed baseline"},
    {"case_id": "E3", "category": "E_emotional", "session": "session_912", "round": 1, "turn": 12, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "note": "CASE-3 emotional departure", "stochastic_passes": 3},
    # F — crowded
    {"case_id": "F1", "category": "F_crowded", "session": "session_910", "round": 1, "turn": 1, "actor": "harley_quinn", "expected_decision": "no_covered_change", "expected_kind": None, "note": "3-char opening Harley", "stochastic_passes": 3},
    {"case_id": "F2", "category": "F_crowded", "session": "session_910", "round": 5, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "reentry", "note": "3-char mid-scene"},
    {"case_id": "F3", "category": "F_crowded", "session": "session_912", "round": 1, "turn": 10, "actor": "kizzie", "expected_decision": "monitor", "expected_kind": "off_focal", "note": "3-char Kizzie subject malformed", "stochastic_passes": 3},
    # G — low pressure
    {"case_id": "G1", "category": "G_low_pressure", "session": "session_908", "round": 1, "turn": 8, "actor": "kizzie", "expected_decision": "no_covered_change", "expected_kind": None, "note": "casual dorm chatter"},
    {"case_id": "G2", "category": "G_low_pressure", "session": "session_910", "round": 11, "turn": 3, "actor": "willow_reeves", "expected_decision": "no_covered_change", "expected_kind": None, "note": "late-round idle"},
    {"case_id": "G3", "category": "G_low_pressure", "session": "session_910", "round": 8, "turn": 2, "actor": "marlene_fletcher", "expected_decision": "no_covered_change", "expected_kind": None, "note": "kitchen/dorm slice"},
    # M — malformed baseline cohort
    {"case_id": "M1", "category": "M_malformed", "session": "session_908", "round": 1, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "invalid_fields": "reason", "stochastic_passes": 3},
    {"case_id": "M2", "category": "M_malformed", "session": "session_908", "round": 1, "turn": 5, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "reentry", "invalid_fields": "reason", "stochastic_passes": 3},
    {"case_id": "M3", "category": "M_malformed", "session": "session_908", "round": 1, "turn": 7, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "invalid_fields": "reason", "stochastic_passes": 3},
    {"case_id": "M4", "category": "M_malformed", "session": "session_908", "round": 1, "turn": 9, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "reentry", "invalid_fields": "character_id+reason", "stochastic_passes": 3},
    {"case_id": "M5", "category": "M_malformed", "session": "session_910", "round": 5, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "reentry", "invalid_fields": "description", "stochastic_passes": 3},
    {"case_id": "M6", "category": "M_malformed", "session": "session_910", "round": 7, "turn": 3, "actor": "willow_reeves", "expected_decision": "monitor", "expected_kind": "off_focal", "invalid_fields": "strategy+rationale", "stochastic_passes": 3},
    {"case_id": "M7", "category": "M_malformed", "session": "session_912", "round": 1, "turn": 10, "actor": "kizzie", "expected_decision": "monitor", "expected_kind": "off_focal", "invalid_fields": "subject", "stochastic_passes": 3},
]


def _turn_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (row["session"], row["round"], row["turn"], row["actor"])


def _dedupe_run_cases() -> list[dict[str, Any]]:
    by_key: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    tags: dict[tuple[str, int, int, str], list[str]] = defaultdict(list)
    for row in MATRIX_ROWS:
        key = _turn_key(row)
        tags[key].append(row["case_id"])
        passes = int(row.get("stochastic_passes") or 1)
        if key not in by_key:
            merged = dict(row)
            merged["matrix_case_ids"] = []
            merged["categories"] = []
            merged["stochastic_passes"] = passes
            merged["matrix_expectations"] = []
            by_key[key] = merged
        cur = by_key[key]
        cur["stochastic_passes"] = max(cur["stochastic_passes"], passes)
        if row["category"] not in cur["categories"]:
            cur["categories"].append(row["category"])
        cur["matrix_expectations"].append(
            {
                "case_id": row["case_id"],
                "category": row["category"],
                "expected_decision": row.get("expected_decision"),
                "expected_kind": row.get("expected_kind"),
            }
        )
        if row.get("expected_decision") == "no_covered_change":
            cur["expected_decision"] = "no_covered_change"
    for key, case in by_key.items():
        case["matrix_case_ids"] = tags[key]
        case["run_id"] = f"{case['session']}_R{case['round']}T{case['turn']:02d}_{case['actor']}"
    return list(by_key.values())


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


def committed_metrics(audit: dict[str, Any]) -> dict[str, Any]:
    se = semantic_eval_from_audit(audit)
    proposals = se.get("proposals") or []
    schema = proposal_schema_metrics(proposals if isinstance(proposals, list) else [])
    kinds = [str(p.get("kind") or "") for p in proposals if isinstance(p, dict)]
    return {
        "decision": se.get("decision"),
        "proposals": proposals,
        "schema_valid": schema["schema_valid"] if proposals else None,
        "forbidden_keys_found": schema["forbidden_keys_found"],
        "missing_character": schema["missing_character"],
        "proposal_kinds": kinds,
        "emitted": se.get("decision") == "covered_change" and bool(proposals),
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
    kinds = [str(p.get("kind") or "") for p in proposals if isinstance(p, dict)]
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
        "proposal_kinds": kinds,
        "emitted": se.get("decision") == "covered_change" and bool(proposals),
    }


def evaluate_attempt(*, raw: str, bot_name: str, scene_state: dict[str, Any]) -> dict[str, Any]:
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
            "forbidden_keys_found": [],
            "missing_character": True,
            "authority_outcome": None,
            "authority_reached": False,
            "proposal_kinds": [],
            "emitted": False,
        }
    ingress_error = validate_issue240_semantic_evaluation_ingress(move)
    if ingress_error:
        se = move.get("semantic_evaluation") or {}
        proposals = se.get("proposals") or []
        schema = proposal_schema_metrics(proposals if isinstance(proposals, list) else [])
        kinds = [str(p.get("kind") or "") for p in proposals if isinstance(p, dict)]
        return {
            "parse_ok": True,
            "parse_error": "",
            "ingress_pass": False,
            "ingress_error": ingress_error,
            "decision": se.get("decision"),
            "proposals": proposals,
            "schema_valid": schema["schema_valid"],
            "forbidden_keys_found": schema["forbidden_keys_found"],
            "missing_character": schema["missing_character"],
            "authority_outcome": None,
            "authority_reached": False,
            "proposal_kinds": kinds,
            "emitted": se.get("decision") == "covered_change" and bool(proposals),
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
    kinds = [str(p.get("kind") or "") for p in proposals if isinstance(p, dict)]
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
        "proposal_kinds": kinds,
        "emitted": se.get("decision") == "covered_change" and bool(proposals),
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


def _rate(vals: list[bool | None]) -> float | None:
    usable = [v for v in vals if isinstance(v, bool)]
    if not usable:
        return None
    return round(sum(usable) / len(usable), 3)


def aggregate_by_category(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        for cat in row.get("categories") or []:
            by_cat[cat].append(row)

    out: dict[str, Any] = {}
    for cat, rows in sorted(by_cat.items()):
        attempts: list[dict[str, Any]] = []
        for row in rows:
            for att in row.get("passes") or []:
                attempts.append(att)
        out[cat] = {
            "unique_turns": len(rows),
            "total_attempts": len(attempts),
            "baseline_first_ingress_pass_rate": _rate(
                [
                    (row.get("baseline_first_attempt") or {}).get("ingress_pass")
                    for row in rows
                    if (row.get("baseline_first_attempt") or {}).get("found")
                ]
            ),
            "baseline_first_forbidden_key_rate": _rate(
                [
                    bool((row.get("baseline_first_attempt") or {}).get("forbidden_keys_found"))
                    for row in rows
                    if (row.get("baseline_first_attempt") or {}).get("found")
                ]
            ),
            "phase_a_ingress_pass_rate": _rate([a.get("ingress_pass") for a in attempts]),
            "phase_a_schema_valid_rate": _rate([a.get("schema_valid") for a in attempts if a.get("emitted") or a.get("proposals")]),
            "phase_a_forbidden_key_rate": _rate([bool(a.get("forbidden_keys_found")) for a in attempts]),
            "phase_a_missing_character_rate": _rate([a.get("missing_character") for a in attempts if a.get("emitted")]),
            "phase_a_emission_rate": _rate([a.get("emitted") for a in attempts]),
            "phase_a_over_trigger_rate": _rate(
                [
                    a.get("emitted")
                    for row in rows
                    for a in (row.get("passes") or [])
                    if row.get("expected_decision") == "no_covered_change"
                ]
            ),
        }
    return out


def aggregate_global(results: list[dict[str, Any]]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for row in results:
        attempts.extend(row.get("passes") or [])

    baseline_rows = [r for r in results if (r.get("baseline_first_attempt") or {}).get("found")]
    tether_rows = [r for r in results if r.get("expected_decision") == "no_covered_change"]

    return {
        "matrix_rows": len(MATRIX_ROWS),
        "unique_turns": len(results),
        "total_llm_attempts": len(attempts),
        "baseline_first_n": len(baseline_rows),
        "baseline_first_ingress_pass_rate": _rate(
            [r["baseline_first_attempt"]["ingress_pass"] for r in baseline_rows]
        ),
        "baseline_first_forbidden_key_rate": _rate(
            [bool(r["baseline_first_attempt"].get("forbidden_keys_found")) for r in baseline_rows]
        ),
        "phase_a_ingress_pass_rate": _rate([a.get("ingress_pass") for a in attempts]),
        "phase_a_schema_valid_when_proposals_rate": _rate(
            [a.get("schema_valid") for a in attempts if a.get("emitted")]
        ),
        "phase_a_forbidden_key_rate": _rate([bool(a.get("forbidden_keys_found")) for a in attempts]),
        "phase_a_missing_character_rate": _rate(
            [a.get("missing_character") for a in attempts if a.get("emitted")]
        ),
        "phase_a_over_trigger_rate_tether_expected": _rate(
            [
                a.get("emitted")
                for row in tether_rows
                for a in (row.get("passes") or [])
            ]
        ),
        "phase_a_authority_reached_rate_when_emitted": _rate(
            [a.get("authority_reached") for a in attempts if a.get("emitted")]
        ),
        "by_category": aggregate_by_category(results),
    }


def stochastic_summary(row: dict[str, Any]) -> dict[str, Any]:
    passes = row.get("passes") or []
    if len(passes) < 2:
        return {"passes": len(passes), "consistent": None}
    decisions = [p.get("decision") for p in passes]
    emitted = [bool(p.get("emitted")) for p in passes]
    ingress = [bool(p.get("ingress_pass")) for p in passes]
    forbidden = [bool(p.get("forbidden_keys_found")) for p in passes]
    return {
        "passes": len(passes),
        "decision_mode": max(set(decisions), key=decisions.count),
        "emission_rate": round(sum(emitted) / len(emitted), 3),
        "ingress_pass_rate": round(sum(ingress) / len(ingress), 3),
        "forbidden_key_rate": round(sum(forbidden) / len(forbidden), 3),
        "consistent_decision": len(set(decisions)) == 1,
        "consistent_emission": len(set(emitted)) == 1,
    }


async def rerun_turn(case: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    session = case["session"]
    rnd = case["round"]
    turn = case["turn"]
    actor = case["actor"]
    passes_n = int(case.get("stochastic_passes") or 1)

    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {
            **case,
            "status": "artifact_missing",
            "error": f"missing committed artifact {session} R{rnd}T{turn} {actor}",
        }

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
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
    }

    scene_state = scene_state_from_prompt(original_prompt)
    baseline = baseline_first_attempt(session, rnd, turn, actor)
    committed = committed_metrics(audit)

    if dry_run:
        return {
            **case,
            "status": "dry_run",
            "source_artifact": str(committed_path),
            "preflight": preflight,
            "committed_baseline": committed,
            "baseline_first_attempt": baseline,
            "stochastic_passes_planned": passes_n,
        }

    pass_results: list[dict[str, Any]] = []
    excerpts: list[str] = []
    for i in range(passes_n):
        raw = await call_character_once(experimental_prompt, bot_name)
        att = evaluate_attempt(raw=raw, bot_name=bot_name, scene_state=scene_state)
        att["pass_index"] = i + 1
        pass_results.append(att)
        if i == 0:
            excerpts.append(raw[:1500])

    return {
        **case,
        "status": "ok",
        "source_artifact": str(committed_path),
        "preflight": preflight,
        "committed_baseline": committed,
        "baseline_first_attempt": baseline,
        "passes": pass_results,
        "stochastic_summary": stochastic_summary({**case, "passes": pass_results}),
        "raw_response_excerpt": excerpts[0] if excerpts else "",
        "teaching_excerpt": _extract_teaching_excerpt(experimental_prompt),
    }


def _extract_teaching_excerpt(prompt: str) -> str:
    marker = ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER
    idx = prompt.find(marker)
    if idx < 0:
        return ""
    return prompt[max(0, idx - 200) : idx + 400]


async def run_all(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    os.environ["RP_ISSUE240_PROMPT_TOPOLOGY"] = "v1_next7_proposal_schema_a"
    run_cases = _dedupe_run_cases()
    total_attempts = sum(int(c.get("stochastic_passes") or 1) for c in run_cases)

    results: list[dict[str, Any]] = []
    for case in run_cases:
        label = case["run_id"]
        print(
            f"=== {label} cases={','.join(case['matrix_case_ids'])} passes={case['stochastic_passes']} ===",
            flush=True,
        )
        row = await rerun_turn(case, dry_run=dry_run)
        if row.get("status") == "artifact_missing":
            print(f"  SKIP: {row.get('error')}", flush=True)
        elif dry_run:
            print(f"  dry_run baseline_found={(row.get('baseline_first_attempt') or {}).get('found')}", flush=True)
        else:
            ss = row.get("stochastic_summary") or {}
            p0 = (row.get("passes") or [{}])[0]
            print(
                f"  ingress={ss.get('ingress_pass_rate')} forbidden={ss.get('forbidden_key_rate')} "
                f"emit={ss.get('emission_rate')} decision_mode={ss.get('decision_mode')}",
                flush=True,
            )
        results.append(row)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": "v1_next7_proposal_schema_a",
        "topology_env": os.environ.get("RP_ISSUE240_PROMPT_TOPOLOGY"),
        "dry_run": dry_run,
        "matrix_rows": MATRIX_ROWS,
        "unique_turns": len(run_cases),
        "planned_llm_attempts": total_attempts,
        "phase_a_prior_source": str(PHASE_A_PRIOR),
        "results": results,
        "aggregate": aggregate_global(results) if not dry_run else {},
    }
    out_path = OUT_DIR / "i249_proposal_schema_generalization_results.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Artifact resolution only")
    args = parser.parse_args()
    asyncio.run(run_all(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
