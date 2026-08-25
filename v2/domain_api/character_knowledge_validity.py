"""Semantic reuse key for Character Librarian cognition (#38)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _fingerprint_dict(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def build_character_knowledge_reuse_key(
    *,
    character_id: str,
    hg_round_id: str,
    turn_index: int,
    continuity_version: int,
    upstream_fingerprint: str,
    director_decision: dict[str, Any] | None,
    correction_context: dict[str, Any] | None,
    kar_fingerprint: str,
    storyteller_package_id: str | None = None,
    storyteller_valid: bool | None = None,
    known_by_snapshot_id: str | None = None,
) -> str:
    parts = [
        f"character:{character_id}",
        f"round:{hg_round_id}",
        f"turn:{turn_index}",
        f"continuity:{continuity_version}",
        f"upstream:{upstream_fingerprint}",
        f"director:{_fingerprint_dict(director_decision)}",
        f"correction:{_fingerprint_dict(correction_context)}",
        f"kar:{kar_fingerprint}",
        f"storyteller:{storyteller_package_id or ''}:{storyteller_valid}",
        f"known_by:{known_by_snapshot_id or ''}",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"char-knowledge-reuse:{digest}"
