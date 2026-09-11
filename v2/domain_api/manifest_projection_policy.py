"""Phase/inference allowlists for model-only prompt contributions (#134).

PromptContribution collections are model-context contracts. Each inference path
declares which source_kind values may appear in bridge-bound packages.
"""

from __future__ import annotations

from typing import Final, Literal, Sequence

from .contract import PromptContribution

InferenceKind = Literal[
    "character_turn",
    "character_orientation",
    "character_semantic_evaluation",
    "character_advisory_generation",
    "director_turn",
    "director_semantic_qa",
    "narrator_presentation",
    "narrator_environment_cognition",
    "narrator_semantic_qa",
    "librarian_mediation",
    "librarian_mediation_contract_correction",
    "librarian_proposal",
    "librarian_proposal_contract_correction",
    "storyteller_post_commit_issue_pressure",
    "storyteller_post_commit_issue_pressure_contract_correction",
    "opening",
    "opening_segmentation",
    "player_decomposition",
    "player_visibility_triage",
    "plot_cognition_init",
    "plot_cognition_init_contract_correction",
    "plot_cognition_update",
    "plot_cognition_update_contract_correction",
    "plot_cognition_epistemic_eval",
    "plot_cognition_epistemic_eval_contract_correction",
    "storyteller_orientation",
    "storyteller_assessment",
    "storyteller_certification_eval",
    "infrastructure_provider_probe",
]

INFERENCE_KINDS: Final[tuple[str, ...]] = (
    "character_turn",
    "character_orientation",
    "character_semantic_evaluation",
    "character_advisory_generation",
    "director_turn",
    "director_semantic_qa",
    "narrator_presentation",
    "narrator_environment_cognition",
    "narrator_semantic_qa",
    "librarian_mediation",
    "librarian_mediation_contract_correction",
    "librarian_proposal",
    "librarian_proposal_contract_correction",
    "storyteller_post_commit_issue_pressure",
    "storyteller_post_commit_issue_pressure_contract_correction",
    "opening",
    "opening_segmentation",
    "player_decomposition",
    "player_visibility_triage",
    "plot_cognition_init",
    "plot_cognition_init_contract_correction",
    "plot_cognition_update",
    "plot_cognition_update_contract_correction",
    "plot_cognition_epistemic_eval",
    "plot_cognition_epistemic_eval_contract_correction",
    "storyteller_orientation",
    "storyteller_assessment",
    "storyteller_certification_eval",
    "infrastructure_provider_probe",
)

_SCENE_AUTHORITY: Final[frozenset[str]] = frozenset(
    {
        "scene_setup",
        "scene_state",
        "scene_progression",
        "recent_environment",
        "continuity_canon",
        "scene_grounding",
        "active_constraints",
    }
)

_STORYTELLER_ADVISORY: Final[frozenset[str]] = frozenset(
    {
        "storyteller_narrative_priorities",
        "storyteller_active_tensions",
        "storyteller_progression_opportunities",
        "storyteller_unresolved_threads",
        "storyteller_thematic_context",
        "storyteller_progression_hooks",
        "storyteller_emphasis_guidance",
    }
)

_PLOT_OVERLAY: Final[frozenset[str]] = frozenset(
    {
        "overlay_goal",
        "overlay_pressure",
        "overlay_character_candidate",
    }
)

_DIRECTOR_DIGESTS: Final[frozenset[str]] = frozenset(
    {
        "recent_orchestration",
        "actor_suitability",
        "scene_pressures",
        "user_turn_source",
        "user_steering_hints",
    }
)

_CHARACTER_LANES: Final[frozenset[str]] = frozenset(
    {
        "character_identity",
        "character_expression",
        "character_relationships",
        "scene_context",
        "scene_pressures",
        "director_context",
        "character_private",
        "character_memory",
        "recent_scene_transcript",
        "user_turn_trigger",
        "continuity_summary",
        "librarian_knowledge",
        "librarian_synthesis",
        "authored_character_knowledge",
        "learned_world_knowledge",
        "scene_reference",
        "user_profile",
    }
)

_NARRATOR_PRESENTATION_LANES: Final[frozenset[str]] = frozenset(
    {
        "narrator_environment_baseline",
        "immediate_user_turn_context",
        "triggering_user_context",
        "committed_move",
        "director_decision",
        "environmental_response_obligation",
    }
)

_NARRATOR_ENV_COGNITION_LANES: Final[frozenset[str]] = frozenset(
    {
        "narrator_environment_baseline",
        "immediate_user_turn_context",
        "triggering_user_context",
        "narrator_environment_cognition",
    }
)

_COMMON_INSTRUCTION: Final[frozenset[str]] = frozenset({"inference_instruction"})
_CORRECTION: Final[frozenset[str]] = frozenset({"semantic_correction"})
_PLOT_COGNITION_INIT: Final[frozenset[str]] = frozenset({"active_constraints"})
_PLOT_COGNITION_UPDATE: Final[frozenset[str]] = frozenset(
    {"active_constraints", "advisory_context"}
)
_PLOT_COGNITION_EPISTEMIC: Final[frozenset[str]] = frozenset(
    {"active_constraints", "derived"}
)
_CERTIFICATION_TRUTH: Final[frozenset[str]] = frozenset({"certification_truth"})
_INFRASTRUCTURE_PROVIDER_PROBE: Final[frozenset[str]] = frozenset()

ALLOWED_SOURCE_KINDS: Final[dict[str, frozenset[str]]] = {
    "character_turn": (
        _SCENE_AUTHORITY
        | _STORYTELLER_ADVISORY
        | _PLOT_OVERLAY
        | _CHARACTER_LANES
        | _COMMON_INSTRUCTION
        | _CORRECTION
    ),
    "character_orientation": (
        _SCENE_AUTHORITY
        | _STORYTELLER_ADVISORY
        | _PLOT_OVERLAY
        | _CHARACTER_LANES
        | _COMMON_INSTRUCTION
    ),
    "character_semantic_evaluation": (
        _SCENE_AUTHORITY
        | _CHARACTER_LANES
        | _COMMON_INSTRUCTION
        | frozenset({"active_constraints"})
    ),
    "director_turn": (
        _SCENE_AUTHORITY
        | _STORYTELLER_ADVISORY
        | _PLOT_OVERLAY
        | _DIRECTOR_DIGESTS
        | _COMMON_INSTRUCTION
        | _CORRECTION
        | frozenset({"director_scratch"})
    ),
    "director_semantic_qa": (
        _SCENE_AUTHORITY
        | _DIRECTOR_DIGESTS
        | _COMMON_INSTRUCTION
        | frozenset({"active_constraints"})
    ),
    "narrator_presentation": (
        _SCENE_AUTHORITY
        | _STORYTELLER_ADVISORY
        | _NARRATOR_PRESENTATION_LANES
        | _COMMON_INSTRUCTION
        | _CORRECTION
    ),
    "narrator_environment_cognition": (
        _NARRATOR_ENV_COGNITION_LANES | _COMMON_INSTRUCTION
    ),
    "narrator_semantic_qa": (
        _SCENE_AUTHORITY
        | _NARRATOR_PRESENTATION_LANES
        | _COMMON_INSTRUCTION
        | frozenset({"active_constraints"})
    ),
    "librarian_mediation": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints"})
    ),
    "librarian_mediation_contract_correction": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints"})
    ),
    "librarian_proposal": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints", "librarian_knowledge"})
    ),
    "librarian_proposal_contract_correction": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints", "librarian_knowledge"})
    ),
    "storyteller_post_commit_issue_pressure": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints", "librarian_knowledge"})
    ),
    "storyteller_post_commit_issue_pressure_contract_correction": (
        _COMMON_INSTRUCTION | frozenset({"active_constraints", "librarian_knowledge"})
    ),
    "opening": (
        _SCENE_AUTHORITY
        | _COMMON_INSTRUCTION
        | frozenset({"scene_reference", "character_profile"})
    ),
    "opening_segmentation": (
        _SCENE_AUTHORITY
        | _COMMON_INSTRUCTION
        | frozenset({"opening_text", "scene_reference"})
    ),
    "player_decomposition": (
        _COMMON_INSTRUCTION | frozenset({"player_pvr_entitlement_context"})
    ),
    "player_visibility_triage": _COMMON_INSTRUCTION,
    "storyteller_orientation": (
        _DIRECTOR_DIGESTS
        | _COMMON_INSTRUCTION
        | frozenset({"scene_pressures", "scene_state"})
    ),
    "storyteller_assessment": (
        _COMMON_INSTRUCTION | frozenset({"librarian_knowledge"})
    ),
    "storyteller_certification_eval": _CERTIFICATION_TRUTH,
    "infrastructure_provider_probe": _INFRASTRUCTURE_PROVIDER_PROBE,
    "plot_cognition_init": _PLOT_COGNITION_INIT,
    "plot_cognition_init_contract_correction": _PLOT_COGNITION_INIT,
    "plot_cognition_update": _PLOT_COGNITION_UPDATE,
    "plot_cognition_update_contract_correction": _PLOT_COGNITION_UPDATE,
    "plot_cognition_epistemic_eval": _PLOT_COGNITION_EPISTEMIC,
    "plot_cognition_epistemic_eval_contract_correction": _PLOT_COGNITION_EPISTEMIC,
    "character_advisory_generation": _PLOT_COGNITION_EPISTEMIC,
}


class ManifestProjectionPolicyError(ValueError):
    """Raised when a model-context package violates phase/inference allowlists."""


def validate_model_context_contributions(
    inference_kind: str,
    contributions: Sequence[PromptContribution],
) -> None:
    allowed = ALLOWED_SOURCE_KINDS.get(inference_kind)
    if allowed is None:
        raise ManifestProjectionPolicyError(
            f"unknown inference_kind for model-context validation: {inference_kind}"
        )
    violations: list[str] = []
    for contribution in contributions:
        kind = str(contribution.source_kind)
        if kind not in allowed:
            violations.append(
                f"{contribution.contribution_id}: disallowed source_kind '{kind}' "
                f"for inference_kind '{inference_kind}'"
            )
    if violations:
        raise ManifestProjectionPolicyError(
            "model-context package rejected: " + "; ".join(violations)
        )
