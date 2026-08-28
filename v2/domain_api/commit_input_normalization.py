"""Commit-path input normalization shared by validation and commit transaction."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from director_decision_contract import (  # noqa: E402
    normalize_environment_event,
    normalize_tension_shift,
)
from issue240_semantic_evaluation import (  # noqa: E402
    issue240_semantic_evaluation_enabled,
    normalize_issue240_semantic_evaluation_for_continuity,
)

from .continuity_context_projector import collect_recent_environment_evidence  # noqa: E402
from .session_state import LiveSession  # noqa: E402


def normalize_director_auxiliary_fields(
    fixture: LiveSession,
    decision: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(decision)
    normalized["tension_shift"] = normalize_tension_shift(decision.get("tension_shift"))
    normalized["environment_event"] = normalize_environment_event(
        decision.get("environment_event"),
        recent_committed_events=collect_recent_environment_evidence(fixture),
    )
    return normalized


def prepare_commit_move_inputs(
    fixture: LiveSession,
    *,
    validated_move: dict[str, Any],
    director_decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    director = normalize_director_auxiliary_fields(fixture, dict(director_decision))
    move = dict(validated_move)
    if issue240_semantic_evaluation_enabled():
        move = normalize_issue240_semantic_evaluation_for_continuity(move)
    return move, director
