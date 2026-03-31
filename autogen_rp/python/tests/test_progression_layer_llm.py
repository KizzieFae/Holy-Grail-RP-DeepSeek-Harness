"""Live LLM checks for the progression layer (DeepSeek).

These tests require ``DEEPSEEK_API_KEY``. Without it they skip, so the default
suite stays green in CI without credentials.

Run only progression LLM tests::

    cd autogen_rp/python
    pytest tests/test_progression_layer_llm.py -m progression_llm -v

Skip all live LLM tests::

    pytest -m "not llm"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_core import CancellationToken

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager  # noqa: E402
from continuity_state import IssueState, IssueStatus  # noqa: E402
from model_client import create_director_agent  # noqa: E402
from progression_advisory import (  # noqa: E402
    build_progression_advisory,
    build_progression_director_prompt_prefix,
    compute_stall_score,
    default_progression_profile,
)
from progression_enforcement import (  # noqa: E402
    collect_issue_signatures,
    qualifies_as_progression_delta,
)
from prompt_builders import build_director_selection_prompt  # noqa: E402
from response_validation_parsing import parse_character_move  # noqa: E402


@pytest.mark.llm
@pytest.mark.progression_llm
@pytest.mark.slow
@pytest.mark.asyncio
async def test_llm_director_valid_json_under_progression_advisory_prefix(
    deepseek_model_client,
) -> None:
    """Director returns parseable JSON when PROGRESSION ADVISORY prefix is active (high pressure path)."""
    director = create_director_agent(deepseek_model_client)

    director_payload: dict = {
        "current_scene_state": {
            "opening_description": "Two officers argue in a corridor; the standoff has looped.",
            "recent_environment_events": [],
            "tension_history": ["escalate", "escalate"],
            "resolved_events": [],
            "location": "HQ corridor",
            "scene_phase": "rising",
            "current_tension_level": "high",
            "recent_delta": "",
            "latest_trigger": "Morgan: 'We are not doing this again.'",
            "present_characters": ["Blake", "Morgan"],
            "offstage_characters": [],
        },
        "scene_template": {
            "template_id": "progression_llm_probe",
            "premise": "Authority clash",
            "location_entry_slots": [],
        },
        "scene_roles": [
            {"character": "Blake", "role": "senior", "presence_constraint": "", "authority": "high"},
            {"character": "Morgan", "role": "junior", "presence_constraint": "", "authority": "medium"},
        ],
        "recent_structured_character_actions": [
            {
                "speaker": "Blake",
                "action": "holds position at the door",
                "dialogue": "Nobody leaves until I say so.",
                "motivation": {"goal": "control exit", "tactic": "block"},
            },
            {
                "speaker": "Morgan",
                "action": "squared shoulders",
                "dialogue": "We are not doing this again.",
                "motivation": {"goal": "break the loop", "tactic": "push back"},
            },
        ],
        "character_states": {},
        "recent_dialogue_history": [],
        "spotlight_history": ["Blake", "Morgan"],
        "active_issues": [
            {
                "issue_id": "authority_clash",
                "description": "Who controls the exit and the next move",
                "status": "escalating",
                "participants": ["Blake", "Morgan"],
            }
        ],
        "summary_blocks": [],
        "recent_public_events": [],
        "scene_canon_anchors": [],
        "participants": ["Blake", "Morgan"],
        "available_next_actors": ["Blake", "Morgan"],
        "actors_already_used_this_round": [],
    }

    stall_score, stall_components = compute_stall_score(
        scene_state=director_payload["current_scene_state"],
        recent_structured_moves=list(director_payload["recent_structured_character_actions"]),
        active_issues=list(director_payload["active_issues"]),
        beat_shift_snapshots=[
            {"phase": "rising", "tension": "high"},
            {"phase": "rising", "tension": "high"},
        ],
    )
    advisory = build_progression_advisory(
        stall_score=stall_score,
        stall_components=stall_components,
        progression_profile=default_progression_profile(),
    )
    prog_prefix = build_progression_director_prompt_prefix(advisory)
    assert prog_prefix, "expected high-pressure progression prefix for this payload"
    director_payload["progression_director_hints"] = {
        "active": True,
        "prompt_prefix": prog_prefix,
    }

    prompt = build_director_selection_prompt(director_payload)
    assert "PROGRESSION ADVISORY" in prompt

    from autogen_agentchat.messages import TextMessage

    task = TextMessage(content=prompt, source="system")
    cancellation_token = CancellationToken()
    result = None
    async for item in director.on_messages_stream([task], cancellation_token):
        if isinstance(item, Response):
            result = item
    assert result is not None
    raw = result.chat_message.content
    start, end = raw.find("{"), raw.rfind("}") + 1
    assert start >= 0 and end > start, f"no JSON object in director response: {raw[:500]}"
    decision = json.loads(raw[start:end])
    assert decision.get("next_actor") in ("Blake", "Morgan"), decision

    await director.on_reset(CancellationToken())


@pytest.mark.llm
@pytest.mark.progression_llm
@pytest.mark.slow
@pytest.mark.asyncio
async def test_llm_character_move_passes_progression_delta_after_process_turn(
    deepseek_model_client,
) -> None:
    """Under enforcement-style instructions, model emits a move continuity classifies as a progression delta."""

    now = datetime.now(timezone.utc)
    issue = IssueState(
        issue_id="standoff",
        description="Blocked exit; orders conflict",
        participants=["Blake", "Morgan"],
        status=IssueStatus.ESCALATING,
        created_at=now,
        last_turn_index=None,
        status_reason="test seed",
    )
    cm = ContinuityManager()
    cm.initialize_scene(
        location="corridor",
        opening_description="Blake and Morgan face off at the security door.",
        present_characters=["Blake", "Morgan"],
        initial_issues=[issue],
    )
    cm.scene_state.current_tension_level = "high"

    system_message = """You are Blake in a structured RP engine.
Output exactly one JSON object and no other text.
Schema:
{
  "action": "concrete observable behavior",
  "dialogue": "spoken line (may be short)",
  "motivation": {"goal": "str", "tactic": "str", "emotional_driver": "str", "risk_level": "medium"}
}
Rules:
- Morgan is blocking your path; the scene has stalled on talk.
- This beat must CHANGE the situation: refusal, ultimatum, physical attempt to pass, or clear commitment — not observation alone.
- Use wording that clearly refuses, commands, or forces a decision (e.g. "step aside or I go through you")."""

    user_turn = """PROGRESSION ADVISORY: The scene should advance through a concrete change in state (action, movement, consequence, or commitment), not only continued verbal escalation.

TRIGGER: Morgan repeats that nobody leaves. You must break the loop with your next move."""

    blake = AssistantAgent(
        name="Blake",
        model_client=deepseek_model_client,
        system_message=system_message,
        description="Progression probe character",
    )

    from autogen_agentchat.messages import TextMessage

    task = TextMessage(content=user_turn, source="user")
    cancellation_token = CancellationToken()
    result = None
    async for item in blake.on_messages_stream([task], cancellation_token):
        if isinstance(item, Response):
            result = item
    assert result is not None
    raw = result.chat_message.content
    move, err = parse_character_move(raw)
    assert move is not None and not err, f"parse failed: {err} raw={raw[:800]}"

    issues_before = collect_issue_signatures(cm)
    decision = {
        "next_actor": "Blake",
        "environment_event": "",
        "tension_shift": "escalate",
        "reason": "llm progression probe",
    }
    cm.process_turn(
        acting_character="Blake",
        move=move,
        director_decision=decision,
        other_characters=["Morgan"],
    )
    turn_index = cm.turn_counter
    turn_meta = cm.turn_metadata_by_index.get(turn_index, {})
    assert qualifies_as_progression_delta(
        continuity_manager=cm,
        turn_index=turn_index,
        turn_meta=turn_meta if isinstance(turn_meta, dict) else {},
        issues_before=issues_before,
        move=move,
    ), (
        f"LLM move did not yield Q1–Q4 progression delta; "
        f"consequences={turn_meta.get('consequences')!r} turn_index={turn_index}"
    )

    await blake.on_reset(CancellationToken())
