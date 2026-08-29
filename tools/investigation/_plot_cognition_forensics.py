"""Shared helpers for Plot Cognition Forensic Chronicle investigation (#64)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _repo_paths import EXECUTION_EVIDENCE_DIR, PLOT_COGNITION_FORENSICS_DIR


@dataclass(frozen=True)
class PlotCognitionScope:
    plot_cognition_scope_id: str
    root: Path

    def manifest(self) -> dict[str, Any] | None:
        path = self.root / "scope_manifest.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def index(self) -> dict[str, Any]:
        path = self.root / "index.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_record(self, record_id: str) -> dict[str, Any] | None:
        path = self.root / "records" / f"{record_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_content(self, artifact_id: str) -> dict[str, Any] | None:
        path = self.root / "content" / f"{artifact_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("content") if isinstance(data, dict) else None

    def timeline(self) -> list[dict[str, Any]]:
        index = self.index()
        records: list[dict[str, Any]] = []
        for record_id in index.get("record_ids") or []:
            record = self.load_record(str(record_id))
            if record:
                records.append(record)
        records.sort(key=lambda item: int(item.get("recorded_at_ms") or 0))
        return records


def resolve_scope(
    plot_cognition_scope_id: str,
    *,
    forensics_root: Path | None = None,
) -> PlotCognitionScope | None:
    root = (forensics_root or PLOT_COGNITION_FORENSICS_DIR) / plot_cognition_scope_id.replace("/", "_").replace("\\", "_")
    if not root.exists():
        return None
    return PlotCognitionScope(plot_cognition_scope_id=plot_cognition_scope_id, root=root)


def load_execution_evidence(hg_session_id: str, evidence_id: str, *, evidence_root: Path | None = None) -> dict[str, Any] | None:
    root = evidence_root or EXECUTION_EVIDENCE_DIR
    path = root / hg_session_id / "attempts" / f"{evidence_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def format_timeline(scope: PlotCognitionScope) -> str:
    lines: list[str] = []
    manifest = scope.manifest() or {}
    lines.append(f"Scope: {scope.plot_cognition_scope_id}")
    lines.append(f"Activated: {manifest.get('activated', False)}")
    if manifest.get("integrity_status"):
        lines.append(f"Manifest integrity: {manifest['integrity_status']}")
    sessions = manifest.get("attached_sessions") or []
    if sessions:
        lines.append(f"Attached sessions: {', '.join(str(item) for item in sessions)}")
    lines.append("")
    for record in scope.timeline():
        correlation = record.get("correlation") or {}
        lines.append(
            f"[{record.get('recorded_at_ms')}] "
            f"{record.get('record_class')}/{record.get('operation_kind')}"
            f" phase={record.get('mutation_phase') or '-'} "
            f"integrity={record.get('integrity_status')}"
        )
        if correlation:
            keys = (
                "hg_session_id",
                "hg_round_id",
                "domain_commit_id",
                "character_id",
                "batch_id",
                "overlay_revision_before",
                "overlay_revision_after",
            )
            parts = [f"{key}={correlation[key]}" for key in keys if correlation.get(key) is not None]
            if parts:
                lines.append(f"  correlation: {', '.join(parts)}")
        refs = record.get("inference_evidence_refs") or []
        if refs:
            lines.append(f"  inference evidence: {refs}")
        if record.get("integrity_status") not in {None, "complete"}:
            payload = record.get("payload") or {}
            note = payload.get("statement") or payload.get("note") or payload.get("error")
            if note:
                lines.append(f"  note: {note}")
    if not scope.timeline():
        lines.append("(no forensic records)")
    return "\n".join(lines)


def format_commit_effects(scope: PlotCognitionScope, domain_commit_id: str) -> str:
    index = scope.index()
    record_ids = (index.get("by_commit") or {}).get(domain_commit_id) or []
    lines = [f"Commit {domain_commit_id}:"]
    if not record_ids:
        lines.append("  (no chronicle records indexed for this commit)")
        return "\n".join(lines)
    for record_id in record_ids:
        record = scope.load_record(str(record_id))
        if not record:
            lines.append(f"  {record_id}: MISSING RECORD")
            continue
        lines.append(
            f"  {record_id}: {record.get('record_class')}/{record.get('operation_kind')} "
            f"integrity={record.get('integrity_status')}"
        )
    return "\n".join(lines)


def format_integrity_gaps(scope: PlotCognitionScope) -> str:
    lines = ["Integrity / gap records:"]
    found = False
    for record in scope.timeline():
        if record.get("record_class") != "integrity":
            continue
        if record.get("integrity_status") in {None, "complete"}:
            continue
        found = True
        lines.append(
            f"  [{record.get('record_id')}] {record.get('operation_kind')}: "
            f"{record.get('integrity_status')}"
        )
        payload = record.get("payload") or {}
        for key in ("idempotency_key", "intent_record_id", "error", "note", "statement"):
            if payload.get(key):
                lines.append(f"    {key}: {payload[key]}")
    if not found:
        lines.append("  (none)")
    return "\n".join(lines)


def format_layer_b_chain(
    scope: PlotCognitionScope,
    *,
    batch_id: str,
    hg_session_id: str | None = None,
    evidence_root: Path | None = None,
) -> str:
    lines = [f"Layer B chain for batch {batch_id}:"]
    matching = [
        record
        for record in scope.timeline()
        if (record.get("correlation") or {}).get("batch_id") == batch_id
    ]
    if not matching:
        lines.append("  (no chronicle projection records for batch)")
        return "\n".join(lines)
    for record in matching:
        lines.append(
            f"  Chronicle: {record.get('record_id')} "
            f"{record.get('operation_kind')} integrity={record.get('integrity_status')}"
        )
        payload = record.get("payload") or {}
        if payload.get("character_id"):
            lines.append(f"    character_id: {payload['character_id']}")
        for ref in record.get("inference_evidence_refs") or []:
            evidence_id = ref.get("evidence_id")
            if not evidence_id or not hg_session_id:
                lines.append(f"    evidence ref: {ref} (session required to load)")
                continue
            attempt = load_execution_evidence(hg_session_id, str(evidence_id), evidence_root=evidence_root)
            if attempt is None:
                lines.append(f"    evidence {evidence_id}: MISSING")
            else:
                kind = (attempt.get("correlation") or {}).get("inference_kind")
                lines.append(f"    evidence {evidence_id}: inference_kind={kind}")
    return "\n".join(lines)
