"""Deterministic consumer policies for Storyteller → Packaging mapping (#32 S3b)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StorytellerPackagingConsumer = Literal["director", "character", "narrator"]

StorytellerAdvisoryCategory = Literal[
    "narrative_priorities",
    "active_tensions",
    "progression_opportunities",
    "unresolved_threads",
    "observations",
    "uncertainty",
]


@dataclass(frozen=True)
class StorytellerPackagingPolicy:
    consumer_target: StorytellerPackagingConsumer
    allowed_categories: frozenset[str]
    max_entries: int
    max_chars: int
    max_priorities: int
    max_tensions: int
    max_opportunities: int
    max_threads: int
    max_observations: int
    allow_degraded: bool
    require_character_scope: bool
    include_uncertainty_when_degraded: bool
    base_priority: int = 18


def policy_for_storyteller_consumer(
    target: StorytellerPackagingConsumer,
) -> StorytellerPackagingPolicy:
    common = {
        "allow_degraded": True,
        "include_uncertainty_when_degraded": True,
    }
    policies: dict[StorytellerPackagingConsumer, StorytellerPackagingPolicy] = {
        "director": StorytellerPackagingPolicy(
            consumer_target="director",
            allowed_categories=frozenset(
                {
                    "narrative_priorities",
                    "active_tensions",
                    "progression_opportunities",
                    "unresolved_threads",
                }
            ),
            max_entries=8,
            max_chars=6000,
            max_priorities=3,
            max_tensions=4,
            max_opportunities=3,
            max_threads=3,
            max_observations=0,
            require_character_scope=False,
            base_priority=18,
            **common,
        ),
        "character": StorytellerPackagingPolicy(
            consumer_target="character",
            allowed_categories=frozenset(
                {
                    "observations",
                    "active_tensions",
                    "progression_opportunities",
                }
            ),
            max_entries=5,
            max_chars=3200,
            max_priorities=0,
            max_tensions=2,
            max_opportunities=2,
            max_threads=0,
            max_observations=2,
            require_character_scope=True,
            base_priority=19,
            **common,
        ),
        "narrator": StorytellerPackagingPolicy(
            consumer_target="narrator",
            allowed_categories=frozenset({"observations", "active_tensions"}),
            max_entries=4,
            max_chars=2400,
            max_priorities=0,
            max_tensions=2,
            max_opportunities=0,
            max_threads=0,
            max_observations=2,
            require_character_scope=False,
            base_priority=19,
            **common,
        ),
    }
    return policies[target]
