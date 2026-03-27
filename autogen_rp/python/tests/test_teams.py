"""Tests for SelectorGroupChat team functionality."""

import os

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient


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


@pytest.mark.asyncio
async def test_selector_group_chat_creation():
    """Test creating a SelectorGroupChat team."""
    model_client = create_test_model_client()

    agent1 = AssistantAgent(
        name="Character1",
        model_client=model_client,
        system_message="You are Character1. Be brief.",
        description="A helpful character who responds first.",
    )

    agent2 = AssistantAgent(
        name="Character2",
        model_client=model_client,
        system_message="You are Character2. Be brief.",
        description="A helpful character who responds second.",
    )

    termination = MaxMessageTermination(max_messages=3)

    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
    )

    assert team is not None, "Failed to create SelectorGroupChat"
    assert len(team._participants) == 2, "Wrong number of participants"

    await team.reset()
    await model_client.close()


@pytest.mark.asyncio
async def test_team_run():
    """Test running a team for a few turns."""
    model_client = create_test_model_client()

    agent1 = AssistantAgent(
        name="Narrator",
        model_client=model_client,
        system_message="You are a narrator. Set a scene briefly.",
        description="The narrator who sets the scene.",
    )

    agent2 = AssistantAgent(
        name="Protagonist",
        model_client=model_client,
        system_message="You are the protagonist. Respond briefly.",
        description="The main character who responds to the narrator.",
    )

    # Limit to 2 messages to keep test fast
    termination = MaxMessageTermination(max_messages=2)

    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
    )

    result = await team.run(task="Start a short scene.")

    assert result is not None, "No result from team"
    assert len(result.messages) > 0, "No messages in result"
    assert len(result.messages) <= 2, "Too many messages - termination failed"

    await team.reset()
    await model_client.close()


@pytest.mark.asyncio
async def test_team_save_load_state():
    """Test saving and loading team state."""
    model_client = create_test_model_client()

    agent1 = AssistantAgent(
        name="TestAgent1",
        model_client=model_client,
        system_message="You are the first test agent.",
        description="First test agent.",
    )

    agent2 = AssistantAgent(
        name="TestAgent2",
        model_client=model_client,
        system_message="You are the second test agent.",
        description="Second test agent.",
    )

    termination = MaxMessageTermination(max_messages=1)

    team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
    )

    # Run once
    await team.run(task="Say hello.")

    # Save state (now async)
    state = await team.save_state()
    assert state is not None, "Failed to save state"

    # Create new team and load state
    new_team = SelectorGroupChat(
        participants=[agent1, agent2],
        model_client=model_client,
        termination_condition=termination,
    )
    await new_team.load_state(state)

    await team.reset()
    await new_team.reset()
    await model_client.close()
