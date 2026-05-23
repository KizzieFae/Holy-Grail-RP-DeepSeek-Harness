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
    ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER,
    ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER,
    ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER,
    ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER,
    ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER,
    ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER,
    ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER,
    ISSUE240_V1_OPENING_MARKER,
    apply_issue240_v1_next2_long_prompt_compression,
    apply_issue240_v1_topology_transform,
    build_character_turn_prompt_for_runtime,
    build_character_turn_prompt_issue240_v1,
    build_character_turn_prompt_issue240_v1_next,
    build_character_turn_prompt_issue240_v1_next2,
    build_character_turn_prompt_issue240_v1_next3,
    build_character_turn_prompt_issue240_v1_next4,
    build_character_turn_prompt_issue240_v1_next5,
    build_character_turn_prompt_issue240_v1_next6,
    build_character_turn_prompt_issue240_v1_next7,
    issue240_prompt_topology_mode,
    resolve_character_turn_prompt_builder,
    should_compress_long_prompt,
    should_emit_social_focus_capsule,
)
from test_prompt_builders import _minimal_character_prompt_kwargs


@pytest.fixture(autouse=True)
def _clear_issue240_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_ISSUE240_PROMPT_TOPOLOGY", raising=False)


def test_issue240_default_unset_uses_v1_next7_builder() -> None:
    assert issue240_prompt_topology_mode() == "v1_next7"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next7


def test_issue240_production_legacy_uses_untransformed_production_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "production_legacy")
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
    assert (root / "audit_i225_willow_actor_targeted_overlay.json").is_file()


def _three_character_prompt_kwargs() -> dict:
    kwargs = _minimal_character_prompt_kwargs()
    kwargs.update(
        char_name="Willow_Reeves",
        scene_state={
            "location": "university_dorm_triple",
            "present_characters": ["Kizzie", "Marlene_Fletcher", "Willow_Reeves"],
            "offstage_characters": [],
        },
        cast=["Kizzie", "Marlene_Fletcher", "Willow_Reeves"],
        state_context="- Emotional state: controlled steadiness\n",
        trigger_text=(
            "Traveler (overlay, Willow Reeves ONLY): MUST emit semantic_proposals "
            "for off_focal or reentry when covered intent exists."
        ),
        active_issues=[{"description": "Settle dorm logistics under quiet tension."}],
    )
    return kwargs


def test_issue240_env_gate_v1_next(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next")
    assert issue240_prompt_topology_mode() == "v1_next"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next


def test_issue240_v1_next_preserves_v1_on_two_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["scene_state"] = {"present_characters": ["Ayame", "Celina"]}
    kwargs["cast"] = ["Ayame", "Celina"]
    v1 = build_character_turn_prompt_issue240_v1(**kwargs)
    v1_next = build_character_turn_prompt_for_runtime(**kwargs)
    assert v1 == v1_next
    assert ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER not in v1_next


def test_issue240_v1_next_social_capsule_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next")
    kwargs = _three_character_prompt_kwargs()
    assert should_emit_social_focus_capsule(**kwargs)
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER in prompt
    sem = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    soc = prompt.index(ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert sem < soc < priv
    assert "Step 1" not in prompt
    assert "controlled steadiness" in prompt


def test_issue240_v1_next_size_bounded_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next")
    kwargs = _three_character_prompt_kwargs()
    v1 = build_character_turn_prompt_issue240_v1(**kwargs)
    v1_next = build_character_turn_prompt_for_runtime(**kwargs)
    assert len(v1_next) <= len(v1) + 600


def test_issue240_env_gate_v1_next2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next2")
    assert issue240_prompt_topology_mode() == "v1_next2"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next2


def test_issue240_v1_next2_preserves_v1_on_two_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next2")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["scene_state"] = {"present_characters": ["Ayame", "Celina"]}
    kwargs["cast"] = ["Ayame", "Celina"]
    v1 = build_character_turn_prompt_issue240_v1(**kwargs)
    v1_next2 = build_character_turn_prompt_for_runtime(**kwargs)
    assert v1 == v1_next2
    assert ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER not in v1_next2


def test_issue240_v1_next2_active_focus_capsule_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next2")
    kwargs = _three_character_prompt_kwargs()
    kwargs["recent_dialogue"] = [
        {
            "speaker": "Marlene_Fletcher",
            "content": "Willow, are you still with us?",
        }
    ]
    kwargs["trigger_text"] = (
        "Traveler (overlay, Willow Reeves ONLY): REQUIRED semantic_proposals for reentry."
    )
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER in prompt
    assert ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER not in prompt
    assert "Beat ambiguity" in prompt
    assert "Marlene" in prompt
    sem = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    focus = prompt.index(ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert sem < focus < priv


def test_issue240_v1_next2_long_prompt_compression() -> None:
    kwargs = _three_character_prompt_kwargs()
    base = build_character_turn_prompt_issue240_v1(**kwargs)
    padded_moves = [{"speaker": f"Npc_{i}", "action": f"action {i} " * 120} for i in range(12)]
    padded_dialogue = [{"speaker": f"Npc_{i}", "content": f"line {i} " * 80} for i in range(12)]
    kwargs["recent_moves"] = padded_moves
    kwargs["recent_dialogue"] = padded_dialogue
    kwargs["summary_blocks"] = [{"summary": "old continuity " * 400} for _ in range(6)]
    kwargs["my_interpretations"] = [
        {"character_name": "Willow_Reeves", "emotional_reaction": f"x{i} " * 50} for i in range(8)
    ]
    kwargs["cross_session_user_memories"] = [{"memory": "m " * 200} for _ in range(8)]
    long_base = build_character_turn_prompt_issue240_v1(**kwargs)
    assert len(long_base) >= 35000
    assert should_compress_long_prompt(long_base, **kwargs)
    compressed = apply_issue240_v1_next2_long_prompt_compression(long_base, **kwargs)
    assert len(compressed) < len(long_base)
    assert "[Beat-focus window:" in compressed
    assert "older continuity summaries on file" in compressed


def test_issue240_env_gate_v1_next3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next3")
    assert issue240_prompt_topology_mode() == "v1_next3"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next3


def test_issue240_v1_next3_participation_frame_in_semantic_cluster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next3")
    kwargs = _minimal_character_prompt_kwargs()
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER in prompt
    assert "Emotional color alone is not enough" in prompt
    assert "Step 1" not in prompt
    sem = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    frame = prompt.index(ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert sem < frame < priv


def test_issue240_v1_next3_preserves_v1_next2_extras_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next3")
    kwargs = _three_character_prompt_kwargs()
    v1_next2 = build_character_turn_prompt_issue240_v1_next2(**kwargs)
    v1_next3 = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER in v1_next3
    assert ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER in v1_next3
    assert ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER not in v1_next2
    assert len(v1_next3) <= len(v1_next2) + 400


def test_issue240_v1_next2_unchanged_without_next3_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next2")
    prompt = build_character_turn_prompt_for_runtime(**_minimal_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER not in prompt


def test_issue240_env_gate_v1_next4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next4")
    assert issue240_prompt_topology_mode() == "v1_next4"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next4


def test_issue240_v1_next4_participation_arc_ordering_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next4")
    kwargs = _three_character_prompt_kwargs()
    kwargs["recent_moves"] = [
        {
            "speaker": "Willow_Reeves",
            "action": "Willow turned away from the exchange and looked out the window.",
        },
        {
            "speaker": "Marlene_Fletcher",
            "dialogue": "Willow, are you still with us?",
        },
    ]
    kwargs["recent_dialogue"] = [
        {
            "speaker": "Marlene_Fletcher",
            "content": "Willow, are you still with us?",
        }
    ]
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER in prompt
    assert ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER in prompt
    sem = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    frame = prompt.index(ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER)
    arc = prompt.index(ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER)
    focus = prompt.index(ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert sem < frame < arc < focus < priv
    assert "recent beats" in prompt[arc:focus].lower()


def test_issue240_v1_next4_skips_arc_on_two_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next4")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["scene_state"] = {"present_characters": ["Ayame", "Celina"]}
    kwargs["cast"] = ["Ayame", "Celina"]
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER in prompt
    assert ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER not in prompt
    assert ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER not in prompt


def test_issue240_v1_next4_size_bounded_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next4")
    kwargs = _three_character_prompt_kwargs()
    v1_next3 = build_character_turn_prompt_issue240_v1_next3(**kwargs)
    v1_next4 = build_character_turn_prompt_for_runtime(**kwargs)
    assert len(v1_next4) <= len(v1_next3) + 500


def test_issue240_v1_next3_unchanged_without_next4_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next3")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER not in prompt


def test_issue240_env_gate_v1_next5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next5")
    assert issue240_prompt_topology_mode() == "v1_next5"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next5


def test_issue240_v1_next5_requires_semantic_evaluation_in_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next5")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER in prompt
    assert "required ``semantic_evaluation``" in prompt
    assert ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER in prompt
    assert "omit semantic_proposals entirely" not in prompt


def test_issue240_v1_next4_unchanged_without_next5_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next4")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER not in prompt
    assert "required ``semantic_evaluation``" not in prompt


def test_issue240_env_gate_v1_next6(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next6")
    assert issue240_prompt_topology_mode() == "v1_next6"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next6


def test_issue240_v1_next6_threshold_bridge_ordering_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next6")
    kwargs = _three_character_prompt_kwargs()
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER in prompt
    assert ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER in prompt
    frame = prompt.index(ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER)
    arc = prompt.index(ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER)
    bridge = prompt.index(ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER)
    focus = prompt.index(ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert frame < arc < bridge < focus < priv


def test_issue240_v1_next6_skips_bridge_on_two_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next6")
    kwargs = _minimal_character_prompt_kwargs()
    kwargs["scene_state"] = {"present_characters": ["Ayame", "Celina"]}
    kwargs["cast"] = ["Ayame", "Celina"]
    prompt = build_character_turn_prompt_for_runtime(**kwargs)
    assert ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER in prompt
    assert ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER not in prompt
    assert ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER not in prompt


def test_issue240_v1_next6_size_bounded_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next6")
    kwargs = _three_character_prompt_kwargs()
    v1_next5 = build_character_turn_prompt_issue240_v1_next5(**kwargs)
    v1_next6 = build_character_turn_prompt_for_runtime(**kwargs)
    assert len(v1_next6) <= len(v1_next5) + 500


def test_issue240_v1_next5_unchanged_without_next6_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next5")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER not in prompt


def test_issue240_env_gate_v1_next7(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    assert issue240_prompt_topology_mode() == "v1_next7"
    assert resolve_character_turn_prompt_builder() is build_character_turn_prompt_issue240_v1_next7


def test_issue240_v1_next7_calibration_in_semantic_cluster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER in prompt
    assert "does not require a dramatic or physical exit" in prompt
    assert "If the recent participation arc places you withdrawn" in prompt
    assert ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER not in prompt
    sem = prompt.index(ISSUE240_SEMANTIC_BLOCK_HEADER)
    frame = prompt.index(ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER)
    cal = prompt.index(ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER)
    arc = prompt.index(ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER)
    focus = prompt.index(ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER)
    priv = prompt.index("YOUR PRIVATE STATE:")
    assert sem < frame < cal < arc < focus < priv


def test_issue240_v1_next7_merged_calibration_no_separate_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER not in prompt
    assert ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER in prompt


def test_issue240_v1_next7_size_bounded_on_three_character_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next7")
    kwargs = _three_character_prompt_kwargs()
    v1_next6 = build_character_turn_prompt_issue240_v1_next6(**kwargs)
    v1_next7 = build_character_turn_prompt_for_runtime(**kwargs)
    assert len(v1_next7) <= len(v1_next6) + 700


def test_issue240_v1_next6_unchanged_without_next7_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RP_ISSUE240_PROMPT_TOPOLOGY", "v1_next6")
    prompt = build_character_turn_prompt_for_runtime(**_three_character_prompt_kwargs())
    assert ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER not in prompt

