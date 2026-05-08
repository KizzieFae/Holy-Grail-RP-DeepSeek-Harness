"""Tests for AssistantAgent creation and basic functionality."""

import os

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_core import CancellationToken

from model_client import create_deepseek_client


def create_test_model_client():
    """Helper to create a test model client."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    return create_deepseek_client(api_key=api_key)


@pytest.mark.asyncio
async def test_assistant_agent_creation():
    """Test creating an AssistantAgent with DeepSeek."""
    model_client = create_test_model_client()

    agent = AssistantAgent(
        name="test_assistant",
        model_client=model_client,
        system_message="You are a test assistant. Be concise.",
    )

    assert agent is not None, "Failed to create AssistantAgent"
    assert agent.name == "test_assistant", "Agent name mismatch"

    await agent.on_reset(CancellationToken())
    await model_client.close()


@pytest.mark.asyncio
async def test_assistant_agent_run():
    """Test running a simple task with AssistantAgent."""
    model_client = create_test_model_client()

    agent = AssistantAgent(
        name="test_assistant",
        model_client=model_client,
        system_message="You are a test assistant. Reply with exactly 'Test passed.'",
    )

    result = None
    async for item in agent.run_stream(task="Say 'Test passed.'"):
        if isinstance(item, TaskResult):
            result = item

    assert result is not None, "No result from agent"
    assert len(result.messages) > 0, "No messages in result"

    await agent.on_reset(CancellationToken())
    await model_client.close()


@pytest.mark.asyncio
async def test_character_agent_creation():
    """Test creating a character-style agent."""
    model_client = create_test_model_client()

    character_prompt = """You are Elara, a wise mage from the northern mountains.
    Personality: Thoughtful, reserved, speaks in measured tones.
    Goals: Protect ancient knowledge, guide travelers.
    """

    agent = AssistantAgent(
        name="Elara",
        model_client=model_client,
        system_message=character_prompt,
        description="A wise mage who offers guidance and protection.",
    )

    assert agent.name == "Elara"
    assert agent.description == "A wise mage who offers guidance and protection."

    await agent.on_reset(CancellationToken())
    await model_client.close()
