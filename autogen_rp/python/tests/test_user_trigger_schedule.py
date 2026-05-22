"""Unit tests for headless user-trigger schedule JSON (harness-only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from user_trigger_schedule import (  # noqa: E402
    UserTriggerScheduleError,
    load_user_trigger_schedule,
    make_resolve_effective_user_trigger,
    make_resolve_effective_user_trigger_from_schedule,
)


def test_load_valid_schedule(tmp_path: Path) -> None:
    p = tmp_path / "sched.json"
    p.write_text(
        json.dumps(
            {
                "default_trigger": "  from json  ",
                "by_orchestration_turn": {"1": " override one ", "2": "two"},
            }
        ),
        encoding="utf-8",
    )
    schedule = load_user_trigger_schedule(p, max_orchestration_turn=3)
    assert schedule.default_trigger == "from json"
    assert schedule.by_orchestration_turn == {1: "override one", 2: "two"}


def test_load_rejects_unknown_key(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"default_trigger": "x", "extra": 1}), encoding="utf-8")
    with pytest.raises(UserTriggerScheduleError, match="unknown top-level"):
        load_user_trigger_schedule(p, max_orchestration_turn=1)


def test_load_rejects_key_above_max(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps({"by_orchestration_turn": {"3": "nope"}}),
        encoding="utf-8",
    )
    with pytest.raises(UserTriggerScheduleError, match="exceeds max"):
        load_user_trigger_schedule(p, max_orchestration_turn=2)


def test_resolve_precedence() -> None:
    r = make_resolve_effective_user_trigger(
        {2: "by map"},
        cli_trigger_provided=True,
        cli_trigger_value="cli",
        json_default="jsondef",
        built_in_fallback="builtin",
    )
    assert r(1) == "cli"
    assert r(2) == "by map"
    r2 = make_resolve_effective_user_trigger(
        {},
        cli_trigger_provided=False,
        cli_trigger_value="",
        json_default="jsondef",
        built_in_fallback="builtin",
    )
    assert r2(1) == "jsondef"
    r3 = make_resolve_effective_user_trigger(
        {},
        cli_trigger_provided=False,
        cli_trigger_value="",
        json_default=None,
        built_in_fallback="builtin",
    )
    assert r3(5) == "builtin"
