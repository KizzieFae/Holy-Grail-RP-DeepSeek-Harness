"""Integration: character prompt assembly must not leak directed dialogue to non-recipients.

Exercises ``app_turn_prompting.build_character_turn_prompt`` with a fake session (no LLM,
no Streamlit) so filtering runs on the same path as production before ``prompt_builders``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_prompting import build_character_turn_prompt
from perception_audibility import build_recent_dialogue_history_for_viewer
from prompt_builders import build_character_turn_prompt as build_character_turn_prompt_text
from prompt_builders import build_scene_role_prompt_context
from summary_audit_helpers import build_summary_block_audit_metadata

_SECRET = "XYZZY_LEAK_PROBE_INTEGRATION_99"
_CAST = ["Alice", "Bob", "Carol"]


def _fake_st_module(*, chat_history: list[dict], orchestration_state: dict) -> SimpleNamespace:
    return SimpleNamespace(
        session_state={
            "characters": [SimpleNamespace(name=n) for n in _CAST],
            "chat_history": chat_history,
            "cross_session_memories": {},
        }
    )


def _orch_state_with_whisper_move() -> dict:
    return {
        "recent_structured_moves": [
            {
                "speaker": "Alice",
                "action": "whispers to Bob",
                "dialogue": _SECRET,
                "motivation": {},
                "environment_event": "",
                "tension_shift": "",
                "audibility": "directed",
                "audience": ["Bob"],
            }
        ],
        "scene_state": {
            "present_characters": list(_CAST),
            "role_assignments": {},
            "character_presence_constraints": {},
            "character_authority_labels": {},
        },
        "spotlight_history": [],
    }


def _chat_assistant_beat() -> dict:
    return {
        "role": "assistant",
        "speaker": "Alice",
        "actor": "Alice",
        "content": (
            f'Alice leaned toward Bob and murmured, "{_SECRET}" '
            "while Carol looked out the window."
        ),
        "move": {
            "action": "whispers to Bob",
            "dialogue": _SECRET,
            "audibility": "directed",
            "audience": ["Bob"],
        },
    }


def _build_recent_dialogue_wrapper(
    chat_history: list[dict],
    *,
    limit: int,
    viewer_character_name: str | None = None,
) -> list[dict[str, str]]:
    return build_recent_dialogue_history_for_viewer(
        chat_history=chat_history,
        viewer_character_name=viewer_character_name,
        character_names=_CAST,
        get_character_display_name_fn=lambda n: n,
        limit=limit,
    )


def _run_character_prompt(char_name: str) -> str:
    orch = _orch_state_with_whisper_move()
    st = _fake_st_module(
        chat_history=[_chat_assistant_beat()],
        orchestration_state=orch,
    )
    prompt, _audit = build_character_turn_prompt(
        st_module=st,
        char_name=char_name,
        user_name="Traveler",
        trigger_text="Everyone waits.",
        director_decision={"next_actor": char_name, "reason": "test"},
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: orch,
        get_continuity_manager_fn=lambda: None,
        build_recent_dialogue_history_fn=_build_recent_dialogue_wrapper,
        serialize_events_for_prompt_fn=lambda *a, **k: [],
        serialize_canon_anchors_for_prompt_fn=lambda *a, **k: [],
        serialize_summary_blocks_for_prompt_fn=lambda *a, **k: [],
        build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
        build_character_turn_prompt_text_fn=build_character_turn_prompt_text,
        prompt_structured_move_limit=8,
        prompt_dialogue_history_limit=12,
        get_character_display_name_fn=lambda n: n,
    )
    return prompt


def test_directed_dialogue_hidden_from_non_recipient_character_prompt() -> None:
    carol_prompt = _run_character_prompt("Carol")
    assert _SECRET not in carol_prompt
    assert "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):" in carol_prompt
    assert "RECENT STRUCTURED ACTIONS (PERCEPTION-FILTERED FOR THIS CHARACTER):" in carol_prompt


def test_directed_dialogue_visible_to_addressee_character_prompt() -> None:
    bob_prompt = _run_character_prompt("Bob")
    assert _SECRET in bob_prompt


def test_directed_dialogue_visible_to_speaker_character_prompt() -> None:
    alice_prompt = _run_character_prompt("Alice")
    assert _SECRET in alice_prompt
