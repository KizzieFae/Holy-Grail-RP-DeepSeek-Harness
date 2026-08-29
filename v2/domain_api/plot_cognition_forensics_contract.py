"""Plot Cognition Forensic Chronicle contract (#64)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

FORENSIC_RECORD_SCHEMA = "hg_plot_cognition_forensic_record_v1"
FORENSIC_INDEX_SCHEMA = "hg_plot_cognition_forensics_index_v1"
FORENSIC_SCOPE_MANIFEST_SCHEMA = "hg_plot_cognition_forensics_scope_manifest_v1"
FORENSIC_CONTENT_SCHEMA = "hg_plot_cognition_forensic_content_v1"
CHRONICLE_ACTIVATION_VERSION = "64"

RecordClass = Literal[
    "semantic_decision",
    "operational_mutation",
    "consumer_decision",
    "integrity",
]
OperationKind = Literal[
    "chronicle_activation",
    "initialization",
    "update",
    "replan",
    "reconciliation",
    "authority_advance",
    "pending_work",
    "overlay_item_lifecycle",
    "projection_prepare",
    "projection_evaluate",
    "regeneration",
    "projection_withhold",
    "consumer_delivery",
    "freshness_barrier",
    "integrity_gap",
]
MutationPhase = Literal["intent", "completion"]
IntegrityStatus = Literal[
    "complete",
    "incomplete",
    "gap_detected",
    "history_unavailable",
    "missing_inference_artifact",
    "mutation_completion_missing",
    "state_mismatch",
    "persistence_failed",
]


@dataclass(frozen=True)
class ForensicCorrelation:
    plot_cognition_scope_id: str
    hg_session_id: str | None = None
    hg_scene_id: str | None = None
    hg_round_id: str | None = None
    turn_index: int | None = None
    domain_commit_id: str | None = None
    overlay_revision_before: int | None = None
    overlay_revision_after: int | None = None
    cognition_item_id: str | None = None
    candidate_id: str | None = None
    batch_id: str | None = None
    evaluation_pass_id: str | None = None
    character_id: str | None = None
    consumer: str | None = None
    known_by_snapshot_id: str | None = None
    authority_fingerprint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    artifact_id: str
    role: str = "semantic"

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "artifact_id": self.artifact_id, "role": self.role}


@dataclass(frozen=True)
class InferenceEvidenceRef:
    evidence_id: str
    role: str = "inference"

    def to_dict(self) -> dict[str, str]:
        return {"evidence_id": self.evidence_id, "role": self.role}


@dataclass
class PlotCognitionForensicRecord:
    record_id: str
    schema: str = FORENSIC_RECORD_SCHEMA
    plot_cognition_scope_id: str = ""
    record_class: RecordClass = "semantic_decision"
    operation_kind: OperationKind = "integrity_gap"
    phase: str | None = None
    mutation_phase: MutationPhase | None = None
    idempotency_key: str | None = None
    integrity_status: IntegrityStatus = "complete"
    correlation: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[dict[str, str]] = field(default_factory=list)
    inference_evidence_refs: list[dict[str, str]] = field(default_factory=list)
    recorded_at_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "record_id": self.record_id,
            "schema": self.schema,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "record_class": self.record_class,
            "operation_kind": self.operation_kind,
            "integrity_status": self.integrity_status,
            "correlation": dict(self.correlation),
            "payload": dict(self.payload),
            "artifact_refs": list(self.artifact_refs),
            "inference_evidence_refs": list(self.inference_evidence_refs),
            "recorded_at_ms": self.recorded_at_ms,
        }
        if self.phase is not None:
            body["phase"] = self.phase
        if self.mutation_phase is not None:
            body["mutation_phase"] = self.mutation_phase
        if self.idempotency_key is not None:
            body["idempotency_key"] = self.idempotency_key
        return body

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionForensicRecord:
        return cls(
            record_id=str(data.get("record_id", "")),
            schema=str(data.get("schema", FORENSIC_RECORD_SCHEMA)),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            record_class=data.get("record_class", "semantic_decision"),  # type: ignore[arg-type]
            operation_kind=data.get("operation_kind", "integrity_gap"),  # type: ignore[arg-type]
            phase=data.get("phase"),
            mutation_phase=data.get("mutation_phase"),
            idempotency_key=data.get("idempotency_key"),
            integrity_status=data.get("integrity_status", "complete"),  # type: ignore[arg-type]
            correlation=dict(data.get("correlation") or {}),
            payload=dict(data.get("payload") or {}),
            artifact_refs=list(data.get("artifact_refs") or []),
            inference_evidence_refs=list(data.get("inference_evidence_refs") or []),
            recorded_at_ms=int(data.get("recorded_at_ms", 0)),
        )


def new_record_id() -> str:
    return f"pcf-{uuid.uuid4()}"


def content_artifact_id(payload: dict[str, Any]) -> str:
    import hashlib
    import json

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
