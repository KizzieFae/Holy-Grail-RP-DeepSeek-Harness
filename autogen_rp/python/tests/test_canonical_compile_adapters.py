"""Unit tests for canonical compile adapters (schema v3 compile layer)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from canonical_compile_adapters import (
    AdapterRow,
    apply_dense_narrative_cap,
    clamp_authority_to_ceiling,
    resolve_adapter_row,
    strict_fallback_row,
)
from authored_index_compile import compute_knowledge_id, _validate_decomposition


def test_clamp_authority_ceiling_lore_reference() -> None:
    assert clamp_authority_to_ceiling("foundational_truth", "lore_reference") == "reference_only"


def test_clamp_authority_no_op_when_within_ceiling() -> None:
    assert clamp_authority_to_ceiling("behavioral_guidance", "voice_guidance") == "behavioral_guidance"


def test_dense_narrative_cap_demotes_setup_truth() -> None:
    assert apply_dense_narrative_cap("setup_truth") == "reference_only"


def test_dense_narrative_cap_preserves_behavioral() -> None:
    assert apply_dense_narrative_cap("behavioral_guidance") == "behavioral_guidance"


def test_resolve_adapter_missing_uses_strict_fallback() -> None:
    row, fb = resolve_adapter_row("character", "nonexistent_key_xyz")
    assert fb is True
    assert row.knowledge_type == "lore_reference"
    assert row.authority_class == "reference_only"


def test_strict_fallback_matches_resolve() -> None:
    assert strict_fallback_row().knowledge_type == "lore_reference"


def test_knowledge_id_excludes_authority_from_hash_inputs() -> None:
    """Same ref+text+type → same id; authority is not an input to compute_knowledge_id."""
    kid = compute_knowledge_id(
        source_ref="char:Zeta:voice_notes",
        text="Speaks in fragments.",
        knowledge_type="voice_guidance",
    )
    assert kid == compute_knowledge_id(
        source_ref="char:Zeta:voice_notes",
        text="Speaks in fragments.",
        knowledge_type="voice_guidance",
    )


def test_decomposition_unknown_strategy_raises() -> None:
    bad_row = AdapterRow(
        knowledge_type="lore_reference",
        authority_class="reference_only",
        visibility="public",
        decomposition=cast(Any, "multi_row_split"),
    )
    with pytest.raises(ValueError, match="unsupported decomposition"):
        _validate_decomposition(bad_row)
