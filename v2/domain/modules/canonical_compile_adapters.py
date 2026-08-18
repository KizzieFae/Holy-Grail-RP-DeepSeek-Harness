"""Phase 3.4 compile-layer: deterministic adapter rows for schema_version 3 canonical fields.

Runtime retrieval does not import this module. Mapping table grows incrementally per phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# --- Decomposition: exactly one strategy per (etype, key_path) in the registry ---

DecompositionStrategy = Literal[
    "whole_value_single_row",
    "one_row_per_string_list_item",
    "nested_object_leaf_strings",
    "role_slots_array_rows",
    "emit_zero_chunks",
]

ALLOWED_DECOMPOSITION_STRATEGIES: frozenset[str] = frozenset(
    {
        "whole_value_single_row",
        "one_row_per_string_list_item",
        "nested_object_leaf_strings",
        "role_slots_array_rows",
        "emit_zero_chunks",
    }
)

# --- Authority ordering for ceiling clamp (low -> high) ---

_AUTHORITY_RANK: dict[str, int] = {
    "reference_only": 0,
    "interpretive_guidance": 1,
    "behavioral_guidance": 2,
    "setup_truth": 3,
    "foundational_truth": 4,
}

_RANK_TO_AUTHORITY: list[str] = [
    "reference_only",
    "interpretive_guidance",
    "behavioral_guidance",
    "setup_truth",
    "foundational_truth",
]

# Maximum allowed rank per knowledge_type (canonical contract §4a)
_CEILING_RANK_BY_TYPE: dict[str, int] = {
    "identity_fact": 4,
    "relationship_fact": 4,
    "world_rule": 4,
    "scene_setup_fact": 3,
    "role_constraint": 4,
    "behavioral_tendency": 2,
    "goal_or_drive": 2,
    "voice_guidance": 2,
    "interpretive_frame": 1,
    "lore_reference": 0,
}


@dataclass(frozen=True)
class AdapterRow:
    """Single (etype, key_path) mapping. No optional decomposition: strategy is mandatory."""

    knowledge_type: str
    authority_class: str
    visibility: str
    decomposition: DecompositionStrategy


# Registry key: (manifest entry type, key_path)
_ADAPTER_REGISTRY: dict[tuple[str, str], AdapterRow] = {}


def register_adapter(etype: str, key_path: str, row: AdapterRow) -> None:
    _ADAPTER_REGISTRY[(etype, key_path)] = row


def lookup_adapter(etype: str, key_path: str) -> AdapterRow | None:
    return _ADAPTER_REGISTRY.get((etype, key_path))


def strict_fallback_row() -> AdapterRow:
    """Uncertain classification: reference_only + lore_reference; non-behavioral default."""
    return AdapterRow(
        knowledge_type="lore_reference",
        authority_class="reference_only",
        visibility="public",
        decomposition="whole_value_single_row",
    )


def authority_rank(authority_class: str) -> int:
    r = _AUTHORITY_RANK.get(str(authority_class))
    if r is None:
        raise ValueError(f"unknown authority_class: {authority_class!r}")
    return r


def ceiling_rank_for_knowledge_type(knowledge_type: str) -> int:
    r = _CEILING_RANK_BY_TYPE.get(str(knowledge_type))
    if r is None:
        raise ValueError(f"unknown knowledge_type for ceiling: {knowledge_type!r}")
    return r


def clamp_authority_to_ceiling(authority_class: str, knowledge_type: str) -> str:
    """Clamp assigned authority down so rank <= ceiling(knowledge_type)."""
    ar = authority_rank(authority_class)
    cr = ceiling_rank_for_knowledge_type(knowledge_type)
    eff = min(ar, cr)
    return _RANK_TO_AUTHORITY[eff]


def apply_dense_narrative_cap(authority_class: str) -> str:
    """Dense / narrative sources: never setup_truth or foundational_truth."""
    r = authority_rank(authority_class)
    if r >= authority_rank("setup_truth"):
        return "reference_only"
    return authority_class


def resolve_adapter_row(etype: str, key_path: str) -> tuple[AdapterRow, bool]:
    """Return (row, used_fallback)."""
    row = lookup_adapter(etype, key_path)
    if row is None:
        return strict_fallback_row(), True
    return row, False


def _register_default_adapters() -> None:
    """Real project character / template / setup / lore / initial_message shapes (Phase 2)."""

    # --- compile_sample + generic character card fields (data/autogen_characters) ---
    register_adapter(
        "character",
        "voice_notes",
        AdapterRow(
            knowledge_type="voice_guidance",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "name",
        AdapterRow(
            knowledge_type="identity_fact",
            authority_class="foundational_truth",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "description",
        AdapterRow(
            knowledge_type="behavioral_tendency",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "personality",
        AdapterRow(
            knowledge_type="behavioral_tendency",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "speaking_style",
        AdapterRow(
            knowledge_type="voice_guidance",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "goals",
        AdapterRow(
            knowledge_type="goal_or_drive",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "medium_term_goal",
        AdapterRow(
            knowledge_type="goal_or_drive",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "core_goals",
        AdapterRow(
            knowledge_type="goal_or_drive",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="one_row_per_string_list_item",
        ),
    )
    register_adapter(
        "character",
        "voice_profile",
        AdapterRow(
            knowledge_type="voice_guidance",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="nested_object_leaf_strings",
        ),
    )
    register_adapter(
        "character",
        "reaction_profile",
        AdapterRow(
            knowledge_type="interpretive_frame",
            authority_class="interpretive_guidance",
            visibility="character_scoped",
            decomposition="nested_object_leaf_strings",
        ),
    )
    register_adapter(
        "character",
        "speech_fingerprint",
        AdapterRow(
            knowledge_type="voice_guidance",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="nested_object_leaf_strings",
        ),
    )
    register_adapter(
        "character",
        "system_prompt",
        AdapterRow(
            knowledge_type="behavioral_tendency",
            authority_class="behavioral_guidance",
            visibility="character_scoped",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "character",
        "lore_facts",
        AdapterRow(
            knowledge_type="lore_reference",
            authority_class="reference_only",
            visibility="character_scoped",
            decomposition="one_row_per_string_list_item",
        ),
    )

    # --- scene templates (data/scene_templates) ---
    register_adapter(
        "template",
        "tone",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="template_participants",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "template",
        "premise",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="template_participants",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "template",
        "opening_text",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="template_participants",
            decomposition="whole_value_single_row",
        ),
    )
    register_adapter(
        "template",
        "location_entry_slots",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="template_participants",
            decomposition="one_row_per_string_list_item",
        ),
    )
    register_adapter(
        "template",
        "role_slots",
        AdapterRow(
            knowledge_type="role_constraint",
            authority_class="foundational_truth",
            visibility="template_participants",
            decomposition="role_slots_array_rows",
        ),
    )
    register_adapter(
        "template",
        "initial_messages",
        AdapterRow(
            knowledge_type="lore_reference",
            authority_class="reference_only",
            visibility="template_participants",
            decomposition="emit_zero_chunks",
        ),
    )

    register_adapter(
        "setup",
        "stakes",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="template_participants",
            decomposition="whole_value_single_row",
        ),
    )

    register_adapter(
        "lore_file",
        "__chunk__",
        AdapterRow(
            knowledge_type="lore_reference",
            authority_class="reference_only",
            visibility="public",
            decomposition="whole_value_single_row",
        ),
    )

    register_adapter(
        "initial_message",
        "__body__",
        AdapterRow(
            knowledge_type="scene_setup_fact",
            authority_class="setup_truth",
            visibility="public",
            decomposition="whole_value_single_row",
        ),
    )


_register_default_adapters()
