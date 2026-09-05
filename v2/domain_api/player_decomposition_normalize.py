"""Domain Host player decomposition normalization (#124)."""

from __future__ import annotations

from typing import Any

from player_semantic_normalization import normalize_player_semantic_decomposition


def normalize_player_decomposition_request(
    *,
    content: str,
    speaker: str,
    semantic_decomposition: dict[str, Any] | None,
    generation: dict[str, Any] | None = None,
    attempt_index: int = 0,
) -> dict[str, Any]:
    return normalize_player_semantic_decomposition(
        content=content,
        speaker=speaker,
        semantic_decomposition=semantic_decomposition,
        generation=generation,
        attempt_index=attempt_index,
    )
