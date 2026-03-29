"""Director validation tests for emotional scene turn selection."""

import json
import os
import sys
from pathlib import Path

import pytest
from autogen_agentchat.base import Response
from autogen_core import CancellationToken

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from model_client import DIRECTOR_SYSTEM_MESSAGE, create_director_agent


def create_test_model_client():
    """Helper to create a test model client."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    from autogen_ext.models.openai import OpenAIChatCompletionClient

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


def test_director_prompt_includes_pressure_core_guidance():
    assert (
        "Treat assigned roles, presence constraints, authority labels, active issues, location, scene_phase, and latest_trigger as primary evidence"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "When a character is directly addressed with a challenge, accusation, or question, the addressee should be selected next"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "current_scene_state.offstage_characters"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "Prefer the smallest relevant pressure core for the current beat"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "If a present character is secondary to the current beat, avoid selecting them"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "Treat witness, observer, or intervenor roles as reactive edge roles by default"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert "bystanders often keep doing their own business" in DIRECTOR_SYSTEM_MESSAGE
    assert (
        "fear, hierarchy, or institutional authority is present"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "keep the pressure core on triage, stabilization, assessment, or next-step planning"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "Do not treat a minor care subtask as the scene's main problem"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "do not spend many turns on tiny repetitions of continued stillness"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "a material time-passage environment event is appropriate"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "re-anchor the scene around unresolved threats, injuries, obligations, investigations, or planning pressure"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "A turn counts as meaningful only if it changes the situation"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "Do not broaden a grounded or only-partially-supernatural scene"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "do not assume the rest of the cast shares expert language, countermeasures, or routine familiarity"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "Preserve established capability limits and pacing when selecting the next beat"
        in DIRECTOR_SYSTEM_MESSAGE
    )
    assert (
        "give the most affected witness or responsible character room to register that shift"
        in DIRECTOR_SYSTEM_MESSAGE
    )


@pytest.mark.asyncio
async def test_director_selects_emotionally_engaged_character():
    """Test that Director picks the character most emotionally affected by the current beat.

    Scene: An accusation has been made. Celina (defensive) and Mira (observing) are present.
    The Director should favor Celina because she is directly emotionally engaged.
    """
    model_client = create_test_model_client()
    director = create_director_agent(model_client)

    from autogen_agentchat.messages import TextMessage

    # Build emotional scene state
    director_payload = {
        "current_scene_state": {
            "opening_description": "A tense confrontation in the workshop",
            "recent_environment_events": [],
            "tension_history": ["escalate"],
            "resolved_events": [],
            "latest_trigger": "Ayame directly accuses Celina of sabotage. 'You knew the forge would fail. You wanted it to.'",
        },
        "recent_structured_character_actions": [
            {
                "speaker": "Ayame",
                "action": "points at Celina with visible anger",
                "dialogue": "You knew the forge would fail. You wanted it to.",
                "motivation": {"goal": "expose Celina", "tactic": "direct accusation"},
            }
        ],
        "character_states": {
            "Celina": {
                "emotional_state": "defensive and cornered",
                "current_goal": "protect her reputation",
                "spotlight_count": 1,
            },
            "Mira": {
                "emotional_state": "observing with concern",
                "current_goal": "understand what happened",
                "spotlight_count": 2,
            },
        },
        "recent_dialogue_history": [
            {
                "role": "assistant",
                "speaker": "Ayame",
                "content": "You knew the forge would fail. You wanted it to.",
            }
        ],
        "spotlight_history": ["Mira", "Ayame"],
        "participants": ["Celina", "Mira"],
        "available_next_actors": ["Celina", "Mira"],
        "actors_already_used_this_round": [],
    }

    prompt = (
        "Decide who acts next using only the structured scene information below. Return JSON only.\n\n"
        f"{json.dumps(director_payload, ensure_ascii=False, indent=2)}"
    )

    task = TextMessage(content=prompt, source="system")
    cancellation_token = CancellationToken()
    result = None
    async for item in director.on_messages_stream([task], cancellation_token):
        if isinstance(item, Response):
            result = item
    assert result is not None
    raw_response = result.chat_message.content

    # Parse the decision
    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        decision = json.loads(raw_response[start:end])
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Director returned invalid JSON: {raw_response}")

    # Validate structure
    assert "next_actor" in decision, "Decision missing next_actor field"
    assert decision["next_actor"] in [
        "Celina",
        "Mira",
    ], f"Invalid actor selected: {decision['next_actor']}"

    # The key validation: Celina should be selected because she is emotionally engaged
    # Mira has had more spotlight (2 vs 1) and is only observing
    # Celina is defensive and directly addressed
    assert (
        decision["next_actor"] == "Celina"
    ), f"Expected Celina (emotionally engaged, directly accused), got {decision['next_actor']}. Reason: {decision.get('reason', 'none')}"

    await director.on_reset(CancellationToken())
    await model_client.close()


@pytest.mark.asyncio
async def test_director_avoids_spotlight_domination():
    """Test that Director avoids letting one character dominate despite emotional hooks.

    Scene: Three characters, one has acted twice as much. The next beat favors the
    spotlight-heavy character emotionally, but they should still be deferred for balance.
    """
    model_client = create_test_model_client()
    director = create_director_agent(model_client)

    from autogen_agentchat.messages import TextMessage

    director_payload = {
        "current_scene_state": {
            "opening_description": "Negotiations at the trade table",
            "recent_environment_events": [],
            "tension_history": ["steady"],
            "resolved_events": [],
            "latest_trigger": "A new trade proposal favors the merchant guild",
        },
        "recent_structured_character_actions": [
            {
                "speaker": "Merchant",
                "action": "pushed hard for better terms",
                "dialogue": "This is my final offer.",
                "motivation": {"goal": "maximize profit", "tactic": "pressure"},
            }
        ],
        "character_states": {
            "Merchant": {
                "emotional_state": "confident and aggressive",
                "current_goal": "close the deal on favorable terms",
                "spotlight_count": 4,
            },
            "Negotiator": {
                "emotional_state": "calculating",
                "current_goal": "find compromise",
                "spotlight_count": 1,
            },
            "Guard": {
                "emotional_state": "watchful",
                "current_goal": "maintain order",
                "spotlight_count": 1,
            },
        },
        "recent_dialogue_history": [
            {
                "role": "assistant",
                "speaker": "Merchant",
                "content": "This is my final offer.",
            }
        ],
        "spotlight_history": [
            "Merchant",
            "Merchant",
            "Negotiator",
            "Merchant",
            "Guard",
        ],
        "participants": ["Merchant", "Negotiator", "Guard"],
        "available_next_actors": ["Negotiator", "Guard"],  # Merchant already acted
        "actors_already_used_this_round": ["Merchant"],
    }

    prompt = (
        "Decide who acts next using only the structured scene information below. Return JSON only.\n\n"
        f"{json.dumps(director_payload, ensure_ascii=False, indent=2)}"
    )

    task = TextMessage(content=prompt, source="system")
    cancellation_token = CancellationToken()
    result = None
    async for item in director.on_messages_stream([task], cancellation_token):
        if isinstance(item, Response):
            result = item
    assert result is not None
    raw_response = result.chat_message.content

    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        decision = json.loads(raw_response[start:end])
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Director returned invalid JSON: {raw_response}")

    # Merchant is already excluded, so this validates the constraint works
    assert decision["next_actor"] in [
        "Negotiator",
        "Guard",
    ], f"Selected actor should be from available list, got {decision['next_actor']}"

    # Both have equal spotlight (1 each), so either is valid
    # But the test validates the Director respects available_actors

    await director.on_reset(CancellationToken())
    await model_client.close()


@pytest.mark.asyncio
async def test_director_respects_direct_address_routing():
    """Test that when one character directly addresses another, the addressee is favored.

    Scene: Ayame asks Celina a direct question. Even though Mira has interesting context,
    Celina should be selected because she was directly addressed.
    """
    model_client = create_test_model_client()
    director = create_director_agent(model_client)

    from autogen_agentchat.messages import TextMessage
    from autogen_core import CancellationToken

    director_payload = {
        "current_scene_state": {
            "opening_description": "Evening in the common room",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "latest_trigger": "Ayame turns to Celina: 'Why did you really come back?'",
        },
        "recent_structured_character_actions": [
            {
                "speaker": "Ayame",
                "action": "turns to face Celina directly",
                "dialogue": "Why did you really come back?",
                "motivation": {
                    "goal": "understand Celina's motives",
                    "tactic": "direct question",
                },
            }
        ],
        "character_states": {
            "Celina": {
                "emotional_state": "guarded",
                "current_goal": "protect her secrets",
                "spotlight_count": 0,
            },
            "Mira": {
                "emotional_state": "curious",
                "current_goal": "learn the truth",
                "spotlight_count": 1,
            },
            "Ayame": {
                "emotional_state": "determined",
                "current_goal": "get answers",
                "spotlight_count": 2,
            },
        },
        "recent_dialogue_history": [
            {
                "role": "assistant",
                "speaker": "Ayame",
                "content": "Why did you really come back?",
            }
        ],
        "spotlight_history": ["Ayame", "Mira", "Ayame"],
        "participants": ["Celina", "Mira", "Ayame"],
        "available_next_actors": ["Celina", "Mira"],  # Ayame just spoke
        "actors_already_used_this_round": ["Ayame"],
    }

    prompt = (
        "Decide who acts next using only the structured scene information below. Return JSON only.\n\n"
        f"{json.dumps(director_payload, ensure_ascii=False, indent=2)}"
    )

    task = TextMessage(content=prompt, source="system")
    cancellation_token = CancellationToken()
    result = None
    async for item in director.on_messages_stream([task], cancellation_token):
        if isinstance(item, Response):
            result = item
    assert result is not None
    raw_response = result.chat_message.content

    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        decision = json.loads(raw_response[start:end])
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Director returned invalid JSON: {raw_response}")

    # Celina was directly addressed with a personal question
    # She should be selected despite Mira having higher spotlight
    assert (
        decision["next_actor"] == "Celina"
    ), f"Expected Celina (directly addressed), got {decision['next_actor']}. Reason: {decision.get('reason', 'none')}"

    await director.on_reset(CancellationToken())
    await model_client.close()
