"""Deserialize LibrarianKnowledgeBundle payloads from HTTP/DSH transport (#38)."""

from __future__ import annotations

from typing import Any

from .contract import AuthorityClass
from .librarian_contract import (
    BundleAudit,
    BundleDegradation,
    BundleValidity,
    BudgetAccounting,
    HostMediationValidation,
    InvalidationKey,
    LibrarianAnnotation,
    LibrarianBundleEntry,
    LibrarianKnowledgeBundle,
    MediationMode,
    RequestSatisfactionSummary,
    SourceDiagnostics,
    SourceStatus,
    StableReference,
    SynthesisMeta,
)


def _stable_ref(raw: dict[str, Any]) -> StableReference:
    return StableReference(
        ref_kind=str(raw.get("ref_kind", "")),
        stable_ref=str(raw.get("stable_ref", "")),
        display_hint=raw.get("display_hint"),
    )


def _bundle_entry(raw: dict[str, Any]) -> LibrarianBundleEntry:
    synth_raw = raw.get("synthesis_meta")
    synthesis = None
    if isinstance(synth_raw, dict):
        synthesis = SynthesisMeta(
            synthesis_kind=synth_raw.get("synthesis_kind", "summary"),  # type: ignore[arg-type]
            source_entry_refs=tuple(
                _stable_ref(item) for item in (synth_raw.get("source_entry_refs") or []) if isinstance(item, dict)
            ),
            synthesis_authority=str(synth_raw.get("synthesis_authority", "suggestive")),  # type: ignore[arg-type]
        )
        annotation_raw = dict(raw.get("librarian_annotation") or {})
    return LibrarianBundleEntry(
        entry_id=str(raw.get("entry_id", "")),
        ref=_stable_ref(dict(raw.get("ref") or {})),
        content=str(raw.get("content", "")),
        authority_class=str(raw.get("authority_class", "suggestive")),  # type: ignore[arg-type]
        information_class=str(raw.get("information_class", "")),
        visibility_scope=str(raw.get("visibility_scope", "")),
        source_tier=str(raw.get("source_tier", "")),
        librarian_annotation=LibrarianAnnotation(
            relevance_rank=int(annotation_raw.get("relevance_rank", 1)),
            salience_note=annotation_raw.get("salience_note"),
            interpretive_status=annotation_raw.get("interpretive_status"),
            relevance_band=annotation_raw.get("relevance_band"),
        ),
        synthesis_meta=synthesis,
        provenance=dict(raw.get("provenance") or {}),
    )


def librarian_knowledge_bundle_from_dict(data: dict[str, Any]) -> LibrarianKnowledgeBundle:
    validity_raw = dict(data.get("validity") or {})
    degradation_raw = dict(data.get("degradation") or {})
    satisfaction_raw = dict(data.get("satisfaction") or {})
    budget_raw = dict(data.get("budget_accounting") or {})
    diagnostics_raw = dict(data.get("source_diagnostics") or {})
    audit_raw = dict(data.get("audit") or {})
    host_validation_raw = audit_raw.get("host_validation")
    host_validation = None
    if isinstance(host_validation_raw, dict):
        host_validation = HostMediationValidation(
            accepted=bool(host_validation_raw.get("accepted")),
            reason=str(host_validation_raw.get("reason", "")),
            rejection_codes=tuple(str(item) for item in (host_validation_raw.get("rejection_codes") or [])),
        )
    validity = BundleValidity(
        validity_scope=validity_raw.get("validity_scope", "stage_current"),  # type: ignore[arg-type]
        bound_hg_round_id=str(validity_raw.get("bound_hg_round_id", "")),
        bound_turn_index=int(validity_raw.get("bound_turn_index", 0)),
        bound_pipeline_stage=validity_raw.get("bound_pipeline_stage"),
        valid_from_authoritative_snapshot_id=str(validity_raw.get("valid_from_authoritative_snapshot_id", "")),
        invalidation_keys=tuple(
            InvalidationKey(key_kind=str(item.get("key_kind", "")), key_value=str(item.get("key_value", "")))
            for item in (validity_raw.get("invalidation_keys") or [])
            if isinstance(item, dict)
        ),
        bound_domain_commit_id=validity_raw.get("bound_domain_commit_id"),
    )
    return LibrarianKnowledgeBundle(
        bundle_id=str(data.get("bundle_id", "")),
        request_id=str(data.get("request_id", "")),
        consumer_role=data.get("consumer_role", "character"),  # type: ignore[arg-type]
        pipeline_stage=data.get("pipeline_stage", "character"),  # type: ignore[arg-type]
        hg_round_id=str(data.get("hg_round_id", "")),
        turn_index=int(data.get("turn_index", 0)),
        mediation_mode=data.get("mediation_mode", "contextual_semantic"),  # type: ignore[arg-type]
        validity=validity,
        degradation=BundleDegradation(
            level=degradation_raw.get("level", "none"),  # type: ignore[arg-type]
            mode=degradation_raw.get("mode", "none"),  # type: ignore[arg-type]
            per_source=tuple(
                SourceStatus(
                    source_tier=str(item.get("source_tier", "")),
                    status=item.get("status", "ok"),  # type: ignore[arg-type]
                    detail=str(item.get("detail", "")),
                )
                for item in (degradation_raw.get("per_source") or [])
                if isinstance(item, dict)
            ),
            deterministic_fallback_used=bool(degradation_raw.get("deterministic_fallback_used")),
        ),
        satisfaction=RequestSatisfactionSummary(
            focus_questions=(),
            truncated=bool(satisfaction_raw.get("truncated")),
            truncation_reason=satisfaction_raw.get("truncation_reason"),
        ),
        entries=tuple(_bundle_entry(item) for item in (data.get("entries") or []) if isinstance(item, dict)),
        budget_accounting=BudgetAccounting(
            entries_returned=int(budget_raw.get("entries_returned", 0)),
            entries_considered=int(budget_raw.get("entries_considered", 0)),
            chars_returned=int(budget_raw.get("chars_returned", 0)),
            chars_budget=int(budget_raw.get("chars_budget", 0)),
            entries_truncated=int(budget_raw.get("entries_truncated", 0)),
        ),
        source_diagnostics=SourceDiagnostics(
            consulted_tiers=tuple(str(item) for item in (diagnostics_raw.get("consulted_tiers") or [])),
            omitted_tiers=tuple(str(item) for item in (diagnostics_raw.get("omitted_tiers") or [])),
        ),
        audit=BundleAudit(
            bundle_hash=str(audit_raw.get("bundle_hash", "")),
            retrieval_request_ids=tuple(str(item) for item in (audit_raw.get("retrieval_request_ids") or [])),
            candidate_ids_considered=tuple(str(item) for item in (audit_raw.get("candidate_ids_considered") or [])),
            original_request_id=str(audit_raw.get("original_request_id", "")),
            mediation_mode=audit_raw.get("mediation_mode", "contextual_semantic"),  # type: ignore[arg-type]
            mediation_strategy=str(audit_raw.get("mediation_strategy", "")),
            inference_id=audit_raw.get("inference_id"),
            host_validation=host_validation,
            fallback_reason=audit_raw.get("fallback_reason"),
            structured_mediation_evidence=dict(audit_raw.get("structured_mediation_evidence") or {}),
        ),
        connections=(),
    )
