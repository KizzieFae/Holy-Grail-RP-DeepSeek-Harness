"""File-backed Plot Cognition Overlay sidecar persistence (#59)."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .plot_cognition_overlay_store import (
    PLOT_COGNITION_OVERLAY_STORE_SCHEMA,
    PlotCognitionOverlayStore,
)


class PersistenceError(RuntimeError):
    """Raised when overlay state cannot be durably persisted."""


class RevisionConflictError(RuntimeError):
    """Raised when an optimistic revision check fails."""


@dataclass(frozen=True)
class RawLoadResult:
    status: str
    payload: dict[str, Any] | None
    quarantine_path: str | None = None
    diagnostics: tuple[str, ...] = ()


class PlotCognitionOverlayRepository:
    """Sidecar current-state store keyed by plot_cognition_scope_id."""

    def __init__(self, store_root: str | Path) -> None:
        self.store_root = Path(store_root)
        self.store_root.mkdir(parents=True, exist_ok=True)

    def _scope_path(self, plot_cognition_scope_id: str) -> Path:
        safe = plot_cognition_scope_id.replace("/", "_").replace("\\", "_")
        return self.store_root / f"{safe}.json"

    def _blocked_marker_path(self, plot_cognition_scope_id: str) -> Path:
        safe = plot_cognition_scope_id.replace("/", "_").replace("\\", "_")
        return self.store_root / f"{safe}.blocked.json"

    def _read_blocked_marker(self, plot_cognition_scope_id: str) -> RawLoadResult | None:
        marker_path = self._blocked_marker_path(plot_cognition_scope_id)
        if not marker_path.exists():
            return None
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return RawLoadResult(
                status="corrupt",
                payload=None,
                quarantine_path=None,
                diagnostics=("blocked_marker_unreadable",),
            )
        if not isinstance(payload, dict):
            return RawLoadResult(
                status="corrupt",
                payload=None,
                diagnostics=("blocked_marker_not_object",),
            )
        status = str(payload.get("load_status") or "corrupt")
        quarantine_path = payload.get("quarantine_path")
        return RawLoadResult(
            status=status,
            payload=None,
            quarantine_path=str(quarantine_path) if quarantine_path else None,
            diagnostics=(f"blocked:{payload.get('reason', status)}",),
        )

    def _write_blocked_marker(
        self,
        plot_cognition_scope_id: str,
        *,
        load_status: str,
        quarantine_path: Path | None,
        reason: str,
    ) -> None:
        marker_path = self._blocked_marker_path(plot_cognition_scope_id)
        payload = {
            "load_status": load_status,
            "quarantine_path": str(quarantine_path) if quarantine_path else None,
            "reason": reason,
            "blocked_at_ms": int(time.time() * 1000),
        }
        marker_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def store_path(self, plot_cognition_scope_id: str) -> Path:
        return self._scope_path(plot_cognition_scope_id)

    def load_raw(self, plot_cognition_scope_id: str) -> RawLoadResult:
        blocked = self._read_blocked_marker(plot_cognition_scope_id)
        if blocked is not None:
            return blocked

        path = self._scope_path(plot_cognition_scope_id)
        if not path.exists():
            return RawLoadResult(status="absent", payload=None)

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            quarantine = self.quarantine_corrupt(plot_cognition_scope_id, raw_text=b"")
            return RawLoadResult(
                status="corrupt",
                payload=None,
                quarantine_path=str(quarantine),
                diagnostics=(f"read_failed:{exc}",),
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            quarantine = self.quarantine_corrupt(
                plot_cognition_scope_id,
                raw_text=raw_text.encode("utf-8"),
            )
            return RawLoadResult(
                status="corrupt",
                payload=None,
                quarantine_path=str(quarantine),
                diagnostics=(f"json_decode_failed:{exc}",),
            )

        if not isinstance(payload, dict):
            quarantine = self.quarantine_corrupt(
                plot_cognition_scope_id,
                raw_text=raw_text.encode("utf-8"),
            )
            return RawLoadResult(
                status="corrupt",
                payload=None,
                quarantine_path=str(quarantine),
                diagnostics=("envelope_not_object",),
            )

        schema = str(payload.get("store_schema", ""))
        if schema != PLOT_COGNITION_OVERLAY_STORE_SCHEMA:
            self._write_blocked_marker(
                plot_cognition_scope_id,
                load_status="unsupported_version",
                quarantine_path=None,
                reason=f"unsupported_store_schema:{schema or '<missing>'}",
            )
            return RawLoadResult(
                status="unsupported_version",
                payload=None,
                diagnostics=(f"unsupported_store_schema:{schema or '<missing>'}",),
            )

        return RawLoadResult(status="present", payload=payload)

    def save_raw(
        self,
        plot_cognition_scope_id: str,
        payload: dict[str, Any],
        *,
        expected_revision: int | None,
    ) -> int:
        current = self.load_raw(plot_cognition_scope_id)
        if current.status in {"corrupt", "unsupported_version"}:
            raise PersistenceError(
                f"overlay store {plot_cognition_scope_id} is not writable in status {current.status}"
            )

        current_revision = 0
        if current.payload is not None:
            current_revision = int(current.payload.get("store_revision", 0))
        elif current.status != "absent":
            raise PersistenceError(
                f"overlay store {plot_cognition_scope_id} load status {current.status} blocks save"
            )

        if expected_revision is not None and expected_revision != current_revision:
            raise RevisionConflictError(
                f"expected revision {expected_revision} but current revision is {current_revision}"
            )

        new_revision = current_revision + 1
        payload = dict(payload)
        payload["store_revision"] = new_revision
        payload["plot_cognition_scope_id"] = plot_cognition_scope_id
        payload["store_schema"] = PLOT_COGNITION_OVERLAY_STORE_SCHEMA

        path = self._scope_path(plot_cognition_scope_id)
        temp_path = path.with_suffix(f".json.tmp.{os.getpid()}")
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
        try:
            temp_path.write_text(encoded, encoding="utf-8")
            temp_path.replace(path)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise PersistenceError(str(exc)) from exc

        return new_revision

    def quarantine_corrupt(
        self,
        plot_cognition_scope_id: str,
        *,
        raw_text: bytes,
    ) -> Path:
        path = self._scope_path(plot_cognition_scope_id)
        stamp = int(time.time() * 1000)
        quarantine_path = path.with_name(f"{path.stem}.corrupt.{stamp}.json")
        if path.exists():
            path.replace(quarantine_path)
        elif raw_text:
            quarantine_path.write_bytes(raw_text)
        self._write_blocked_marker(
            plot_cognition_scope_id,
            load_status="corrupt",
            quarantine_path=quarantine_path,
            reason="quarantined_corrupt_store",
        )
        return quarantine_path

    def parse_store(self, payload: dict[str, Any]) -> PlotCognitionOverlayStore:
        return PlotCognitionOverlayStore.from_dict(payload)
