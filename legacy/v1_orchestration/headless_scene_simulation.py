"""Wire ``turn_runner.run_character_turns`` without Streamlit (same LLM stack as the app).

Director selection, character generation, narrator render, validation, progression gate,
and continuity updates follow the production path. Use for checklist-style review instead
of only hand-running Streamlit scenes.

Implementation is split across ``headless_session_prepare``, ``headless_turn_runner_wire``,
``headless_simulation_runner``, and ``headless_simulation_reporting``. This module re-exports
the public harness surface for backward-compatible imports and test patching.
"""

from __future__ import annotations

import app_state_helpers as state_helpers
from model_client import create_deepseek_client
from response_validation import parse_director_decision, validate_bot_response

from headless_session_prepare import (
    HeadlessStreamlit,
    _parse_scene_phase,
    prepare_headless_session,
)
from headless_turn_runner_wire import (
    DIRECTOR_SPOTLIGHT_HISTORY_LIMIT,
    ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT,
    ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT,
    ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT,
    ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT,
    ORCHESTRATION_TENSION_HISTORY_LIMIT,
    PROMPT_DIALOGUE_HISTORY_LIMIT,
    PROMPT_STRUCTURED_MOVE_LIMIT,
    build_headless_turn_runner_kwargs,
    get_available_actors_allow_repeat_in_round,
    resolve_bot_reply_limit_deep_simulation,
)
from headless_turn_runner_wire import (
    _issue29_resolve_synthetic_available_actors,
    _wrap_get_available_actors_for_issue29_long_run,
)
from headless_simulation_reporting import format_simulation_audit_markdown
from headless_simulation_runner import HeadlessSimulationResult, run_headless_llm_scene

__all__ = [
    "HeadlessSimulationResult",
    "HeadlessStreamlit",
    "_issue29_resolve_synthetic_available_actors",
    "_parse_scene_phase",
    "_wrap_get_available_actors_for_issue29_long_run",
    "build_headless_turn_runner_kwargs",
    "create_deepseek_client",
    "format_simulation_audit_markdown",
    "get_available_actors_allow_repeat_in_round",
    "parse_director_decision",
    "prepare_headless_session",
    "resolve_bot_reply_limit_deep_simulation",
    "run_headless_llm_scene",
    "state_helpers",
    "validate_bot_response",
]
