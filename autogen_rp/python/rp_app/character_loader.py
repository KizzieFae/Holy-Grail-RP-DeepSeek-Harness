"""Character loader module for RP app.

Handles loading character cards from JSON and creating AssistantAgent instances
with structured output format for narrator-mediated architecture.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import ChatCompletionClient
from character_state import CharacterState
from model_client import MODEL_CONTEXT_BUFFER_SIZE

# JSON schema for character structured output
CHARACTER_MOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "Brief visible action the character takes (self only, third person). Describe what YOU do, not others.",
        },
        "dialogue": {
            "type": "string",
            "description": "What the character says out loud, if anything. Use first person within quotes.",
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
                }
            },
            "description": "Optional scene-state update for a sleeping-surface assignment settled by this move.",
        },
    },
    "required": ["action", "motivation"],
    "description": "Character move: core action, dialogue, private structured motivation, and an optional sleeping-surface assignment update settled by this move.",
}


def make_agent_identifier(name: str) -> str:
    """Convert a display name into a valid AssistantAgent identifier."""
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


def _normalize_relationships(relationships: Any) -> dict[str, dict[str, Any]]:
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


class CharacterLoader:
    """Loads character cards and creates AssistantAgent instances."""

    def __init__(self, characters_dir: str | Path = None) -> None:
        """Initialize the character loader.

        Args:
            characters_dir: Directory containing character JSON files.
                           Defaults to data/characters/ relative to project root.
        """
        if characters_dir is None:
            # Default to python/data/autogen_characters/
            self.characters_dir = (
                Path(__file__).parent.parent / "data" / "autogen_characters"
            )
        else:
            self.characters_dir = Path(characters_dir)

    def load_character_card(self, filename: str) -> dict[str, Any]:
        """Load a character card from JSON file.

        Args:
            filename: Name of the JSON file (with or without .json extension)

        Returns:
            Character card dictionary

        Raises:
            FileNotFoundError: If character file doesn't exist
            json.JSONDecodeError: If file is invalid JSON
        """
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = self.characters_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Character file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_available_characters(self) -> list[str]:
        """List all available character files.

        Returns:
            List of character filenames (without .json extension)
        """
        if not self.characters_dir.exists():
            return []

        characters = []
        for filepath in self.characters_dir.glob("*.json"):
            # Skip lorebook files
            if "lorebook" in filepath.stem.lower():
                continue
            # Skip if not a valid character card (must be a dict with 'name')
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "name" in data:
                    characters.append(filepath.stem)
            except (json.JSONDecodeError, IOError):
                continue

        return sorted(characters)

    def create_agent(
        self,
        character_card: dict[str, Any],
        model_client: ChatCompletionClient,
    ) -> tuple[AssistantAgent, CharacterState]:
        """Create an AssistantAgent and CharacterState from a character card.

        Args:
            character_card: Character card dictionary
            model_client: Model client for the agent

        Returns:
            Tuple of (Configured AssistantAgent, CharacterState for private tracking)

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if not isinstance(character_card, dict):
            raise ValueError(
                f"Character card must be a dict, got {type(character_card)}"
            )

        required_fields = ["name", "description"]
        missing = [f for f in required_fields if f not in character_card]
        if missing:
            raise ValueError(f"Character card missing required fields: {missing}")

        char_name = character_card["name"]
        agent_name = str(
            character_card.get("agent_name", "") or make_agent_identifier(char_name)
        )
        voice_profile = character_card.get("voice_profile", {})
        reaction_profile = character_card.get("reaction_profile", {})
        speech_fingerprint = character_card.get("speech_fingerprint", {})
        core_goals = character_card.get("core_goals", [])
        relationships = _normalize_relationships(
            character_card.get("relationships", {})
        )

        # Build system message from character card - structured output format
        system_parts = []

        # Core identity
        system_parts.append(f"You are {char_name}.")

        if "personality" in character_card:
            system_parts.append(f"Personality: {character_card['personality']}")

        if "speaking_style" in character_card:
            system_parts.append(f"Speaking style: {character_card['speaking_style']}")

        if "goals" in character_card:
            system_parts.append(f"Goals: {character_card['goals']}")

        if core_goals:
            system_parts.append(
                f"Core goals: {json.dumps(core_goals, ensure_ascii=False)}"
            )

        if voice_profile:
            system_parts.append(
                "Voice profile (never drop or summarize this): "
                f"{json.dumps(voice_profile, ensure_ascii=False)}"
            )

        if reaction_profile:
            system_parts.append(
                "Reaction profile (use this to interpret events): "
                f"{json.dumps(reaction_profile, ensure_ascii=False)}"
            )

        if speech_fingerprint:
            system_parts.append(
                "Speech fingerprint (lightweight voice reminders): "
                f"{json.dumps(speech_fingerprint, ensure_ascii=False)}"
            )

        # Add the main system prompt if provided
        if "system_prompt" in character_card:
            system_parts.append(character_card["system_prompt"])

        # Critical RP constraints for narrator-mediated architecture
        system_parts.extend(
            [
                "",
                "CRITICAL RULES:",
                f"- You are {char_name} and ONLY {char_name}.",
                "- NEVER speak for the user or other characters.",
                "- NEVER narrate what other characters do, think, or feel.",
                "- NEVER describe other characters' reactions or expressions.",
                "- Only speak as yourself, in your own voice, from your own perspective.",
                "- Only your own actions and words should appear in your response.",
                "- Your voice_profile, reaction_profile, speech_fingerprint, and core goals are persistent identity anchors.",
                "- Do not flatten your voice to match the others; keep your own diction, cadence, and worldview.",
                "- Use your reaction_profile to interpret events through your own bias, not an objective shared truth.",
                "- Stay in character at all times.",
                "",
                "OUTPUT FORMAT:",
                "You must respond with a JSON object using these core fields, plus one narrow optional field when needed:",
                '  "action": "Brief description of YOUR visible action only (3rd person, past tense). What YOU do, not others.",',
                '  "dialogue": "What you say out loud, if anything. Use first person inside quotes. (Optional, can be empty)",',
                '  "motivation": {"goal": "What you want", "tactic": "How you are pursuing it", "emotional_driver": "What feeling drives you", "risk_level": "low|medium|high"},',
                '  "scene_state_updates": {"sleeping_surface_assignment": {"assignee_id": "character", "surface_id": "surface"}} (optional)',
                "Only include scene_state_updates.sleeping_surface_assignment when your own move explicitly establishes, actively enforces against present resistance or dispute, or reassigns where someone will sleep in this turn.",
                "Do not include it for offers, suggestions, negotiation, reactions, observations, reminders, restating prior state, or unresolved argument.",
                "Do not include it if the sleeping assignment is already established and this move does not change it.",
                "surface_id must be exactly one valid allowed surface_id value, not a list, blend, or descriptive phrase.",
                "",
                "EXAMPLES:",
                'Positive: {"action": "pointed at the couch and squared her shoulders", "dialogue": "Take the couch tonight. That\'s final.", "motivation": {"goal": "settle the room", "tactic": "issue a firm instruction", "emotional_driver": "protective resolve", "risk_level": "medium"}, "scene_state_updates": {"sleeping_surface_assignment": {"assignee_id": "Kizzie", "surface_id": "couch"}}}',
                'Negative: {"action": "gestured between the couch and the floor", "dialogue": "You can take the couch if you want.", "motivation": {"goal": "offer an option", "tactic": "keep the decision open", "emotional_driver": "tentative concern", "risk_level": "low"}}',
                "",
                "RULE: Only output the JSON object. No other text.",
            ]
        )

        system_message = "\n".join(system_parts)

        # Create the agent
        agent = AssistantAgent(
            name=agent_name,
            model_client=model_client,
            system_message=system_message,
            description=character_card.get("description", f"Character: {char_name}"),
            model_context=BufferedChatCompletionContext(
                buffer_size=MODEL_CONTEXT_BUFFER_SIZE
            ),
        )

        # Create initial character state
        character_state = CharacterState(
            name=char_name,
            description=character_card.get("description", ""),
            personality=character_card.get("personality", ""),
            long_term_goal=character_card.get("goals", ""),
            medium_term_goal=character_card.get("medium_term_goal", ""),
            core_goals=core_goals,
            voice_profile=voice_profile,
            reaction_profile=reaction_profile,
            speech_fingerprint=speech_fingerprint,
            relationships=relationships,
        )

        return agent, character_state

    def load_and_create_agent(
        self,
        filename: str,
        model_client: ChatCompletionClient,
    ) -> tuple[AssistantAgent, CharacterState]:
        """Convenience method to load a character file and create an agent.

        Args:
            filename: Character JSON filename
            model_client: Model client for the agent

        Returns:
            Tuple of (Configured AssistantAgent, CharacterState for private tracking)
        """
        card = self.load_character_card(filename)
        return self.create_agent(card, model_client)
