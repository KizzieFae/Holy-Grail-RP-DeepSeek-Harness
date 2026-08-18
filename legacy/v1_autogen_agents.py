"""Legacy V1 AutoGen character agent construction (not used by V2 production)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _REPO_ROOT / "autogen_rp" / "python" / "rp_app"
_V2 = _REPO_ROOT / "v2"
for path in (_RP_APP, _V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from autogen_agentchat.agents import AssistantAgent  # noqa: E402
from autogen_core.model_context import BufferedChatCompletionContext  # noqa: E402
from autogen_core.models import ChatCompletionClient  # noqa: E402
from character_state import CharacterState  # noqa: E402
from domain.character_cards import (  # noqa: E402
    make_agent_identifier,
    normalize_relationships,
    validate_character_card,
)
from model_client import MODEL_CONTEXT_BUFFER_SIZE  # noqa: E402


def build_character_system_message(character_card: dict[str, Any]) -> str:
    char_name = character_card["name"]
    voice_profile = character_card.get("voice_profile", {})
    reaction_profile = character_card.get("reaction_profile", {})
    speech_fingerprint = character_card.get("speech_fingerprint", {})
    core_goals = character_card.get("core_goals", [])

    system_parts = [f"You are {char_name}."]

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

    if "system_prompt" in character_card:
        system_parts.append(character_card["system_prompt"])

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
            "You must respond with a single JSON object: canonical character move v2.",
            '  "move_schema_version": 2 (integer, required)',
            '  "semantic_evaluation": { "decision": "covered_change" | "no_covered_change", "proposals": [ ... ] } — REQUIRED every beat. Include non-empty proposals only when decision is covered_change (self-only off_focal, reentry, or excursion_lifecycle items; operation required only for excursion_lifecycle). Omit proposals when decision is no_covered_change. Do not emit root semantic_proposals or semantic_proposals: [].',
            '  "beats": [ ordered beats — each object is either:',
            '    {"type": "action", "action": "Brief visible action YOU take only (3rd person). What YOU do, not others."}',
            '    or {"type": "speech", "dialogue": "What you say out loud (optional audibility / audience on speech beats — see below)"} ]',
            "  Speech audibility (only on type speech): omit audibility for public speech. Use audibility directed or private only when limiting who hears the line; then include non-empty audience (array of present character names). For public speech, omit audience or use [].",
            "  Audibility/audience controls who receives verbatim dialogue in prompts — it does not by itself change continuity focal presence.",
            "  Do not put root-level action, dialogue, audibility, or audience on the JSON object — only inside beats[].",
            '  "motivation": {"goal": "What you want", "tactic": "How you are pursuing it", "emotional_driver": "What feeling drives you", "risk_level": "low|medium|high"} (required)',
            '  "scene_state_updates": {"sleeping_surface_assignment": {"assignee_id": "character", "surface_id": "surface"}, "housing_call_outcome": {"status": "completed|failed"}, "suppressant_formulation_outcome": {"subject_id": "character", "status": "compatible|incompatible"}, "location_entry_outcome": {"subject_id": "character", "location_id": "bounded_location", "status": "allowed|denied"}} (optional)',
            "Only include scene_state_updates.sleeping_surface_assignment when your own move explicitly establishes, actively enforces against present resistance or dispute, or reassigns where someone will sleep in this turn.",
            "Contested enforcement vs reminder: Include scene_state_updates.sleeping_surface_assignment when another present character has just challenged the existing sleeping plan in the current exchange, and your move directly responds by keeping the same assignee_id on the same surface_id, even if your tone is soft, conciliatory, or framed as \"already settled.\" That is contested enforcement, not a reminder. Do not use tone as the deciding factor. Do not include the field when no such challenge is present and your move is only informational, referential, or housekeeping about an assignment nobody is contesting in that exchange.",
            "Do not include it for offers, suggestions, negotiation, reactions, observations, reminders, restating prior state, or unresolved argument.",
            "Do not include it solely because the assignment is unchanged unless the contested-enforcement case above applies.",
            "surface_id must be exactly one valid allowed surface_id value, not a list, blend, or descriptive phrase.",
            "Only include scene_state_updates.housing_call_outcome when your own move explicitly settles the shared housing/res-life call by making it completed or failed in this turn.",
            "housing_call_outcome.status must be exactly one of: completed or failed.",
            "Do not include housing_call_outcome for discussing, planning, attempting, dialing, waiting on hold, leaving voicemail, or asking whether someone called.",
            "Only include scene_state_updates.suppressant_formulation_outcome when your own move explicitly settles whether a named subject's current suppressant formulation is compatible or incompatible in this turn.",
            "suppressant_formulation_outcome.status must be exactly one of: compatible or incompatible.",
            "Do not include suppressant_formulation_outcome for symptoms alone, suspicion, diagnosis, dosage changes, treatment planning, or historical formulations.",
            "Only include scene_state_updates.location_entry_outcome when your own move explicitly settles a named subject's current permission to enter one bounded location in this turn.",
            "Emit it only for direct permission rulings such as \"you may enter\" or \"you are not allowed inside.\"",
            "Do not include location_entry_outcome for requests, predictions, preferences, blocked paths, locked doors, or physical obstruction.",
            "Do not treat \"not yet,\" \"for now,\" \"stay here,\" \"wait,\" or \"until I say otherwise\" as permission settlement. These are control instructions, not allowed/denied outcomes.",
            "Do not include location_entry_outcome for partial, conditional, or fragmented permission that does not clearly resolve to allowed or denied for the specified location.",
            "Base location_entry_outcome emission on the in-fiction assertion made in the turn, not on whether the speaker has real authority.",
            "location_entry_outcome.location_id must match the intended in-fiction location exactly. Do not remap, normalize, or substitute it. If the location is outside the allowed set, emit it as-is and let validation reject it.",
            "location_entry_outcome.status must be exactly one of: allowed or denied.",
            "",
            "EXAMPLES:",
            'Positive: {"move_schema_version": 2, "beats": [{"type": "action", "action": "pointed at the couch and squared her shoulders"}, {"type": "speech", "dialogue": "Take the couch tonight. That\'s final."}], "motivation": {"goal": "settle the room", "tactic": "issue a firm instruction", "emotional_driver": "protective resolve", "risk_level": "medium"}, "scene_state_updates": {"sleeping_surface_assignment": {"assignee_id": "Kizzie", "surface_id": "couch"}}}',
            'Negative: {"move_schema_version": 2, "beats": [{"type": "action", "action": "gestured between the couch and the floor"}, {"type": "speech", "dialogue": "You can take the couch if you want."}], "motivation": {"goal": "offer an option", "tactic": "keep the decision open", "emotional_driver": "tentative concern", "risk_level": "low"}}',
            "",
            "RULE: Only output the JSON object. No other text.",
        ]
    )
    return "\n".join(system_parts)


def create_character_state_from_card(character_card: dict[str, Any]) -> CharacterState:
    validate_character_card(character_card)
    char_name = character_card["name"]
    core_goals = character_card.get("core_goals", [])
    voice_profile = character_card.get("voice_profile", {})
    reaction_profile = character_card.get("reaction_profile", {})
    speech_fingerprint = character_card.get("speech_fingerprint", {})
    relationships = normalize_relationships(character_card.get("relationships", {}))
    return CharacterState(
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


def create_character_agent(
    character_card: dict[str, Any],
    model_client: ChatCompletionClient,
) -> tuple[AssistantAgent, CharacterState]:
    """Create a legacy V1 AutoGen AssistantAgent and CharacterState from a card."""
    validate_character_card(character_card)
    char_name = character_card["name"]
    agent_name = str(
        character_card.get("agent_name", "") or make_agent_identifier(char_name)
    )
    system_message = build_character_system_message(character_card)
    agent = AssistantAgent(
        name=agent_name,
        model_client=model_client,
        system_message=system_message,
        description=character_card.get("description", f"Character: {char_name}"),
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )
    return agent, create_character_state_from_card(character_card)
