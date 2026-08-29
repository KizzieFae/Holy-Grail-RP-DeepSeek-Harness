"""Storyteller round-local advisory packaging and bind validation (#54 C2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contract import PromptContribution
from .librarian_packaging_validity import PackagingBindingContext
from .session_state import LiveSession, RoundFixture
from .storyteller_contract import (
    StorytellerAdvisoryPackage,
    advisory_package_from_dict,
    advisory_package_to_dict,
    invalidate_storyteller_package,
)
from .plot_cognition_overlay_store import (
    BoundednessPolicy,
    LoadStatus,
    OperativePlotCognitionView,
)
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_projection_contract import ProjectionBudget
from .plot_cognition_projection_service import project_director_overlay
from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService
from .plot_cognition_projection_batch import CharacterProjectionSemanticResult
from .plot_cognition_projection_contract import SemanticEvaluationResult
from .plot_cognition_orchestration_contract import RegenerationGuidance
from .storyteller_packaging_mapper import map_storyteller_package_to_contributions
from .storyteller_packaging_policy import StorytellerPackagingConsumer


def active_storyteller_package(rnd: RoundFixture) -> StorytellerAdvisoryPackage | None:
    stored = rnd.storyteller_advisory_package
    if not stored:
        return None
    package = advisory_package_from_dict(stored)
    if not package.validity.is_valid:
        return None
    return package


def storyteller_packaging_binding(
    fixture: LiveSession,
    rnd: RoundFixture,
    package: StorytellerAdvisoryPackage,
    *,
    pipeline_stage: str,
) -> PackagingBindingContext:
    return PackagingBindingContext(
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
        pipeline_stage=pipeline_stage,
        continuity_version=int(fixture.continuity_version),
        authoritative_snapshot_id=package.validity.valid_from_authoritative_snapshot_id,
    )


_DEFAULT_OVERLAY_POLICY = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
_DEFAULT_CHARACTER_OVERLAY_BUDGET = ProjectionBudget(
    max_evaluation_candidates=8,
    max_projection_candidates=5,
)


def _resolve_overlay_view(
    fixture: LiveSession,
    overlay_service: PlotCognitionOverlayService | None,
    overlay_view: OperativePlotCognitionView | None,
    *,
    policy: BoundednessPolicy,
) -> OperativePlotCognitionView | None:
    if overlay_view is not None:
        return overlay_view
    if overlay_service is None:
        return None
    scope_id = str(fixture.plot_cognition_scope_id or "").strip()
    if not scope_id:
        return None
    loaded = overlay_service.load(scope_id, policy=policy)
    if loaded.status != LoadStatus.READY or loaded.store is None:
        return None
    return overlay_service.operative_view(
        loaded.store,
        policy=policy,
        load_status=loaded.status,
    )


def _parse_semantic_results(
    raw_results: list[dict[str, Any]] | None,
) -> tuple[CharacterProjectionSemanticResult, ...]:
    if not raw_results:
        return ()
    parsed: list[CharacterProjectionSemanticResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        semantic_raw = item.get("semantic") or {}
        guidance_raw = item.get("regeneration_guidance")
        guidance = None
        if isinstance(guidance_raw, dict):
            guidance = RegenerationGuidance.from_dict(guidance_raw)
        semantic = SemanticEvaluationResult(
            verdict=semantic_raw.get("verdict", "evaluator_unavailable"),  # type: ignore[arg-type]
            rationale=str(semantic_raw.get("rationale", "")),
            leak_indicators=tuple(str(x) for x in (semantic_raw.get("leak_indicators") or [])),
            forensic_rationale=semantic_raw.get("forensic_rationale"),
            regeneration_guidance=guidance,
        )
        parsed.append(
            CharacterProjectionSemanticResult(
                evaluation_pass_id=str(item.get("evaluation_pass_id", "")),
                candidate_id=str(item.get("candidate_id", "")),
                semantic=semantic,
                regeneration_guidance=guidance,
                inference_evidence_id=item.get("inference_evidence_id"),
            )
        )
    return tuple(parsed)


def storyteller_contributions_for_consumer(
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    manifest_id: str,
    consumer_target: StorytellerPackagingConsumer,
    character_id: str | None = None,
    overlay_service: PlotCognitionOverlayService | None = None,
    overlay_view: OperativePlotCognitionView | None = None,
    overlay_policy: BoundednessPolicy | None = None,
    orchestration_service: PlotCognitionOrchestrationService | None = None,
    projection_batch_id: str | None = None,
    projection_semantic_results: list[dict[str, Any]] | None = None,
) -> tuple[PromptContribution, ...]:
    contributions: list[PromptContribution] = []
    policy = overlay_policy or _DEFAULT_OVERLAY_POLICY
    orch = orchestration_service or (
        PlotCognitionOrchestrationService(overlay_service) if overlay_service else None
    )
    freshness = (
        orch.assess_overlay_freshness(fixture) if orch is not None else None
    )
    overlay_fresh = freshness.fresh if freshness is not None else True

    view = _resolve_overlay_view(
        fixture,
        overlay_service,
        overlay_view,
        policy=policy,
    ) if overlay_fresh else None

    if view is not None and orch is not None:
        if consumer_target == "director":
            contributions.extend(
                orch.director_overlay_contributions(
                    view,
                    manifest_id=manifest_id,
                    freshness=freshness,  # type: ignore[arg-type]
                )
            )
        elif consumer_target == "character" and character_id:
            all_candidates = orch.collect_character_candidates(
                fixture,
                rnd,
                character_id=character_id,
                overlay_view=view,
                include_model_a=True,
            )
            if projection_batch_id and projection_semantic_results is not None:
                try:
                    finalized = orch.finalize_projection(
                        fixture,
                        rnd,
                        batch_id=projection_batch_id,
                        semantic_results=_parse_semantic_results(projection_semantic_results),
                    )
                    contributions.extend(finalized.contributions)
                except ValueError:
                    pass
            elif all_candidates:
                # Production path without supplied semantic results remains fail-closed.
                pass
    elif view is not None:
        if consumer_target == "director":
            contributions.extend(project_director_overlay(view, manifest_id=manifest_id))

    package = active_storyteller_package(rnd)
    if package is None:
        return tuple(contributions)

    # Model A direct mapping for director/narrator; character uses orchestration finalize above.
    if consumer_target != "character" or not (orch and projection_batch_id):
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id=manifest_id,
            consumer_target=consumer_target,
            binding=storyteller_packaging_binding(
                fixture,
                rnd,
                package,
                pipeline_stage=consumer_target,
            ),
            character_id=character_id,
            fixture=fixture,
        )
        contributions.extend(result.contributions)
    return tuple(contributions)


@dataclass(frozen=True)
class StorytellerBindValidation:
    accepted: bool
    reason: str
    package_id: str | None
    parsed_package: StorytellerAdvisoryPackage | None
    degradation_level: str | None = None
    validity: dict[str, Any] | None = None
    mapped_preview: dict[str, Any] | None = None

    def to_response_dict(self, *, audit: dict[str, Any] | None) -> dict[str, Any]:
        if not self.accepted:
            return {
                "accepted": False,
                "reason": self.reason,
                "package_id": self.package_id,
            }
        return {
            "accepted": True,
            "reason": "ok",
            "package_id": self.package_id,
            "degradation_level": self.degradation_level,
            "validity": self.validity,
            "mapped_preview": self.mapped_preview,
            "audit": audit,
        }


def validate_storyteller_bind(
    fixture: LiveSession,
    rnd: RoundFixture,
    package: dict[str, Any],
) -> StorytellerBindValidation:
    if not package:
        return StorytellerBindValidation(
            accepted=False,
            reason="missing_package",
            package_id=None,
            parsed_package=None,
        )
    parsed = advisory_package_from_dict(package)
    if parsed.hg_round_id and parsed.hg_round_id != rnd.hg_round_id:
        return StorytellerBindValidation(
            accepted=False,
            reason="round_mismatch",
            package_id=parsed.package_id,
            parsed_package=None,
        )
    if not parsed.validity.is_valid:
        return StorytellerBindValidation(
            accepted=False,
            reason=parsed.validity.invalidation_reason or "package_invalid",
            package_id=parsed.package_id,
            parsed_package=None,
        )
    director_preview = map_storyteller_package_to_contributions(
        parsed,
        manifest_id=f"manifest-director-preview-{parsed.package_id}",
        consumer_target="director",
        binding=storyteller_packaging_binding(
            fixture,
            rnd,
            parsed,
            pipeline_stage="director",
        ),
    )
    return StorytellerBindValidation(
        accepted=True,
        reason="ok",
        package_id=parsed.package_id,
        parsed_package=parsed,
        degradation_level=parsed.degradation.level,
        validity={
            "is_valid": parsed.validity.is_valid,
            "bound_hg_round_id": parsed.validity.bound_hg_round_id,
        },
        mapped_preview={
            "director": {
                "items_mapped": director_preview.items_mapped,
                "source_kinds": sorted(
                    {item.source_kind for item in director_preview.contributions}
                ),
            }
        },
    )


def peek_storyteller_invalidation_reason_for_round(
    rnd: RoundFixture,
    *,
    reason: str,
) -> str | None:
    """Return the S2 invalidation reason without mutating round-local Storyteller state."""
    stored = rnd.storyteller_advisory_package
    if not stored:
        return None
    package = advisory_package_from_dict(stored)
    if not package.validity.is_valid:
        return rnd.storyteller_invalidation_reason
    return reason


def invalidate_storyteller_package_for_round(
    rnd: RoundFixture,
    *,
    reason: str,
) -> str | None:
    """Invalidate round-local Storyteller advisory after authoritative commit (S2)."""
    outcome = peek_storyteller_invalidation_reason_for_round(rnd, reason=reason)
    stored = rnd.storyteller_advisory_package
    if not stored:
        return None
    package = advisory_package_from_dict(stored)
    if not package.validity.is_valid:
        return outcome
    invalidated = invalidate_storyteller_package(package, reason=reason)
    rnd.storyteller_advisory_package = advisory_package_to_dict(invalidated)
    rnd.storyteller_invalidation_reason = reason
    return reason
