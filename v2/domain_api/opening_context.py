"""Opening bootstrap context/manifest assembly (#54 C2)."""

from __future__ import annotations

from .context_substrate import auth_projections_to_contributions
from .continuity_context_projector import project_authoritative_context
from .contract import OpeningContextPrepareRequest, PromptContribution, PromptContributionManifest
from .opening_prompt import build_opening_generation_instruction
from .session_state import LiveSession


def prepare_opening_context(
    fixture: LiveSession,
    req: OpeningContextPrepareRequest,
) -> PromptContributionManifest:
    opening_entry_id = f"opening-{req.hg_session_id}"
    if any(
        item.get("entry_id") == opening_entry_id or item.get("kind") == "opening"
        for item in fixture.rp_history
    ):
        raise ValueError("opening presentation already materialized")

    mgr = fixture.manager
    assert mgr.scene_state is not None
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = "opening-bootstrap"
    manifest_id = f"manifest-opening-{req.inference_id}"
    snapshot = fixture.setup_snapshot or {}
    scene_template = dict(snapshot.get("scene_template") or {})
    premise = str(
        scene_template.get("premise")
        or getattr(mgr.scene_state, "opening_description", "")
        or ""
    ).strip()

    auth_projections = project_authoritative_context(
        fixture,
        role="narrator",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
    )
    contributions: list[PromptContribution] = list(
        auth_projections_to_contributions(manifest_id, auth_projections)
    )

    has_scene_setup = any(c.source_kind == "scene_setup" for c in contributions)
    if premise and not has_scene_setup:
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-scene-reference",
                source_kind="scene_reference",
                authority_class="authoritative",
                knowledge_ids=(f"template:{scene_template.get('template_id', 'scene')}",),
                priority=8,
                content=f"Scene premise (authoritative): {premise}",
                provenance={
                    "hg_scene_id": hg_scene_id,
                    "template_id": scene_template.get("template_id"),
                },
            )
        )

    profile_lines: list[str] = []
    cards = dict(snapshot.get("character_cards") or {})
    for display_name in fixture.cast:
        card = None
        file_id = fixture.character_file_ids.get(display_name)
        if file_id and file_id in cards:
            card = cards[file_id]
        if not card:
            continue
        description = str(card.get("description", "")).strip()
        personality = str(card.get("personality", "")).strip()
        profile_lines.append(
            f"- {display_name}: {description}"
            + (f" Personality: {personality}" if personality else "")
        )
    if profile_lines:
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-character-profiles",
                source_kind="character_profile",
                authority_class="authoritative",
                knowledge_ids=tuple(f"profile:{name}" for name in fixture.cast),
                priority=10,
                content="Character profiles (authoritative setup):\n" + "\n".join(profile_lines),
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
            content=build_opening_generation_instruction(
                present_characters=list(fixture.cast),
                premise=premise,
            ),
            provenance={"inference_id": req.inference_id, "role": "opening"},
        )
    )
    return PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role="opening",
        character_id=None,
        turn_index=0,
        attempt_index=0,
        contributions=tuple(contributions),
    )
