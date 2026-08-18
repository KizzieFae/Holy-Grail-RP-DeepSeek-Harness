"""Issue #246 — optional LLM adjudication adapter (offline, opt-in only).

Live LLM invocation is **never** required for CI. Operators must explicitly
enable LLM mode via CLI flags.
"""

from __future__ import annotations

import json
from typing import Any

from participation_adjudication_v1 import (
    PROMPT_VERSION,
    AdjudicationInputBundle,
    AdjudicationRecord,
    DEFAULT_LIMITATIONS,
)

LLM_MODEL_ID = "participation-adjudication-v1-stub"


def build_llm_prompt(bundle: AdjudicationInputBundle) -> str:
    """Structured prompt for selective offline adjudication."""
    return (
        "You are an offline audit adjudicator. You do NOT decide runtime truth.\n"
        "Decide whether this deterministic C3 suspicion should survive into the "
        "human-facing validation failure report.\n\n"
        f"Suspicion id: {bundle.suspicion_id}\n"
        f"Probe: {bundle.probe_instruction}\n"
        f"Scene focus: {bundle.active_scene_focus_excerpt}\n"
        f"Participation arc: {bundle.participation_arc_excerpt}\n"
        f"Topology: {bundle.scene_topology_excerpt}\n"
        f"Beats: {bundle.beats_excerpt}\n"
        f"Semantic summary: {json.dumps(bundle.semantic_output_summary, ensure_ascii=False)}\n"
        f"False-positive hints: {bundle.false_positive_class_hints}\n\n"
        "Respond JSON only with keys: "
        "adjudication_outcome (adjudicated_failure|adjudicated_non_failure|"
        "ambiguous_or_unresolved|needs_human_review), "
        "adjudication_confidence (high|medium|low), "
        "adjudication_rationale (short string)."
    )


def parse_llm_response(raw: str, *, suspicion_id: str) -> AdjudicationRecord:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AdjudicationRecord(
            suspicion_id=suspicion_id,
            adjudication_outcome="needs_human_review",
            adjudication_confidence="low",
            adjudication_rationale="LLM response was not valid JSON",
            adjudicator_kind="llm",
            adjudicator_model=LLM_MODEL_ID,
            adjudicator_prompt_version=PROMPT_VERSION,
            limitations=list(DEFAULT_LIMITATIONS),
        )
    outcome = str(data.get("adjudication_outcome") or "needs_human_review").strip()
    confidence = str(data.get("adjudication_confidence") or "low").strip()
    rationale = str(data.get("adjudication_rationale") or "")[:500]
    if confidence == "low" and outcome not in ("needs_human_review", "ambiguous_or_unresolved"):
        outcome = "needs_human_review"
    return AdjudicationRecord(
        suspicion_id=suspicion_id,
        adjudication_outcome=outcome,
        adjudication_confidence=confidence,
        adjudication_rationale=rationale,
        adjudicator_kind="llm",
        adjudicator_model=LLM_MODEL_ID,
        adjudicator_prompt_version=PROMPT_VERSION,
        limitations=list(DEFAULT_LIMITATIONS),
    )


def llm_adjudicate_bundle(bundle: AdjudicationInputBundle, *, llm_call: Any) -> AdjudicationRecord:
    """Run LLM adjudication via injected callable (for tests/operators)."""
    prompt = build_llm_prompt(bundle)
    raw = llm_call(prompt)
    return parse_llm_response(str(raw), suspicion_id=bundle.suspicion_id)
