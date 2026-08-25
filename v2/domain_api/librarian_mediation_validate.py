"""Deterministic Host validation of DSH Librarian mediation results (#34 S2a)."""

from __future__ import annotations

from typing import Any

from .librarian_contract import (
    LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    HostMediationValidation,
    InterpretiveStatus,
    KnowledgeAccessRequest,
    LibrarianMediationResult,
    MediationCatalogItem,
    MediationConnectionItem,
    MediationSelectionItem,
    MediationSynthesisItem,
    QuestionOutcome,
    RelevanceBand,
)

_VALID_EDGE = frozenset({"supports", "contradicts", "same_entity", "causal_candidate"})
_VALID_SYNTH = frozenset({"summary", "connection_bridge", "consolidated_fact_view"})
_VALID_BAND = frozenset({"high", "medium", "low"})
_VALID_STATUS = frozenset({"confirmed", "likely", "speculative"})


def _as_tuple_str(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def parse_librarian_mediation_result(raw: Any) -> tuple[LibrarianMediationResult | None, str]:
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, f"invalid_json:{exc.msg}"
    if not isinstance(raw, dict):
        return None, "malformed:not_object"
    schema = str(raw.get("schema", "") or "").strip()
    if schema != LIBRARIAN_MEDIATION_RESULT_SCHEMA:
        return None, f"malformed:schema:{schema or '<missing>'}"

    selected: list[MediationSelectionItem] = []
    for index, item in enumerate(raw.get("selected_items") or []):
        if not isinstance(item, dict):
            return None, f"malformed:selected_items[{index}]"
        source_id = str(item.get("source_id", "") or "").strip()
        if not source_id:
            return None, f"malformed:selected_items[{index}].source_id"
        try:
            rank = int(item.get("relevance_rank"))
        except (TypeError, ValueError):
            return None, f"malformed:selected_items[{index}].relevance_rank"
        band = item.get("relevance_band")
        band_value = str(band).strip() if band is not None else None
        if band_value is not None and band_value not in _VALID_BAND:
            return None, f"malformed:selected_items[{index}].relevance_band"
        status = item.get("interpretive_status")
        status_value = str(status).strip() if status is not None else None
        if status_value is not None and status_value not in _VALID_STATUS:
            return None, f"malformed:selected_items[{index}].interpretive_status"
        selected.append(
            MediationSelectionItem(
                source_id=source_id,
                relevance_rank=rank,
                relevance_band=band_value,  # type: ignore[arg-type]
                salience_note=str(item.get("salience_note", "") or "").strip() or None,
                interpretive_status=status_value,  # type: ignore[arg-type]
                answers_focus_questions=_as_tuple_str(item.get("answers_focus_questions")),
            )
        )

    connections: list[MediationConnectionItem] = []
    for index, item in enumerate(raw.get("connections") or []):
        if not isinstance(item, dict):
            return None, f"malformed:connections[{index}]"
        edge = str(item.get("edge_kind", "") or "").strip()
        if edge not in _VALID_EDGE:
            return None, f"malformed:connections[{index}].edge_kind"
        from_id = str(item.get("from_source_id", "") or "").strip()
        to_id = str(item.get("to_source_id", "") or "").strip()
        if not from_id or not to_id:
            return None, f"malformed:connections[{index}].source_ids"
        connections.append(
            MediationConnectionItem(
                connection_id=str(item.get("connection_id", "") or f"conn-{index}"),
                edge_kind=edge,  # type: ignore[arg-type]
                from_source_id=from_id,
                to_source_id=to_id,
                note=str(item.get("note", "") or "").strip() or None,
            )
        )

    synthesis_entries: list[MediationSynthesisItem] = []
    for index, item in enumerate(raw.get("synthesis_entries") or []):
        if not isinstance(item, dict):
            return None, f"malformed:synthesis_entries[{index}]"
        kind = str(item.get("synthesis_kind", "") or "").strip()
        if kind not in _VALID_SYNTH:
            return None, f"malformed:synthesis_entries[{index}].synthesis_kind"
        content = str(item.get("content", "") or "").strip()
        source_ids = _as_tuple_str(item.get("source_ids"))
        if not content or not source_ids:
            return None, f"malformed:synthesis_entries[{index}]"
        status = str(item.get("interpretive_status", "likely") or "likely").strip()
        if status not in _VALID_STATUS:
            return None, f"malformed:synthesis_entries[{index}].interpretive_status"
        synthesis_entries.append(
            MediationSynthesisItem(
                synthesis_id=str(item.get("synthesis_id", "") or f"synth-{index}"),
                synthesis_kind=kind,  # type: ignore[arg-type]
                content=content,
                source_ids=source_ids,
                interpretive_status=status,  # type: ignore[arg-type]
            )
        )

    outcomes: list[QuestionOutcome] = []
    for index, item in enumerate(raw.get("focus_question_outcomes") or []):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "") or "").strip()
        status = str(item.get("status", "") or "").strip()
        if not question or status not in {"answered", "partial", "unanswered", "not_applicable"}:
            continue
        outcomes.append(
            QuestionOutcome(
                question=question,
                status=status,  # type: ignore[arg-type]
                supporting_entry_ids=_as_tuple_str(item.get("supporting_source_ids")),
                note=str(item.get("note", "") or "").strip() or None,
            )
        )

    return (
        LibrarianMediationResult(
            schema=schema,
            selected_items=tuple(selected),
            connections=tuple(connections),
            synthesis_entries=tuple(synthesis_entries),
            focus_question_outcomes=tuple(outcomes),
        ),
        "",
    )


def validate_librarian_mediation_result(
    result: LibrarianMediationResult,
    *,
    catalog: dict[str, MediationCatalogItem],
    request: KnowledgeAccessRequest,
) -> HostMediationValidation:
    codes: list[str] = []
    if not result.selected_items and not result.synthesis_entries:
        codes.append("empty_selection")

    seen: set[str] = set()
    for item in result.selected_items:
        if item.source_id not in catalog:
            codes.append(f"unknown_source:{item.source_id}")
            continue
        if item.source_id in seen:
            codes.append(f"duplicate_source:{item.source_id}")
        seen.add(item.source_id)
        if item.relevance_rank <= 0:
            codes.append(f"invalid_rank:{item.source_id}")
        catalog_item = catalog[item.source_id]
        if item.interpretive_status == "confirmed" and catalog_item.authority_class != "authoritative":
            codes.append(f"authority_elevation:{item.source_id}")

    for synth in result.synthesis_entries:
        if len(synth.content) > request.budget_expectations.max_bundle_chars:
            codes.append(f"synthesis_too_large:{synth.synthesis_id}")
        for source_id in synth.source_ids:
            if source_id not in catalog:
                codes.append(f"synthesis_unknown_source:{source_id}")

    for conn in result.connections:
        if conn.from_source_id not in catalog or conn.to_source_id not in catalog:
            codes.append(f"connection_unknown_source:{conn.connection_id}")

    if len(result.selected_items) + len(result.synthesis_entries) > request.budget_expectations.max_bundle_entries:
        codes.append("budget_exceeded")

    if codes:
        return HostMediationValidation(
            accepted=False,
            reason="mediation_result_rejected",
            rejection_codes=tuple(codes),
        )
    return HostMediationValidation(accepted=True, reason="accepted")
