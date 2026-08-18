"""Architecture-quality assessment toggles for headless scenario runs.

Same pattern as ``progression_enforcement_disabled``: ``prepare_headless_session`` sets
``session_state['arch_quality_variant']``; Streamlit leaves it unset (= baseline).

Variants only affect the agreed prompt surfaces / override hook — not thresholds or truth.
"""

from __future__ import annotations

from typing import Any

_VALID = frozenset({"baseline", "a1", "b", "c"})


def arch_quality_variant(st_module: Any) -> str:
    raw = st_module.session_state.get("arch_quality_variant")
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in _VALID:
            return v
    return "baseline"


def arch_quality_a1_suppress_director_soft_prefixes(st_module: Any) -> bool:
    """A1: omit progression / anti-regression / low-pressure director *text* prefixes only."""
    return arch_quality_variant(st_module) == "a1"


def arch_quality_b_no_character_progression_suffix(st_module: Any) -> bool:
    """B: omit PROGRESSION_CHARACTER_SUFFIX on character prompts."""
    return arch_quality_variant(st_module) == "b"


def arch_quality_c_disable_progression_override(st_module: Any) -> bool:
    """C: do not apply resolve_progression_override_actor."""
    return arch_quality_variant(st_module) == "c"
