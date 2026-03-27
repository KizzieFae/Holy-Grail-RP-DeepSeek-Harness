from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from summary_audit_helpers import (
    build_summary_block_audit_metadata,
    get_character_scene_audit_context,
    get_scene_audit_logging_kwargs,
    serialize_canon_anchors_for_prompt,
    serialize_events_for_prompt,
    serialize_summary_blocks_for_prompt,
)


class EventWithKnowledge:
    def __init__(self, summary: str) -> None:
        self.summary = summary

    def to_dict(self) -> dict[str, str]:
        return {"summary": self.summary}

    def knowledge_level_for(self, character_name: str) -> str:
        return f"known_by_{character_name.lower()}"


class SimpleSerializable:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.summary_id = str(payload.get("summary_id", ""))

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


def test_get_scene_audit_logging_kwargs_returns_empty_defaults_for_missing_scene() -> (
    None
):
    assert get_scene_audit_logging_kwargs(None) == {
        "scene_template_id": None,
        "scene_premise": "",
        "role_assignments": {},
        "character_presence_constraints": {},
        "character_authority_labels": {},
    }


def test_get_scene_audit_logging_kwargs_serializes_scene_state_fields() -> None:
    scene_state = SimpleNamespace(
        scene_template_id="household_entry_evaluation",
        scene_premise="A guarded evaluation.",
        role_assignments={"Ayame": "host"},
        character_presence_constraints={"Ayame": "must_remain"},
        character_authority_labels={"Ayame": "high"},
    )

    assert get_scene_audit_logging_kwargs(scene_state) == {
        "scene_template_id": "household_entry_evaluation",
        "scene_premise": "A guarded evaluation.",
        "role_assignments": {"Ayame": "host"},
        "character_presence_constraints": {"Ayame": "must_remain"},
        "character_authority_labels": {"Ayame": "high"},
    }


def test_get_character_scene_audit_context_reads_role_presence_and_authority() -> None:
    scene_audit = {
        "role_assignments": {"Ayame": "host"},
        "character_presence_constraints": {"Ayame": "must_remain"},
        "character_authority_labels": {"Ayame": "high"},
    }

    assert get_character_scene_audit_context("Ayame", scene_audit) == {
        "character_role": "host",
        "character_presence_constraint": "must_remain",
        "character_authority_label": "high",
    }


def test_serialize_events_for_prompt_includes_character_knowledge_level() -> None:
    serialized = serialize_events_for_prompt(
        [EventWithKnowledge("Door slams shut.")], character_name="Ayame"
    )

    assert serialized == [
        {"summary": "Door slams shut.", "knowledge_level": "known_by_ayame"}
    ]


def test_serialize_prompt_helpers_convert_serializable_items() -> None:
    anchor = SimpleSerializable(
        {"anchor_id": "canon_1", "statement": "The forge matters."}
    )
    summary = SimpleSerializable(
        {
            "summary_id": "summary_1_12",
            "key_events": ["A confrontation begins."],
            "continuity_facts": ["Ayame denied bringing danger directly to the forge."],
        }
    )

    assert serialize_canon_anchors_for_prompt([anchor]) == [
        {"anchor_id": "canon_1", "statement": "The forge matters."}
    ]
    assert serialize_summary_blocks_for_prompt([summary]) == [
        {
            "summary_id": "summary_1_12",
            "key_events": ["A confrontation begins."],
            "continuity_facts": ["Ayame denied bringing danger directly to the forge."],
        }
    ]


def test_build_summary_block_audit_metadata_tracks_generated_available_and_selected_ids() -> (
    None
):
    generated = [
        SimpleSerializable({"summary_id": "summary_1_12"}),
        SimpleSerializable({"summary_id": "summary_13_24"}),
    ]
    selected = [SimpleSerializable({"summary_id": "summary_13_24"})]

    metadata = build_summary_block_audit_metadata(
        generated_blocks=generated,
        available_blocks=generated,
        selected_blocks=selected,
        selection_reason="deterministic retrieval",
        summary_generation_eligible=True,
        summary_limit=2,
    )

    assert metadata["summary_generation_eligible"] is True
    assert metadata["summary_blocks_generated_total"] == 2
    assert metadata["generated_summary_block_ids"] == ["summary_1_12", "summary_13_24"]
    assert metadata["available_summary_block_ids"] == ["summary_1_12", "summary_13_24"]
    assert metadata["selected_summary_block_ids"] == ["summary_13_24"]
    assert metadata["excluded_summary_block_ids"] == ["summary_1_12"]
    assert metadata["selection_reason"] == "deterministic retrieval"
    assert metadata["summary_limit"] == 2
