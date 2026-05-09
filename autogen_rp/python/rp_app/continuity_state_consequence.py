"""Consequence taxonomy and detected-consequence row (types only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConsequenceCategory(Enum):
    """Semantic consequence types detected from structured move analysis.

    These categories capture the dramatic function of a turn rather than
    its surface phrasing, enabling robust consequence detection across
    varied character voices and scene dynamics.
    """

    # Authority dynamics
    AUTHORITY_ASSERTED = "authority_asserted"
    AUTHORITY_CHALLENGED = "authority_challenged"

    # Agreement/alignment
    REFUSAL = "refusal"
    AGREEMENT = "agreement"
    COMMITMENT = "commitment"

    # Territory/presence
    TERRITORIAL_CLAIM = "territorial_claim"
    TERRITORIAL_DENIAL = "territorial_denial"
    ARRIVAL = "arrival"
    EXIT = "exit"
    REPOSITIONING = "repositioning"

    # Access/control
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Scene mediation
    MEDIATION_ATTEMPTED = "mediation_attempted"
    INTERCEPTION = "interception"

    # Tension trajectory
    ESCALATION = "escalation"
    DEESCALATION = "deescalation"

    # Information state
    REVELATION = "revelation"
    CONCEALMENT = "concealment"

    # Persistent scene reality (deterministic lexical signals; not issue pressure)
    PHYSICAL_STATE_SET = "physical_state_set"
    MEDICAL_STATE_SET = "medical_state_set"

    # Future pressure
    DECISION_MADE = "decision_made"
    PLAN_COMMITTED = "plan_committed"
    DEPENDENCY_ADVANCED = "dependency_advanced"


@dataclass(frozen=True)
class DetectedConsequence:
    """A consequence detected from turn analysis.

    Captures what category was detected, confidence level, which fields
    contributed to the detection, and the specific excerpt that triggered it.
    """

    category: ConsequenceCategory
    confidence: str  # 'strong', 'moderate', 'weak'
    source_fields: list[str]  # Which input fields contributed
    excerpt: str  # Specific text that triggered detection (truncated)
