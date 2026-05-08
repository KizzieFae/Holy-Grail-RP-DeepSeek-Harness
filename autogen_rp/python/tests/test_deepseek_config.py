"""Tests for DeepSeek configuration and client creation (V4-native)."""

import os
from pathlib import Path

import pytest
import yaml
from autogen_ext.models.openai import OpenAIChatCompletionClient

from model_client import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_DEEPSEEK_OPENAI_BASE_URL,
    create_deepseek_client,
)


@pytest.mark.llm
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
    assert config["config"]["model"] == "deepseek-v4-flash"
    assert config["config"]["base_url"] == "https://api.deepseek.com"
    assert config["config"]["extra_body"]["thinking"]["type"] == "disabled"


def test_rejects_deprecated_deepseek_chat(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    with pytest.raises(ValueError, match="deepseek-v4-flash"):
        create_deepseek_client(api_key="sk-test", model="deepseek-chat")


def test_rejects_deprecated_deepseek_reasoner(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    with pytest.raises(ValueError, match="deepseek-v4-flash"):
        create_deepseek_client(api_key="sk-test", model="deepseek-reasoner")


def test_rejects_unknown_model(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    with pytest.raises(ValueError, match="Unsupported DeepSeek model"):
        create_deepseek_client(api_key="sk-test", model="not-a-deepseek-model")


def test_default_model_is_v4_flash(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    client = create_deepseek_client(api_key="sk-test")
    assert client._create_args["model"] == DEFAULT_DEEPSEEK_MODEL == "deepseek-v4-flash"


def test_explicit_non_thinking_default(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_THINKING", raising=False)
    monkeypatch.delenv("DEEPSEEK_REASONING_EFFORT", raising=False)
    client = create_deepseek_client(api_key="sk-test")
    assert client._create_args["extra_body"]["thinking"]["type"] == "disabled"
    assert "reasoning_effort" not in client._create_args["extra_body"]


def test_thinking_enabled_and_reasoning_effort(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.setenv("DEEPSEEK_THINKING", "1")
    monkeypatch.setenv("DEEPSEEK_REASONING_EFFORT", "max")
    client = create_deepseek_client(api_key="sk-test")
    assert client._create_args["extra_body"]["thinking"]["type"] == "enabled"
    assert client._create_args["extra_body"]["reasoning_effort"] == "max"


def test_default_openai_base_matches_documented_deepseek_host():
    """Guardrail: default host matches DeepSeek OpenAI-format docs (Issue #130 probe)."""
    assert DEFAULT_DEEPSEEK_OPENAI_BASE_URL == "https://api.deepseek.com"


@pytest.mark.llm
def test_deepseek_model_client_creation():
    """Test creating DeepSeek model client with shared factory (live key required)."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    client = create_deepseek_client(api_key=api_key)
    assert client is not None, "Failed to create OpenAIChatCompletionClient"


@pytest.mark.llm
@pytest.mark.asyncio
async def test_deepseek_client_connectivity():
    """Test DeepSeek client can connect and get a response."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set")

    client = create_deepseek_client(api_key=api_key)

    # Test simple completion
    from autogen_core.models import UserMessage

    messages = [UserMessage(content="Say 'test' and nothing else.", source="user")]
    response = await client.create(messages=messages)

    assert response is not None, "No response from DeepSeek"
    assert len(response.content) > 0, "Empty response from DeepSeek"

    await client.close()


def test_yaml_roundtrip_matches_component_schema():
    """deepseek_config.yaml must load into OpenAIChatCompletionClient."""
    config_path = Path(__file__).resolve().parent.parent / "deepseek_config.yaml"
    with open(config_path, "r") as f:
        wrapped = yaml.safe_load(f)
    api_key = os.environ.get("DEEPSEEK_API_KEY") or "sk-placeholder"
    cfg = dict(wrapped["config"])
    cfg["api_key"] = api_key
    client = OpenAIChatCompletionClient(**cfg)
    assert client._create_args["model"] == "deepseek-v4-flash"
    assert client._raw_config.get("base_url") == "https://api.deepseek.com"
