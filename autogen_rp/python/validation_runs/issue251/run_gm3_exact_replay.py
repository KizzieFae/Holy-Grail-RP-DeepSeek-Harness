#!/usr/bin/env python3
"""GM3 exact-prompt ontology replay (issue #251 investigation)."""

from __future__ import annotations

import asyncio
import hashlib
import json
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

from continuity_semantic_proposals import evaluate_proposal_legality
from i251_metrics import enrich_attempt_metrics
from issue240_semantic_evaluation import validate_issue240_semantic_evaluation_ingress
from model_client import MODEL_CONTEXT_BUFFER_SIZE, create_deepseek_client, get_model_info
from response_validation_parsing import parse_character_move
from run_i251_anchor_guard_experiment import attempt_metrics, scene_state_from_prompt

AUDIT_PATH = (
    _PY
    / "rp_app/data/rp_audits/session_912/round_001/"
    "audit_i225_willow_must_remain_v2_offstage_cycles_session912_round001_turn12_willow_reeves_full.json"
)
OUT_PATH = Path(__file__).resolve().parent / "gm3_exact_replay_results.json"
BOT_NAME = "Willow_Reeves"
INTROSPECTION_USER = (
    "Briefly explain why this beat did or did not constitute a participation-state "
    "transition. What factors influenced whether the character remained part of the "
    "active shared scene?"
)


def load_audit() -> dict[str, Any]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def extract_prompt(audit: dict[str, Any]) -> str:
    for msg in audit.get("input_messages") or []:
        if isinstance(msg, dict) and msg.get("role") == "system":
            return str(msg.get("content") or "")
    raise ValueError("no system prompt in audit")


async def call_exact_once(prompt: str) -> str:
    client = create_deepseek_client()
    agent = AssistantAgent(
        name="Willow_Reeves_gm3_replay",
        description="GM3 exact prompt replay",
        system_message="",
        model_client=client,
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )
    result = await agent.on_messages(
        [TextMessage(content=prompt, source="system")],
        CancellationToken(),
    )
    return str(result.chat_message.content or "")


async def call_introspection_after(prompt: str, prior_assistant: str) -> str:
    client = create_deepseek_client()
    agent = AssistantAgent(
        name="Willow_Reeves_gm3_introspect",
        description="GM3 post-hoc introspection",
        system_message="",
        model_client=client,
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )
    result = await agent.on_messages(
        [
            TextMessage(content=prompt, source="system"),
            TextMessage(content=prior_assistant, source="assistant"),
            TextMessage(content=INTROSPECTION_USER, source="user"),
        ],
        CancellationToken(),
    )
    return str(result.chat_message.content or "")


def metrics_from_raw(raw: str, scene_state: dict[str, Any]) -> dict[str, Any]:
    base = attempt_metrics(raw=raw, bot_name=BOT_NAME, scene_state=scene_state)
    return enrich_attempt_metrics(base, "off_focal")


def summarize_run(
    *,
    run_id: str,
    raw: str,
    scene_state: dict[str, Any],
    historical: dict[str, Any],
    introspection: str | None = None,
) -> dict[str, Any]:
    m = metrics_from_raw(raw, scene_state)
    hist_decision = (historical.get("semantic_evaluation") or {}).get("decision")
    match_prod = m.get("decision") == hist_decision and (
        not (m.get("proposal_kinds") or [])
        if hist_decision == "no_covered_change"
        else "off_focal" in (m.get("proposal_kinds") or [])
    )
    return {
        "run_id": run_id,
        "raw_response": raw,
        "semantic_decision": m.get("decision"),
        "proposals": m.get("proposals"),
        "proposal_kinds": m.get("proposal_kinds"),
        "parse_ok": m.get("parse_ok"),
        "ingress_pass": m.get("ingress_pass"),
        "ingress_error": m.get("ingress_error"),
        "S1_semantic_intent_correct": m.get("S1_semantic_intent_correct"),
        "S2_structural_legality_pass": m.get("S2_structural_legality_pass"),
        "issue251_genuine_miss": m.get("issue251_genuine_miss"),
        "route_to_249": m.get("route_to_249"),
        "matches_historical_decision": match_prod,
        "historical_decision": hist_decision,
        "introspection_text": introspection,
    }


async def main() -> None:
    audit = load_audit()
    prompt = extract_prompt(audit)
    prompt_fp = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    scene_state = scene_state_from_prompt(prompt)
    historical_po = audit.get("parsed_output") or {}

    fidelity = {
        "audit_path": str(AUDIT_PATH),
        "timestamp_production": audit.get("timestamp"),
        "prompt_byte_length": len(prompt.encode("utf-8")),
        "prompt_sha256": prompt_fp,
        "support_manifest_prompt_fp": (
            (audit.get("metadata") or {})
            .get("support_manifest", {})
            .get("units", [{}])[1]
            .get("content_fp", "")
            if (audit.get("metadata") or {}).get("support_manifest")
            else ""
        ),
        "parse_retry_artifacts_present": False,
        "turn_execution": (audit.get("metadata") or {}).get("turn_execution"),
        "model_info_replay": get_model_info(),
        "deviations": [
            "Replay uses current create_deepseek_client() defaults (model from DEEPSEEK_MODEL env, thinking from DEEPSEEK_THINKING); production audit does not record temperature or model id on this turn.",
            "Replay path: single system TextMessage, empty AssistantAgent.system_message — matches issue251 anchor replay harness, not live turn_runner chat accumulation.",
            "Introspection runs 2–3 add assistant+user messages after the move; production had no follow-up turn.",
        ],
    }

    print("=== Run 1: exact replay ===", flush=True)
    raw1 = await call_exact_once(prompt)
    run1 = summarize_run(
        run_id="run1_exact_control",
        raw=raw1,
        scene_state=scene_state,
        historical=historical_po,
    )

    print("=== Run 2: exact + introspection ===", flush=True)
    raw2 = await call_exact_once(prompt)
    intro2 = await call_introspection_after(prompt, raw2)
    run2 = summarize_run(
        run_id="run2_introspection_a",
        raw=raw2,
        scene_state=scene_state,
        historical=historical_po,
        introspection=intro2,
    )

    print("=== Run 3: exact + introspection (repeat) ===", flush=True)
    raw3 = await call_exact_once(prompt)
    intro3 = await call_introspection_after(prompt, raw3)
    run3 = summarize_run(
        run_id="run3_introspection_b",
        raw=raw3,
        scene_state=scene_state,
        historical=historical_po,
        introspection=intro3,
    )

    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "case": "GM3",
        "session": "session_912",
        "turn": 12,
        "fidelity": fidelity,
        "historical_production": {
            "semantic_evaluation": historical_po.get("semantic_evaluation"),
            "raw_response_excerpt": (audit.get("raw_response") or "")[:500],
            "semantic_proposal_decision": (audit.get("metadata") or {}).get(
                "semantic_proposal_decision"
            ),
        },
        "runs": [run1, run2, run3],
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
