"""Tests for character card loading and management."""

import json
import os
import sys
from pathlib import Path

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_loader import CHARACTER_MOVE_SCHEMA, _normalize_relationships
from character_state import CharacterState, CharacterStateManager
from scene_lifecycle_start import (
    _seed_scene_role_character_priorities,
    _seed_scene_role_relationship_context,
)


def create_test_model_client():
    """Helper to create a test model client."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    return OpenAIChatCompletionClient(
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key=api_key,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "family": "unknown",
            "structured_output": True,
        },
    )


def test_character_card_schema():
    """Test that character card schema is valid."""
    character_card = {
        "name": "Elara",
        "description": "A wise mage from the northern mountains",
        "system_prompt": "You are Elara, a wise mage...",
        "speaking_style": "Thoughtful, uses archaic words",
        "goals": "Protect ancient knowledge",
        "relationships": {"player": "cautious ally"},
        "lore_facts": ["Studied at the Academy", "Knows dragon lore"],
    }

    # Validate required fields
    assert "name" in character_card
    assert "description" in character_card
    assert "system_prompt" in character_card

    # Validate types
    assert isinstance(character_card["name"], str)
    assert isinstance(character_card["lore_facts"], list)


def test_character_card_json_serialization():
    """Test that character cards can be saved and loaded as JSON."""
    character_card = {
        "name": "TestCharacter",
        "description": "A test character",
        "system_prompt": "You are a test character.",
        "speaking_style": "Casual",
        "goals": "Help with testing",
        "lore_facts": ["Fact 1", "Fact 2"],
    }

    # Save to JSON
    test_file = "test_character.json"
    with open(test_file, "w") as f:
        json.dump(character_card, f, indent=2)

    # Load from JSON
    with open(test_file, "r") as f:
        loaded = json.load(f)

    assert loaded["name"] == character_card["name"]
    assert loaded["lore_facts"] == character_card["lore_facts"]

    # Cleanup
    os.remove(test_file)


def test_character_move_schema_requires_structured_motivation():
    """Test that the move schema requires structured motivation fields."""
    assert "motivation" in CHARACTER_MOVE_SCHEMA["properties"]
    assert CHARACTER_MOVE_SCHEMA["required"] == ["action", "motivation"]
    assert CHARACTER_MOVE_SCHEMA["properties"]["motivation"]["required"] == [
        "goal",
        "tactic",
        "emotional_driver",
        "risk_level",
    ]
    assert "scene_state_updates" in CHARACTER_MOVE_SCHEMA["properties"]
    scene_state_updates = CHARACTER_MOVE_SCHEMA["properties"]["scene_state_updates"]
    assert "sleeping_surface_assignment" in scene_state_updates["properties"]
    sleeping_assignment = scene_state_updates["properties"]["sleeping_surface_assignment"]
    assert sleeping_assignment["required"] == ["assignee_id", "surface_id"]
    assert "actively enforces against present resistance or dispute" in sleeping_assignment[
        "description"
    ]
    assert "changes or newly settles that assignment" in sleeping_assignment[
        "description"
    ]
    assert "Exactly one valid surface_id" in sleeping_assignment["properties"][
        "surface_id"
    ]["description"]


def test_character_state_preserves_identity_anchors_and_memory_summaries():
    """Test that character state retains identity anchors and per-character memory summaries."""
    state = CharacterState(
        name="Mira",
        long_term_goal="Expose Thorn",
        core_goals=["Expose Thorn", "Protect the archive"],
        voice_profile={"speech_style": "blunt", "sentence_length": "short"},
        reaction_profile={"worldview": "assumes deception", "trust_bias": "low"},
        speech_fingerprint={"question_frequency": "high", "formality_level": "casual"},
    )

    state.update_from_move(
        action="leaned against the table",
        dialogue="You're hiding something.",
        motivation={
            "goal": "expose Thorn",
            "tactic": "provoke anger",
            "emotional_driver": "resentment",
            "risk_level": "high",
        },
    )
    state.remember_event(
        "Thorn avoided the question.",
        "I read his silence as confirmation that he is hiding the map.",
    )

    prompt_context = state.to_prompt_context()

    assert state.current_objective == "expose Thorn"
    assert state.short_term_tactic == "provoke anger"
    assert state.local_task_goal == "expose Thorn"
    assert state.local_task_tactic == "provoke anger"
    assert state.emotional_state == "resentment"
    assert "Voice profile" in prompt_context
    assert "Reaction profile" in prompt_context
    assert "Speech fingerprint" in prompt_context
    assert "private interpretation summary" in prompt_context.lower()
    assert "hiding the map" in prompt_context


def test_character_state_move_updates_do_not_mutate_protected_identity_anchors():
    """Test that short-term move updates preserve stable identity anchor fields."""
    state = CharacterState(
        name="Ayame",
        description="A disciplined investigator.",
        personality="Controlled and severe",
        long_term_goal="Protect the forge",
        medium_term_goal="Corner the saboteur",
        core_goals=["Protect the forge", "Expose betrayal"],
        voice_profile={"cadence": "measured", "tone": "cool"},
        reaction_profile={"under_pressure": "narrows focus"},
        speech_fingerprint={"signature": "spare phrasing"},
        hidden_agenda="Test the loyalty of everyone in the room.",
    )
    anchor_snapshot = state.identity_anchor_snapshot()

    state.update_from_move(
        action="steps in front of the forge",
        dialogue="No one leaves until I have the truth.",
        motivation={
            "goal": "force a confession now",
            "tactic": "apply direct pressure",
            "emotional_driver": "anger",
            "risk_level": "high",
        },
    )

    assert state.identity_anchor_snapshot() == anchor_snapshot
    assert state.current_objective == "force a confession now"
    assert state.short_term_tactic == "apply direct pressure"
    assert state.local_task_goal == "force a confession now"
    assert state.local_task_tactic == "apply direct pressure"
    assert state.emotional_state == "anger"


def test_character_state_preserves_persistent_goal_when_new_move_is_only_a_local_task() -> (
    None
):
    state = CharacterState(
        name="Celina",
        long_term_goal="Protect what falls under her roof",
        medium_term_goal="Keep the refuge stable through the night",
        current_objective="stabilize Kizzie while controlling the immediate scene around them",
        short_term_tactic="keep the scene focused on assessment and control",
    )

    state.update_from_move(
        action="reached for the towel",
        dialogue="Hold still.",
        motivation={
            "goal": "dry the tail quickly",
            "tactic": "finish the immediate care subtask without inviting extra conversation",
            "emotional_driver": "practical focus",
            "risk_level": "low",
        },
    )

    prompt_context = state.to_prompt_context()

    assert (
        state.current_objective
        == "stabilize Kizzie while controlling the immediate scene around them"
    )
    assert state.short_term_tactic == "keep the scene focused on assessment and control"
    assert state.local_task_goal == "dry the tail quickly"
    assert (
        state.local_task_tactic
        == "finish the immediate care subtask without inviting extra conversation"
    )
    assert "Current local task: dry the tail quickly" in prompt_context
    assert (
        "Local execution method: finish the immediate care subtask without inviting extra conversation"
        in prompt_context
    )


def test_character_state_tracks_cross_session_user_relationship_memory() -> None:
    state = CharacterState(name="Celina", trust_toward_player=7)

    state.remember_user_interaction("Alex", "Alex said or signaled: I prefer honesty.")
    state.remember_user_interaction("Alex", "Alex said or signaled: Call me Alex.")

    relationship = state.relationships["Alex"]

    assert relationship["entity_type"] == "user"
    assert relationship["trust"] == 7
    assert relationship["interaction_count"] == 2
    assert relationship["last_summary"] == "Alex said or signaled: Call me Alex."
    assert state.cross_session_user_context("Alex") == [
        "Alex said or signaled: I prefer honesty.",
        "Alex said or signaled: Call me Alex.",
    ]


def test_character_state_prompt_context_surfaces_focused_goal_threads_and_secondary_posture() -> (
    None
):
    state = CharacterState(
        name="Celina",
        long_term_goal="Maintain control without becoming dependent.",
        medium_term_goal="Get through the night with the scene contained.",
        core_goals=["Maintain control", "Protect what falls under her care"],
    )

    state.set_relationship_context(
        "Kizzie",
        stance="guarded protective",
        medium_term_goal="stabilize Kizzie and assess whether she is dangerous",
        current_objective="get Kizzie to eat and stay awake",
        tactical_posture="use gruff care to keep emotional distance",
    )
    state.set_relationship_context(
        "Ayame",
        stance="controlled antagonism",
        long_term_goal="deny Ayame leverage over the apartment",
        medium_term_goal="force Ayame to concede procedural control",
        current_objective="make Ayame back off this decision",
        tactical_posture="hold authority without open escalation",
    )
    state.set_relationship_context(
        "Orderly",
        stance="dismissive caution",
        tactical_posture="keep him out of the core exchange unless he interferes",
        threat_level="low",
    )

    prompt_context = state.to_prompt_context(
        relationship_focus_names=["Kizzie", "Ayame"],
        relationship_secondary_names=["Orderly"],
    )

    assert "Key relationship goal threads:" in prompt_context
    assert (
        "Medium-term goal toward them: stabilize Kizzie and assess whether she is dangerous"
        in prompt_context
    )
    assert (
        "Long-term goal toward them: deny Ayame leverage over the apartment"
        in prompt_context
    )
    assert (
        "Immediate objective toward them: get Kizzie to eat and stay awake"
        in prompt_context
    )
    assert "Secondary present-character posture:" in prompt_context
    assert "Orderly: stance=dismissive caution" in prompt_context
    assert "threat_level=low" in prompt_context


def test_normalize_relationships_preserves_string_stance_and_goal_thread_fields() -> (
    None
):
    normalized = _normalize_relationships(
        {
            "Kizzie": "guarded protective",
            "Ayame": {
                "entity_type": "character",
                "stance": "controlled antagonism",
                "medium_term_goal": "outmaneuver Ayame without open rupture",
                "current_objective": "force a concession on room access",
            },
        }
    )

    assert normalized["Kizzie"] == {
        "entity_type": "character",
        "stance": "guarded protective",
    }
    assert normalized["Ayame"]["entity_type"] == "character"
    assert normalized["Ayame"]["stance"] == "controlled antagonism"
    assert (
        normalized["Ayame"]["medium_term_goal"]
        == "outmaneuver Ayame without open rupture"
    )
    assert (
        normalized["Ayame"]["current_objective"] == "force a concession on room access"
    )


def test_scene_role_relationship_seeding_creates_prompt_visible_goal_threads() -> None:
    char_states = {
        "Celina": CharacterState(name="Celina", long_term_goal="Protect the refuge"),
        "Kizzie": CharacterState(
            name="Kizzie", long_term_goal="Stay safe without losing freedom"
        ),
    }

    _seed_scene_role_relationship_context(
        char_states=char_states,
        scene_setup={
            "role_assignments": {
                "Celina": "protector",
                "Kizzie": "recovering_demi_human",
            },
            "character_presence_constraints": {
                "Celina": "must_remain",
                "Kizzie": "must_remain",
            },
            "character_authority_labels": {
                "Celina": "high",
                "Kizzie": "low",
            },
        },
    )

    celina_prompt = char_states["Celina"].to_prompt_context(
        relationship_focus_names=["Kizzie"]
    )
    kizzie_prompt = char_states["Kizzie"].to_prompt_context(
        relationship_focus_names=["Celina"]
    )

    assert "Key relationship goal threads:" in celina_prompt
    assert "  - Kizzie:" in celina_prompt
    assert "    - Stance: protective control" in celina_prompt
    assert (
        "Medium-term goal toward them: stabilize Kizzie while controlling the immediate scene around them"
        in celina_prompt
    )
    assert (
        "Immediate objective toward them: assess Kizzie's condition and keep them responsive"
        in celina_prompt
    )
    assert "Key relationship goal threads:" in kizzie_prompt
    assert "  - Celina:" in kizzie_prompt
    assert "    - Stance: wary dependence" in kizzie_prompt
    assert (
        "Immediate objective toward them: judge whether Celina's control is safe enough to cooperate with"
        in kizzie_prompt
    )


def test_scene_role_character_priority_seeding_sets_persistent_objectives() -> None:
    char_states = {
        "Celina": CharacterState(name="Celina", long_term_goal="Protect the refuge"),
        "Kizzie": CharacterState(
            name="Kizzie", long_term_goal="Stay safe without losing freedom"
        ),
    }

    _seed_scene_role_character_priorities(
        char_states=char_states,
        scene_setup={
            "role_assignments": {
                "Celina": "protector",
                "Kizzie": "recovering_demi_human",
            },
            "character_authority_labels": {
                "Celina": "high",
                "Kizzie": "low",
            },
        },
    )

    assert (
        char_states["Celina"].current_objective
        == "stabilize Kizzie while controlling the immediate scene around them"
    )
    assert (
        "assess, stabilize, and direct the scene"
        in char_states["Celina"].short_term_tactic
    )
    assert (
        char_states["Kizzie"].current_objective
        == "stay responsive and judge whether Celina's control is safe enough to cooperate with"
    )
    assert (
        char_states["Kizzie"].short_term_tactic
        == "cooperate selectively while protecting your condition, freedom, and next options"
    )


def test_character_state_manager_public_snapshot_uses_structured_goals():
    """Test that the orchestration snapshot exposes structured goal and emotion data."""
    manager = CharacterStateManager()
    manager.register_character(
        "Thorn",
        CharacterState(
            name="Thorn",
            long_term_goal="Keep the relic",
            medium_term_goal="Deflect suspicion",
            current_objective="misdirect Mira",
            short_term_tactic="answer with half-truths",
            local_task_goal="stall for another answer",
            local_task_tactic="offer partial truth and redirect attention",
            emotional_state="guarded",
            stress_level=6,
            core_goals=["Keep the relic"],
        ),
    )

    snapshot = manager.public_state_snapshot()

    assert snapshot["Thorn"]["core_goals"] == ["Keep the relic"]
    assert snapshot["Thorn"]["medium_term_goal"] == "Deflect suspicion"
    assert snapshot["Thorn"]["current_objective"] == "misdirect Mira"
    assert snapshot["Thorn"]["local_task_goal"] == "stall for another answer"
    assert snapshot["Thorn"]["emotional_state"] == "guarded"
    assert snapshot["Thorn"]["stress_level"] == 6


@pytest.mark.asyncio
async def test_agent_from_character_card():
    """Test creating an agent from a character card."""
    model_client = create_test_model_client()

    character_card = {
        "name": "Gareth",
        "description": "A grumpy blacksmith",
        "system_prompt": """You are Gareth, a blacksmith.
        Personality: Gruff but skilled.
        Speaking style: Short sentences, talks about metal work.
        """,
    }

    agent = AssistantAgent(
        name=character_card["name"],
        model_client=model_client,
        system_message=character_card["system_prompt"],
        description=character_card["description"],
    )

    assert agent.name == "Gareth"
    assert agent.description == "A grumpy blacksmith"

    await agent.on_reset(CancellationToken())
    await model_client.close()
