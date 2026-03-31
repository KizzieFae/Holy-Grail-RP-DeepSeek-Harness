"""Headless deep simulation helpers (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from headless_scene_simulation import (  # noqa: E402
    get_available_actors_allow_repeat_in_round,
    resolve_bot_reply_limit_deep_simulation,
)
from response_validation_selection import get_available_actors  # noqa: E402


def test_resolve_bot_reply_limit_deep_simulation() -> None:
    assert resolve_bot_reply_limit_deep_simulation(2, 10) == 10
    assert resolve_bot_reply_limit_deep_simulation(3, 8) == 8
    assert resolve_bot_reply_limit_deep_simulation(2, None) == 2
    assert resolve_bot_reply_limit_deep_simulation(0, 5) == 0


def test_get_available_actors_allow_repeat_ignores_used() -> None:
    names = ["A", "B"]
    assert get_available_actors(names, ["A"], None, None) == ["B"]
    assert get_available_actors_allow_repeat_in_round(names, ["A"], None, None) == [
        "A",
        "B",
    ]
