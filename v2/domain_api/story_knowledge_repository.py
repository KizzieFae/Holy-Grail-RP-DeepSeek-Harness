"""Append-oriented JSONL story-knowledge store per memory_scope_id (#50)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .story_knowledge_contract import STORY_KNOWLEDGE_SCHEMA_VERSION, StoryKnowledgeRecord


@dataclass
class StoryKnowledgeManifest:
    schema_version: int = STORY_KNOWLEDGE_SCHEMA_VERSION
    memory_scope_id: str = ""
    record_count: int = 0
    record_index: dict[str, int] = field(default_factory=dict)
    last_valid_offset: int = 0
    index_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "memory_scope_id": self.memory_scope_id,
            "record_count": self.record_count,
            "record_index": dict(self.record_index),
            "last_valid_offset": self.last_valid_offset,
            "index_state": dict(self.index_state),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryKnowledgeManifest:
        return cls(
            schema_version=int(data.get("schema_version", STORY_KNOWLEDGE_SCHEMA_VERSION)),
            memory_scope_id=str(data.get("memory_scope_id", "")),
            record_count=int(data.get("record_count", 0)),
            record_index={str(k): int(v) for k, v in dict(data.get("record_index") or {}).items()},
            last_valid_offset=int(data.get("last_valid_offset", 0)),
            index_state=dict(data.get("index_state") or {}),
        )


class StoryKnowledgeRepository:
    """Durable story-knowledge corpus — authoritative evidence, not Continuity truth."""

    def __init__(self, store_root: str | Path) -> None:
        self.store_root = Path(store_root)
        self.store_root.mkdir(parents=True, exist_ok=True)

    def _scope_dir(self, memory_scope_id: str) -> Path:
        safe = memory_scope_id.replace("/", "_").replace("\\", "_")
        path = self.store_root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def records_path(self, memory_scope_id: str) -> Path:
        return self._scope_dir(memory_scope_id) / "records.jsonl"

    def manifest_path(self, memory_scope_id: str) -> Path:
        return self._scope_dir(memory_scope_id) / "manifest.json"

    def semantic_index_path(self, memory_scope_id: str) -> Path:
        return self._scope_dir(memory_scope_id) / "semantic_index_v1.json"

    def load_manifest(self, memory_scope_id: str) -> StoryKnowledgeManifest:
        path = self.manifest_path(memory_scope_id)
        if not path.exists():
            return StoryKnowledgeManifest(memory_scope_id=memory_scope_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = StoryKnowledgeManifest.from_dict(data)
        manifest.memory_scope_id = memory_scope_id
        return manifest

    def save_manifest(self, manifest: StoryKnowledgeManifest) -> None:
        path = self.manifest_path(manifest.memory_scope_id)
        path.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def append_record(self, record: StoryKnowledgeRecord) -> bool:
        record_id = record.record_id
        if not record_id:
            raise ValueError("story knowledge record requires event_id or story_record_id")

        scope_id = record.memory_scope_id
        manifest = self.load_manifest(scope_id)
        if record_id in manifest.record_index:
            return False

        record.content_hash = record.compute_content_hash()
        if not record.written_at:
            record.written_at = datetime.now(UTC).isoformat()

        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        records_path = self.records_path(scope_id)
        offset = records_path.stat().st_size if records_path.exists() else 0
        with open(records_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

        manifest.record_index[record_id] = offset
        manifest.record_count = len(manifest.record_index)
        manifest.last_valid_offset = records_path.stat().st_size
        self.save_manifest(manifest)
        return True

    def get_record(self, memory_scope_id: str, record_id: str) -> StoryKnowledgeRecord | None:
        manifest = self.load_manifest(memory_scope_id)
        offset = manifest.record_index.get(record_id)
        if offset is None:
            return None
        return self._read_record_at_offset(memory_scope_id, offset)

    def list_record_ids(self, memory_scope_id: str) -> list[str]:
        manifest = self.load_manifest(memory_scope_id)
        return list(manifest.record_index.keys())

    def list_records(self, memory_scope_id: str) -> list[StoryKnowledgeRecord]:
        manifest = self.load_manifest(memory_scope_id)
        records: list[StoryKnowledgeRecord] = []
        for record_id in sorted(manifest.record_index, key=lambda rid: manifest.record_index[rid]):
            record = self.get_record(memory_scope_id, record_id)
            if record is not None:
                records.append(record)
        return records

    def _read_record_at_offset(self, memory_scope_id: str, offset: int) -> StoryKnowledgeRecord | None:
        path = self.records_path(memory_scope_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            handle.seek(offset)
            line = handle.readline()
        if not line.strip():
            return None
        try:
            return StoryKnowledgeRecord.from_dict(json.loads(line))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def recover_truncated_tail(self, memory_scope_id: str) -> int:
        path = self.records_path(memory_scope_id)
        if not path.exists():
            return 0
        manifest = StoryKnowledgeManifest(memory_scope_id=memory_scope_id)
        offset = 0
        with open(path, "rb") as handle:
            while True:
                start = handle.tell()
                line = handle.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8"))
                    record = StoryKnowledgeRecord.from_dict(data)
                    record_id = record.record_id
                    if record_id:
                        manifest.record_index[record_id] = start
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError):
                    break
                offset = handle.tell()
        manifest.record_count = len(manifest.record_index)
        manifest.last_valid_offset = offset
        self.save_manifest(manifest)
        if offset < path.stat().st_size:
            with open(path, "r+b") as handle:
                handle.truncate(offset)
        return manifest.record_count
