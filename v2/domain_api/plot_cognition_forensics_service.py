"""Plot Cognition Forensic Chronicle service — WAFI, D-class gating, integrity (#64)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .plot_cognition_forensics_capture import bounded_overlay_snapshot
from .plot_cognition_forensics_contract import (
    CHRONICLE_ACTIVATION_VERSION,
    PlotCognitionForensicRecord,
    new_record_id,
)
from .plot_cognition_forensics_repository import (
    ForensicsPersistenceError,
    PlotCognitionForensicsRepository,
)


def mutation_already_applied(result: Any, intent_payload: dict[str, Any]) -> bool:
    code = getattr(result, "code", None) or (
        result.get("code") if isinstance(result, dict) else None
    )
    if code in {"already_initialized", "reconciliation_established"}:
        return True
    if code == "stale_revision":
        prior = intent_payload.get("prior_revision")
        current = getattr(result, "store_revision", None) or (
            result.get("store_revision") if isinstance(result, dict) else None
        )
        if prior is not None and current is not None and int(current) > int(prior):
            return True
    return False


@dataclass(frozen=True)
class WafiResult:
    ok: bool
    code: str
    message: str
    idempotency_key: str
    intent_record_id: str | None = None
    completion_record_id: str | None = None
    replayed: bool = False


@dataclass(frozen=True)
class DecisionRecordResult:
    ok: bool
    code: str
    message: str
    record_id: str | None = None
    replayed: bool = False


class PlotCognitionForensicsService:
    """Domain-owned forensic chronicle writer (not operational truth)."""

    def __init__(self, repository: PlotCognitionForensicsRepository) -> None:
        self._repo = repository

    @property
    def repository(self) -> PlotCognitionForensicsRepository:
        return self._repo

    def ensure_scope_activation(
        self,
        plot_cognition_scope_id: str,
        *,
        overlay_store_dict: dict[str, Any] | None,
        hg_session_id: str | None,
    ) -> str | None:
        manifest = self._repo.load_manifest(plot_cognition_scope_id)
        if manifest and manifest.get("activated"):
            if hg_session_id:
                self._repo.attach_session(plot_cognition_scope_id, hg_session_id)
            return None
        snapshot = bounded_overlay_snapshot(overlay_store_dict)
        record = PlotCognitionForensicRecord(
            record_id=new_record_id(),
            plot_cognition_scope_id=plot_cognition_scope_id,
            record_class="integrity",
            operation_kind="chronicle_activation",
            integrity_status="history_unavailable",
            correlation={"hg_session_id": hg_session_id} if hg_session_id else {},
            payload={
                "activation_version": CHRONICLE_ACTIVATION_VERSION,
                "activation_timestamp_ms": int(time.time() * 1000),
                "overlay_store_revision_at_activation": snapshot.get("store_revision"),
                "bounded_operational_snapshot": snapshot,
                "statement": (
                    "Prior Plot Cognition mutation history unavailable; "
                    "baseline is observational snapshot only."
                ),
            },
            recorded_at_ms=int(time.time() * 1000),
        )
        record_id = self._repo.append_record(record.to_dict())
        self._repo.save_manifest(
            plot_cognition_scope_id,
            {
                "activated": True,
                "activated_at_ms": int(time.time() * 1000),
                "activation_record_id": record_id,
                "attached_sessions": [hg_session_id] if hg_session_id else [],
                "integrity_status": "history_unavailable",
            },
        )
        return record_id

    def execute_wafi_mutation(
        self,
        *,
        plot_cognition_scope_id: str,
        idempotency_key: str,
        operation_kind: str,
        intent_payload: dict[str, Any],
        correlation: dict[str, Any],
        mutation_fn: Callable[[], Any],
        completion_builder: Callable[[Any], dict[str, Any]],
    ) -> WafiResult:
        if self._repo.has_mutation_phase(plot_cognition_scope_id, idempotency_key, "completion"):
            return WafiResult(
                ok=True,
                code="replayed",
                message="mutation already completed",
                idempotency_key=idempotency_key,
                replayed=True,
            )

        intent_record_id: str | None = None
        if not self._repo.has_mutation_phase(plot_cognition_scope_id, idempotency_key, "intent"):
            intent_record = PlotCognitionForensicRecord(
                record_id=new_record_id(),
                plot_cognition_scope_id=plot_cognition_scope_id,
                record_class="operational_mutation",
                operation_kind=operation_kind,  # type: ignore[arg-type]
                mutation_phase="intent",
                idempotency_key=idempotency_key,
                integrity_status="incomplete",
                correlation=dict(correlation),
                payload=dict(intent_payload),
                recorded_at_ms=int(time.time() * 1000),
            )
            try:
                intent_record_id = self._repo.append_record(intent_record.to_dict())
            except ForensicsPersistenceError as exc:
                return WafiResult(
                    ok=False,
                    code="intent_persistence_failed",
                    message=str(exc),
                    idempotency_key=idempotency_key,
                )
        else:
            index = self._repo.load_index(plot_cognition_scope_id)
            intent_record_id = (
                (index.get("by_idempotency_key") or {})
                .get(idempotency_key, {})
                .get("intent")
            )

        mutation_result = mutation_fn()
        if getattr(mutation_result, "success", None) is False or (
            isinstance(mutation_result, dict) and mutation_result.get("success") is False
        ):
            intent_payload = {}
            if intent_record_id:
                intent_record = self._repo.load_record(plot_cognition_scope_id, str(intent_record_id))
                if intent_record:
                    intent_payload = dict(intent_record.get("payload") or {})
            if mutation_already_applied(mutation_result, intent_payload):
                completion_payload = completion_builder(mutation_result)
            else:
                return WafiResult(
                    ok=False,
                    code="mutation_failed",
                    message=getattr(mutation_result, "message", None)
                    or (
                        mutation_result.get("message")
                        if isinstance(mutation_result, dict)
                        else "mutation failed"
                    ),
                    idempotency_key=idempotency_key,
                    intent_record_id=intent_record_id,
                )
        else:
            completion_payload = completion_builder(mutation_result)
        completion_record = PlotCognitionForensicRecord(
            record_id=new_record_id(),
            plot_cognition_scope_id=plot_cognition_scope_id,
            record_class="operational_mutation",
            operation_kind=operation_kind,  # type: ignore[arg-type]
            mutation_phase="completion",
            idempotency_key=idempotency_key,
            integrity_status="complete",
            correlation={
                **correlation,
                "overlay_revision_after": completion_payload.get("store_revision"),
            },
            payload=completion_payload,
            recorded_at_ms=int(time.time() * 1000),
        )
        try:
            completion_record_id = self._repo.append_record(completion_record.to_dict())
        except ForensicsPersistenceError as exc:
            self.record_integrity(
                plot_cognition_scope_id,
                operation_kind="integrity_gap",
                integrity_status="mutation_completion_missing",
                correlation=correlation,
                payload={
                    "idempotency_key": idempotency_key,
                    "intent_record_id": intent_record_id,
                    "error": str(exc),
                },
            )
            return WafiResult(
                ok=False,
                code="completion_persistence_failed",
                message=str(exc),
                idempotency_key=idempotency_key,
                intent_record_id=intent_record_id,
            )

        return WafiResult(
            ok=True,
            code="completed",
            message="mutation forensically recorded",
            idempotency_key=idempotency_key,
            intent_record_id=intent_record_id,
            completion_record_id=completion_record_id,
        )

    def record_semantic_decision(
        self,
        *,
        plot_cognition_scope_id: str,
        idempotency_key: str,
        record_class: str,
        operation_kind: str,
        correlation: dict[str, Any],
        payload: dict[str, Any],
        artifact_refs: list[dict[str, str]] | None = None,
        inference_evidence_refs: list[dict[str, str]] | None = None,
    ) -> DecisionRecordResult:
        index = self._repo.load_index(plot_cognition_scope_id)
        existing = (index.get("by_idempotency_key") or {}).get(idempotency_key, {}).get("record")
        if existing:
            return DecisionRecordResult(
                ok=True,
                code="replayed",
                message="decision already recorded",
                record_id=str(existing),
                replayed=True,
            )
        record = PlotCognitionForensicRecord(
            record_id=new_record_id(),
            plot_cognition_scope_id=plot_cognition_scope_id,
            record_class=record_class,  # type: ignore[arg-type]
            operation_kind=operation_kind,  # type: ignore[arg-type]
            idempotency_key=idempotency_key,
            integrity_status="complete",
            correlation=dict(correlation),
            payload=dict(payload),
            artifact_refs=list(artifact_refs or []),
            inference_evidence_refs=list(inference_evidence_refs or []),
            recorded_at_ms=int(time.time() * 1000),
        )
        try:
            record_id = self._repo.append_record(record.to_dict())
        except ForensicsPersistenceError as exc:
            return DecisionRecordResult(
                ok=False,
                code="decision_persistence_failed",
                message=str(exc),
            )
        return DecisionRecordResult(
            ok=True,
            code="recorded",
            message="semantic decision recorded",
            record_id=record_id,
        )

    def store_semantic_artifact(
        self,
        plot_cognition_scope_id: str,
        content: dict[str, Any],
    ) -> str:
        return self._repo.store_content(plot_cognition_scope_id, content)

    def record_integrity(
        self,
        plot_cognition_scope_id: str,
        *,
        operation_kind: str = "integrity_gap",
        integrity_status: str,
        correlation: dict[str, Any],
        payload: dict[str, Any],
    ) -> str:
        record = PlotCognitionForensicRecord(
            record_id=new_record_id(),
            plot_cognition_scope_id=plot_cognition_scope_id,
            record_class="integrity",
            operation_kind=operation_kind,  # type: ignore[arg-type]
            integrity_status=integrity_status,  # type: ignore[arg-type]
            correlation=dict(correlation),
            payload=dict(payload),
            recorded_at_ms=int(time.time() * 1000),
        )
        return self._repo.append_record(record.to_dict())

    def forensic_preservation_satisfied(
        self,
        plot_cognition_scope_id: str,
        *,
        cognition_item_id: str,
        idempotency_key: str,
    ) -> bool:
        if not self._repo.has_mutation_phase(plot_cognition_scope_id, idempotency_key, "completion"):
            return False
        index = self._repo.load_index(plot_cognition_scope_id)
        completion_id = (
            (index.get("by_idempotency_key") or {})
            .get(idempotency_key, {})
            .get("completion")
        )
        if not completion_id:
            return False
        record = self._repo.load_record(plot_cognition_scope_id, str(completion_id))
        if not record:
            return False
        payload = record.get("payload") or {}
        retired = payload.get("retired_or_superseded_items") or []
        prior = payload.get("prior_snapshot") or {}
        if cognition_item_id in retired:
            return True
        for goal in prior.get("goals") or []:
            if isinstance(goal, dict) and goal.get("goal_id") == cognition_item_id:
                return True
        for pressure in prior.get("pressures") or []:
            if isinstance(pressure, dict) and pressure.get("pressure_id") == cognition_item_id:
                return True
        return payload.get("integrity_status") == "complete"

    def reconcile_incomplete_wafi(self, plot_cognition_scope_id: str) -> list[dict[str, Any]]:
        index = self._repo.load_index(plot_cognition_scope_id)
        results: list[dict[str, Any]] = []
        for idem, phases in (index.get("by_idempotency_key") or {}).items():
            if phases.get("completion"):
                continue
            if not phases.get("intent"):
                continue
            intent_record = self._repo.load_record(plot_cognition_scope_id, str(phases["intent"]))
            if not intent_record:
                continue
            record_id = self.record_integrity(
                plot_cognition_scope_id,
                integrity_status="mutation_completion_missing",
                correlation=intent_record.get("correlation") or {},
                payload={
                    "idempotency_key": idem,
                    "intent_record_id": phases.get("intent"),
                    "note": "exact completion may be written only from durable intent evidence",
                },
            )
            results.append({"idempotency_key": idem, "integrity_record_id": record_id})
        return results

    def attach_session(self, plot_cognition_scope_id: str, hg_session_id: str) -> None:
        self._repo.attach_session(plot_cognition_scope_id, hg_session_id)
