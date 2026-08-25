"""Deterministic consumer policies for Librarian → Packaging mapping (#34 S2b)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PackagingConsumerTarget = Literal[
    "character",
    "director",
    "narrator",
    "storyteller",
    "host_default",
]

# Live continuity tiers already projected directly by Packaging prepare_* paths.
PROJECTION_DUPLICATE_SOURCE_TIERS = frozenset(
    {
        "authoritative_live_continuity",
        "scene_grounding",
        "canon_anchors",
        "recent_developments",
        "committed_turn",
        "director_decision",
    }
)

_VISIBILITY_BY_CONSUMER: dict[PackagingConsumerTarget, frozenset[str]] = {
    "character": frozenset({"character_scoped", "public", "template_participants"}),
    "director": frozenset(
        {"scene_orchestration", "public", "template_participants", "orchestration_only"}
    ),
    "narrator": frozenset({"scene_orchestration", "public", "template_participants"}),
    "storyteller": frozenset(
        {"scene_orchestration", "public", "template_participants", "orchestration_only"}
    ),
    "host_default": frozenset(
        {"character_scoped", "scene_orchestration", "public", "template_participants", "orchestration_only"}
    ),
}


@dataclass(frozen=True)
class LibrarianPackagingPolicy:
    consumer_target: PackagingConsumerTarget
    max_entries: int
    max_chars: int
    allowed_authority_classes: frozenset[str]
    allowed_information_classes: frozenset[str] | None
    allow_synthesis: bool
    allow_deterministic_fallback: bool
    skip_projection_duplicate_tiers: bool
    allowed_visibility_scopes: frozenset[str]
    base_priority: int = 22


def policy_for_consumer(target: PackagingConsumerTarget) -> LibrarianPackagingPolicy:
    common = {
        "allowed_authority_classes": frozenset({"suggestive", "derived", "authoritative"}),
        "allowed_information_classes": None,
        "skip_projection_duplicate_tiers": True,
    }
    policies: dict[PackagingConsumerTarget, LibrarianPackagingPolicy] = {
        "character": LibrarianPackagingPolicy(
            consumer_target="character",
            max_entries=8,
            max_chars=4000,
            allow_synthesis=True,
            allow_deterministic_fallback=False,
            allowed_visibility_scopes=_VISIBILITY_BY_CONSUMER["character"],
            base_priority=22,
            **common,
        ),
        "director": LibrarianPackagingPolicy(
            consumer_target="director",
            max_entries=12,
            max_chars=8000,
            allow_synthesis=True,
            allow_deterministic_fallback=True,
            allowed_visibility_scopes=_VISIBILITY_BY_CONSUMER["director"],
            base_priority=21,
            **common,
        ),
        "narrator": LibrarianPackagingPolicy(
            consumer_target="narrator",
            max_entries=10,
            max_chars=6000,
            allow_synthesis=True,
            allow_deterministic_fallback=True,
            allowed_visibility_scopes=_VISIBILITY_BY_CONSUMER["narrator"],
            base_priority=22,
            **common,
        ),
        "storyteller": LibrarianPackagingPolicy(
            consumer_target="storyteller",
            max_entries=16,
            max_chars=12000,
            allow_synthesis=True,
            allow_deterministic_fallback=True,
            allowed_visibility_scopes=_VISIBILITY_BY_CONSUMER["storyteller"],
            base_priority=20,
            **common,
        ),
        "host_default": LibrarianPackagingPolicy(
            consumer_target="host_default",
            max_entries=12,
            max_chars=8000,
            allow_synthesis=True,
            allow_deterministic_fallback=True,
            allowed_visibility_scopes=_VISIBILITY_BY_CONSUMER["host_default"],
            base_priority=22,
            **common,
        ),
    }
    return policies[target]
