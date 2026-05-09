"""Continuity engine for RP app.

Converts transient dialogue and structured moves into durable narrative state.
Manages scene state, issues/pressures, public events, and per-character interpretations.

Public API: import types from this module only (``from continuity_state import ...``).
Implementation is split across ``continuity_state_*.py`` siblings.
"""

from __future__ import annotations

from continuity_state_canon import CanonAnchor
from continuity_state_consequence import ConsequenceCategory, DetectedConsequence
from continuity_state_excursion import ExcursionRecord, ExcursionStatus
from continuity_state_interpretation import CharacterInterpretation
from continuity_state_issue import IssueState, IssueStatus
from continuity_state_public_event import PublicEvent
from continuity_state_resolved_outcome import ResolvedOutcome
from continuity_state_scene import ScenePhase, SceneState, create_fresh_scene_state
from continuity_state_snapshot import ContinuitySnapshot
from continuity_state_summary import SummaryBlock

__all__ = [
    "CanonAnchor",
    "CharacterInterpretation",
    "ConsequenceCategory",
    "ContinuitySnapshot",
    "DetectedConsequence",
    "ExcursionRecord",
    "ExcursionStatus",
    "IssueState",
    "IssueStatus",
    "PublicEvent",
    "ResolvedOutcome",
    "ScenePhase",
    "SceneState",
    "SummaryBlock",
    "create_fresh_scene_state",
]
