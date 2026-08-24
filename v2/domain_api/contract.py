"""Transport-neutral Holy Grail Domain API contract (V2 boundary prototype).

The logical contract is architectural. Prototype HTTP transport in
``http_transport.py`` is replaceable and must not be treated as permanent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AuthorityClass = Literal["authoritative", "derived", "suggestive"]
EligibilityStatus = Literal["eligible", "ineligible"]
SourceKind = Literal[
    "scene_setup",
    "scene_state",
    "scene_progression",
    "recent_environment",
    "continuity_canon",
    "scene_grounding",
    "active_constraints",
    "character_profile",
    "character_private",
    "character_memory",
    "authored_character_knowledge",
    "scene_reference",
    "learned_world_knowledge",
    "user_profile",
    "director_scratch",
    "continuity_summary",
    "recent_scene_transcript",
    "user_turn_trigger",
    "director_decision",
    "committed_move",
    "inference_instruction",
    "semantic_correction",
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
    correction_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class DirectorContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    turn_index: int
    attempt_index: int
    actors_used_this_round: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoundStartRequest:
    hg_scene_id: str


@dataclass(frozen=True)
class RoundStartResponse:
    hg_scene_id: str
    hg_round_id: str
    turn_index: int


@dataclass(frozen=True)
class EligibleActorsRequest:
    hg_scene_id: str
    hg_round_id: str


@dataclass(frozen=True)
class EligibleActorEntry:
    character_id: str
    eligibility_status: EligibilityStatus
    presence_status: str
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class EligibleActorsResponse:
    hg_scene_id: str
    hg_round_id: str
    eligibility_snapshot_id: str
    eligible_actors: tuple[str, ...]
    actors_used_this_round: tuple[str, ...]
    character_roles: dict[str, str]
    actors: tuple[EligibleActorEntry, ...]
    present_characters: tuple[str, ...]
    offstage_characters: tuple[str, ...]
    absent_but_relevant: tuple[str, ...]


SelectionMode = Literal["direct", "director"]


@dataclass(frozen=True)
class ParticipationDecisionRequest:
    hg_scene_id: str
    hg_round_id: str
    eligibility_snapshot_id: str
    forced_designation: str | None = None


@dataclass(frozen=True)
class ParticipationDecision:
    hg_scene_id: str
    hg_round_id: str
    eligibility_snapshot_id: str
    selection_mode: SelectionMode
    selected_actor: str | None
    director_required: bool
    director_constraint_actor: str | None
    participation_sources: tuple[str, ...]
    reason: str
    forced_designation_ignored: bool = False
    forced_designation_ignore_reason: str | None = None
    continuation_c2_skip: bool = False


@dataclass(frozen=True)
class DirectorDecisionValidationRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    turn_index: int
    attempt_index: int
    proposed_decision: dict[str, Any]
    raw_model_output: str | None = None
    eligibility_snapshot_id: str | None = None
    director_constraint_actor: str | None = None
    continuation_c2_skip: bool = False


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
class SemanticEvaluationContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    character_id: str
    role: str
    turn_index: int
    evaluation_pass_id: str
    candidate_move: dict[str, Any]
    raw_model_output: str | None = None


@dataclass(frozen=True)
class SemanticEvaluationContextResponse:
    manifest_id: str
    evaluation_pass_id: str
    inference_id: str
    hg_scene_id: str
    hg_round_id: str
    character_id: str
    turn_index: int
    contributions: tuple[PromptContribution, ...]
    authority_references: tuple[dict[str, Any], ...]
    candidate_package: dict[str, Any]


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
class OpeningContextPrepareRequest:
    hg_session_id: str
    inference_id: str


@dataclass(frozen=True)
class OpeningPersistRequest:
    hg_session_id: str
    inference_id: str
    presentation_text: str
    presentation_failed: bool = False
    manifest_id: str | None = None


@dataclass(frozen=True)
class NarratorContextPrepareRequest:
    hg_scene_id: str
    hg_round_id: str
    inference_id: str
    character_id: str
    domain_commit_id: str
    continuity_turn_index: int


@dataclass(frozen=True)
class NarratorPresentationValidationRequest:
    hg_scene_id: str
    domain_commit_id: str
    presentation_text: str


@dataclass(frozen=True)
class NarratorPresentationValidationResponse:
    accepted: bool
    validation_class: str
    reason: str
    retryable: bool


@dataclass(frozen=True)
class SessionCreateRequest:
    cast: tuple[str, ...] | None = None
    characters: tuple[str, ...] | None = None
    scene_template_id: str | None = None
    role_assignments: dict[str, str] | None = None
    opening: dict[str, Any] | None = None
    location: str = "Workshop"
    hg_session_id: str | None = None
    memory_scope_id: str | None = None
    player_character_file_id: str | None = None
    user_persona_id: str | None = None


@dataclass(frozen=True)
class SessionOpenRequest:
    hg_session_id: str


@dataclass(frozen=True)
class UserTurnRecordRequest:
    hg_session_id: str
    content: str
    speaker: str = "Player"
    forced_designation: str | None = None
    hg_round_id: str | None = None


@dataclass(frozen=True)
class PlayerSkipRecordRequest:
    hg_session_id: str
    speaker: str = "Player"


@dataclass(frozen=True)
class UserProfileSetRequest:
    hg_session_id: str
    profile_key: str
    content: str
    user_persona_id: str = "Player"


@dataclass(frozen=True)
class PresentationRecordRequest:
    hg_session_id: str
    domain_commit_id: str
    hg_round_id: str
    character_id: str
    presentation_text: str | None = None
    presentation_failed: bool = False
    inference_outcome: str | None = None


@dataclass(frozen=True)
class SessionHistoryResponse:
    hg_session_id: str
    entries: tuple[dict[str, Any], ...]
    transcript: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SessionInfoResponse:
    hg_session_id: str
    hg_scene_id: str
    turn_counter: int
    continuity_version: int
    committed_move_count: int
    present_characters: tuple[str, ...]
    location: str
    setup_provenance: dict[str, Any] | None = None
    character_file_ids: dict[str, str] | None = None
    memory_scope_id: str | None = None


@dataclass(frozen=True)
class SceneStateSnapshot:
    hg_scene_id: str
    location: str
    turn_counter: int
    present_characters: tuple[str, ...]
    committed_move_count: int
    hg_session_id: str = ""
    continuity_version: int = 0
