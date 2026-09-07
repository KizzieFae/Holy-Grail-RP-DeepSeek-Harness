"""Host-side Storyteller informed-assessment manifest assembly (#32 S3a)."""

from __future__ import annotations

import json
from typing import Any

from storyteller_assessment_response_contract import (  # noqa: E402
    project_storyteller_assessment_response_contract_text,
    storyteller_assessment_response_contract_provenance,
)

from .contract import PromptContribution
from .librarian_contract import LibrarianKnowledgeBundle
from .storyteller_contract import StorytellerOrientationAssessment


STORYTELLER_ASSESSMENT_CONTRACT = "storyteller_assessment_v1"
MAX_BUNDLE_ENTRIES = 12
MAX_ENTRY_CHARS = 480


def _truncate(text: str, max_len: int = MAX_ENTRY_CHARS) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def _bundle_digest(bundle: LibrarianKnowledgeBundle | dict[str, Any]) -> dict[str, Any]:
    if isinstance(bundle, dict):
        entries_raw = bundle.get("entries") or []
        satisfaction_raw = (bundle.get("satisfaction") or {}).get("focus_questions") or []
        degradation_raw = bundle.get("degradation") or {}
        validity_raw = bundle.get("validity") or {}
        entries = []
        for entry in entries_raw[:MAX_BUNDLE_ENTRIES]:
            if not isinstance(entry, dict):
                continue
            annotation = entry.get("librarian_annotation") or {}
            ref = entry.get("ref") or {}
            entries.append(
                {
                    "entry_id": entry.get("entry_id"),
                    "stable_ref": ref.get("stable_ref"),
                    "content": _truncate(str(entry.get("content") or "")),
                    "authority_class": entry.get("authority_class"),
                    "source_tier": entry.get("source_tier"),
                    "relevance_rank": annotation.get("relevance_rank"),
                    "answers_focus_questions": list(annotation.get("answers_focus_questions") or []),
                }
            )
        satisfaction = [
            {
                "question": outcome.get("question"),
                "status": outcome.get("status"),
                "supporting_entry_ids": list(outcome.get("supporting_entry_ids") or []),
            }
            for outcome in satisfaction_raw
            if isinstance(outcome, dict)
        ]
        return {
            "bundle_id": bundle.get("bundle_id"),
            "request_id": bundle.get("request_id"),
            "mediation_mode": bundle.get("mediation_mode"),
            "degradation": {
                "level": degradation_raw.get("level"),
                "mode": degradation_raw.get("mode"),
            },
            "validity": {
                "validity_scope": validity_raw.get("validity_scope"),
                "bound_hg_round_id": validity_raw.get("bound_hg_round_id"),
            },
            "satisfaction": satisfaction,
            "entries": entries,
        }

    entries = []
    for entry in bundle.entries[:MAX_BUNDLE_ENTRIES]:
        entries.append(
            {
                "entry_id": entry.entry_id,
                "stable_ref": entry.ref.stable_ref,
                "content": _truncate(entry.content),
                "authority_class": entry.authority_class,
                "source_tier": entry.source_tier,
                "relevance_rank": entry.librarian_annotation.relevance_rank,
                "answers_focus_questions": list(entry.librarian_annotation.answers_focus_questions),
            }
        )
    satisfaction = [
        {
            "question": outcome.question,
            "status": outcome.status,
            "supporting_entry_ids": list(outcome.supporting_entry_ids),
        }
        for outcome in bundle.satisfaction.focus_questions
    ]
    return {
        "bundle_id": bundle.bundle_id,
        "request_id": bundle.request_id,
        "mediation_mode": bundle.mediation_mode,
        "degradation": {
            "level": bundle.degradation.level,
            "mode": bundle.degradation.mode,
        },
        "validity": {
            "validity_scope": bundle.validity.validity_scope,
            "bound_hg_round_id": bundle.validity.bound_hg_round_id,
        },
        "satisfaction": satisfaction,
        "entries": entries,
    }


def build_storyteller_assessment_context(
    orientation: StorytellerOrientationAssessment,
    bundle: LibrarianKnowledgeBundle | dict[str, Any],
    *,
    inference_id: str,
    manifest_id: str | None = None,
) -> tuple[str, tuple[PromptContribution, ...]]:
    manifest = manifest_id or f"manifest-storyteller-assess-{inference_id}"
    digest = _bundle_digest(bundle)
    bundle_id = bundle.bundle_id if isinstance(bundle, LibrarianKnowledgeBundle) else str(bundle.get("bundle_id") or "")
    entry_ids = (
        tuple(entry.entry_id for entry in bundle.entries[:MAX_BUNDLE_ENTRIES])
        if isinstance(bundle, LibrarianKnowledgeBundle)
        else tuple(
            str(entry.get("entry_id"))
            for entry in (bundle.get("entries") or [])[:MAX_BUNDLE_ENTRIES]
            if isinstance(entry, dict) and entry.get("entry_id")
        )
    )
    orientation_summary = {
        "orientation_id": orientation.orientation_id,
        "information_gaps": list(orientation.information_gaps),
        "temporal_focus": orientation.temporal_focus,
        "breadth_preference": orientation.breadth_preference,
    }

    contract_provenance = storyteller_assessment_response_contract_provenance()
    contributions = (
        PromptContribution(
            contribution_id=f"{manifest}:storyteller_orientation_summary",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(),
            priority=10,
            content=(
                "STORYTELLER ORIENTATION SUMMARY (audit-only):\n"
                + json.dumps(orientation_summary, ensure_ascii=False, indent=2)
            ),
            provenance={"projection_kind": "storyteller_orientation_summary"},
        ),
        PromptContribution(
            contribution_id=f"{manifest}:storyteller_assessment_response_contract",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(),
            priority=28,
            content=project_storyteller_assessment_response_contract_text(),
            provenance={
                "projection_kind": "storyteller_assessment_response_contract",
                "contract": STORYTELLER_ASSESSMENT_CONTRACT,
                **contract_provenance,
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest}:librarian_bundle_digest",
            source_kind="librarian_knowledge",
            authority_class="derived",
            knowledge_ids=entry_ids,
            priority=30,
            content=(
                "LIBRARIAN KNOWLEDGE BUNDLE DIGEST (information plane — not dramatic prescription):\n"
                + json.dumps(digest, ensure_ascii=False, indent=2)
            ),
            provenance={
                "projection_kind": "storyteller_librarian_bundle_digest",
                "bundle_id": bundle_id,
                "contract": STORYTELLER_ASSESSMENT_CONTRACT,
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest}:storyteller_assessment_instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(),
            priority=100,
            content=(
                "STORYTELLER INFORMED ASSESSMENT TASK:\n"
                "Given the Librarian bundle, assess what is narratively significant now.\n"
                "Use opportunity framing — not mandates. Cite evidence_refs from bundle entries "
                "or authoritative refs.\n"
                "PROHIBITED: next_actor, required_action, mandated_beat, dialogue, narration, "
                "structured_move, continuity mutations."
            ),
            provenance={
                "projection_kind": "storyteller_assessment_instruction",
                "contract": STORYTELLER_ASSESSMENT_CONTRACT,
            },
        ),
    )
    return manifest, contributions
