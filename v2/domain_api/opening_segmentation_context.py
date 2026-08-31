"""Opening narrative-visibility segmentation context for template/authored openers (#81)."""

from __future__ import annotations

from narrative_visibility_prompt import OPENING_SEGMENTATION_OUTPUT_INSTRUCTION

from narrative_visibility_contract import narrative_visibility_from_metadata

from .context_substrate import auth_projections_to_contributions
from .continuity_context_projector import project_authoritative_context
from .contract import OpeningSegmentationContextPrepareRequest, PromptContribution, PromptContributionManifest
from .session_state import LiveSession


def _opening_entry(fixture: LiveSession) -> dict | None:
    for item in fixture.rp_history:
        if str(item.get("kind", "")) == "opening":
            return item
    return None


def prepare_opening_segmentation_context(
    fixture: LiveSession,
    req: OpeningSegmentationContextPrepareRequest,
) -> PromptContributionManifest:
    entry = _opening_entry(fixture)
    if entry is None:
        raise ValueError("opening history entry not found")

    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    if narrative_visibility_from_metadata(metadata) is not None:
        raise ValueError("opening narrative visibility already materialized")

    opener_text = str(entry.get("content", "") or "").strip()
    if not opener_text:
        raise ValueError("opening text is required for segmentation")

    mgr = fixture.manager
    assert mgr.scene_state is not None
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = "opening-segmentation"
    manifest_id = f"manifest-opening-segmentation-{req.inference_id}"

    auth_projections = project_authoritative_context(
        fixture,
        role="narrator",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
    )
    contributions: list[PromptContribution] = list(
        auth_projections_to_contributions(manifest_id, auth_projections)
    )

    cast_label = ", ".join(fixture.cast) if fixture.cast else "the cast"
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-opening-text",
            source_kind="opening_text",
            authority_class="authoritative",
            knowledge_ids=(f"opening:{entry.get('entry_id', 'opening')}",),
            priority=5,
            content=f"OPENING PROSE (authoritative — do not rewrite; segment only):\n{opener_text}",
            provenance={"entry_id": entry.get("entry_id"), "kind": "opening"},
        )
    )
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-cast",
            source_kind="scene_reference",
            authority_class="authoritative",
            knowledge_ids=tuple(f"cast:{name}" for name in fixture.cast),
            priority=8,
            content=f"Present characters (use exact display names in recipients): {cast_label}",
            provenance={"cast": list(fixture.cast)},
        )
    )
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=(
                "Segment the authoritative opening prose into narrative visibility units.\n"
                "Do NOT rewrite, paraphrase, or omit opening prose in unit text fragments.\n"
                "Use exact substrings from the opening where possible.\n"
                f"\n{OPENING_SEGMENTATION_OUTPUT_INSTRUCTION}\n"
            ),
            provenance={"inference_id": req.inference_id, "role": "opening_segmentation"},
        )
    )

    return PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role="opening_segmentation",
        character_id=None,
        turn_index=0,
        attempt_index=0,
        contributions=tuple(contributions),
    )
