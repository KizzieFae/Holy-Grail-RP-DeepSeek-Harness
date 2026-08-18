"""Framework-neutral character card I/O (no AutoGen, Streamlit, or provider deps)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Canonical v2 character move JSON schema (model-facing contract; GitHub #142).
CHARACTER_MOVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "move_schema_version": {
            "type": "integer",
            "description": "Must be exactly 2 for this character move contract.",
        },
        "beats": {
            "type": "array",
            "minItems": 1,
            "description": "Ordered beats for this turn: action (visible self-only) and/or speech (dialogue).",
            "items": {
                "type": "object",
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["action"],
                                "description": "Physical / visible beat.",
                            },
                            "action": {
                                "type": "string",
                                "description": "Brief visible action (self only, third person). Describe what YOU do, not others.",
                            },
                        },
                        "required": ["type", "action"],
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["speech"],
                                "description": "Spoken beat.",
                            },
                            "dialogue": {
                                "type": "string",
                                "description": "What you say out loud. Use first person within quotes when applicable.",
                            },
                            "audibility": {
                                "type": "string",
                                "enum": ["public", "directed", "private"],
                                "description": "Optional on speech beats; omit for public. directed/private require non-empty audience.",
                            },
                            "audience": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Required when audibility is directed or private; omit or empty for public.",
                            },
                        },
                        "required": ["type", "dialogue"],
                    },
                ],
            },
        },
        "motivation": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The immediate goal you are trying to advance.",
                },
                "tactic": {
                    "type": "string",
                    "description": "The approach you are using in this moment.",
                },
                "emotional_driver": {
                    "type": "string",
                    "description": "The feeling or pressure driving your choice.",
                },
                "risk_level": {
                    "type": "string",
                    "description": "The level of risk you are willing to take right now.",
                },
            },
            "required": ["goal", "tactic", "emotional_driver", "risk_level"],
            "description": "Private structured motivation for this move.",
        },
        "scene_state_updates": {
            "type": "object",
            "properties": {
                "sleeping_surface_assignment": {
                    "type": "object",
                    "properties": {
                        "assignee_id": {
                            "type": "string",
                            "description": "Who the acting speaker is establishing, actively enforcing against present resistance or dispute, or explicitly reassigning a sleeping surface for in this move.",
                        },
                        "surface_id": {
                            "type": "string",
                            "description": "Exactly one valid surface_id from the allowed set for the bounded sleeping surface the acting speaker is establishing for that assignee in this move.",
                        },
                    },
                    "required": ["assignee_id", "surface_id"],
                    "description": "Optional. Use only when the acting speaker's own move explicitly establishes, actively enforces against present resistance or dispute, or reassigns where someone will sleep, and only if this turn changes or newly settles that assignment.",
                },
                "housing_call_outcome": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Terminal housing-call outcome only. Must be exactly one of: completed or failed.",
                        },
                    },
                    "required": ["status"],
                    "description": "Optional. Use only when the acting speaker's own move explicitly settles the shared housing/res-life call thread by making it completed or failed in this turn. Do not use it for planning, attempting, waiting, or discussing the call without a terminal outcome.",
                },
                "suppressant_formulation_outcome": {
                    "type": "object",
                    "properties": {
                        "subject_id": {
                            "type": "string",
                            "description": "Who the acting speaker is explicitly settling current suppressant formulation compatibility for in this move.",
                        },
                        "status": {
                            "type": "string",
                            "description": "Current suppressant formulation compatibility only. Must be exactly one of: compatible or incompatible.",
                        },
                    },
                    "required": ["subject_id", "status"],
                    "description": "Optional. Use only when the acting speaker's own move explicitly settles whether the named subject's current suppressant formulation is compatible or incompatible in this turn. Do not use it for symptoms, suspicion, diagnosis, dosage, historical formulations, or treatment planning.",
                },
                "location_entry_outcome": {
                    "type": "object",
                    "properties": {
                        "subject_id": {
                            "type": "string",
                            "description": "Who the acting speaker is explicitly granting or denying current entry permission for in this move.",
                        },
                        "location_id": {
                            "type": "string",
                            "description": "The exact intended in-fiction location_id. Do not remap, normalize, or substitute it. If it is outside the bounded allowed set already present in the current scene or template, emit it as-is and let validation reject it.",
                        },
                        "status": {
                            "type": "string",
                            "description": "Current entry permission only. Must be exactly one of: allowed or denied.",
                        },
                    },
                    "required": ["subject_id", "location_id", "status"],
                    "description": "Optional. Use only when the acting speaker's own move explicitly settles a named subject's current permission to enter one bounded location in this turn. Do not use it for requests, predictions, preferences, blocked paths, locked doors, physical obstruction, cautionary control language like not yet or wait, or for partial, conditional, or fragmented permission.",
                },
            },
            "description": "Optional scene-state updates for bounded sleeping-surface assignment, housing-call outcome, current suppressant-formulation compatibility, or current location-entry permission facts settled by this move.",
        },
        "semantic_evaluation": {
            "type": "object",
            "description": "Required every beat. decision is covered_change or no_covered_change; include non-empty proposals only when decision is covered_change (self-only off_focal, reentry, or excursion_lifecycle items). Omit proposals when decision is no_covered_change. Do not emit root semantic_proposals or semantic_proposals: [].",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["covered_change", "no_covered_change"],
                    "description": "Whether this beat has covered semantic commit intent for continuity.",
                },
                "proposals": {
                    "type": "array",
                    "description": "Required non-empty when decision is covered_change; omit when no_covered_change. Semantic commit intent only (continuity evaluates and accepts or rejects).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": ["off_focal", "reentry", "excursion_lifecycle"],
                                "description": "Proposal kind: off_focal interval, explicit reentry, or excursion lifecycle.",
                            },
                            "character": {
                                "type": "string",
                                "description": "Character subject of this proposal.",
                            },
                            "operation": {
                                "type": "string",
                                "enum": ["open", "update", "close"],
                                "description": "Required when kind is excursion_lifecycle; omit for off_focal and reentry.",
                            },
                        },
                        "required": ["kind", "character"],
                    },
                },
            },
            "required": ["decision"],
        },
    },
    "required": ["move_schema_version", "beats", "motivation", "semantic_evaluation"],
    "description": "Character move v2: move_schema_version 2, non-empty beats[], motivation, required semantic_evaluation, optional scene_state_updates.",
}


def default_characters_dir() -> Path:
    """Resolve the repository character-card directory."""
    return (
        Path(__file__).resolve().parents[2]
        / "autogen_rp"
        / "python"
        / "data"
        / "autogen_characters"
    )


def make_agent_identifier(name: str) -> str:
    """Convert a display name into a valid agent identifier (framework-neutral naming)."""
    raw_name = str(name or "").strip()
    if not raw_name:
        return "Character"

    identifier = re.sub(r"\W+", "_", raw_name, flags=re.UNICODE).strip("_")
    if not identifier:
        identifier = "Character"
    if identifier[0].isdigit():
        identifier = f"Character_{identifier}"
    if not identifier.isidentifier():
        identifier = re.sub(r"[^0-9A-Za-z_]", "_", identifier).strip("_") or "Character"
        if identifier[0].isdigit():
            identifier = f"Character_{identifier}"
    return identifier


def normalize_relationships(relationships: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(relationships, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for target_name, raw_relationship in relationships.items():
        target = str(target_name or "").strip()
        if not target:
            continue
        if isinstance(raw_relationship, str):
            stance = raw_relationship.strip()
            normalized[target] = (
                {"entity_type": "character", "stance": stance}
                if stance
                else {"entity_type": "character"}
            )
            continue
        if not isinstance(raw_relationship, dict):
            continue

        relationship = dict(raw_relationship)
        relationship["entity_type"] = (
            str(relationship.get("entity_type", "character") or "character").strip()
            or "character"
        )
        for field_name in (
            "stance",
            "tactical_posture",
            "long_term_goal",
            "medium_term_goal",
            "current_objective",
            "threat_level",
            "usefulness",
            "last_summary",
            "relationship_trend",
        ):
            if field_name in relationship:
                relationship[field_name] = str(
                    relationship.get(field_name, "") or ""
                ).strip()
        normalized[target] = relationship

    return normalized


def validate_character_card(character_card: dict[str, Any]) -> None:
    if not isinstance(character_card, dict):
        raise ValueError(
            f"Character card must be a dict, got {type(character_card)}"
        )
    missing = [field for field in ("name", "description") if field not in character_card]
    if missing:
        raise ValueError(f"Character card missing required fields: {missing}")


class CharacterCardLoader:
    """Loads and enumerates authored character cards from JSON files."""

    def __init__(self, characters_dir: str | Path | None = None) -> None:
        self.characters_dir = (
            Path(characters_dir) if characters_dir is not None else default_characters_dir()
        )

    def load_character_card(self, filename: str) -> dict[str, Any]:
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = self.characters_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Character file not found: {filepath}")

        with open(filepath, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Character file must contain a JSON object: {filepath}")
        return data

    def list_available_characters(self) -> list[str]:
        if not self.characters_dir.exists():
            return []

        characters: list[str] = []
        for filepath in self.characters_dir.glob("*.json"):
            if "lorebook" in filepath.stem.lower():
                continue
            try:
                with open(filepath, encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and "name" in data:
                    characters.append(filepath.stem)
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(characters)
