from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from turn_selection_preference import (
    build_routing_preference_snapshot,
    resolve_participant_key,
    sanitize_semantic_turn_selection_assessment,
)


def test_resolve_participant_key_matches_display_name() -> None:
    assert (
        resolve_participant_key(
            "Hannah Lovelace",
            ["Ayame", "Hannah_Lovelace"],
            display_name_for_key=lambda k: (
                "Hannah Lovelace" if k == "Hannah_Lovelace" else k
            ),
        )
        == "Hannah_Lovelace"
    )


def test_sanitize_clears_direct_address_miss_when_pick_matches_resolved_target() -> None:
    out = sanitize_semantic_turn_selection_assessment(
        {
            "should_flag_direct_address_miss": True,
            "direct_address_target": "Ayame",
            "supports_selected_actor": False,
        },
        selected_actor="Ayame",
        participant_names=["Ayame", "Celina"],
        display_name_for_key=lambda k: k,
    )
    assert out is not None
    assert out["should_flag_direct_address_miss"] is False
    assert out["supports_selected_actor"] is True


def test_build_routing_preference_prefers_responder_obligation_over_action() -> None:
    snap = build_routing_preference_snapshot(
        responder_obligation={
            "active": True,
            "confidence": "high",
            "primary_actor": "Celina",
        },
        action_responsibility={
            "active": True,
            "confidence": "high",
            "primary_actor": "Ayame",
        },
        available_actors=["Ayame", "Celina"],
    )
    assert snap["preference_candidate"] == "Celina"
    assert snap["preference_source"] == "responder_obligation"
