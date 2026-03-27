"""Audit logging module for RP app.

Provides full and light-weight audit logging for bot interactions.
Organized by scene owner character, 3-digit session number, and round number.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from audit_logger_paths import (
    generate_filename as build_audit_filename,
    get_next_session_number as get_next_audit_session_number,
    get_round_path as get_audit_round_path,
    get_session_path as get_audit_session_path,
    resolve_base_dir,
)
from audit_logger_serialization import (
    append_limited as append_limited_helper,
    empty_summary_block_visibility as empty_summary_block_visibility_helper,
    entry_to_full_dict,
    entry_to_light_dict,
    normalize_scene_template_metadata as normalize_scene_template_metadata_helper,
    normalize_string_mapping as normalize_string_mapping_helper,
    normalize_summary_block_metadata as normalize_summary_block_metadata_helper,
    prompt_reference as prompt_reference_helper,
    utc_timestamp as utc_timestamp_helper,
)
from audit_logger_summary_report import (
    write_summary_report as write_summary_report_helper,
)
from audit_logger_writers import (
    update_narrative_summary as update_narrative_summary_helper,
    write_round_index as write_round_index_helper,
    write_session_manifest as write_session_manifest_helper,
)


class AuditLevel(Enum):
    """Audit detail levels."""

    FULL = "full"
    LIGHT = "light"


@dataclass
class AuditEntry:
    """A single audit entry for a bot interaction."""

    timestamp: str
    session_owner: str  # Character who owns the initial message/scene
    session_number: int  # 3-digit session number
    round_number: int
    turn_number: int
    bot_name: str  # Director, Narrator, or Character name
    bot_type: str  # director, narrator, character
    input_messages: list[dict[str, Any]] = field(default_factory=list)
    raw_response: str = ""
    parsed_output: dict[str, Any] = field(default_factory=dict)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_full_dict(self) -> dict[str, Any]:
        """Convert to full audit format."""
        return entry_to_full_dict(self)

    def to_light_dict(self) -> dict[str, Any]:
        """Convert to lightweight audit format."""
        return entry_to_light_dict(self)


ISSUE_CATEGORY_KEYS = (
    "character_drift",
    "memory_drift",
    "turn_selection_mistakes",
    "repetitive_phrasing",
    "continuity_signal_gaps",
    "issue_lifecycle_gaps",
)


def _empty_issue_categories() -> dict[str, dict[str, Any]]:
    return {key: {"count": 0, "examples": []} for key in ISSUE_CATEGORY_KEYS}


def _categorize_issue_text(text: str) -> str | None:
    normalized = str(text or "").lower()
    if not normalized:
        return None
    if any(
        token in normalized
        for token in [
            "character_drift",
            "wrong pov",
            "voice profile",
            "identity anchor",
        ]
    ):
        return "character_drift"
    if any(
        token in normalized
        for token in ["memory", "canon", "continuity", "summary block", "anchor"]
    ):
        return "memory_drift"
    if any(
        token in normalized
        for token in [
            "turn_selection",
            "direct address",
            "spotlight",
            "available_next_actors",
            "fallback selection",
        ]
    ):
        return "turn_selection_mistakes"
    if any(
        token in normalized
        for token in [
            "duplicate",
            "repeated content",
            "substantial content overlap",
            "repetitive",
        ]
    ):
        return "repetitive_phrasing"
    if any(
        token in normalized
        for token in [
            "state change",
            "recent_delta",
            "continuity_event_type",
            "actionable implication",
            "dialogue-only",
            "no material change",
            "consequence",
        ]
    ):
        return "continuity_signal_gaps"
    if any(
        token in normalized
        for token in [
            "stalled issue",
            "issue lifecycle",
            "resolved issue",
            "active issue",
            "issue update",
        ]
    ):
        return "issue_lifecycle_gaps"
    return None


def _record_issue_category(
    categories: dict[str, dict[str, Any]], category: str | None, example: str
) -> None:
    if category is None or category not in categories:
        return
    categories[category]["count"] += 1
    if example and example not in categories[category]["examples"]:
        categories[category]["examples"].append(example)
        categories[category]["examples"] = categories[category]["examples"][:5]


def _normalize_string_mapping(value: Any) -> dict[str, str]:
    return normalize_string_mapping_helper(value)


def _normalize_scene_template_metadata(value: Any) -> dict[str, Any]:
    return normalize_scene_template_metadata_helper(value)


def _empty_summary_block_visibility() -> dict[str, Any]:
    return empty_summary_block_visibility_helper()


def _normalize_summary_block_metadata(metadata: Any) -> dict[str, Any] | None:
    return normalize_summary_block_metadata_helper(metadata)


def _prompt_reference(
    round_number: int, turn_number: int, bot_name: str
) -> dict[str, Any]:
    return prompt_reference_helper(round_number, turn_number, bot_name)


def _append_limited(
    target: list[dict[str, Any]], value: dict[str, Any], limit: int = 20
) -> None:
    append_limited_helper(target, value, limit)


def utc_timestamp() -> str:
    return utc_timestamp_helper()


class AuditLogger:
    """Logger for bot interactions with full and light variants."""

    def __init__(self, base_dir: str | None = None):
        """Initialize audit logger.

        Args:
            base_dir: Base directory for audit logs. Defaults to data/rp_audits.
        """
        self.base_dir = resolve_base_dir(file_path=__file__, base_dir=base_dir)

    def get_next_session_number(self) -> int:
        """Return the next available audit session number."""
        return get_next_audit_session_number(base_dir=self.base_dir)

    def _get_session_path(self, session_owner: str, session_number: int) -> Path:
        """Get the directory path for a specific session.

        Args:
            session_owner: Character who owns the initial message/scene
            session_number: 3-digit session number

        Returns:
            Path to session directory
        """
        return get_audit_session_path(
            base_dir=self.base_dir, session_number=session_number
        )

    def _get_round_path(
        self, session_owner: str, session_number: int, round_number: int
    ) -> Path:
        """Get the directory path for a specific round within a session."""
        return get_audit_round_path(
            base_dir=self.base_dir,
            session_number=session_number,
            round_number=round_number,
        )

    def generate_filename(
        self,
        session_owner: str,
        session_number: int,
        round_number: int,
        turn_number: int,
        bot_name: str,
        level: AuditLevel,
    ) -> str:
        """Generate audit filename in format: {owner}_session{num}_round{num}_turn{num}_{bot}_{level}.json

        Args:
            session_owner: Character who owns the initial message/scene
            session_number: 3-digit session number
            round_number: Round number
            bot_name: Name of the bot (Director, Narrator, or Character name)
            level: Audit detail level

        Returns:
            Formatted filename
        """
        return build_audit_filename(
            session_owner=session_owner,
            session_number=session_number,
            round_number=round_number,
            turn_number=turn_number,
            bot_name=bot_name,
            level_value=level.value,
        )

    def write_session_manifest(
        self,
        session_owner: str,
        session_number: int,
        cast: list[str],
        opening_description: str,
        user_name: str,
        scene_template_id: str | None = None,
        scene_premise: str = "",
        role_assignments: dict[str, str] | None = None,
        character_presence_constraints: dict[str, str] | None = None,
        character_authority_labels: dict[str, str] | None = None,
        continuity_event: dict[str, Any] | None = None,
        scene_state_after: dict[str, Any] | None = None,
        issue_updates: list[dict[str, Any]] | None = None,
        presence_changes: list[dict[str, Any]] | None = None,
    ) -> str:
        """Write a session manifest file listing all characters and scene info.

        Args:
            session_owner: Character who owns the scene
            session_number: 3-digit session number
            cast: List of all character names in the scene
            opening_description: The scene opening text
            user_name: Player/user name
            scene_template_id: Optional scene template ID
            scene_premise: Optional scene premise
            role_assignments: Optional role assignments
            character_presence_constraints: Optional character presence constraints
            character_authority_labels: Optional character authority labels

        Returns:
            Path to manifest file
        """
        session_path = self._get_session_path(session_owner, session_number)
        return write_session_manifest_helper(
            session_path=session_path,
            session_owner=session_owner,
            session_number=session_number,
            cast=cast,
            opening_description=opening_description,
            user_name=user_name,
            scene_template_id=scene_template_id,
            scene_premise=scene_premise,
            role_assignments=role_assignments,
            character_presence_constraints=character_presence_constraints,
            character_authority_labels=character_authority_labels,
            continuity_event=continuity_event,
            scene_state_after=scene_state_after,
            issue_updates=issue_updates,
            presence_changes=presence_changes,
            normalize_scene_template_metadata=_normalize_scene_template_metadata,
            utc_timestamp=utc_timestamp,
        )

    def write_round_index(
        self,
        session_owner: str,
        session_number: int,
        round_number: int,
        turn_number: int,
        acting_character: str,
        director_choice_reason: str,
        acting_role: str = "",
        presence_constraint: str = "",
        authority_label: str = "",
        continuity_event_type: str = "",
        state_change_count: int = 0,
        issue_update_count: int = 0,
        presence_change_count: int = 0,
    ) -> str:
        """Append to a round index file mapping rounds to their turns.

        Args:
            session_owner: Character who owns the scene
            session_number: 3-digit session number
            round_number: Round number
            acting_character: Character who acted this round
            director_choice_reason: Why Director chose this character
            acting_role: Optional acting role
            presence_constraint: Optional presence constraint
            authority_label: Optional authority label

        Returns:
            Path to index file
        """
        session_path = self._get_session_path(session_owner, session_number)
        return write_round_index_helper(
            session_path=session_path,
            round_number=round_number,
            turn_number=turn_number,
            acting_character=acting_character,
            director_choice_reason=director_choice_reason,
            acting_role=acting_role,
            presence_constraint=presence_constraint,
            authority_label=authority_label,
            continuity_event_type=continuity_event_type,
            state_change_count=state_change_count,
            issue_update_count=issue_update_count,
            presence_change_count=presence_change_count,
            utc_timestamp=utc_timestamp,
        )

    def log_bot_interaction(
        self,
        entry: AuditEntry,
    ) -> tuple[str, str]:
        """Log a bot interaction with both full and light audit files.

        Args:
            entry: The audit entry to log

        Returns:
            Tuple of (full_filepath, light_filepath)
        """
        round_path = self._get_round_path(
            entry.session_owner, entry.session_number, entry.round_number
        )

        # Generate filenames
        full_filename = self.generate_filename(
            entry.session_owner,
            entry.session_number,
            entry.round_number,
            entry.turn_number,
            entry.bot_name,
            AuditLevel.FULL,
        )
        light_filename = self.generate_filename(
            entry.session_owner,
            entry.session_number,
            entry.round_number,
            entry.turn_number,
            entry.bot_name,
            AuditLevel.LIGHT,
        )

        full_path = round_path / full_filename
        light_path = round_path / light_filename

        # Write full audit
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(entry.to_full_dict(), f, indent=2, ensure_ascii=False)

        # Write light audit
        with open(light_path, "w", encoding="utf-8") as f:
            json.dump(entry.to_light_dict(), f, indent=2, ensure_ascii=False)

        return str(full_path), str(light_path)

    def create_entry(
        self,
        session_owner: str,
        session_number: int,
        round_number: int,
        turn_number: int,
        bot_name: str,
        bot_type: str,
        input_messages: list[dict[str, Any]],
        raw_response: str,
        parsed_output: dict[str, Any],
        context_snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        scene_template_id: str | None = None,
        scene_premise: str = "",
        role_assignments: dict[str, str] | None = None,
        character_presence_constraints: dict[str, str] | None = None,
        character_authority_labels: dict[str, str] | None = None,
    ) -> AuditEntry:
        """Create an audit entry with current timestamp.

        Args:
            session_owner: Character who owns the initial message/scene
            session_number: 3-digit session number
            round_number: Round number
            bot_name: Name of the bot
            bot_type: Type (director, narrator, character)
            input_messages: Messages sent to the bot
            raw_response: Raw response from the bot
            parsed_output: Parsed structured output
            context_snapshot: Snapshot of relevant context
            metadata: Additional metadata
            scene_template_id: Optional scene template ID
            scene_premise: Optional scene premise
            role_assignments: Optional role assignments
            character_presence_constraints: Optional character presence constraints
            character_authority_labels: Optional character authority labels

        Returns:
            Configured AuditEntry
        """
        scene_template = _normalize_scene_template_metadata(
            {
                "template_id": scene_template_id,
                "premise": scene_premise,
                "role_assignments": role_assignments or {},
                "character_presence_constraints": (
                    character_presence_constraints or {}
                ),
                "character_authority_labels": character_authority_labels or {},
            }
        )
        normalized_context_snapshot = dict(context_snapshot or {})
        if any(
            [
                scene_template["template_id"],
                scene_template["premise"],
                scene_template["role_assignments"],
                scene_template["character_presence_constraints"],
                scene_template["character_authority_labels"],
            ]
        ):
            normalized_context_snapshot["scene_template"] = scene_template

        return AuditEntry(
            timestamp=utc_timestamp(),
            session_owner=session_owner,
            session_number=session_number,
            round_number=round_number,
            turn_number=turn_number,
            bot_name=bot_name,
            bot_type=bot_type,
            input_messages=input_messages,
            raw_response=raw_response,
            parsed_output=parsed_output,
            context_snapshot=normalized_context_snapshot,
            metadata=metadata or {},
        )

    def update_narrative_summary(
        self,
        session_owner: str,
        session_number: int,
        round_number: int,
        turn_number: int,
        acting_character: str,
        rendered_output: str,
        character_move: dict[str, Any],
        director_decision: dict[str, Any],
        acting_role: str = "",
        presence_constraint: str = "",
        authority_label: str = "",
        scene_template_id: str | None = None,
        scene_premise: str = "",
        role_assignments: dict[str, str] | None = None,
        character_presence_constraints: dict[str, str] | None = None,
        character_authority_labels: dict[str, str] | None = None,
        continuity_event: dict[str, Any] | None = None,
        scene_state_after: dict[str, Any] | None = None,
        issue_updates: list[dict[str, Any]] | None = None,
        presence_changes: list[dict[str, Any]] | None = None,
    ) -> str:
        """Update or create the narrative summary file with this round's contribution.

        Args:
            session_owner: Character who owns the scene
            session_number: 3-digit session number
            round_number: Round number
            acting_character: Character who acted this round
            rendered_output: The final rendered prose from Narrator
            character_move: Character's structured move (action, dialogue, motivation)
            director_decision: Director's decision for this round
            acting_role: Optional acting role
            presence_constraint: Optional presence constraint
            authority_label: Optional authority label
            scene_template_id: Optional scene template ID
            scene_premise: Optional scene premise
            role_assignments: Optional role assignments
            character_presence_constraints: Optional character presence constraints
            character_authority_labels: Optional character authority labels

        Returns:
            Path to narrative file
        """
        session_path = self._get_session_path(session_owner, session_number)
        return update_narrative_summary_helper(
            session_path=session_path,
            session_owner=session_owner,
            session_number=session_number,
            round_number=round_number,
            turn_number=turn_number,
            acting_character=acting_character,
            rendered_output=rendered_output,
            character_move=character_move,
            director_decision=director_decision,
            acting_role=acting_role,
            presence_constraint=presence_constraint,
            authority_label=authority_label,
            scene_template_id=scene_template_id,
            scene_premise=scene_premise,
            role_assignments=role_assignments,
            character_presence_constraints=character_presence_constraints,
            character_authority_labels=character_authority_labels,
            continuity_event=continuity_event,
            scene_state_after=scene_state_after,
            issue_updates=issue_updates,
            presence_changes=presence_changes,
            normalize_scene_template_metadata=_normalize_scene_template_metadata,
            utc_timestamp=utc_timestamp,
        )

    def update_manifest_turn_counter(
        self,
        session_owner: str,
        session_number: int,
        total_turns: int,
    ) -> str:
        """Update the session manifest with the current total turn count.

        Args:
            session_owner: Character who owns the scene
            session_number: 3-digit session number
            total_turns: Current total number of turns logged

        Returns:
            Path to manifest file
        """
        session_path = self._get_session_path(session_owner, session_number)
        manifest_path = session_path / "_manifest.json"

        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        manifest["total_turns"] = total_turns
        manifest["last_updated"] = utc_timestamp()

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return str(manifest_path)

    def write_summary_report(
        self,
        session_owner: str,
        session_number: int,
    ) -> str:
        """Write a generated session-level audit summary report.

        The report is optimized for long-running scenes by summarizing session state,
        spotlight distribution, recent activity, and one compact entry per round.
        """
        session_path = self._get_session_path(session_owner, session_number)
        return write_summary_report_helper(
            session_path=session_path,
            session_owner=session_owner,
            session_number=session_number,
            normalize_scene_template_metadata=_normalize_scene_template_metadata,
            empty_issue_categories=_empty_issue_categories,
            empty_summary_block_visibility=_empty_summary_block_visibility,
            categorize_issue_text=_categorize_issue_text,
            record_issue_category=_record_issue_category,
            normalize_summary_block_metadata=_normalize_summary_block_metadata,
            prompt_reference=_prompt_reference,
            append_limited=_append_limited,
            utc_timestamp=utc_timestamp,
        )


# Global logger instance
_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _logger
    if _logger is None:
        _logger = AuditLogger()
    return _logger


def reset_audit_logger() -> None:
    """Reset the global audit logger (useful for testing)."""
    global _logger
    _logger = None
