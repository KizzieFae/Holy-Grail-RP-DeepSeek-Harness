"""Hybrid tension pacing: Director-primary with consequence-informed fallback.

Neutrality = absence of a valid directional ``tension_shift`` token (escalate/soften).
When neutral, ``consequence_tension_recommendation`` maps classified ``tags`` to up/down/hold.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

DirectionalPacing = Literal["escalate", "soften"]
ConsequencePacing = Literal["up", "down", "hold"]
PacingSource = Literal["director", "consequence", "none"]

_UP_TAGS = frozenset(
    {
        "authority_challenged",
        "refusal",
        "territorial_denial",
        "access_denied",
        "escalation",
        "interception",
        "territorial_claim",
    }
)
_DOWN_TAGS = frozenset(
    {
        "agreement",
        "commitment",
        "deescalation",
        "mediation_attempted",
        "access_granted",
    }
)


def parse_director_directional_pacing(
    director_decision: dict[str, Any] | None,
) -> Optional[DirectionalPacing]:
    """Return escalate/soften when Director supplies a valid directional token; else None (neutral).

    Malformed values (wrong type, unknown string, whitespace-only) are neutral.
    """
    if not isinstance(director_decision, dict):
        return None
    raw = director_decision.get("tension_shift", "")
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None
    token = raw.strip().lower()
    if token == "escalate":
        return "escalate"
    if token == "soften":
        return "soften"
    return None


def director_pacing_is_neutral(director_decision: dict[str, Any] | None) -> bool:
    """True iff there is no valid directional pacing token (hybrid spec)."""
    return parse_director_directional_pacing(director_decision) is None


def consequence_tension_recommendation(turn_consequences: dict[str, Any]) -> ConsequencePacing:
    """Map classified ``tags`` to a single tension nudge (neutral Director path only).

    Presence-based: any UP tag -> U, any DOWN tag -> D; U and D -> hold; unknown tags ignored.
    Order-independent. No weighting or scoring.
    """
    raw = turn_consequences.get("tags") if isinstance(turn_consequences, dict) else None
    if not isinstance(raw, list):
        return "hold"

    has_u = False
    has_d = False
    for item in raw:
        t = str(item).strip().lower()
        if not t:
            continue
        if t in _UP_TAGS:
            has_u = True
        elif t in _DOWN_TAGS:
            has_d = True

    if has_u and has_d:
        return "hold"
    if has_u:
        return "up"
    if has_d:
        return "down"
    return "hold"


def resolve_hybrid_pacing(
    *,
    director_decision: dict[str, Any] | None,
    turn_consequences: dict[str, Any],
) -> tuple[PacingSource, ConsequencePacing, bool]:
    """Decide pacing source and direction without mutating scene state.

    Returns:
        (pacing_source, pacing_direction, director_neutral)

    ``pacing_direction`` is always ``up``/``down``/``hold`` in the consequence vocabulary;
    for Director escalate/soften this is mapped to up/down.
    """
    directional = parse_director_directional_pacing(director_decision)
    neutral = directional is None

    if directional == "escalate":
        return ("director", "up", False)
    if directional == "soften":
        return ("director", "down", False)

    rec = consequence_tension_recommendation(turn_consequences)
    if rec == "up":
        return ("consequence", "up", True)
    if rec == "down":
        return ("consequence", "down", True)
    return ("none", "hold", True)


def apply_consequence_up_saturation_gate(
    *,
    pacing_source: PacingSource,
    pacing_direction: ConsequencePacing,
    current_tension_level: str | None,
) -> tuple[PacingSource, ConsequencePacing, bool]:
    """Suppress consequence-driven ``up`` when tension is already at the ladder top.

    Returns ``(effective_source, effective_direction, consequence_up_suppressed_saturation)``.
    Director pacing is unchanged (``pacing_source`` is never ``consequence`` there).
    """
    if pacing_source != "consequence" or pacing_direction != "up":
        return (pacing_source, pacing_direction, False)
    if str(current_tension_level or "").strip().lower() != "extreme":
        return (pacing_source, pacing_direction, False)
    return ("none", "hold", True)
