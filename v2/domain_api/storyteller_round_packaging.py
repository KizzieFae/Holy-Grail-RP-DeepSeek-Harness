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


def storyteller_contributions_for_consumer(
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    manifest_id: str,
    consumer_target: StorytellerPackagingConsumer,
    character_id: str | None = None,
) -> tuple[PromptContribution, ...]:
    package = active_storyteller_package(rnd)
    if package is None:
        return ()
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
    )
    return result.contributions


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


def invalidate_storyteller_package_for_round(
    rnd: RoundFixture,
    *,
    reason: str,
) -> str | None:
    """Invalidate round-local Storyteller advisory after authoritative commit (S2)."""
    stored = rnd.storyteller_advisory_package
    if not stored:
        return None
    package = advisory_package_from_dict(stored)
    if not package.validity.is_valid:
        return rnd.storyteller_invalidation_reason
    invalidated = invalidate_storyteller_package(package, reason=reason)
    rnd.storyteller_advisory_package = advisory_package_to_dict(invalidated)
    rnd.storyteller_invalidation_reason = reason
    return reason
