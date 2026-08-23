"""Issue #18 — objective production runtime Character validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_DOMAIN_MODULES = Path(__file__).resolve().parents[1] / "modules"
if str(_DOMAIN_MODULES) not in sys.path:
    sys.path.insert(0, str(_DOMAIN_MODULES))

from response_validation import (  # noqa: E402
    contains_unresolved_user_placeholders,
    validate_bot_response_for_runtime,
)
from response_validation_content import USER_PLACEHOLDER_PREFIX  # noqa: E402


def _minimal_move() -> dict:
    return {
        "action": "nods",
        "dialogue": "Hello.",
        "motivation": {
            "goal": "greet",
            "tactic": "friendly",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }


@pytest.mark.parametrize(
    "content",
    [
        "Still waiting on {{user}} to answer.",
        "Dear {{user_name}}, welcome back.",
        "Mixed case {{USER}} placeholder.",
    ],
)
def test_runtime_rejects_unresolved_user_placeholders(content: str) -> None:
    has_placeholder, _ = contains_unresolved_user_placeholders(content)
    assert has_placeholder is True

    ok, reason = validate_bot_response_for_runtime(
        content=content,
        speaker="A",
        move=_minimal_move(),
    )
    assert ok is False
    assert reason.startswith(USER_PLACEHOLDER_PREFIX)


def test_runtime_accepts_prose_that_looks_like_player_speech() -> None:
    content = "Player said hello and waved from the doorway."
    has_placeholder, _ = contains_unresolved_user_placeholders(content)
    assert has_placeholder is False

    ok, reason = validate_bot_response_for_runtime(
        content=content,
        speaker="A",
        move=_minimal_move(),
    )
    assert ok is True
    assert reason == ""


def test_runtime_keeps_registry_validation() -> None:
    move = _minimal_move()
    move["scene_state_updates"] = {
        "sleeping_surface_assignment": {
            "assignee_id": "willow",
            "surface_id": "not_a_real_slot",
        }
    }
    ok, reason = validate_bot_response_for_runtime(
        content="Hello.",
        speaker="A",
        move=move,
        scene_state={"sleeping_surface_slots": ["bed_a"]},
    )
    assert ok is False
    assert "[REGISTRY_SLOT]" in reason
