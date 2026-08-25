"""Packaging validity gate for StorytellerAdvisoryPackage (#32 S3b).

Packaging consumes already-produced advisory packages; it never triggers Storyteller refresh.
"""

from __future__ import annotations

from dataclasses import dataclass

from .librarian_packaging_validity import PackagingBindingContext
from .storyteller_contract import StorytellerAdvisoryPackage


@dataclass(frozen=True)
class StorytellerPackagingEligibility:
    accepted: bool
    reason: str
    rejection_codes: tuple[str, ...] = ()


def assess_storyteller_packaging_eligibility(
    package: StorytellerAdvisoryPackage,
    context: PackagingBindingContext,
) -> StorytellerPackagingEligibility:
    if not package.validity.is_valid:
        return StorytellerPackagingEligibility(
            accepted=False,
            reason=package.validity.invalidation_reason or "storyteller package invalidated",
            rejection_codes=("package_invalidated",),
        )

    if package.degradation.level == "skipped":
        return StorytellerPackagingEligibility(
            accepted=False,
            reason="storyteller assessment skipped",
            rejection_codes=("degradation_skipped",),
        )

    codes: list[str] = []
    validity = package.validity

    if validity.bound_hg_round_id and validity.bound_hg_round_id != context.hg_round_id:
        codes.append("round_mismatch")

    if _snapshot_stale(validity.valid_from_authoritative_snapshot_id, context.authoritative_snapshot_id):
        codes.append("authoritative_snapshot_stale")

    if validity.bound_turn_index != context.turn_index:
        codes.append("turn_index_mismatch")

    for key in validity.invalidation_keys:
        if key.key_kind == "continuity_version" and key.key_value != str(context.continuity_version):
            codes.append("continuity_version_stale")
        if key.key_kind == "hg_round_id" and key.key_value != context.hg_round_id:
            codes.append("invalidation_round_mismatch")

    if codes:
        return StorytellerPackagingEligibility(
            accepted=False,
            reason="storyteller package stale or mismatched for packaging context",
            rejection_codes=tuple(dict.fromkeys(codes)),
        )

    return StorytellerPackagingEligibility(accepted=True, reason="eligible")


def _snapshot_stale(package_snapshot: str, context_snapshot: str) -> bool:
    package_snapshot = str(package_snapshot or "").strip()
    context_snapshot = str(context_snapshot or "").strip()
    if not package_snapshot or not context_snapshot:
        return False
    return package_snapshot != context_snapshot
