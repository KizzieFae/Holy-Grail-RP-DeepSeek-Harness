"""Deterministic normalization helpers for resolved outcome registry."""

from __future__ import annotations

import re


def encode_slot_key(aspect_id: str, subject_id: str) -> str:
    return f"{aspect_id}::{subject_id}"


def normalize_scene_commitment_token(s: str, *, max_len: int = 64) -> str:
    t = re.sub(r"[^a-z0-9_:]+", "_", str(s or "").lower().strip()).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t or "x"


def normalize_outcome_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_") or "x"


# Stable private aliases matching pre-split `resolved_outcome_registry` naming.
_normalize_scene_commitment_token = normalize_scene_commitment_token
_normalize_outcome_fragment = normalize_outcome_fragment
