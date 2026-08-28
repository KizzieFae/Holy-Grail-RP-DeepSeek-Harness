"""Bind active scene location to stable referent (#49)."""

from __future__ import annotations

import re

from .story_knowledge_contract import StableRef


def normalize_location_label(location: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(location or "").strip())
    return cleaned or "unknown"


def location_stable_ref(location: str) -> str:
    label = normalize_location_label(location)
    slug = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    return f"location:{slug or 'unknown'}"


def bind_location_stable_ref(location: str | None) -> StableRef:
    label = normalize_location_label(str(location or ""))
    return StableRef(
        ref_kind="location",
        stable_ref=location_stable_ref(label),
        display_hint=label,
    )
