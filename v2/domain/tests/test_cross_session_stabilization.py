"""Cross-session stabilization: injection report, toggle, promote filter."""

import json
import sys
from pathlib import Path
import pytest


from cross_session_memory_policy import (
    is_cross_session_memory_enabled,
    new_injection_report,
    should_promote_cross_session,
)
from session_manager import SESSION_INDEX_FILE_NAME, SessionManager


def test_should_promote_keeps_interaction_like_history() -> None:
    assert should_promote_cross_session(
        "Alex said or signaled: hello there.", "relationship_history"
    )
    assert should_promote_cross_session(
        "Observed: Celina refused the offer.", "relationship_history"
    )


def test_should_promote_drops_purely_descriptive_without_interaction() -> None:
    assert not should_promote_cross_session(
        "The room smelled of cinnamon and wildflowers.",
        "relationship_history",
    )


def test_get_cross_session_memories_populates_injection_report(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="sess_a",
        team_state={},
        characters=["Ayame"],
        metadata={
            "summary": "s",
            "memory_buckets": {
                "session_summary": "Ayame and Alex talked by the forge.",
                "persistent_world_facts": ["Recent recurring location: Workshop."],
                "user_preferences": [],
            },
            "character_states": {
                "Ayame": {
                    "name": "Ayame",
                    "relationships": {
                        "Traveler": {
                            "entity_type": "user",
                            "history": [
                                "Traveler said or signaled: Watch the door.",
                                "The air was thick with perfume.",
                            ],
                            "trust": 5,
                            "interaction_count": 1,
                            "last_summary": "Traveler said or signaled: Watch the door.",
                        },
                    },
                }
            },
        },
        chat_history=[],
    )
    report = new_injection_report(
        cross_session_memory_enabled=True,
        exclude_session_id=None,
        indexed_session_count=0,
    )
    manager.get_cross_session_memories(
        character_names=["Ayame"],
        user_name="Traveler",
        injection_report=report,
    )
    assert any(
        i.get("preview", "").startswith("Traveler said")
        for i in report.get("load_items", [])
    )
    filtered = report.get("load_items_filtered", [])
    assert any("perfume" in str(i.get("preview", "")).lower() for i in filtered)


def test_example_report_json_shape(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Document example output shape (used for operator verification)."""
    manager = SessionManager(tmp_path)
    manager.save_session(
        session_id="demo_sess",
        team_state={},
        characters=["Ayame"],
        metadata={
            "summary": "demo",
            "memory_buckets": {
                "session_summary": "Ayame greeted the traveler.",
                "persistent_world_facts": ["Forge heat defines the workshop."],
                "user_preferences": ["Call me Alex."],
            },
            "character_states": {
                "Ayame": {
                    "name": "Ayame",
                    "relationships": {
                        "Alex": {
                            "entity_type": "user",
                            "history": ["Alex said or signaled: Stay close."],
                            "trust": 6,
                            "interaction_count": 1,
                            "last_summary": "Alex said or signaled: Stay close.",
                        },
                    },
                }
            },
        },
        chat_history=[],
    )
    report = new_injection_report(
        cross_session_memory_enabled=True,
        exclude_session_id=None,
        indexed_session_count=0,
    )
    manager.get_cross_session_memories(
        character_names=["Ayame"],
        user_name="Alex",
        injection_report=report,
    )
    report["indexed_session_count"] = 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    out = capsys.readouterr().out
    assert "cross_session_memory_enabled" in out
    assert "load_items" in out
    assert (tmp_path / SESSION_INDEX_FILE_NAME).exists()


def test_env_toggle_cross_session_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_CROSS_SESSION_MEMORY", "0")
    from cross_session_memory_policy import is_cross_session_memory_enabled as enabled_fn

    assert enabled_fn() is False
