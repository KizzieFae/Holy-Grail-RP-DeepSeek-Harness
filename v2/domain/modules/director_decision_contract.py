"""Deterministic contract normalization for Director auxiliary output."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Literal

CanonicalTensionShift = Literal["escalate", "soften", "steady"]

CANONICAL_TENSION_SHIFTS = frozenset({"escalate", "soften", "steady"})


def normalize_tension_shift(value: Any) -> CanonicalTensionShift:
    """Normalize Director pacing to the closed contract without requiring retry."""
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in CANONICAL_TENSION_SHIFTS:
            return token  # type: ignore[return-value]
    return "steady"


def canonicalize_environment_event(value: Any) -> str:
    """Return a comparison-only exact canonical form; never infer semantics."""
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def normalize_environment_event(
    value: Any,
    *,
    recent_committed_events: Iterable[str],
) -> str:
    """Keep unique text verbatim and blank exact canonical duplicates."""
    if not isinstance(value, str):
        return ""
    proposed = value.strip()
    canonical = canonicalize_environment_event(proposed)
    if not canonical:
        return ""
    committed = {
        candidate
        for item in recent_committed_events
        if (candidate := canonicalize_environment_event(item))
    }
    return "" if canonical in committed else proposed
