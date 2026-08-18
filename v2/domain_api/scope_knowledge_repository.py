"""File-backed durable scope knowledge (learned world facts + user profile)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEARNED_WORLD_KNOWLEDGE = "learned_world_knowledge"
USER_PROFILE = "user_profile"
DEFAULT_LEARNED_WORLD_LIMIT = 8
DEFAULT_USER_PROFILE_LIMIT = 6


@dataclass
class ScopeKnowledgeRecord:
    knowledge_id: str
    scope_id: str
    knowledge_kind: str
    content: str
    authority_class: str = "suggestive"
    visibility: str = "scope_global"
    subject_character_file_id: str | None = None
    source_kind: str = ""
    source_session_id: str = ""
    source_domain_commit_id: str | None = None
    source_continuity_anchor_id: str | None = None
    profile_key: str | None = None
    user_persona_id: str | None = None
    created_at: str = ""
    supersedes_knowledge_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScopeKnowledgeRecord:
        return cls(
            knowledge_id=str(data["knowledge_id"]),
            scope_id=str(data["scope_id"]),
            knowledge_kind=str(data["knowledge_kind"]),
            content=str(data["content"]),
            authority_class=str(data.get("authority_class", "suggestive")),
            visibility=str(data.get("visibility", "scope_global")),
            subject_character_file_id=data.get("subject_character_file_id"),
            source_kind=str(data.get("source_kind", "")),
            source_session_id=str(data.get("source_session_id", "")),
            source_domain_commit_id=data.get("source_domain_commit_id"),
            source_continuity_anchor_id=data.get("source_continuity_anchor_id"),
            profile_key=data.get("profile_key"),
            user_persona_id=data.get("user_persona_id"),
            created_at=str(data.get("created_at", "")),
            supersedes_knowledge_id=data.get("supersedes_knowledge_id"),
            provenance=dict(data.get("provenance") or {}),
        )


class ScopeKnowledgeRepository:
    """Deterministic JSON file store: one file per scope_id."""

    def __init__(self, store_dir: str | Path) -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _scope_file(self, scope_id: str) -> Path:
        safe = scope_id.replace("/", "_").replace("\\", "_")
        return self.store_dir / f"{safe}.json"

    def _load_scope(self, scope_id: str) -> dict[str, Any]:
        path = self._scope_file(scope_id)
        if not path.exists():
            return {"scope_id": scope_id, "records": []}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"invalid scope knowledge store for {scope_id}")
        data.setdefault("records", [])
        return data

    def _save_scope(self, payload: dict[str, Any]) -> None:
        scope_id = str(payload["scope_id"])
        path = self._scope_file(scope_id)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def append_records(self, records: list[ScopeKnowledgeRecord]) -> int:
        if not records:
            return 0
        scope_id = records[0].scope_id
        payload = self._load_scope(scope_id)
        added = 0
        records_payload = [
            item for item in payload.get("records", []) if isinstance(item, dict)
        ]
        index_by_id = {
            str(item.get("knowledge_id", "")): idx
            for idx, item in enumerate(records_payload)
            if str(item.get("knowledge_id", ""))
        }
        for record in records:
            if record.knowledge_id in index_by_id:
                records_payload[index_by_id[record.knowledge_id]] = record.to_dict()
                continue
            records_payload.append(record.to_dict())
            index_by_id[record.knowledge_id] = len(records_payload) - 1
            added += 1
        if added or records:
            payload["records"] = records_payload
            self._save_scope(payload)
        return added

    def upsert_user_profile(self, record: ScopeKnowledgeRecord) -> str:
        payload = self._load_scope(record.scope_id)
        records = [
            item
            for item in payload.get("records", [])
            if isinstance(item, dict)
            and not (
                item.get("knowledge_kind") == USER_PROFILE
                and item.get("profile_key") == record.profile_key
                and item.get("user_persona_id") == record.user_persona_id
            )
        ]
        prior = next(
            (
                str(item.get("knowledge_id", ""))
                for item in payload.get("records", [])
                if isinstance(item, dict)
                and item.get("knowledge_kind") == USER_PROFILE
                and item.get("profile_key") == record.profile_key
                and item.get("user_persona_id") == record.user_persona_id
            ),
            None,
        )
        new_record = ScopeKnowledgeRecord(
            **{
                **record.to_dict(),
                "supersedes_knowledge_id": prior,
            }
        )
        records.append(new_record.to_dict())
        payload["records"] = records
        self._save_scope(payload)
        return new_record.knowledge_id

    def list_records(
        self,
        scope_id: str,
        *,
        knowledge_kinds: set[str] | None = None,
        limit: int = DEFAULT_LEARNED_WORLD_LIMIT,
    ) -> list[ScopeKnowledgeRecord]:
        payload = self._load_scope(scope_id)
        records: list[ScopeKnowledgeRecord] = []
        for item in payload.get("records", []):
            if not isinstance(item, dict):
                continue
            record = ScopeKnowledgeRecord.from_dict(item)
            if knowledge_kinds and record.knowledge_kind not in knowledge_kinds:
                continue
            records.append(record)
        records.sort(key=lambda item: item.created_at)
        return records[-limit:]

    @staticmethod
    def make_knowledge_id(*, parts: list[str]) -> str:
        fingerprint = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
        return f"hg-know-{fingerprint}"

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()
