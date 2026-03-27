from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_prompting import _build_priority_ladder, _select_relationship_prompt_names
from character_state import CharacterState
from prompt_builders import (
    build_character_turn_prompt,
    build_director_selection_prompt,
    build_narrator_render_prompt,
    build_scene_role_prompt_context,
)


def test_build_scene_role_prompt_context_preserves_requested_participant_order() -> (
    None
):
    scene_state = {
        "role_assignments": {"Ayame": "host", "Celina": "guard"},
        "character_presence_constraints": {
            "Ayame": "must_remain",
            "Celina": "must_remain",
        },
        "character_authority_labels": {"Ayame": "high"},
    }

    assert build_scene_role_prompt_context(scene_state, ["Celina", "Ayame"]) == [
        {
            "character": "Celina",
            "role": "guard",
            "presence_constraint": "must_remain",
            "authority": "",
        },
        {
            "character": "Ayame",
            "role": "host",
            "presence_constraint": "must_remain",
            "authority": "high",
        },
    ]


def test_build_director_selection_prompt_serializes_payload_as_json_block() -> None:
    director_payload = {
        "participants": ["Ayame", "Celina"],
        "available_next_actors": ["Celina"],
        "current_scene_state": {"latest_trigger": "Ayame asks a direct question."},
    }

    prompt = build_director_selection_prompt(director_payload)

    assert prompt.startswith(
        "Decide who acts next using only the structured scene information below. Return JSON only. "
    )
    assert "end_round" in prompt
    assert '"participants": [' in prompt
    assert '"available_next_actors": [' in prompt
    assert '"latest_trigger": "Ayame asks a direct question."' in prompt


def test_build_character_turn_prompt_includes_expected_sections_and_rules() -> None:
    prompt = build_character_turn_prompt(
        char_name="Ayame",
        user_name="Alex",
        trigger_text="Celina challenges Ayame in front of the room.",
        director_decision={
            "next_actor": "Ayame",
            "reason": "She was directly addressed.",
        },
        scene_state={"location": "workshop", "present_characters": ["Ayame", "Celina"]},
        scene_template_context={
            "template_id": "ayame_household_entry_evaluation",
            "premise": "A guarded entry.",
        },
        my_scene_role={
            "character": "Ayame",
            "role": "host",
            "presence_constraint": "must_remain",
            "authority": "high",
        },
        scene_roles=[
            {
                "character": "Ayame",
                "role": "host",
                "presence_constraint": "must_remain",
                "authority": "high",
            },
            {
                "character": "Celina",
                "role": "guard",
                "presence_constraint": "must_remain",
                "authority": "",
            },
        ],
        recent_moves=[
            {"speaker": "Celina", "action": "steps closer", "dialogue": "Answer me."}
        ],
        recent_dialogue=[
            {"role": "assistant", "speaker": "Celina", "content": "Answer me."}
        ],
        active_issues=[{"issue_id": "issue_1", "summary": "Entry challenge"}],
        priority_ladder=[
            "Persistent obligation: hold the doorway and control the exchange",
            "Preferred execution stance: answer Celina without ceding space",
            "Local subtask only if it serves a higher obligation: answer Celina directly",
            "Active issue pressure only if it materially blocks, invalidates, or supersedes your current line: Entry challenge",
        ],
        summary_blocks=[
            {"summary_id": "summary_1_12", "key_events": ["A confrontation begins."]}
        ],
        recent_public_events=[
            {"summary": "Celina blocked the doorway.", "knowledge_level": "observed"}
        ],
        cross_session_user_memories=["Alex once defended Ayame."],
        cross_session_world_facts=["The workshop forge matters."],
        user_preferences=["Alex prefers direct answers."],
        my_interpretations=[{"summary": "Celina is testing me."}],
        canon_anchors=[
            {"anchor_id": "canon_1", "statement": "Ayame protects the household."}
        ],
        state_context="Private goal: maintain control without revealing fear.",
        cast=["Celina"],
    )

    assert "CURRENT SCENE STATE:" in prompt
    assert "SCENE TEMPLATE:" in prompt
    assert "YOUR SCENE ROLE:" in prompt
    assert "CAST ROLE MAP:" in prompt
    assert "SUMMARY BLOCKS (OLDER CONTINUITY HISTORY):" in prompt
    assert "PRIORITY LADDER FOR THIS BEAT:" in prompt
    assert "ACTIVE ISSUES / PRESSURES (ACTIONABLE NOW):" in prompt
    assert "STALLED / BACKGROUND ISSUES" in prompt
    assert "default to staying occupied with your own business" in prompt
    assert "fear, hierarchy, and institutional pressure often suppress speech" in prompt
    assert "Stay within your own established language repertoire" in prompt
    assert (
        "Preserve the established meaning of ambiguous terms from the scene context"
        in prompt
    )
    assert (
        "Rumors and secondhand claims should usually prompt source, credibility, and implication questions"
        in prompt
    )
    assert "Do not upgrade uncertainty into certainty" in prompt
    assert "Do not broaden the scene's ontology beyond what canon anchors" in prompt
    assert (
        "Do not exaggerate healing speed, power scale, duration, ease, or form-specific limitations"
        in prompt
    )
    assert (
        "Rare, miraculous, or destabilizing events should not be flattened into routine logistics"
        in prompt
    )
    assert (
        "Treat earlier items in the priority ladder as more important than later ones"
        in prompt
    )
    assert (
        "treat triage and stabilization as higher priority than comfort, grooming, drying"
        in prompt
    )
    assert (
        "Do not let a small care subtask become the whole meaning of the beat" in prompt
    )
    assert "Continue your current objective and short-term tactic by default" in prompt
    assert (
        "Continue your current line of action unless it has been materially blocked, invalidated, or superseded"
        in prompt
    )
    assert (
        "Active issue pressure should shape how you continue your line, not replace it by default"
        in prompt
    )
    assert "Only output a JSON object with action, dialogue, and motivation." in prompt
    assert "OTHER PRESENT CHARACTERS: Celina" in prompt
    assert "PLAYER NAME: Alex" in prompt


def test_build_priority_ladder_places_active_issue_after_owned_line() -> None:
    ladder = _build_priority_ladder(
        state=CharacterState(
            name="Ayame",
            current_objective="hold the doorway and control the exchange",
            short_term_tactic="answer Celina without ceding space",
            local_task_goal="answer Celina directly",
            local_task_tactic="hold eye contact while refusing to step back",
        ),
        active_issues=[{"issue_id": "issue_1", "summary": "Entry challenge"}],
    )

    assert ladder == [
        "Persistent obligation: hold the doorway and control the exchange",
        "Preferred execution stance: answer Celina without ceding space",
        "Local subtask only if it serves a higher obligation: answer Celina directly",
        "Local execution detail: hold eye contact while refusing to step back",
        "Active issue pressure only if it materially blocks, invalidates, or supersedes your current line: Entry challenge",
    ]


def test_select_relationship_prompt_names_prioritizes_protagonist_and_co_holder_roles() -> (
    None
):
    focus_names, secondary_names = _select_relationship_prompt_names(
        char_name="Celina",
        cast=["Kizzie", "Ayame", "Orderly"],
        my_scene_role={
            "character": "Celina",
            "role": "protector",
            "presence_constraint": "must_remain",
            "authority": "high",
        },
        scene_roles=[
            {
                "character": "Celina",
                "role": "protector",
                "presence_constraint": "must_remain",
                "authority": "high",
            },
            {
                "character": "Kizzie",
                "role": "recovering_demi_human",
                "presence_constraint": "must_remain",
                "authority": "low",
            },
            {
                "character": "Ayame",
                "role": "host",
                "presence_constraint": "must_remain",
                "authority": "high",
            },
            {
                "character": "Orderly",
                "role": "observer",
                "presence_constraint": "present",
                "authority": "",
            },
        ],
    )

    assert focus_names == ["Kizzie", "Ayame"]
    assert secondary_names == ["Orderly"]


def test_build_narrator_render_prompt_with_dialogue_preserves_verbatim_rule() -> None:
    prompt = build_narrator_render_prompt(
        char_name="Ayame",
        action="narrows her eyes",
        dialogue="Who is she?",
        environment_event="The shutters rattle in the wind.",
        scene_context="A tense room.",
    )

    assert (
        "Render the following character action and dialogue into scene narration."
        in prompt
    )
    assert 'DIALOGUE TO INCLUDE: "Who is she?"' in prompt
    assert "Include the EXACT dialogue in double quotes as provided above" in prompt
    assert "NEVER paraphrase or alter the quoted dialogue" in prompt
    assert (
        "Preserve the established meaning of ambiguous or figurative language already present in the scene context and provided dialogue"
        in prompt
    )


def test_build_narrator_render_prompt_without_dialogue_uses_action_only_variant() -> (
    None
):
    prompt = build_narrator_render_prompt(
        char_name="Ayame",
        action="narrows her eyes",
        dialogue="",
        environment_event="",
        scene_context="A tense room.",
    )

    assert "Render the following character action into scene narration." in prompt
    assert "DIALOGUE TO INCLUDE" not in prompt
    assert "Only describe what this character does" in prompt
    assert (
        "Preserve the established meaning of ambiguous or figurative language already present in the scene context"
        in prompt
    )
