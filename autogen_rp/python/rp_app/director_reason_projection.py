"""Pure helpers for assembling Director ``decision[\"reason\"]`` (GitHub #210 C-A).

Orchestration continues to mutate machine fields (``next_actor``, attribution records);
this module owns **deterministic concatenation only** plus the **caller-supplied**
terminal normalization (display-name substitution).

Hard-route Director paths (forced speaker, continuation override, empty pool) do **not**
use these helpers yet; parity scope is ``finalize_director_selection_after_llm`` only.

No public structured segment arrays — C-A is string assembly parity only.

"""

from __future__ import annotations

from collections.abc import Callable


def merge_addressee_alignment_reason(
    previous_reason: str, prev_actor: str, resolved_actor: str
) -> str:
    """Match ``semantic_validation.apply_gated_addressee_alignment_*`` reason merge."""
    suffix = (
        f"| Addressee alignment (progression gate): {prev_actor} -> {resolved_actor}"
    )
    prior = str(previous_reason or "").strip()
    return f"{prior} {suffix}".strip() if prior else suffix.strip()


def merge_progression_override_reason(
    previous_reason: str, original_actor: str, new_actor: str
) -> str:
    """Append progression override prose; mirrors ``finalize_director_selection_after_llm``."""
    return (
        f"{str(previous_reason or '')} | Progression override from {original_actor} to {new_actor}"
    ).strip(" |")


def merge_participation_fairness_reason(
    previous_reason: str, unheard_actor: str
) -> str:
    """Mirror ``apply_participation_fairness_to_decision`` reason branch."""
    note = (
        f"Spotlight fairness: rotate to {unheard_actor} "
        "(present participant not yet heard this response cycle)"
    )
    prev = str(previous_reason or "").strip()
    return f"{prev} | {note}".strip(" |") if prev else note


def merge_turn_selection_diagnostics_reason(
    previous_reason: str, extra_parts: list[str]
) -> str:
    """Append validation/routing diagnostics; mirrors finalize branch."""
    return (
        f"{str(previous_reason or '')} | {' | '.join(extra_parts)}"
    ).strip(" |")


def finalize_reason_with_display_substitution(
    assembled_reason_before_normalize: str,
    *,
    substitute_display_names: Callable[[str], str],
) -> str:
    """Apply terminal human-log normalization (display names for agent keys)."""
    return substitute_display_names(str(assembled_reason_before_normalize or ""))

