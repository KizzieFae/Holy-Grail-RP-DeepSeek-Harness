"""Host-side Storyteller orientation manifest assembly (#32 S3a)."""

from __future__ import annotations

import json
from typing import Any

from .contract import PromptContribution
from .director_context_digests import (
    project_recent_orchestration_digest,
    project_scene_pressures_digest,
    project_user_turn_source_and_hints,
)
from .session_state import LiveSession, RoundFixture
from storyteller_orientation_response_contract import (  # noqa: E402
    project_storyteller_orientation_response_contract_text,
    storyteller_orientation_response_contract_provenance,
)


STORYTELLER_ORIENTATION_CONTRACT = "storyteller_orientation_v1"


def _truncate(text: str, max_len: int = 240) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def build_storyteller_orientation_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    inference_id: str,
    manifest_id: str | None = None,
) -> tuple[str, tuple[PromptContribution, ...], tuple[dict[str, Any], ...], dict[str, Any]]:
    manifest = manifest_id or f"manifest-storyteller-orient-{inference_id}"
    contributions: list[PromptContribution] = []
    authority_refs: list[dict[str, Any]] = []

    user_contribs, user_refs = project_user_turn_source_and_hints(
        fixture,
        list(fixture.cast),
        manifest,
    )
    if user_contribs:
        contributions.extend(user_contribs)
        authority_refs.extend(user_refs)

    pressure_contrib, pressure_refs = project_scene_pressures_digest(fixture, manifest)
    if pressure_contrib is not None:
        contributions.append(pressure_contrib)
        authority_refs.extend(pressure_refs)

    orch_contrib, orch_refs = project_recent_orchestration_digest(fixture, rnd, manifest)
    if orch_contrib is not None:
        contributions.append(orch_contrib)
        authority_refs.extend(orch_refs)

    mgr = fixture.manager
    scene_state = getattr(mgr, "scene_state", None)
    scene_summary = {
        "hg_round_id": rnd.hg_round_id,
        "turn_index": int(rnd.turn_index),
        "phase": str(getattr(scene_state, "phase", None) or ""),
        "tension_level": str(getattr(scene_state, "tension_level", None) or ""),
        "present_characters": list(getattr(scene_state, "present_characters", None) or fixture.cast),
    }
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest}:storyteller_scene_snapshot",
            source_kind="scene_state",
            authority_class="authoritative",
            knowledge_ids=(),
            priority=20,
            content=(
                "STORYTELLER ORIENTATION SCENE SNAPSHOT (authoritative, bounded):\n"
                + json.dumps(scene_summary, ensure_ascii=False, indent=2)
            ),
            provenance={
                "projection_kind": "storyteller_orientation_scene_snapshot",
                "contract": STORYTELLER_ORIENTATION_CONTRACT,
            },
        )
    )

    contract_provenance = storyteller_orientation_response_contract_provenance()
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest}:storyteller_orientation_response_contract",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(),
            priority=28,
            content=project_storyteller_orientation_response_contract_text(),
            provenance={
                "projection_kind": "storyteller_orientation_response_contract",
                "contract": STORYTELLER_ORIENTATION_CONTRACT,
                **contract_provenance,
            },
        )
    )

    instruction = PromptContribution(
        contribution_id=f"{manifest}:storyteller_orientation_instruction",
        source_kind="inference_instruction",
        authority_class="derived",
        knowledge_ids=(),
        priority=100,
        content=(
            "STORYTELLER ORIENTATION TASK:\n"
            "Identify what information you need to understand the current narrative situation.\n"
            "Return focus questions in information_gaps. Do NOT prescribe plot outcomes, actor "
            "selection, dialogue, narration, or continuity mutations.\n"
            "Do NOT reference retrieval backends, candidate ids, or relevance ranks."
        ),
        provenance={
            "projection_kind": "storyteller_orientation_instruction",
            "contract": STORYTELLER_ORIENTATION_CONTRACT,
        },
    )
    contributions.append(instruction)

    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    envelope = {
        "viewer_role": "orchestration",
        "authority_ceiling_enforced": "derived",
        "session_template_id": template_id,
    }
    completeness = {
        "contract": STORYTELLER_ORIENTATION_CONTRACT,
        "has_user_trigger": bool(user_contribs),
        "has_scene_pressures": pressure_contrib is not None,
        "has_recent_orchestration": orch_contrib is not None,
    }
    return manifest, tuple(contributions), tuple(authority_refs), envelope
