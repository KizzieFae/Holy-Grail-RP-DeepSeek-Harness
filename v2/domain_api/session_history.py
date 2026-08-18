"""Durable user-visible RP history projection stored with authoritative sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

HistoryKind = Literal["user", "committed_turn", "presentation", "opening"]


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


def append_history_entry(
    history: list[dict[str, Any]],
    *,
    kind: HistoryKind,
    content: str,
    hg_round_id: str | None = None,
    domain_commit_id: str | None = None,
    actor_id: str | None = None,
    presentation_status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = RpHistoryEntry(
        entry_id=f"hg-hist-{uuid.uuid4()}",
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
