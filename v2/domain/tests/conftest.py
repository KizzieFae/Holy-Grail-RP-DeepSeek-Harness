"""Pytest configuration and shared fixtures."""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_V2 = _REPO_ROOT / "v2"
for path in (_REPO_ROOT, _V2):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import pytest


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "llm: live DeepSeek/API tests (skip with DEEPSEEK_API_KEY unset or -m \"not llm\")",
    )
    config.addinivalue_line(
        "markers",
        "progression_llm: progression-focused live LLM checks",
    )
    config.addinivalue_line(
        "markers",
        "supplemental_simulation: monkeypatched simulation paths (not primary scenario coverage)",
    )


@pytest.fixture
def deepseek_api_key():
    """Fixture to get DeepSeek API key."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY environment variable not set")
    return api_key
