"""Memory Implementation Phase A: commit-time writes and perception-filtered observers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from character_state_manager import CharacterStateManager
from memory_layer.facade import commit_character_turn_memory
from memory_layer.writes import resolve_present_characters


def _register_cast(manager: CharacterStateManager, names: list[str]) -> None:
    for name in names:
        manager.register_character(name, CharacterState(name=name))


def test_resolve_present_characters_prefers_scene_state() -> None:
    cm = MagicMock()
    cm.scene_state.present_characters = ["A", "B"]
    assert resolve_present_characters(continuity_manager=cm, char_names=["X", "Y"]) == [
        "A",
        "B",
    ]


def test_resolve_present_characters_falls_back_when_empty() -> None:
    cm = MagicMock()
    cm.scene_state.present_characters = []
    assert resolve_present_characters(continuity_manager=cm, char_names=["X", "Y"]) == [
        "X",
        "Y",
    ]


def test_resolve_present_characters_falls_back_when_no_scene() -> None:
    assert resolve_present_characters(continuity_manager=None, char_names=["X"]) == ["X"]


def test_observer_writes_only_for_event_knowledge_recipients_private() -> None:
    manager = CharacterStateManager()
    cast = ["Alice", "Bob", "Carol"]
    _register_cast(manager, cast)

    move = {
        "action": "whispers to Bob",
        "dialogue": "Meet me at midnight.",
        "motivation": {"goal": "conspire", "tactic": "whisper"},
        "audibility": "private",
        "audience": [],
    }
    decision = {"reason": "Testing private beat."}

    commit_character_turn_memory(
        state_manager=manager,
        character_names=cast,
        acting_character="Alice",
        move=move,
        director_decision=decision,
        continuity_manager=None,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} did something.",
    )

    alice = manager.get_state("Alice")
    bob = manager.get_state("Bob")
    carol = manager.get_state("Carol")
    assert alice is not None and bob is not None and carol is not None

    alice_private = " ".join(alice.private_memories)
    bob_private = " ".join(bob.private_memories)
    carol_private = " ".join(carol.private_memories)

    assert "Alice did something" in alice_private
    assert "Observed:" in bob_private
    assert "Observed:" not in carol_private


def test_observer_writes_all_present_for_public_move() -> None:
    manager = CharacterStateManager()
    cast = ["Alice", "Bob", "Carol"]
    _register_cast(manager, cast)

    move = {
        "action": "shouts to the room",
        "dialogue": "Everyone listen!",
        "motivation": {"goal": "gather attention", "tactic": "shout"},
    }
    decision: dict = {}

    commit_character_turn_memory(
        state_manager=manager,
        character_names=cast,
        acting_character="Alice",
        move=move,
        director_decision=decision,
        continuity_manager=None,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} public act.",
    )

    bob = manager.get_state("Bob")
    carol = manager.get_state("Carol")
    assert bob is not None and carol is not None
    assert "Observed:" in " ".join(bob.private_memories)
    assert "Observed:" in " ".join(carol.private_memories)
