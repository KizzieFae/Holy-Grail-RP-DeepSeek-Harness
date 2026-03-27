"""Pytest configuration and shared fixtures."""

import os

import pytest
from autogen_ext.models.openai import OpenAIChatCompletionClient


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture
def deepseek_api_key():
    """Fixture to get DeepSeek API key."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY environment variable not set")
    return api_key


@pytest.fixture
async def deepseek_model_client(deepseek_api_key):
    """Fixture to create a DeepSeek model client."""
    client = OpenAIChatCompletionClient(
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key=deepseek_api_key,
        model_info={
            "function_calling": True,
            "json_output": True,
            "vision": False,
            "family": "unknown",
            "structured_output": True,
        },
    )

    yield client

    # Cleanup
    await client.close()
