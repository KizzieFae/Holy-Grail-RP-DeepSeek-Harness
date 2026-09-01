"""Durable user-visible RP history projection stored with authoritative sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from perceptual_visibility_legacy import perceptual_visibility_record_from_entry_metadata
from perceptual_visibility_projection import (
    assemble_perceptual_history_entry_for_viewer,
    build_perceptual_visibility_audit_metadata,
)

HistoryKind = Literal["user", "committed_turn", "presentation", "opening", "player_skip"]

PLAYER_SKIP_KIND = "player_skip"
PLAYER_SKIP_CONTENT = "Turn skipped"

PRESENTATION_SOURCE_NARRATOR = "narrator"
PRESENTATION_SOURCE_COMMITTED_FALLBACK = "committed_fallback"
PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC = "degraded_deterministic_fallback"

INFERENCE_OUTCOME_SUCCEEDED = "succeeded"
INFERENCE_OUTCOME_EMPTY_OUTPUT = "empty_output"
INFERENCE_OUTCOME_INFERENCE_ERROR = "inference_error"
INFERENCE_OUTCOME_OUTPUT_LIMIT = "output_limit"


@dataclass(frozen=True)
class RpHistoryEntry:
    entry_id: str
    sequence_index: int
    kind: HistoryKind
    content: str
    hg_round_id: str | None = None
    domain_commit_id: str | None = None
    actor_id: str | None = None
    presentation_status: str | None = None
    metadata: dict[str, Any] | None = None
    recorded_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "sequence_index": self.sequence_index,
            "kind": self.kind,
            "content": self.content,
            "hg_round_id": self.hg_round_id,
            "domain_commit_id": self.domain_commit_id,
            "actor_id": self.actor_id,
            "presentation_status": self.presentation_status,
            "metadata": dict(self.metadata or {}),
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RpHistoryEntry:
        return cls(
            entry_id=str(data["entry_id"]),
            sequence_index=int(data["sequence_index"]),
            kind=str(data["kind"]),  # type: ignore[arg-type]
            content=str(data.get("content", "")),
            hg_round_id=data.get("hg_round_id"),
            domain_commit_id=data.get("domain_commit_id"),
            actor_id=data.get("actor_id"),
            presentation_status=data.get("presentation_status"),
            metadata=dict(data.get("metadata") or {}),
            recorded_at=data.get("recorded_at"),
        )


IMMEDIATE_USER_TURN_SOURCE = "rp_history_substantive_user_entry"
_MAX_IMMEDIATE_USER_CONTENT = 300


def project_immediate_user_turn_context(
    history: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Bounded immediate substantive user turn for Narrator orchestration (#71).

    Uses the same skip-aware latest-user selection as Character/Director triggers.
    Non-authoritative current-turn context — not durable occurrence evidence.
    """
    entry = substantive_user_entry_for_trigger(history)
    if entry is None:
        return None
    entry_id = str(entry.get("entry_id", "") or "").strip()
    if not entry_id:
        return None
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    speaker = str(entry.get("actor_id") or metadata.get("speaker") or "Player").strip()
    raw_content = str(entry.get("content", "") or "").strip()
    if not raw_content:
        return None
    content = (
        raw_content
        if len(raw_content) <= _MAX_IMMEDIATE_USER_CONTENT
        else raw_content[: _MAX_IMMEDIATE_USER_CONTENT - 1] + "…"
    )
    payload: dict[str, Any] = {
        "entry_id": entry_id,
        "speaker": speaker,
        "content": content,
        "source": IMMEDIATE_USER_TURN_SOURCE,
    }
    seq = entry.get("sequence_index")
    if seq is not None:
        payload["sequence_index"] = int(seq)
    hg_round_id = entry.get("hg_round_id")
    if hg_round_id:
        payload["hg_round_id"] = str(hg_round_id)
    return payload


def substantive_user_entry_for_trigger(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest substantive user entry eligible for user_turn_trigger (skip-aware)."""
    entries = history_entries(history)
    latest_user: RpHistoryEntry | None = None
    latest_skip: RpHistoryEntry | None = None
    for entry in entries:
        if entry.kind == "user":
            latest_user = entry
        elif entry.kind == PLAYER_SKIP_KIND:
            latest_skip = entry
    if latest_user is None:
        return None
    if latest_skip is not None and latest_skip.sequence_index > latest_user.sequence_index:
        return None
    return latest_user.to_dict()


def summarize_committed_move(move: dict[str, Any]) -> str:
    beats = move.get("beats") if isinstance(move, dict) else None
    if not isinstance(beats, list):
        return "[committed action]"
    actions = [
        str(beat.get("action", "")).strip()
        for beat in beats
        if isinstance(beat, dict) and beat.get("type") == "action" and beat.get("action")
    ]
    return "; ".join(actions) if actions else "[committed action]"


def find_history_entry_by_id(
    history: list[dict[str, Any]], entry_id: str
) -> dict[str, Any] | None:
    for item in history:
        if str(item.get("entry_id", "")) == entry_id:
            return item
    return None


def append_history_entry(
    history: list[dict[str, Any]],
    *,
    kind: HistoryKind,
    content: str,
    entry_id: str | None = None,
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    actor_id: str | None = None,
    presentation_status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if entry_id:
        existing = find_history_entry_by_id(history, entry_id)
        if existing is not None:
            return existing
    entry = RpHistoryEntry(
        entry_id=entry_id or f"hg-hist-{uuid.uuid4()}",
        sequence_index=len(history),
        kind=kind,
        content=content,
        hg_round_id=hg_round_id,
        domain_commit_id=domain_commit_id,
        actor_id=actor_id,
        presentation_status=presentation_status,
        metadata=metadata,
        recorded_at=datetime.now(UTC).isoformat(),
    )
    payload = entry.to_dict()
    history.append(payload)
    return payload


def history_entries(history: list[dict[str, Any]]) -> list[RpHistoryEntry]:
    return [RpHistoryEntry.from_dict(item) for item in history]


def _presentation_metadata(entry: RpHistoryEntry) -> dict[str, Any]:
    return dict(entry.metadata or {})


def presentation_uses_narrator_prose_for_character(entry: RpHistoryEntry) -> bool:
    """Whether character-context projection should treat presentation content as narrator prose."""
    if entry.kind != "presentation":
        return False
    if entry.presentation_status == "failed":
        return False
    meta = _presentation_metadata(entry)
    source = meta.get("presentation_source")
    if source in (PRESENTATION_SOURCE_COMMITTED_FALLBACK, PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC):
        return False
    outcome = meta.get("inference_outcome")
    if outcome in (
        INFERENCE_OUTCOME_EMPTY_OUTPUT,
        INFERENCE_OUTCOME_INFERENCE_ERROR,
        INFERENCE_OUTCOME_OUTPUT_LIMIT,
    ):
        return False
    return True


def committed_observable_content_for_character(
    committed_entry: RpHistoryEntry,
    *,
    character_id: str,
    character_names: list[str],
    present_characters: list[str],
    get_character_display_name_fn: Any,
) -> str:
    """Perception-filtered observable line from durable committed-turn metadata."""
    meta = _presentation_metadata(committed_entry)
    speaker = str(committed_entry.actor_id or "Character")
    move = meta.get("structured_move")
    if isinstance(move, dict) and move.get("beats"):
        from character_move_adapters import is_canonical_v2_move
        from perception_audibility_formatting import format_observable_v2_turn_for_viewer
        from perception_audibility_normalize import normalize_move_audibility

        move_norm = normalize_move_audibility(dict(move), speaker, present_characters)
        if is_canonical_v2_move(move_norm):
            return format_observable_v2_turn_for_viewer(
                speaker_label=speaker,
                move_norm=move_norm,
                acting_character=speaker,
                viewer_character_name=character_id,
                present_characters=present_characters,
                get_character_display_name_fn=get_character_display_name_fn,
            )
    content = str(committed_entry.content or "").strip()
    if content:
        prefix = f"{speaker}: "
        return content if content.startswith(prefix) else f"{prefix}{content}"
    return f"{speaker}: [beat]"


def project_history_to_character_context_chat(
    history: list[dict[str, Any]],
    *,
    character_id: str,
    character_names: list[str],
    present_characters: list[str],
    get_character_display_name_fn: Any,
) -> list[dict[str, Any]]:
    """Build perception-oriented chat history for character manifest transcript projection."""
    entries = history_entries(history)
    committed_by_commit = {
        entry.domain_commit_id: entry
        for entry in entries
        if entry.kind == "committed_turn" and entry.domain_commit_id
    }
    chat: list[dict[str, Any]] = []

    for entry in entries:
        if entry.kind == "opening":
            assembly = assemble_perceptual_history_entry_for_viewer(
                entry.to_dict(),
                viewer_character=character_id,
                present_characters=present_characters,
                source_kind="opening",
            )
            record, _ = perceptual_visibility_record_from_entry_metadata(
                entry.metadata if isinstance(entry.metadata, dict) else {}
            )
            if assembly.content:
                chat.append(
                    {
                        "role": "assistant",
                        "content": assembly.content,
                        "speaker": "Narrator",
                        "perceptual_assembled": True,
                        "perceptual_visibility_projection": build_perceptual_visibility_audit_metadata(
                            assembly,
                            record=record,
                        ).get("perceptual_visibility_projection"),
                    }
                )
            continue

        if entry.kind == "user":
            chat.append(
                {
                    "role": "user",
                    "content": entry.content,
                    "speaker": entry.actor_id or entry.metadata.get("speaker", "Player"),
                }
            )
            continue

        if entry.kind == PLAYER_SKIP_KIND:
            continue

        if entry.kind == "presentation":
            commit_id = entry.domain_commit_id
            committed = committed_by_commit.get(commit_id) if commit_id else None
            structured_move = None
            acting_character = None
            if committed is not None:
                move = (committed.metadata or {}).get("structured_move")
                if isinstance(move, dict):
                    structured_move = move
                acting_character = str(committed.actor_id or "Character")

            if presentation_uses_narrator_prose_for_character(entry):
                assembly = assemble_perceptual_history_entry_for_viewer(
                    entry.to_dict(),
                    viewer_character=character_id,
                    present_characters=present_characters,
                    structured_move=structured_move,
                    acting_character=acting_character,
                    source_kind="narrator",
                )
                record, _ = perceptual_visibility_record_from_entry_metadata(
                    entry.metadata if isinstance(entry.metadata, dict) else {},
                    structured_move=structured_move,
                    acting_character=acting_character,
                )
                if assembly.content:
                    chat.append(
                        {
                            "role": "assistant",
                            "content": assembly.content,
                            "speaker": entry.actor_id or "Narrator",
                            "perceptual_assembled": True,
                            "move": structured_move if structured_move else None,
                            "actor": acting_character,
                            "perceptual_visibility_projection": build_perceptual_visibility_audit_metadata(
                                assembly,
                                record=record,
                            ).get("perceptual_visibility_projection"),
                        }
                    )
            elif committed is not None:
                chat.append(
                    {
                        "role": "assistant",
                        "content": committed_observable_content_for_character(
                            committed,
                            character_id=character_id,
                            character_names=character_names,
                            present_characters=present_characters,
                            get_character_display_name_fn=get_character_display_name_fn,
                        ),
                        "speaker": committed.actor_id or "Character",
                        "move": structured_move,
                        "actor": acting_character,
                    }
                )
            continue

        if entry.kind == "committed_turn":
            if entry.domain_commit_id:
                has_presentation = any(
                    e.kind == "presentation" and e.domain_commit_id == entry.domain_commit_id
                    for e in entries
                )
                if has_presentation:
                    continue
            chat.append(
                {
                    "role": "assistant",
                    "content": committed_observable_content_for_character(
                        entry,
                        character_id=character_id,
                        character_names=character_names,
                        present_characters=present_characters,
                        get_character_display_name_fn=get_character_display_name_fn,
                    ),
                    "speaker": entry.actor_id or "Character",
                    "move": (entry.metadata or {}).get("structured_move"),
                    "actor": entry.actor_id,
                }
            )

    return chat


def project_history_to_transcript(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build user-facing transcript from durable history entries."""
    entries = history_entries(history)
    presentations_by_commit = {
        entry.domain_commit_id: entry
        for entry in entries
        if entry.kind == "presentation" and entry.domain_commit_id
    }
    transcript: list[dict[str, Any]] = []

    for entry in entries:
        if entry.kind == "opening":
            transcript.append(
                {
                    "role": "assistant",
                    "content": entry.content,
                    "speaker": "Narrator",
                    "entry_id": entry.entry_id,
                    "sequence_index": entry.sequence_index,
                    "opening": True,
                }
            )
            continue

        if entry.kind == "user":
            transcript.append(
                {
                    "role": "user",
                    "content": entry.content,
                    "speaker": entry.actor_id or entry.metadata.get("speaker", "Player"),
                    "entry_id": entry.entry_id,
                    "sequence_index": entry.sequence_index,
                }
            )
            continue

        if entry.kind == PLAYER_SKIP_KIND:
            transcript.append(
                {
                    "role": "assistant",
                    "content": entry.content,
                    "speaker": entry.actor_id or entry.metadata.get("speaker", "Player"),
                    "entry_id": entry.entry_id,
                    "sequence_index": entry.sequence_index,
                    "player_skip": True,
                }
            )
            continue

        if entry.kind == "presentation":
            transcript.append(
                {
                    "role": "assistant",
                    "content": entry.content,
                    "speaker": entry.actor_id or "Narrator",
                    "entry_id": entry.entry_id,
                    "sequence_index": entry.sequence_index,
                    "domain_commit_id": entry.domain_commit_id,
                    "presentation_failed": entry.presentation_status == "failed",
                }
            )
            continue

        if entry.kind == "committed_turn":
            if entry.domain_commit_id and entry.domain_commit_id in presentations_by_commit:
                continue
            transcript.append(
                {
                    "role": "assistant",
                    "content": entry.content,
                    "speaker": entry.actor_id or "Character",
                    "entry_id": entry.entry_id,
                    "sequence_index": entry.sequence_index,
                    "domain_commit_id": entry.domain_commit_id,
                    "presentation_failed": True,
                }
            )

    return transcript
