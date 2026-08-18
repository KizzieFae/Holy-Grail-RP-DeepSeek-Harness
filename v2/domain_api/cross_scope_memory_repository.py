"""File-backed cross-session memory records scoped by memory_scope_id."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CROSS_SCOPE_USER_RELATIONSHIP = "cross_scope_user_relationship"
DEFAULT_CROSS_SCOPE_LIMIT = 8


@dataclass
class CrossScopeMemoryRecord:
    memory_id: str
    memory_scope_id: str
    subject_character_file_id: str
    subject_display_name: str
    memory_kind: str
    content: str
    authority_class: str = "derived"
    source_session_id: str = ""
    source_domain_commit_id: str | None = None
    source_hg_round_id: str | None = None
    user_persona_id: str | None = None
    created_at: str = ""
    supersedes_memory_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrossScopeMemoryRecord:
        return cls(
            memory_id=str(data["memory_id"]),
            memory_scope_id=str(data["memory_scope_id"]),
            subject_character_file_id=str(data["subject_character_file_id"]),
            subject_display_name=str(data.get("subject_display_name", "")),
            memory_kind=str(data["memory_kind"]),
            content=str(data["content"]),
            authority_class=str(data.get("authority_class", "derived")),
            source_session_id=str(data.get("source_session_id", "")),
            source_domain_commit_id=data.get("source_domain_commit_id"),
            source_hg_round_id=data.get("source_hg_round_id"),
            user_persona_id=data.get("user_persona_id"),
            created_at=str(data.get("created_at", "")),
            supersedes_memory_id=data.get("supersedes_memory_id"),
            provenance=dict(data.get("provenance") or {}),
        )


class CrossScopeMemoryRepository:
    """Deterministic JSON file store: one file per memory_scope_id."""

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _scope_file(self, memory_scope_id: str) -> Path:
        safe = memory_scope_id.replace("/", "_").replace("\\", "_")
        return self.store_dir / f"{safe}.json"

    def _load_scope(self, memory_scope_id: str) -> dict[str, Any]:
        path = self._scope_file(memory_scope_id)
        if not path.exists():
            return {"memory_scope_id": memory_scope_id, "records": []}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"invalid cross-scope store for {memory_scope_id}")
        data.setdefault("records", [])
        return data

    def _save_scope(self, payload: dict[str, Any]) -> None:
        scope_id = str(payload["memory_scope_id"])
        path = self._scope_file(scope_id)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def append_records(self, records: list[CrossScopeMemoryRecord]) -> int:
        if not records:
            return 0
        scope_id = records[0].memory_scope_id
        payload = self._load_scope(scope_id)
        existing_ids = {
            str(item.get("memory_id", ""))
            for item in payload.get("records", [])
            if isinstance(item, dict)
        }
        added = 0
        for record in records:
            if record.memory_id in existing_ids:
                continue
            payload["records"].append(record.to_dict())
            existing_ids.add(record.memory_id)
            added += 1
        if added:
            self._save_scope(payload)
        return added

    def list_records(
        self,
        memory_scope_id: str,
        *,
        subject_character_file_id: str,
        memory_kinds: set[str] | None = None,
        limit: int = DEFAULT_CROSS_SCOPE_LIMIT,
    ) -> list[CrossScopeMemoryRecord]:
        payload = self._load_scope(memory_scope_id)
        records: list[CrossScopeMemoryRecord] = []
        for item in payload.get("records", []):
            if not isinstance(item, dict):
                continue
            record = CrossScopeMemoryRecord.from_dict(item)
            if record.subject_character_file_id != subject_character_file_id:
                continue
            if memory_kinds and record.memory_kind not in memory_kinds:
                continue
            records.append(record)
        records.sort(key=lambda item: item.created_at)
        return records[-limit:]

    def list_scope_ids(self) -> list[str]:
        ids: list[str] = []
        for path in sorted(self.store_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and data.get("memory_scope_id"):
                ids.append(str(data["memory_scope_id"]))
        return ids

    @staticmethod
    def make_memory_id(
        *,
        memory_scope_id: str,
        subject_character_file_id: str,
        memory_kind: str,
        source_session_id: str,
        content: str,
        user_persona_id: str | None = None,
    ) -> str:
        import hashlib

        fingerprint = hashlib.sha256(
            "|".join(
                [
                    memory_scope_id,
                    subject_character_file_id,
                    memory_kind,
                    source_session_id,
                    user_persona_id or "",
                    content.strip(),
                ]
            ).encode("utf-8")
        ).hexdigest()[:24]
        return f"hg-mem-{fingerprint}"

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()
