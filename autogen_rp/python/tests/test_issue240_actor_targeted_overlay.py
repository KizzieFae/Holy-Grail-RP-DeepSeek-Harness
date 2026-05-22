"""Issue #240 actor-targeted overlay schedule harness tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from user_trigger_schedule import (  # noqa: E402
    UserTriggerScheduleError,
    actor_names_match,
    load_user_trigger_schedule,
    make_actor_targeted_character_turn_resolver,
    make_resolve_effective_user_trigger_from_schedule,
)


def test_load_legacy_by_orchestration_turn_schedule(tmp_path: Path) -> None:
    p = tmp_path / "sched.json"
    p.write_text(
        json.dumps({"by_orchestration_turn": {"1": "one", "2": "two"}}),
        encoding="utf-8",
    )
    schedule = load_user_trigger_schedule(p, max_orchestration_turn=3)
    assert schedule.by_orchestration_turn == {1: "one", 2: "two"}
    assert schedule.by_actor_targeted_turn == {}


def test_load_actor_targeted_schedule(tmp_path: Path) -> None:
    p = tmp_path / "actor.json"
    p.write_text(
        json.dumps(
            {
                "by_actor_targeted_turn": {
                    "6": {
                        "target_actor": "Willow_Reeves",
                        "trigger": "Willow overlay",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    schedule = load_user_trigger_schedule(p, max_orchestration_turn=12)
    assert len(schedule.by_actor_targeted_turn) == 1
    entry = schedule.by_actor_targeted_turn[6]
    assert entry.target_actor == "Willow_Reeves"
    assert entry.trigger == "Willow overlay"


def test_rejects_shared_turn_keys(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            {
                "by_orchestration_turn": {"3": "turn overlay"},
                "by_actor_targeted_turn": {
                    "3": {"target_actor": "Willow_Reeves", "trigger": "x"}
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(UserTriggerScheduleError, match="cannot share turns"):
        load_user_trigger_schedule(p, max_orchestration_turn=12)


def test_actor_targeted_applies_only_to_target_actor() -> None:
    schedule = load_user_trigger_schedule(
        Path(__file__).resolve().parent.parent
        / "data/issue240/audit_i225_willow_actor_targeted_overlay.json",
        max_orchestration_turn=12,
    )
    base = make_resolve_effective_user_trigger_from_schedule(
        schedule,
        cli_trigger_provided=False,
        cli_trigger_value="",
        built_in_fallback="baseline",
    )
    resolve = make_actor_targeted_character_turn_resolver(schedule, base_resolve=base)
    trig, meta = resolve(6, "Willow_Reeves")
    assert "Willow Reeves ONLY" in trig
    assert meta["overlay_applied"] is True
    assert meta["overlay_schedule_mode"] == "actor_targeted_overlay"
    assert actor_names_match(meta["overlay_target_actor"], "Willow_Reeves")

    trig2, meta2 = resolve(6, "Kizzie")
    assert trig2 == "baseline"
    assert meta2["overlay_applied"] is False
    assert meta2["overlay_skipped_reason"] == "target_actor_did_not_act"


def test_actor_targeted_non_overlay_turn_uses_baseline() -> None:
    schedule = load_user_trigger_schedule(
        Path(__file__).resolve().parent.parent
        / "data/issue240/audit_i225_willow_actor_targeted_overlay.json",
        max_orchestration_turn=12,
    )
    base = make_resolve_effective_user_trigger_from_schedule(
        schedule,
        cli_trigger_provided=False,
        cli_trigger_value="",
        built_in_fallback="baseline",
    )
    resolve = make_actor_targeted_character_turn_resolver(schedule, base_resolve=base)
    trig, meta = resolve(4, "Willow_Reeves")
    assert trig == "baseline"
    assert meta["overlay_applied"] is False
    assert meta["overlay_target_actor"] is None
