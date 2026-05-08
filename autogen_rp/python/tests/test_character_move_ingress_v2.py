"""Unit tests for Issue #137 / #143 character move ingress (v2-only, caps, adapters)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_move_adapters import (
    CanonicalV2Move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
    legacy_move_text_for_validation,
)
from character_move_ingress import (
    MAX_V2_BEATS,
    ingest_character_move_json_object,
    load_json_object_duplicate_safe,
    parse_character_move_content_to_v2,
    validate_canonical_v2,
)


def test_duplicate_key_rejects_before_ingest() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        load_json_object_duplicate_safe('{"a": 1, "a": 2}')


def test_nested_duplicate_key_rejects() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        load_json_object_duplicate_safe('{"x": {"y": 1, "y": 2}}')


def test_v1_shaped_object_without_version_rejects() -> None:
    d = json.loads(
        '{"action": "x", "dialogue": "y", "motivation": {"goal": "g", "tactic": "t", '
        '"emotional_driver": "e", "risk_level": "l"}, "intent": "bad"}'
    )
    m, err = ingest_character_move_json_object(d)
    assert m is None and "move_schema_version is required" in (err or "")


def test_v1_shaped_object_unknown_extra_root_rejects() -> None:
    """Without move_schema_version, ingress does not apply v1 allowlist; require v2 first."""
    d = json.loads(
        '{"action": "x", "dialogue": "y", "motivation": {"goal": "g", "tactic": "t", '
        '"emotional_driver": "e", "risk_level": "l"}}'
    )
    m, err = ingest_character_move_json_object(d)
    assert m is None and "move_schema_version is required" in (err or "")


def test_v2_rejects_mixed_action_with_version() -> None:
    d = {
        "move_schema_version": 2,
        "action": "bad",
        "beats": [
            {"type": "action", "action": "a"},
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "l",
        },
    }
    m, err = ingest_character_move_json_object(d)
    assert m is None and "invalid mixed" in err


def test_unknown_move_schema_version_rejects() -> None:
    d = {
        "move_schema_version": 3,
        "beats": [{"type": "action", "action": "a"}],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "l",
        },
    }
    m, err = ingest_character_move_json_object(d)
    assert m is None and "Unsupported" in err


def test_v2_string_round_trip_minimal() -> None:
    s = (
        '{"move_schema_version":2,"beats":[{"type":"action","action":"A"}],'
        '"motivation":{"goal":"g","tactic":"t","emotional_driver":"e","risk_level":"r"}}'
    )
    m, err = parse_character_move_content_to_v2(s)
    assert not err
    assert m and m.get("action") == "A"


def test_cap_beats_count() -> None:
    many = [
        {
            "type": "action",
            "action": "x",
        }
    ] * (MAX_V2_BEATS + 1)
    d = {
        "move_schema_version": 2,
        "beats": many,
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "l",
        },
    }
    m, err = ingest_character_move_json_object(d)
    assert m is None and "beats" in (err or "").lower()


def test_adapters_parity() -> None:
    d = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "One"},
            {"type": "speech", "dialogue": "Two"},
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "l",
        },
    }
    c = CanonicalV2Move()
    c.update(d)
    assert legacy_flat_action_text(c) == "One"
    assert legacy_flat_dialogue_text(c) == "Two"
    assert legacy_move_text_for_validation(c) == "One Two"
    assert "action" not in c and "dialogue" not in c


def test_validate_rejects_speech_public_with_audience() -> None:
    d = {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "speech",
                "dialogue": "Hi",
                "audibility": "public",
                "audience": ["A"],
            }
        ],
        "motivation": {
            "goal": "g",
            "tactic": "t",
            "emotional_driver": "e",
            "risk_level": "l",
        },
    }
    assert validate_canonical_v2(d) != ""
