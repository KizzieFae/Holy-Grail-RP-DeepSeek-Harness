"""Tests for DeepSeek configuration and client creation."""

import os
from pathlib import Path

import pytest
import yaml
from autogen_ext.models.openai import OpenAIChatCompletionClient


def test_deepseek_api_key_exists():
    """Verify DEEPSEEK_API_KEY environment variable is set."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    assert api_key is not None, "DEEPSEEK_API_KEY environment variable not set"
    assert len(api_key) > 0, "DEEPSEEK_API_KEY is empty"


def test_deepseek_config_file_exists():
    """Verify deepseek_config.yaml exists and is valid."""
    config_path = Path(__file__).resolve().parent.parent / "deepseek_config.yaml"
    assert os.path.exists(config_path), f"Config file {config_path} not found"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    assert "provider" in config, "Config missing 'provider' field"
    assert "config" in config, "Config missing 'config' field"
    assert config["provider"] == "autogen_ext.models.openai.OpenAIChatCompletionClient"


def test_deepseek_model_client_creation():
    """Test creating DeepSeek model client with direct config."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    client = OpenAIChatCompletionClient(
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

    assert client is not None, "Failed to create OpenAIChatCompletionClient"
    # Client created successfully - that's the main test


@pytest.mark.asyncio
async def test_deepseek_client_connectivity():
    """Test DeepSeek client can connect and get a response."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    client = OpenAIChatCompletionClient(
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

    # Test simple completion
    from autogen_core.models import UserMessage

    messages = [UserMessage(content="Say 'test' and nothing else.", source="user")]
    response = await client.create(messages=messages)

    assert response is not None, "No response from DeepSeek"
    assert len(response.content) > 0, "Empty response from DeepSeek"

    await client.close()
