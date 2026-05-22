"""Issue #240 — env-gated dual-role one-pass prompt topology (investigation)."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from prompt_builders import build_character_turn_prompt as production_build
from prompt_topology_issue240 import (
    ISSUE240_DOCTRINE_PHRASE,
    ISSUE240_SEMANTIC_BLOCK_HEADER,
    ISSUE240_V1_OPENING_MARKER,
    apply_issue240_v1_topology_transform,
    build_character_turn_prompt_for_runtime,
    build_character_turn_prompt_issue240_v1,
    issue240_prompt_topology_mode,
    resolve_character_turn_prompt_builder,
)
from test_prompt_builders import _minimal_character_prompt_kwargs


@pytest.fixture(autouse=True)
def _clear_issue240_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_ISSUE240_PROMPT_TOPOLOGY", raising=False)


def test_issue240_env_gate_off_uses_production_builder() -> None:
    assert issue240_prompt_topology_mode() is None
    assert resolve_character_turn_prompt_builder() is production_build
    kwargs = _minimal_character_prompt_kwargs()
    assert build_character_turn_prompt_for_runtime(**kwargs) == production_build(**kwargs)


def test_issue240_env_gate_v1_uses_experimental_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1")
    assert issue240_prompt_topology_mode() == "v1"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1


def test_issue240_v1_opening_and_doctrine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1")
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    assert ISSUE240_V1_OPENING_MARKER in prompt
    assert ISSUE240_DOCTRINE_PHRASE in prompt
    assert "You are taking your next turn in an ongoing roleplay scene." not in prompt
    assert "Step 1" not in prompt
    assert "Step 2" not in prompt
    assert "SEMANTIC REPORTER" not in prompt.upper()


def test_issue240_v1_semantic_block_is_trigger_adjacent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["trigger_text"] = "##UNIQUE_TRIGGER_240##"
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    trig = prompt.index("TRIGGER FOR THIS BEAT:")
    semantic = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    private = prompt.index("YOUR PRIVATE STATE:")
    output_rules = prompt.index("OUTPUT RULES:")
    assert trig < semantic < private < output_rules
    assert "##UNIQUE_TRIGGER_240##" in prompt[trig:semantic]


def test_issue240_v1_slim_output_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1")
    prod = production_build(**_minimal_character_prompt_kwargs())
    v1 = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    assert "sleeping_surface_assignment" not in v1
    assert "Positive example:" not in v1
    assert "Covered semantic intent (``semantic_proposals``): MUST emit" not in v1
    assert len(v1) <= len(prod) + int(len(prod) * 0.05) + 500


def test_issue240_v1_compressed_priorities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1")
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    assert "5. SOCIAL REALISM" in prompt
    assert "Treat absent-but-relevant characters as continuity context only" not in prompt


def test_apply_issue240_v1_transform_is_pure_on_production_base() -> None:
    base = production_build(**_minimal_character_prompt_kwargs())
    out = apply_issue240_v1_topology_transform(base, char_name="Ayame")
    assert ISSUE240_V1_OPENING_MARKER in out
    assert ISSUE240_SEMANTIC_BLOCK_HEADER in out


def test_issue240_schedule_files_exist() -> None:
    root = Path(__file__).resolve().parent.parent / "data" / "issue240"
    assert (root / "cert_i234_reinforced_overlay.json").is_file()
    assert (root / "audit_i225_willow_proposal_overlay.json").is_file()
