from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from orchestration_helpers import (
    append_turn_to_orchestration_state,
    assign_progression_band_for_actor,
    build_recent_scene_context,
    choose_fallback_actor,
    ensure_orchestration_state,
    resolve_progression_override_actor,
    resolve_continuation_override_actor,
    sync_orchestration_state_from_continuity,
)

from app_turn_director import choose_next_actor as choose_next_actor_impl


class SerializableItem:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.summary_id = str(payload.get("summary_id", ""))
        self.description = str(payload.get("description", ""))
        self.summary = str(payload.get("summary", ""))
        self.statement = str(payload.get("statement", ""))
        self.key_events = list(payload.get("key_events", []))

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


class FakeContinuityManager:
    def __init__(self) -> None:
        self.summary_blocks = [
            SerializableItem(
                {"summary_id": "summary_1", "key_events": ["Old conflict"]}
            )
        ]
        self.summary_interval = 12
        self.turn_counter = 12
        self.scene_state = SimpleNamespace(
            location="workshop",
            time_of_day="night",
            environment_description="The forge glows low.",
            scene_template_id="ayame_household_entry_evaluation",
            scene_premise="A guarded entry.",
            role_assignments={"Ayame": "host"},
            character_presence_constraints={"Ayame": "must_remain"},
            character_authority_labels={"Ayame": "high"},
            present_characters=["Ayame", "Celina"],
            phase=SimpleNamespace(value="confrontation"),
            current_tension_level="high",
            recent_delta="Celina challenged the entry.",
            opening_description="The household receives a newcomer.",
            recent_environment_events=["A draft slips under the door."],
        )

    def get_orchestration_context(
        self, active_issue_limit: int, recent_event_limit: int, summary_limit: int
    ) -> dict[str, object]:
        assert active_issue_limit >= 3
        assert recent_event_limit >= 3
        assert summary_limit >= 2
        return {
            "resolved_events": ["Entry complete"],
            "active_issues": [
                SerializableItem(
                    {"issue_id": "issue_1", "description": "Entry challenge"}
                )
            ],
            "recent_public_events": [
                SerializableItem(
                    {"event_id": "event_1", "summary": "Celina blocked the doorway."}
                )
            ],
            "summary_blocks": self.summary_blocks[:summary_limit],
            "scene_canon_anchors": [
                SerializableItem(
                    {
                        "anchor_id": "canon_1",
                        "statement": "Ayame protects the household.",
                    }
                )
            ],
        }

    def get_snapshot(self) -> SimpleNamespace:
        scene_state_dict = {
            "opening_description": self.scene_state.opening_description,
            "location": self.scene_state.location,
            "environment_description": self.scene_state.environment_description,
            "recent_environment_events": list(
                self.scene_state.recent_environment_events
            ),
            "tension_history": ["steady", "high"],
            "current_tension_level": self.scene_state.current_tension_level,
        }
        return SimpleNamespace(
            scene_state=SimpleNamespace(to_dict=lambda: scene_state_dict)
        )

    def retrieve_summary_blocks(self, limit: int = 0) -> list[SerializableItem]:
        return self.summary_blocks[:] if limit == 0 else self.summary_blocks[:limit]


def test_ensure_orchestration_state_initializes_missing_defaults() -> None:
    state = ensure_orchestration_state(None)

    assert state["spotlight_history"] == []
    assert state["recent_structured_moves"] == []
    assert state["director_decisions"] == []
    assert state["scene_state"]["scene_template_id"] == ""


def test_choose_fallback_actor_prefers_non_last_spotlight_actor() -> None:
    assert choose_fallback_actor(["Ayame", "Celina"], None, ["Ayame"]) == "Celina"


def test_choose_fallback_actor_prefer_continuing_spotlight_keeps_last_when_available() -> (
    None
):
    assert (
        choose_fallback_actor(
            ["Ayame", "Celina"],
            None,
            ["Ayame"],
            prefer_continuing_spotlight=True,
        )
        == "Ayame"
    )


def test_append_turn_to_orchestration_state_updates_bounded_histories() -> None:
    state = ensure_orchestration_state(None)

    updated = append_turn_to_orchestration_state(
        orchestration_state=state,
        next_actor="Ayame",
        move={
            "action": "steps forward",
            "dialogue": "No.",
            "motivation": {"goal": "block"},
        },
        decision={
            "environment_event": "The shutters rattle.",
            "tension_shift": "escalate",
            "reason": "direct response",
        },
        spotlight_history_limit=2,
        structured_move_history_limit=2,
        director_decision_history_limit=2,
        environment_history_limit=2,
        tension_history_limit=2,
    )

    assert updated["spotlight_history"] == ["Ayame"]
    assert updated["recent_structured_moves"][0]["speaker"] == "Ayame"
    assert updated["director_decisions"][0]["reason"] == "direct response"
    assert updated["scene_state"]["recent_environment_events"] == [
        "The shutters rattle."
    ]
    assert updated["scene_state"]["tension_history"] == ["escalate"]


def test_assign_progression_band_is_neutral_when_outcome_fields_missing() -> None:
    state = ensure_orchestration_state(None)
    state["recent_structured_moves"] = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
        }
    ]
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[],
        recent_structured_moves=state["recent_structured_moves"],
    )
    assert band == "med"


def test_assign_progression_band_marks_high_for_escalating_issue_participant() -> None:
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[
            {
                "status": "escalating",
                "participants": ["Ayame"],
            }
        ],
        recent_structured_moves=[],
    )
    assert band == "high"


def test_assign_progression_band_marks_high_for_active_issue_with_interaction_density() -> (
    None
):
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[
            {
                "status": "active",
                "participants": ["Ayame", "Celina"],
            }
        ],
        recent_structured_moves=[],
    )
    assert band == "high"


def test_assign_progression_band_marks_high_for_active_issue_with_momentum() -> None:
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stepped forward",
            "dialogue": "No.",
            "motivation": {"goal": "block", "tactic": "deny"},
            "consequences": ["authority_asserted"],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[
            {
                "status": "active",
                "participants": ["Ayame"],
            }
        ],
        recent_structured_moves=recent_moves,
    )
    assert band == "high"


def test_assign_progression_band_marks_low_only_for_non_actionable_with_weak_repetition() -> (
    None
):
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[],
        recent_structured_moves=recent_moves,
    )
    assert band == "low"


def test_assign_progression_band_does_not_mark_low_when_actor_is_in_active_issue_even_with_weak_repetition() -> (
    None
):
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    band = assign_progression_band_for_actor(
        actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=[{"status": "active", "participants": ["Ayame"]}],
        recent_structured_moves=recent_moves,
    )
    assert band == "med"


def test_resolve_progression_override_actor_overrides_only_low_to_high_when_actionable_exists() -> (
    None
):
    active_issues = [
        {
            "status": "escalating",
            "participants": ["Celina"],
        }
    ]
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    override = resolve_progression_override_actor(
        director_selected_actor="Ayame",
        available_actors=["Ayame", "Mira", "Celina"],
        active_issues=active_issues,
        recent_structured_moves=recent_moves,
    )
    assert override == "Celina"


async def _run_choose_next_actor_early_return(
    *,
    session_state: dict[str, object],
    available_actors: list[str],
    continuation_override_actor: str | None,
) -> dict[str, object]:
    st_module = SimpleNamespace(session_state=session_state)
    session_state.setdefault("selector_decisions", [])
    return await choose_next_actor_impl(
        st_module=st_module,
        director=None,
        get_model_client_fn=lambda: None,
        participant_names=available_actors,
        trigger_text="hello",
        cancellation_token=None,
        round_number=1,
        turn_number=1,
        available_actors=available_actors,
        continuation_override_actor=continuation_override_actor,
        enforce_must_remain_presence_fn=lambda: None,
        get_orchestration_state_fn=lambda: {},
        get_continuity_manager_fn=lambda: None,
        build_scene_role_prompt_context_fn=lambda *_args, **_kwargs: {},
        serialize_summary_blocks_for_prompt_fn=lambda *_args, **_kwargs: [],
        build_summary_block_audit_metadata_fn=lambda *_args, **_kwargs: {},
        serialize_events_for_prompt_fn=lambda *_args, **_kwargs: [],
        serialize_canon_anchors_for_prompt_fn=lambda *_args, **_kwargs: [],
        build_director_selection_prompt_fn=lambda *_args, **_kwargs: "",
        parse_director_decision_fn=lambda *_args, **_kwargs: ({"next_actor": ""}, ""),
        choose_fallback_actor_fn=lambda *_args, **_kwargs: "",
        validate_turn_selection_decision_fn=lambda *_args, **_kwargs: [],
        assess_turn_selection_decision_semantics_fn=lambda *_args, **_kwargs: {},
        reconcile_turn_selection_issues_fn=lambda issues, _assessment: issues,
        is_audit_enabled_fn=lambda: False,
        get_audit_logger_fn=lambda: None,
        get_audit_context_fn=lambda: ("", 0, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_args, **_kwargs: {},
        refresh_audit_summary_report_fn=lambda: None,
        build_recent_dialogue_history_fn=lambda *_args, **_kwargs: [],
        prompt_dialogue_history_limit=6,
        director_spotlight_history_limit=6,
    )


@pytest.mark.asyncio
async def test_direct_address_forced_speaker_overrides_everything() -> None:
    decision = await _run_choose_next_actor_early_return(
        session_state={
            "pending_forced_speaker": "Celina",
            "forced_speaker_consumed": False,
            "selector_decisions": [],
        },
        available_actors=["Ayame", "Celina"],
        continuation_override_actor="Ayame",
    )
    assert decision.get("next_actor") == "Celina"


@pytest.mark.asyncio
async def test_continuation_override_dominates_over_director_and_progression() -> None:
    decision = await _run_choose_next_actor_early_return(
        session_state={
            "pending_forced_speaker": None,
            "forced_speaker_consumed": False,
            "selector_decisions": [],
        },
        available_actors=["Ayame", "Celina"],
        continuation_override_actor="Ayame",
    )
    assert decision.get("next_actor") == "Ayame"


def test_resolve_progression_override_actor_no_override_when_only_stalled_issues_exist() -> (
    None
):
    active_issues = [
        {
            "status": "stalled",
            "participants": ["Celina", "Ayame"],
        }
    ]
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    override = resolve_progression_override_actor(
        director_selected_actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=active_issues,
        recent_structured_moves=recent_moves,
    )
    assert override is None


def test_resolve_progression_override_actor_prefers_escalating_participant_when_overriding() -> (
    None
):
    active_issues = [
        {
            "status": "active",
            "participants": ["Mira", "Celina"],
        },
        {
            "status": "escalating",
            "participants": ["Celina"],
        },
    ]
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "stood still",
            "dialogue": "",
            "motivation": {"goal": "wait", "tactic": "silence"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        }
    ]
    override = resolve_progression_override_actor(
        director_selected_actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=active_issues,
        recent_structured_moves=recent_moves,
    )
    assert override == "Celina"


def test_resolve_continuation_override_actor_allows_one_step_owned_continuation() -> None:
    orchestration_state = ensure_orchestration_state(None)
    orchestration_state["recent_structured_moves"] = [
        {
            "speaker": "Ayame",
            "action": "steps into Celina's path",
            "dialogue": "No.",
            "motivation": {
                "goal": "hold the doorway and force Celina to stop",
                "tactic": "maintain the physical block until Celina yields",
            },
        }
    ]
    orchestration_state["spotlight_history"] = ["Ayame"]
    continuity_manager = SimpleNamespace(
        turn_counter=1,
        turn_metadata_by_index={1: {"tags": ["authority_asserted"]}},
    )

    assert (
        resolve_continuation_override_actor(
            orchestration_state=orchestration_state,
            continuity_manager=continuity_manager,
            eligible_participants=["Ayame", "Celina"],
            actors_used_this_round=["Ayame"],
        )
        == "Ayame"
    )


def test_resolve_continuation_override_actor_rejects_superseded_line() -> None:
    orchestration_state = ensure_orchestration_state(None)
    orchestration_state["recent_structured_moves"] = [
        {
            "speaker": "Ayame",
            "action": "steps into Celina's path",
            "dialogue": "No.",
            "motivation": {
                "goal": "hold the doorway and force Celina to stop",
                "tactic": "maintain the physical block until Celina yields",
            },
        }
    ]
    orchestration_state["spotlight_history"] = ["Ayame"]
    continuity_manager = SimpleNamespace(
        turn_counter=1,
        turn_metadata_by_index={1: {"tags": ["refusal"]}},
    )

    assert (
        resolve_continuation_override_actor(
            orchestration_state=orchestration_state,
            continuity_manager=continuity_manager,
            eligible_participants=["Ayame", "Celina"],
            actors_used_this_round=["Ayame"],
        )
        is None
    )


def test_sync_orchestration_state_from_continuity_copies_scene_and_continuity_views() -> (
    None
):
    continuity_manager = FakeContinuityManager()
    state = ensure_orchestration_state(None)
    enforced: list[str] = []

    updated = sync_orchestration_state_from_continuity(
        orchestration_state=state,
        continuity_manager=continuity_manager,
        enforce_must_remain_presence_fn=lambda: enforced.append("called"),
    )

    assert enforced == ["called"]
    assert updated["scene_state"]["location"] == "workshop"
    assert (
        updated["scene_state"]["scene_template_id"]
        == "ayame_household_entry_evaluation"
    )
    assert updated["scene_state"]["role_assignments"] == {"Ayame": "host"}
    assert updated["continuity_active_issues"] == [
        {"issue_id": "issue_1", "description": "Entry challenge"}
    ]
    assert updated["continuity_recent_public_events"] == [
        {"event_id": "event_1", "summary": "Celina blocked the doorway."}
    ]
    assert updated["continuity_summary_blocks"] == [
        {"summary_id": "summary_1", "key_events": ["Old conflict"]}
    ]


def test_build_recent_scene_context_formats_continuity_and_transcript_sections() -> (
    None
):
    continuity_manager = FakeContinuityManager()
    orchestration_state = ensure_orchestration_state(None)
    chat_history = [
        {"role": "assistant", "speaker": "Ayame", "content": "State your purpose."},
        {"role": "user", "speaker": "Alex", "content": "I'm here to talk."},
    ]

    context, audit = build_recent_scene_context(
        chat_history=chat_history,
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
        build_recent_dialogue_history_fn=lambda history, _limit: [
            {"speaker": item["speaker"], "content": item["content"]} for item in history
        ],
        limit=6,
    )

    assert "OPENING DESCRIPTION:" in context
    assert "LOCATION:" in context
    assert "CURRENT ENVIRONMENT:" in context
    assert "ACTIVE ISSUES:" in context
    assert "RECENT PUBLIC EVENTS:" in context
    assert "OLDER CONTINUITY SUMMARY BLOCKS:" in context
    assert "SCENE CANON:" in context
    assert "RECENT TRANSCRIPT:" in context
    assert audit["summary_blocks_selected_count"] == 1
    assert audit["summary_limit"] == 2
