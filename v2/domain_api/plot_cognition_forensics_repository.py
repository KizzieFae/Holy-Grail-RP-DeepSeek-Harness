"""File-backed Plot Cognition Forensic Chronicle persistence (#64)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .plot_cognition_forensics_contract import (
    FORENSIC_CONTENT_SCHEMA,
    FORENSIC_INDEX_SCHEMA,
    FORENSIC_SCOPE_MANIFEST_SCHEMA,
    content_artifact_id,
    new_record_id,
)


class ForensicsPersistenceError(RuntimeError):
    """Raised when forensic evidence cannot be durably persisted."""


class PlotCognitionForensicsRepository:
    """Scope-keyed append-only forensic chronicle under HG_DATA_DIR."""

    def __init__(self, store_root: str | Path) -> None:
        self.store_root = Path(store_root)
        self.store_root.mkdir(parents=True, exist_ok=True)

    def _safe_scope(self, plot_cognition_scope_id: str) -> str:
        return plot_cognition_scope_id.replace("/", "_").replace("\\", "_")

    def scope_dir(self, plot_cognition_scope_id: str) -> Path:
        return self.store_root / self._safe_scope(plot_cognition_scope_id)

    def records_dir(self, plot_cognition_scope_id: str) -> Path:
        return self.scope_dir(plot_cognition_scope_id) / "records"

    def content_dir(self, plot_cognition_scope_id: str) -> Path:
        return self.scope_dir(plot_cognition_scope_id) / "content"

    def manifest_path(self, plot_cognition_scope_id: str) -> Path:
        return self.scope_dir(plot_cognition_scope_id) / "scope_manifest.json"

    def index_path(self, plot_cognition_scope_id: str) -> Path:
        return self.scope_dir(plot_cognition_scope_id) / "index.json"

    def _write_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
        try:
            temp_path.write_text(encoded, encoding="utf-8")
            temp_path.replace(path)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise ForensicsPersistenceError(str(exc)) from exc

    def load_manifest(self, plot_cognition_scope_id: str) -> dict[str, Any] | None:
        path = self.manifest_path(plot_cognition_scope_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_manifest(self, plot_cognition_scope_id: str, manifest: dict[str, Any]) -> None:
        manifest = dict(manifest)
        manifest["schema"] = FORENSIC_SCOPE_MANIFEST_SCHEMA
        manifest["plot_cognition_scope_id"] = plot_cognition_scope_id
        self._write_atomic(self.manifest_path(plot_cognition_scope_id), manifest)

    def attach_session(self, plot_cognition_scope_id: str, hg_session_id: str) -> None:
        manifest = self.load_manifest(plot_cognition_scope_id) or {
            "plot_cognition_scope_id": plot_cognition_scope_id,
            "attached_sessions": [],
            "integrity_status": "complete",
            "activated": False,
        }
        sessions = list(manifest.get("attached_sessions") or [])
        if hg_session_id and hg_session_id not in sessions:
            sessions.append(hg_session_id)
        manifest["attached_sessions"] = sessions
        manifest["updated_at_ms"] = int(time.time() * 1000)
        self.save_manifest(plot_cognition_scope_id, manifest)

    def store_content(self, plot_cognition_scope_id: str, content: dict[str, Any]) -> str:
        artifact_id = content_artifact_id(content)
        path = self.content_dir(plot_cognition_scope_id) / f"{artifact_id}.json"
        if path.exists():
            return artifact_id
        payload = {
            "schema": FORENSIC_CONTENT_SCHEMA,
            "artifact_id": artifact_id,
            "content": content,
            "stored_at_ms": int(time.time() * 1000),
        }
        self._write_atomic(path, payload)
        return artifact_id

    def load_content(self, plot_cognition_scope_id: str, artifact_id: str) -> dict[str, Any] | None:
        path = self.content_dir(plot_cognition_scope_id) / f"{artifact_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("content") if isinstance(data, dict) else None

    def append_record(self, record: dict[str, Any]) -> str:
        scope_id = str(record.get("plot_cognition_scope_id", "")).strip()
        if not scope_id:
            raise ForensicsPersistenceError("plot_cognition_scope_id required")
        record_id = str(record.get("record_id") or new_record_id())
        record = dict(record)
        record["record_id"] = record_id
        record.setdefault("recorded_at_ms", int(time.time() * 1000))
        path = self.records_dir(scope_id) / f"{record_id}.json"
        if path.exists():
            return record_id
        self._write_atomic(path, record)
        self._index_record(scope_id, record)
        return record_id

    def load_record(self, plot_cognition_scope_id: str, record_id: str) -> dict[str, Any] | None:
        path = self.records_dir(plot_cognition_scope_id) / f"{record_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def has_mutation_phase(self, plot_cognition_scope_id: str, idempotency_key: str, phase: str) -> bool:
        index = self.load_index(plot_cognition_scope_id)
        entry = (index.get("by_idempotency_key") or {}).get(idempotency_key) or {}
        return phase in entry

    def load_index(self, plot_cognition_scope_id: str) -> dict[str, Any]:
        path = self.index_path(plot_cognition_scope_id)
        if not path.exists():
            return self._empty_index(plot_cognition_scope_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _empty_index(self, plot_cognition_scope_id: str) -> dict[str, Any]:
        return {
            "schema": FORENSIC_INDEX_SCHEMA,
            "plot_cognition_scope_id": plot_cognition_scope_id,
            "record_ids": [],
            "by_idempotency_key": {},
            "by_session": {},
            "by_commit": {},
            "by_cognition_item": {},
            "by_candidate": {},
            "by_inference_evidence": {},
            "updated_at_ms": int(time.time() * 1000),
        }

    def _index_record(self, scope_id: str, record: dict[str, Any]) -> None:
        index = self.load_index(scope_id)
        record_id = str(record["record_id"])
        if record_id not in index["record_ids"]:
            index["record_ids"].append(record_id)

        idem = record.get("idempotency_key")
        mutation_phase = record.get("mutation_phase")
        if idem:
            bucket = dict(index["by_idempotency_key"].get(idem) or {})
            if mutation_phase:
                bucket[str(mutation_phase)] = record_id
            else:
                bucket["record"] = record_id
            index["by_idempotency_key"][str(idem)] = bucket

        correlation = record.get("correlation") or {}
        session_id = correlation.get("hg_session_id")
        if session_id:
            sessions = list(index["by_session"].get(session_id) or [])
            if record_id not in sessions:
                sessions.append(record_id)
            index["by_session"][str(session_id)] = sessions

        commit_id = correlation.get("domain_commit_id")
        if commit_id:
            commits = list(index["by_commit"].get(commit_id) or [])
            if record_id not in commits:
                commits.append(record_id)
            index["by_commit"][str(commit_id)] = commits

        item_id = correlation.get("cognition_item_id")
        if item_id:
            items = list(index["by_cognition_item"].get(item_id) or [])
            if record_id not in items:
                items.append(record_id)
            index["by_cognition_item"][str(item_id)] = items

        candidate_id = correlation.get("candidate_id")
        if candidate_id:
            candidates = list(index["by_candidate"].get(candidate_id) or [])
            if record_id not in candidates:
                candidates.append(record_id)
            index["by_candidate"][str(candidate_id)] = candidates

        for ref in record.get("inference_evidence_refs") or []:
            evidence_id = ref.get("evidence_id")
            if not evidence_id:
                continue
            refs = list(index["by_inference_evidence"].get(evidence_id) or [])
            if record_id not in refs:
                refs.append(record_id)
            index["by_inference_evidence"][str(evidence_id)] = refs

        index["updated_at_ms"] = int(time.time() * 1000)
        self._write_atomic(self.index_path(scope_id), index)

    def list_record_ids(self, plot_cognition_scope_id: str) -> list[str]:
        records_dir = self.records_dir(plot_cognition_scope_id)
        if not records_dir.exists():
            return []
        return sorted(path.stem for path in records_dir.glob("*.json"))

    def rebuild_index(self, plot_cognition_scope_id: str) -> dict[str, Any]:
        index = self._empty_index(plot_cognition_scope_id)
        self._write_atomic(self.index_path(plot_cognition_scope_id), index)
        for record_id in self.list_record_ids(plot_cognition_scope_id):
            record = self.load_record(plot_cognition_scope_id, record_id)
            if record:
                self._index_record(plot_cognition_scope_id, record)
        return self.load_index(plot_cognition_scope_id)
