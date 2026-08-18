"""Transport-neutral Holy Grail Domain API contract (V2 boundary prototype).

The logical contract is architectural. Prototype HTTP transport in
``http_transport.py`` is replaceable and must not be treated as permanent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AuthorityClass = Literal["authoritative", "derived", "suggestive"]
SourceKind = Literal[
    "scene_state",
    "character_profile",
    "character_private",
    "director_scratch",
    "continuity_summary",
    "director_decision",
    "committed_move",
    "inference_instruction",
]
ValidationClass = Literal[
    "accepted",
    "parse_error",
    "structural",
    "domain_rule",
    "continuity_anchor",
]


@dataclass(frozen=True)
class ContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    character_id: str
    role: str
    turn_index: int
    attempt_index: int


@dataclass(frozen=True)
class DirectorContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    turn_index: int
    attempt_index: int


@dataclass(frozen=True)
class RoundStartRequest:
    hg_scene_id: str


@dataclass(frozen=True)
class RoundStartResponse:
    hg_scene_id: str
    hg_round_id: str
    turn_index: int


@dataclass(frozen=True)
class DirectorDecisionValidationRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    turn_index: int
    attempt_index: int
    proposed_decision: dict[str, Any]
    raw_model_output: str | None = None


@dataclass(frozen=True)
class DirectorDecisionResult:
    accepted: bool
    validation_class: ValidationClass
    reason: str
    retryable: bool
    normalized_decision: dict[str, Any] | None = None
    selected_character_id: str | None = None


@dataclass(frozen=True)
class PromptContribution:
    contribution_id: str
    source_kind: SourceKind
    authority_class: AuthorityClass
    knowledge_ids: tuple[str, ...]
    priority: int
    content: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptContributionManifest:
    manifest_id: str
    inference_id: str
    hg_scene_id: str
    hg_round_id: str
    role: str
    character_id: str | None
    turn_index: int
    attempt_index: int
    contributions: tuple[PromptContribution, ...]


@dataclass(frozen=True)
class ValidationRequest:
    inference_id: str
    hg_scene_id: str
    hg_round_id: str
    character_id: str
    role: str
    turn_index: int
    attempt_index: int
    proposed_move: dict[str, Any]
    raw_model_output: str | None = None


@dataclass(frozen=True)
class ValidationResponse:
    accepted: bool
    validation_class: ValidationClass
    reason: str
    retryable: bool
    normalized_move: dict[str, Any] | None = None


@dataclass(frozen=True)
class CommitRequest:
    inference_id: str
    hg_scene_id: str
    hg_round_id: str
    character_id: str
    validated_move: dict[str, Any]
    director_decision: dict[str, Any]
    expected_turn_index: int


@dataclass(frozen=True)
class CommitResponse:
    committed: bool
    continuity_turn_index: int | None
    domain_commit_id: str | None
    hg_scene_id: str
    inference_id: str
    reason: str = ""


@dataclass(frozen=True)
class NarratorContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    character_id: str
    domain_commit_id: str
    continuity_turn_index: int


@dataclass(frozen=True)
class SceneStateSnapshot:
    hg_scene_id: str
    location: str
    turn_counter: int
    present_characters: tuple[str, ...]
    committed_move_count: int
