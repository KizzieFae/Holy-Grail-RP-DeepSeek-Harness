"""Integration: episodic recall wiring in app_turn_prompting (Phase 3.2 step 4)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_prompting import build_character_turn_prompt
from continuity_manager import ContinuityManager
from continuity_scene_helpers import initialize_scene_state
from continuity_state import PublicEvent
from perception_audibility import build_recent_dialogue_history_for_viewer
from prompt_builders import build_character_turn_prompt as build_character_turn_prompt_text
from prompt_builders import build_scene_role_prompt_context
from summary_audit_helpers import build_summary_block_audit_metadata

_CAST = ["Alice", "Bob"]


def _fake_st_module(*, chat_history: list[dict], orchestration_state: dict) -> SimpleNamespace:
    return SimpleNamespace(
        session_state={
            "characters": [SimpleNamespace(name=n) for n in _CAST],
            "chat_history": chat_history,
            "cross_session_memories": {},
        }
    )


def _orch_state() -> dict:
    return {
        "recent_structured_moves": [],
        "scene_state": {
            "present_characters": list(_CAST),
            "role_assignments": {},
            "character_presence_constraints": {},
            "character_authority_labels": {},
            "scene_template_id": "",
            "scene_premise": "",
        },
        "spotlight_history": [],
    }


def _continuity_with_event(*, known_by: list[str]) -> ContinuityManager:
    m = ContinuityManager()
    initialize_scene_state(
        manager=m,
        location="room",
        opening_description="",
        present_characters=list(_CAST),
    )
    m.public_events.append(
        PublicEvent(
            event_id="e_episodic_integration",
            timestamp=datetime(2025, 1, 2, 15, 0, 0, tzinfo=timezone.utc),
            event_type="action",
            participants=["Alice"],
            summary="EPISODIC_UNIQUE_LINE_FOR_TEST",
            turn_index=1,
            significance="major",
            known_by=list(known_by),
        )
    )
    return m


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


def _prompt_for(
    *,
    char_name: str,
    monkeypatch,
    episodic_env: str | None,
    continuity: ContinuityManager,
) -> str:
    if episodic_env is None:
        monkeypatch.delenv("RP_EPISODIC_MEMORY", raising=False)
    else:
        monkeypatch.setenv("RP_EPISODIC_MEMORY", episodic_env)

    orch = _orch_state()
    st = _fake_st_module(chat_history=[], orchestration_state=orch)
    prompt, _audit = build_character_turn_prompt(
        st_module=st,
        char_name=char_name,
        user_name="Traveler",
        trigger_text="Continue.",
        director_decision={"next_actor": char_name, "reason": "test"},
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: orch,
        get_continuity_manager_fn=lambda: continuity,
        build_recent_dialogue_history_fn=_build_recent_dialogue_wrapper,
        serialize_events_for_prompt_fn=lambda events, character_name: [
            {"summary": e.summary, "knowledge_level": "observed"} for e in events
        ],
        serialize_canon_anchors_for_prompt_fn=lambda anchors: [a.to_dict() for a in anchors],
        serialize_summary_blocks_for_prompt_fn=lambda blocks: [b.to_dict() for b in blocks],
        build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
        build_character_turn_prompt_text_fn=build_character_turn_prompt_text,
        prompt_structured_move_limit=8,
        prompt_dialogue_history_limit=12,
        get_character_display_name_fn=lambda n: n,
    )
    return prompt


def test_episodic_disabled_no_episodic_line_in_retrieved(monkeypatch):
    m = _continuity_with_event(known_by=["Alice", "Bob"])
    p = _prompt_for(
        char_name="Alice",
        monkeypatch=monkeypatch,
        episodic_env=None,
        continuity=m,
    )
    assert "episodic:" not in p


def test_episodic_enabled_visible_character_gets_merged_retrieved(monkeypatch):
    m = _continuity_with_event(known_by=["Alice"])
    p = _prompt_for(
        char_name="Alice",
        monkeypatch=monkeypatch,
        episodic_env="1",
        continuity=m,
    )
    assert "RETRIEVED REFERENCE MATERIAL (NON-AUTHORITATIVE):" in p
    assert "episodic:public_event" in p
    assert "EPISODIC_UNIQUE_LINE_FOR_TEST" in p


def test_episodic_enabled_not_in_known_by_gets_no_episodic_line(monkeypatch):
    m = _continuity_with_event(known_by=["Alice"])
    p = _prompt_for(
        char_name="Bob",
        monkeypatch=monkeypatch,
        episodic_env="1",
        continuity=m,
    )
    assert "episodic:" not in p


def test_episodic_pool_cache_shared_across_characters_same_session(monkeypatch):
    m = _continuity_with_event(known_by=["Alice", "Bob"])
    monkeypatch.setenv("RP_EPISODIC_MEMORY", "1")
    orch = _orch_state()
    st = _fake_st_module(chat_history=[], orchestration_state=orch)

    def run(char_name: str) -> None:
        build_character_turn_prompt(
            st_module=st,
            char_name=char_name,
            user_name="Traveler",
            trigger_text="Continue.",
            director_decision={"next_actor": char_name, "reason": "test"},
            enforce_must_remain_presence_fn=lambda: None,
            get_orchestration_state_fn=lambda: orch,
            get_continuity_manager_fn=lambda: m,
            build_recent_dialogue_history_fn=_build_recent_dialogue_wrapper,
            serialize_events_for_prompt_fn=lambda events, character_name: [
                {"summary": e.summary, "knowledge_level": "observed"} for e in events
            ],
            serialize_canon_anchors_for_prompt_fn=lambda anchors: [
                a.to_dict() for a in anchors
            ],
            serialize_summary_blocks_for_prompt_fn=lambda blocks: [
                b.to_dict() for b in blocks
            ],
            build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
            build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
            build_character_turn_prompt_text_fn=build_character_turn_prompt_text,
            prompt_structured_move_limit=8,
            prompt_dialogue_history_limit=12,
            get_character_display_name_fn=lambda n: n,
        )

    run("Alice")
    cache_after_alice = st.session_state.get("episodic_memory_candidate_cache")
    assert cache_after_alice is not None
    pool_alice = cache_after_alice.get("pool")
    run("Bob")
    cache_after_bob = st.session_state.get("episodic_memory_candidate_cache")
    assert cache_after_bob is not None
    assert cache_after_bob.get("snapshot_key") == cache_after_alice.get("snapshot_key")
    assert cache_after_bob.get("pool") is pool_alice
