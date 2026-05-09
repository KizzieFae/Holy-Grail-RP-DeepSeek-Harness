"""Shared types for resolved-outcome registry aspects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class NormalizedCandidate:
    aspect_id: str
    subject_id: str
    value: dict[str, str]


@dataclass(frozen=True)
class PromotionContext:
    """Read-only context for promotion_policy.evaluate (do not mutate manager)."""

    turn_index: int
    consequence_tags: frozenset[str]
    manager: Any


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    source: str | None
    rule_id: str
    issue_id: str | None
    reject_reason: str
    success_reason: str


class PromotionPolicy(Protocol):
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision: ...


@dataclass(frozen=True)
class AspectSpec:
    aspect_id: str
    outcome_class: str
    legacy_category: str
    legacy_key: str
    parse_candidates: Callable[
        [dict[str, Any], Any], tuple[list[NormalizedCandidate], str]
    ]
    slot_key_fn: Callable[[NormalizedCandidate], str]
    build_outcome_id: Callable[[NormalizedCandidate, int, str], str]
    is_revocation: Callable[[NormalizedCandidate], bool]
    promotion_policy: PromotionPolicy
    superseded_reason: str
    revoked_reason: str
    conflicting_candidates_reason: str = "multiple_candidates_unsupported"
