"""Test helpers for Issue #91 player perceptual decomposition."""

from __future__ import annotations

from typing import Any

from player_source_accounting import (
    SOURCE_ACCOUNTING_NORMALIZATION,
    normalize_source_for_indexing,
    normalized_source_sha256,
)


def build_player_decomposition_for_content(
    content: str,
    *,
    kind: str = "speech",
    scope: str = "public",
    characters: list[str] | None = None,
    unit_id: str = "u1",
    segment_id: str = "s1",
) -> dict[str, Any]:
    """Build a minimal valid player decomposition envelope for tests."""
    normalized = normalize_source_for_indexing(content)
    length = len(normalized)
    if length == 0:
        return {
            "perceptual_visibility": {"units": []},
            "source_accounting": {
                "source_length": 0,
                "source_sha256": normalized_source_sha256(normalized),
                "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
                "segments": [
                    {
                        "segment_id": segment_id,
                        "char_start": 0,
                        "char_end": 0,
                        "disposition": "non_projects",
                        "unit_ids": [],
                    }
                ],
            },
            "generation": {"inference_id": "test-player-decomposition"},
        }

    recipients: dict[str, Any] = {
        "scope": scope,
        "characters": list(characters or []),
        "roles": [],
    }
    return {
        "perceptual_visibility": {
            "units": [
                {
                    "unit_id": unit_id,
                    "kind": kind,
                    "text": normalized,
                    "recipients": recipients,
                    "source_provenance": {
                        "segment_ids": [segment_id],
                        "order_index": 0,
                    },
                    "source": "player_decomposition",
                }
            ]
        },
        "source_accounting": {
            "source_length": length,
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": [
                {
                    "segment_id": segment_id,
                    "char_start": 0,
                    "char_end": length,
                    "disposition": "projects",
                    "unit_ids": [unit_id],
                }
            ],
        },
        "generation": {"inference_id": "test-player-decomposition"},
    }


def build_multi_segment_player_decomposition(
  content: str,
  segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a player decomposition with explicit segments and units."""
    normalized = normalize_source_for_indexing(content)
    units = []
    accounting_segments = []
    for index, segment in enumerate(segments):
        unit_id = str(segment.get("unit_id", f"u{index + 1}"))
        segment_id = str(segment.get("segment_id", f"s{index + 1}"))
        start = int(segment["char_start"])
        end = int(segment["char_end"])
        disposition = str(segment.get("disposition", "projects"))
        kind = str(segment.get("kind", "speech"))
        scope = str(segment.get("scope", "public"))
        characters = list(segment.get("characters") or [])
        text = normalized[start:end]
        unit_ids: list[str] = []
        if disposition == "projects":
            unit_ids = [unit_id]
            units.append(
                {
                    "unit_id": unit_id,
                    "kind": kind,
                    "text": text,
                    "recipients": {
                        "scope": scope,
                        "characters": characters,
                        "roles": [],
                    },
                    "source_provenance": {
                        "segment_ids": [segment_id],
                        "order_index": index,
                    },
                    "source": "player_decomposition",
                }
            )
        accounting_segments.append(
            {
                "segment_id": segment_id,
                "char_start": start,
                "char_end": end,
                "disposition": disposition,
                "unit_ids": unit_ids,
            }
        )
    return {
        "perceptual_visibility": {"units": units},
        "source_accounting": {
            "source_length": len(normalized),
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": accounting_segments,
        },
        "generation": {"inference_id": "test-player-decomposition"},
    }
