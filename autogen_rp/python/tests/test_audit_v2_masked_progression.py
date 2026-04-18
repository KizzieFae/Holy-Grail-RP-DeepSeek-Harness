"""Strict masked progression observability (GitHub #73) — audit-only, escalation-neutral."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_v2_deterministic import build_masked_progression_strict_payload


def test_masked_progression_strict_fires_on_q2_empty_classifier() -> None:
    cm = MagicMock()
    issue = MagicMock()
    issue.issue_id = "iss1"
    issue.last_turn_index = 5
    issue.status = MagicMock()
    issue.status.value = "escalated"
    issue.participants = ["Alice"]
    issue.status_reason = "pressure"
    issue.last_change = "updated"
    cm.issues = {"iss1": issue}
    cm.public_events = []
    payload = build_masked_progression_strict_payload(
        next_actor="Alice",
        continuity_manager=cm,
        turn_index=5,
        turn_meta={"consequences": []},
        issues_before={},
        move={
            "action": "confronts",
            "dialogue": "",
            "motivation": {
                "goal": "pressure",
                "tactic": "direct",
                "emotional_driver": "tense",
                "risk_level": "medium",
            },
        },
        turn_execution={"attempt_index": 0, "progression_retry_triggered": False},
    )
    assert payload["observation"] == "fired"
    assert "q2_issue_material_change" in payload["reasons"]
    assert payload["signals"]["classifier_lane_empty"] is True


def test_masked_progression_clear_dialogue_only_no_structural_proxy() -> None:
    cm = MagicMock()
    cm.issues = {}
    cm.public_events = []
    payload = build_masked_progression_strict_payload(
        next_actor="Alice",
        continuity_manager=cm,
        turn_index=1,
        turn_meta={"consequences": []},
        issues_before={},
        move={"dialogue": "Hello there.", "action": ""},
        turn_execution={"attempt_index": 0, "progression_retry_triggered": False},
    )
    assert payload["observation"] == "clear"
    assert payload["signals"]["structured_intent_present"] is False


def test_masked_progression_skipped_progression_retry_metadata() -> None:
    cm = MagicMock()
    cm.issues = {}
    cm.public_events = []
    payload = build_masked_progression_strict_payload(
        next_actor="Alice",
        continuity_manager=cm,
        turn_index=1,
        turn_meta={"consequences": []},
        issues_before={},
        move={"action": "acts", "motivation": {"goal": "g", "tactic": "t", "emotional_driver": "e", "risk_level": "low"}},
        turn_execution={"attempt_index": 0, "progression_retry_triggered": True},
    )
    assert payload["observation"] == "skipped"
    assert "progression_retry_path" in payload["limitations"]


def test_masked_progression_skipped_non_initial_attempt() -> None:
    cm = MagicMock()
    issue = MagicMock()
    issue.issue_id = "iss1"
    issue.last_turn_index = 2
    issue.status = MagicMock()
    issue.status.value = "open"
    issue.participants = ["Alice"]
    issue.status_reason = ""
    issue.last_change = ""
    cm.issues = {"iss1": issue}
    cm.public_events = []
    payload = build_masked_progression_strict_payload(
        next_actor="Alice",
        continuity_manager=cm,
        turn_index=2,
        turn_meta={"consequences": []},
        issues_before={},
        move={
            "action": "nods",
            "motivation": {
                "goal": "ack",
                "tactic": "nod",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        turn_execution={"attempt_index": 1, "progression_retry_triggered": False},
    )
    assert payload["observation"] == "skipped"
    assert "non_initial_attempt_index" in payload["limitations"]
