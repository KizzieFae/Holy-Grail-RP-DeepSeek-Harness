"""Deterministic uniform-projection synthesis for checker-safe player turns (#121)."""

from __future__ import annotations

from typing import Any

from perception_channel import infer_channel_from_text, text_has_mixed_perception_modalities
from player_source_accounting import (
    SOURCE_ACCOUNTING_NORMALIZATION,
    normalize_source_for_indexing,
    normalized_source_sha256,
)

UNIFORM_PROJECTION_KIND = "uniform_projection"
UNIFORM_PROJECTION_DERIVATION_PROFILE = "uniform_projection"
UNIFORM_PROJECTION_SYNTHESIS_ROUTE = "checker_uniform"
UNIFORM_PROJECTION_SYNTHESIS_SOURCE = "player_uniform_synthesis"
SEMANTIC_DECOMPOSITION_NOT_PERFORMED = "not_performed"

UNIFORM_PROJECTION_UNIT_ID = "u_uniform"
UNIFORM_PROJECTION_SEGMENT_ID = "s_uniform"


def is_uniform_projection_synthesis_decomposition(decomposition: dict[str, Any] | None) -> bool:
    if not isinstance(decomposition, dict):
        return False
    generation = decomposition.get("generation")
    if not isinstance(generation, dict):
        return False
    if generation.get("derivation_profile") != UNIFORM_PROJECTION_DERIVATION_PROFILE:
        return False
    if generation.get("synthesis_route") != UNIFORM_PROJECTION_SYNTHESIS_ROUTE:
        return False
    return True


def build_uniform_projection_decomposition(
    content: str,
    *,
    checker_audit: dict[str, Any] | None = None,
    inference_id: str | None = None,
) -> dict[str, Any]:
    """Build a checker-routed uniform projection decomposition envelope."""
    normalized = normalize_source_for_indexing(content)
    length = len(normalized)
    checker = dict(checker_audit or {})
    if inference_id:
        checker.setdefault("inference_id", inference_id)

    if length == 0:
        return {
            "perceptual_visibility": {"units": []},
            "source_accounting": {
                "source_length": 0,
                "source_sha256": normalized_source_sha256(normalized),
                "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
                "segments": [
                    {
                        "segment_id": UNIFORM_PROJECTION_SEGMENT_ID,
                        "char_start": 0,
                        "char_end": 0,
                        "disposition": "non_projects",
                        "unit_ids": [],
                    }
                ],
            },
            "generation": {
                "derivation_profile": UNIFORM_PROJECTION_DERIVATION_PROFILE,
                "semantic_decomposition": SEMANTIC_DECOMPOSITION_NOT_PERFORMED,
                "synthesis_route": UNIFORM_PROJECTION_SYNTHESIS_ROUTE,
                "checker": checker,
            },
        }

    return {
        "perceptual_visibility": {
            "units": [
                {
                    "unit_id": UNIFORM_PROJECTION_UNIT_ID,
                    "kind": UNIFORM_PROJECTION_KIND,
                    "text": normalized,
                    "recipients": {
                        "scope": "present",
                        "characters": [],
                        "roles": [],
                    },
                    "source_provenance": {
                        "segment_ids": [UNIFORM_PROJECTION_SEGMENT_ID],
                        "order_index": 0,
                    },
                    "source": UNIFORM_PROJECTION_SYNTHESIS_SOURCE,
                    **(
                        {}
                        if text_has_mixed_perception_modalities(normalized)
                        else {
                            "perception_channel": infer_channel_from_text(normalized).channel
                        }
                    ),
                }
            ]
        },
        "source_accounting": {
            "source_length": length,
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": [
                {
                    "segment_id": UNIFORM_PROJECTION_SEGMENT_ID,
                    "char_start": 0,
                    "char_end": length,
                    "disposition": "projects",
                    "unit_ids": [UNIFORM_PROJECTION_UNIT_ID],
                }
            ],
        },
        "generation": {
            "derivation_profile": UNIFORM_PROJECTION_DERIVATION_PROFILE,
            "semantic_decomposition": SEMANTIC_DECOMPOSITION_NOT_PERFORMED,
            "synthesis_route": UNIFORM_PROJECTION_SYNTHESIS_ROUTE,
            "checker": checker,
        },
    }
