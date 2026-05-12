"""Memory Implementation Phase A: commit-time writes and perception-filtered observers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from character_state_manager import CharacterStateManager
from memory_layer.facade import commit_character_turn_memory
from memory_layer.writes import commit_character_turn_memory as commit_character_turn_memory_raw
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


def test_actor_episodic_prefers_director_model_reason_208() -> None:
    """GitHub #208: verbatim director_model_reason over merged diagnostics in interpretation."""
    manager = CharacterStateManager()
    cast = ["Alice", "Bob"]
    _register_cast(manager, cast)
    move = {
        "action": "nods",
        "dialogue": "Understood.",
        "motivation": {"goal": "should_not_win", "tactic": "when_model_reason_nonempty"},
        "audibility": "public",
    }
    decision = {
        "director_model_reason": "_MODEL_VERBATIM_208_",
        "reason": "_MERGED_DIAGNOSTICS_MUST_NOT_WIN_WHEN_MODEL_REASON_SET_",
    }
    commit_character_turn_memory_raw(
        state_manager=manager,
        character_names=cast,
        acting_character="Alice",
        move=move,
        director_decision=decision,
        present_characters=cast,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} acted.",
        display_name_for_key=None,
    )
    alice = manager.get_state("Alice")
    assert alice is not None
    joined_summary = " ".join(alice.character_memory_summary)
    assert "_MODEL_VERBATIM_208_" in joined_summary
    assert "_MERGED_DIAGNOSTICS_MUST_NOT_WIN_" not in joined_summary


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


def _display_space_for_underscore_agent(agent_key: str) -> str:
    return str(agent_key or "").replace("_", " ").strip()


def test_observer_writes_public_when_present_labels_differ_and_display_fn_provided() -> None:
    """Issue #99: present_characters may use display labels; cast iterates agent keys."""
    manager = CharacterStateManager()
    keys = ["Hannah_Lovelace", "Marlene_Knox", "Rex_Archer"]
    present_labels = ["Hannah Lovelace", "Marlene Knox", "Rex Archer"]
    _register_cast(manager, keys)

    cm = MagicMock()
    cm.scene_state.present_characters = present_labels

    move = {
        "action": "addresses the room",
        "dialogue": "We need to talk.",
        "motivation": {"goal": "inform", "tactic": "direct"},
    }
    commit_character_turn_memory(
        state_manager=manager,
        character_names=keys,
        acting_character="Hannah_Lovelace",
        move=move,
        director_decision={},
        continuity_manager=cm,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} spoke.",
        display_name_for_key=_display_space_for_underscore_agent,
    )

    marlene = manager.get_state("Marlene_Knox")
    rex = manager.get_state("Rex_Archer")
    assert marlene is not None and rex is not None
    assert "Observed:" in " ".join(marlene.private_memories)
    assert "Observed:" in " ".join(rex.private_memories)


def test_observer_writes_directed_only_for_valid_recipients_mixed_labels() -> None:
    manager = CharacterStateManager()
    keys = ["Alice_A", "Bob_B", "Carol_C"]
    present_labels = ["Alice A", "Bob B", "Carol C"]
    _register_cast(manager, keys)

    cm = MagicMock()
    cm.scene_state.present_characters = present_labels

    move = {
        "action": "leans toward Bob",
        "dialogue": "Just us.",
        "motivation": {"goal": "confer", "tactic": "quiet"},
        "audibility": "directed",
        "audience": ["Bob B"],
    }
    commit_character_turn_memory(
        state_manager=manager,
        character_names=keys,
        acting_character="Alice_A",
        move=move,
        director_decision={},
        continuity_manager=cm,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} directed.",
        display_name_for_key=_display_space_for_underscore_agent,
    )

    bob = manager.get_state("Bob_B")
    carol = manager.get_state("Carol_C")
    assert bob is not None and carol is not None
    assert "Observed:" in " ".join(bob.private_memories)
    assert "Observed:" not in " ".join(carol.private_memories)


def test_observer_private_skips_other_cast_even_with_display_fn() -> None:
    manager = CharacterStateManager()
    keys = ["Alice_A", "Bob_B", "Carol_C"]
    present_labels = ["Alice A", "Bob B", "Carol C"]
    _register_cast(manager, keys)

    cm = MagicMock()
    cm.scene_state.present_characters = present_labels

    move = {
        "action": "mutters",
        "dialogue": "Nobody else should hear this.",
        "audibility": "private",
        "audience": [],
    }
    commit_character_turn_memory(
        state_manager=manager,
        character_names=keys,
        acting_character="Alice_A",
        move=move,
        director_decision={},
        continuity_manager=cm,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} private.",
        display_name_for_key=_display_space_for_underscore_agent,
    )

    bob = manager.get_state("Bob_B")
    assert bob is not None
    assert "Observed:" not in " ".join(bob.private_memories)


def test_observer_skips_without_display_fn_when_recipients_use_display_labels() -> None:
    """Documents legacy mismatch: raw membership fails without display_name_for_key."""
    manager = CharacterStateManager()
    keys = ["Alice_A", "Bob_B"]
    present_labels = ["Alice A", "Bob B"]
    _register_cast(manager, keys)

    commit_character_turn_memory_raw(
        state_manager=manager,
        character_names=keys,
        acting_character="Alice_A",
        move={
            "action": "says hi",
            "dialogue": "Hello all.",
        },
        director_decision={},
        present_characters=present_labels,
        build_memory_fact_summary_fn=lambda ac, m: f"{ac} hi.",
        display_name_for_key=None,
    )

    bob = manager.get_state("Bob_B")
    assert bob is not None
    assert "Observed:" not in " ".join(bob.private_memories)


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
