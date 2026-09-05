"""Deterministic semantic decomposition normalization (#124)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from perceptual_visibility_contract import MAX_PVR_UNITS, VALID_UNIT_KINDS
from player_perceptual_service import validate_player_perceptual_decomposition
from player_source_accounting import (
    SOURCE_ACCOUNTING_NORMALIZATION,
    normalize_source_for_indexing,
    normalized_source_sha256,
)

NORMALIZER_VERSION = 5
PLAYER_UNIT_SOURCE = "player_decomposition"

# Unified deterministic work budget for normalization (#124 / G-124-03 / G-124-03b).
# Charges occurrence scanning, substantive-mask construction (source + span precompute),
# DFS visits, candidate probes, and overlap comparisons.
# Benchmarked 2026-09-05 (v5, G-124-03b):
# - representative / Yes.Yes / material ambiguity: <= 40 work units
# - 7-unit identical single-char tiling: ~296k work (~196ms), accepts
# - 9-unit pathological tiling: budget fail ~350k work (~206ms)
# - 50k-source 1-char excerpt: budget fail during occurrence_scan (~162ms)
# Headroom ~18% above legitimate 7×`a` stress (~296k).
NORMALIZATION_DETERMINISTIC_WORK_BUDGET = 350_000
# Retained alias — DFS node visits are one charged operation inside the work budget.
NORMALIZATION_SEARCH_NODE_BUDGET = NORMALIZATION_DETERMINISTIC_WORK_BUDGET

VALID_PLAYER_SIR_KINDS = frozenset(
    {"observable_scene", "observable_event", "speech", "internal"}
)
VALID_RECIPIENT_SCOPES = frozenset(
    {"public", "present", "directed", "private", "role_private", "environmental"}
)

FAILURE_SIR_MALFORMED = "sir_malformed"
FAILURE_SIR_INVALID_SEMANTICS = "sir_invalid_semantics"
FAILURE_SIR_NON_VERBATIM = "sir_non_verbatim_excerpt"
FAILURE_SIR_SUBSTANTIVE_OMISSION = "sir_substantive_omission"
FAILURE_SIR_OVERLAP_CONFLICT = "sir_overlap_conflict"
FAILURE_FRAGMENT_AMBIGUOUS = "fragment_assignment_ambiguous"
FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL = "fragment_assignment_ambiguous_terminal"
FAILURE_NORMALIZATION_IMPOSSIBLE = "normalization_impossible"
FAILURE_SEARCH_BUDGET_EXCEEDED = "normalization_search_budget_exceeded"
FAILURE_VALIDATION_REJECTED = "validation_rejected"

RETRY_ELIGIBLE_FAILURES = frozenset(
    {
        FAILURE_SIR_MALFORMED,
        FAILURE_SIR_INVALID_SEMANTICS,
        FAILURE_SIR_NON_VERBATIM,
        FAILURE_SIR_SUBSTANTIVE_OMISSION,
        FAILURE_SIR_OVERLAP_CONFLICT,
        FAILURE_FRAGMENT_AMBIGUOUS,
        FAILURE_SEARCH_BUDGET_EXCEEDED,
        FAILURE_VALIDATION_REJECTED,
    }
)


@dataclass
class _DeterministicWorkLedger:
    budget: int
    consumed: int = 0
    occurrence_scan_steps: int = 0
    candidates_generated: int = 0
    substantive_mask_steps: int = 0
    candidate_probes: int = 0
    overlap_checks: int = 0
    dfs_nodes_visited: int = 0
    exhaustion_stage: str | None = None

    def charge(self, amount: int, stage: str) -> bool:
        if amount <= 0:
            return True
        if self.consumed + amount > self.budget:
            self.exhaustion_stage = stage
            return False
        self.consumed += amount
        if stage == "occurrence_scan":
            self.occurrence_scan_steps += amount
        elif stage == "candidates_generated":
            self.candidates_generated += amount
        elif stage == "substantive_mask":
            self.substantive_mask_steps += amount
        elif stage == "candidate_probe":
            self.candidate_probes += amount
        elif stage == "overlap_check":
            self.overlap_checks += amount
        elif stage == "dfs_visit":
            self.dfs_nodes_visited += amount
        return True

    def to_audit(self) -> dict[str, Any]:
        return {
            "deterministic_work_budget": self.budget,
            "work_consumed": self.consumed,
            "work_occurrence_scan": self.occurrence_scan_steps,
            "work_candidates_generated": self.candidates_generated,
            "work_substantive_mask": self.substantive_mask_steps,
            "work_candidate_probes": self.candidate_probes,
            "work_overlap_checks": self.overlap_checks,
            "search_nodes_visited": self.dfs_nodes_visited,
            "work_exhaustion_stage": self.exhaustion_stage,
        }


@dataclass(frozen=True)
class _SirUnit:
    index: int
    kind: str
    text: str
    recipients: dict[str, Any]


@dataclass(frozen=True)
class _Span:
    start: int
    end: int

    def overlaps(self, other: _Span) -> bool:
        return self.start < other.end and other.start < self.end


def _is_substantive_char(char: str) -> bool:
    return bool(char) and not char.isspace()


def _find_occurrences(
    source: str,
    text: str,
    *,
    ledger: _DeterministicWorkLedger | None = None,
) -> list[_Span] | None:
    if not text:
        return []
    spans: list[_Span] = []
    start = 0
    while True:
        if ledger is not None and not ledger.charge(1, "occurrence_scan"):
            return None
        index = source.find(text, start)
        if index < 0:
            break
        spans.append(_Span(index, index + len(text)))
        if ledger is not None:
            ledger.charge(1, "candidates_generated")
        start = index + 1
    return spans


def _substantive_mask(
    source: str,
    *,
    ledger: _DeterministicWorkLedger | None = None,
) -> int | None:
    mask = 0
    for index, char in enumerate(source):
        if ledger is not None and not ledger.charge(1, "substantive_mask"):
            return None
        if _is_substantive_char(char):
            mask |= 1 << index
    return mask


def _parse_sir_units(
    semantic_decomposition: dict[str, Any] | None,
) -> tuple[list[_SirUnit], str]:
    if not isinstance(semantic_decomposition, dict):
        return [], "semantic_decomposition missing or not an object"
    units_raw = semantic_decomposition.get("units")
    if not isinstance(units_raw, list):
        return [], "semantic_decomposition.units not a list"
    if len(units_raw) > MAX_PVR_UNITS:
        return [], f"unit count exceeds {MAX_PVR_UNITS}"
    if not units_raw and semantic_decomposition.get("units") is not None:
        return [], "semantic_decomposition.units empty"

    parsed: list[_SirUnit] = []
    for index, item in enumerate(units_raw):
        if not isinstance(item, dict):
            return [], f"unit {index} not an object"
        kind = str(item.get("kind", "") or "").strip()
        text = str(item.get("text", "") or "")
        if kind not in VALID_PLAYER_SIR_KINDS:
            return [], f"unit {index} invalid kind"
        if kind not in VALID_UNIT_KINDS:
            return [], f"unit {index} kind not in contract"
        if not text:
            return [], f"unit {index} missing text"
        recipients = item.get("recipients")
        if not isinstance(recipients, dict):
            return [], f"unit {index} recipients not an object"
        scope = str(recipients.get("scope", "") or "").strip().lower()
        if scope not in VALID_RECIPIENT_SCOPES:
            return [], f"unit {index} invalid scope"
        characters = recipients.get("characters")
        roles = recipients.get("roles")
        if characters is not None and not isinstance(characters, list):
            return [], f"unit {index} characters not a list"
        if roles is not None and not isinstance(roles, list):
            return [], f"unit {index} roles not a list"
        parsed.append(
            _SirUnit(
                index=index,
                kind=kind,
                text=text,
                recipients={
                    "scope": scope,
                    "characters": list(characters or []),
                    "roles": list(roles or []),
                },
            )
        )
    return parsed, ""


def _substantive_complete(source: str, spans: list[_Span]) -> bool:
    if not source:
        return True
    covered = [False] * len(source)
    for span in spans:
        for index in range(span.start, span.end):
            covered[index] = True
    for index, char in enumerate(source):
        if _is_substantive_char(char) and not covered[index]:
            return False
    return True


def _span_substantive_mask(
    source: str,
    span: _Span,
    *,
    ledger: _DeterministicWorkLedger | None = None,
) -> int | None:
    mask = 0
    for index in range(span.start, span.end):
        if ledger is not None and not ledger.charge(1, "substantive_mask"):
            return None
        if _is_substantive_char(source[index]):
            mask |= 1 << index
    return mask


def _precompute_span_substantive_masks(
    source: str,
    candidates: list[list[_Span]],
    *,
    ledger: _DeterministicWorkLedger,
) -> dict[tuple[int, int], int] | None:
    """Meter span-mask construction once per unique candidate span (G-124-03b)."""
    masks: dict[tuple[int, int], int] = {}
    for unit_spans in candidates:
        for span in unit_spans:
            key = (span.start, span.end)
            if key in masks:
                continue
            mask = _span_substantive_mask(source, span, ledger=ledger)
            if mask is None:
                return None
            masks[key] = mask
    return masks


def _uncovered_substantive_count(substantive_mask: int, covered_mask: int) -> int:
    return (substantive_mask & ~covered_mask).bit_count()


def _assignment_key(assignment: list[tuple[int, _Span]]) -> tuple[tuple[int, int, int], ...]:
    return tuple(sorted((unit.index, span.start, span.end) for unit, span in assignment))


def _recipients_fingerprint(recipients: dict[str, Any]) -> str:
    return json.dumps(recipients, sort_keys=True, ensure_ascii=False)


def _canonical_semantic_fingerprint(
    source: str,
    assignment: list[tuple[_SirUnit, _Span]],
) -> tuple[tuple[str, str, str, int], ...]:
    ordered = sorted(assignment, key=lambda item: (item[1].start, item[1].end, item[0].index))
    parts: list[tuple[str, str, str, int]] = []
    for order_index, (unit, span) in enumerate(ordered):
        parts.append(
            (
                unit.kind,
                source[span.start : span.end],
                _recipients_fingerprint(unit.recipients),
                order_index,
            )
        )
    return tuple(parts)


def _build_player_decomposition(
    source: str,
    assignment: list[tuple[_SirUnit, _Span]],
    *,
    generation: dict[str, Any],
    normalization_audit: dict[str, Any],
) -> dict[str, Any]:
    ordered = sorted(assignment, key=lambda item: (item[1].start, item[1].end, item[0].index))
    units_payload: list[dict[str, Any]] = []
    segments_payload: list[dict[str, Any]] = []

    cursor = 0
    segment_counter = 1
    for order_index, (unit, span) in enumerate(ordered):
        if cursor < span.start:
            segment_id = f"s{segment_counter}"
            segments_payload.append(
                {
                    "segment_id": segment_id,
                    "char_start": cursor,
                    "char_end": span.start,
                    "disposition": "non_projects",
                    "unit_ids": [],
                }
            )
            segment_counter += 1

        unit_id = f"u{order_index + 1}"
        segment_id = f"s{segment_counter}"
        units_payload.append(
            {
                "unit_id": unit_id,
                "kind": unit.kind,
                "text": source[span.start : span.end],
                "recipients": dict(unit.recipients),
                "source_provenance": {
                    "segment_ids": [segment_id],
                    "order_index": order_index,
                },
                "source": PLAYER_UNIT_SOURCE,
            }
        )
        segments_payload.append(
            {
                "segment_id": segment_id,
                "char_start": span.start,
                "char_end": span.end,
                "disposition": "projects",
                "unit_ids": [unit_id],
            }
        )
        segment_counter += 1
        cursor = span.end

    if cursor < len(source):
        segments_payload.append(
            {
                "segment_id": f"s{segment_counter}",
                "char_start": cursor,
                "char_end": len(source),
                "disposition": "non_projects",
                "unit_ids": [],
            }
        )

    if not source:
        segments_payload = [
            {
                "segment_id": "s1",
                "char_start": 0,
                "char_end": 0,
                "disposition": "non_projects",
                "unit_ids": [],
            }
        ]

    generation_payload = dict(generation)
    generation_payload["normalization"] = normalization_audit
    return {
        "perceptual_visibility": {"units": units_payload},
        "source_accounting": {
            "source_length": len(source),
            "source_sha256": normalized_source_sha256(source),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": segments_payload,
        },
        "generation": generation_payload,
    }


def _budget_failure_audit(
    ledger: _DeterministicWorkLedger,
    *,
    stage: str,
) -> dict[str, Any]:
    audit = {
        "version": NORMALIZER_VERSION,
        "budget_exceeded": True,
        "work_exhaustion_stage": stage,
        **ledger.to_audit(),
    }
    # Back-compat alias: search_budget now reports the unified work budget.
    audit["search_budget"] = ledger.budget
    return audit


def _search_and_resolve_assignment(
    source: str,
    units: list[_SirUnit],
    *,
    attempt_index: int,
) -> tuple[list[tuple[_SirUnit, _Span]] | None, str, str, dict[str, Any]]:
    ledger = _DeterministicWorkLedger(budget=NORMALIZATION_DETERMINISTIC_WORK_BUDGET)
    audit: dict[str, Any] = {
        "version": NORMALIZER_VERSION,
        **ledger.to_audit(),
    }
    audit["search_budget"] = ledger.budget

    if not units:
        if any(_is_substantive_char(char) for char in source):
            audit["failure_reason"] = "empty units with substantive source"
            return None, FAILURE_SIR_SUBSTANTIVE_OMISSION, audit["failure_reason"], audit
        audit["assignment_count"] = 0
        audit["ambiguity_class"] = "unique"
        return [], "", "", audit

    candidates: list[list[_Span]] = []
    for unit in units:
        occurrences = _find_occurrences(source, unit.text, ledger=ledger)
        if occurrences is None:
            return (
                None,
                FAILURE_SEARCH_BUDGET_EXCEEDED,
                "deterministic normalization work budget exceeded",
                _budget_failure_audit(ledger, stage=ledger.exhaustion_stage or "occurrence_scan"),
            )
        if not occurrences:
            reason = f"unit {unit.index} excerpt not found in source"
            audit["failure_reason"] = reason
            audit.update(ledger.to_audit())
            return None, FAILURE_SIR_NON_VERBATIM, reason, audit
        candidates.append(occurrences)

    order = sorted(range(len(units)), key=lambda idx: len(candidates[idx]))
    remaining_text_capacity = [len(units[idx].text) for idx in order]
    suffix_capacity = [0] * (len(order) + 1)
    for index in range(len(order) - 1, -1, -1):
        suffix_capacity[index] = suffix_capacity[index + 1] + remaining_text_capacity[index]

    substantive_mask = _substantive_mask(source, ledger=ledger)
    if substantive_mask is None:
        return (
            None,
            FAILURE_SEARCH_BUDGET_EXCEEDED,
            "deterministic normalization work budget exceeded",
            _budget_failure_audit(ledger, stage=ledger.exhaustion_stage or "substantive_mask"),
        )

    span_substantive_masks = _precompute_span_substantive_masks(
        source,
        candidates,
        ledger=ledger,
    )
    if span_substantive_masks is None:
        return (
            None,
            FAILURE_SEARCH_BUDGET_EXCEEDED,
            "deterministic normalization work budget exceeded",
            _budget_failure_audit(ledger, stage=ledger.exhaustion_stage or "substantive_mask"),
        )

    partial_exists = False
    complete_count = 0
    budget_exceeded = False
    material_proven = False
    fingerprint_best: dict[
        tuple[tuple[str, str, str, int], ...],
        tuple[list[tuple[_SirUnit, _Span]], tuple[tuple[int, int, int], ...]],
    ] = {}

    def visit(
        position: int,
        chosen: list[tuple[_SirUnit, _Span]],
        occupied: list[_Span],
        covered_mask: int,
    ) -> None:
        nonlocal partial_exists, complete_count, budget_exceeded, material_proven
        if budget_exceeded or material_proven:
            return

        if not ledger.charge(1, "dfs_visit"):
            budget_exceeded = True
            return

        if position >= len(order):
            if (substantive_mask & ~covered_mask) == 0:
                complete_count += 1
                fingerprint = _canonical_semantic_fingerprint(source, chosen)
                assignment_key = _assignment_key(chosen)
                existing = fingerprint_best.get(fingerprint)
                if existing is None or assignment_key < existing[1]:
                    fingerprint_best[fingerprint] = (list(chosen), assignment_key)
                if len(fingerprint_best) >= 2:
                    material_proven = True
            else:
                partial_exists = True
            return

        remaining_capacity = suffix_capacity[position]
        if _uncovered_substantive_count(substantive_mask, covered_mask) > remaining_capacity:
            partial_exists = True
            return

        unit_index = order[position]
        unit = units[unit_index]
        for span in candidates[unit_index]:
            if budget_exceeded or material_proven:
                return
            if not ledger.charge(1, "candidate_probe"):
                budget_exceeded = True
                return
            overlap_blocked = False
            for existing in occupied:
                if not ledger.charge(1, "overlap_check"):
                    budget_exceeded = True
                    return
                if span.overlaps(existing):
                    partial_exists = True
                    overlap_blocked = True
                    break
            if budget_exceeded or material_proven:
                return
            if overlap_blocked:
                continue
            span_mask = span_substantive_masks[(span.start, span.end)]
            chosen.append((unit, span))
            occupied.append(span)
            visit(
                position + 1,
                chosen,
                occupied,
                covered_mask | span_mask,
            )
            occupied.pop()
            chosen.pop()

    visit(0, [], [], 0)
    audit.update(ledger.to_audit())
    audit["assignment_count"] = complete_count

    if budget_exceeded:
        audit["budget_exceeded"] = True
        audit["work_exhaustion_stage"] = ledger.exhaustion_stage or "dfs_visit"
        reason = "deterministic normalization work budget exceeded"
        return None, FAILURE_SEARCH_BUDGET_EXCEEDED, reason, audit

    if material_proven or len(fingerprint_best) >= 2:
        audit["ambiguity_class"] = "material"
        audit["material_assignment_count"] = len(fingerprint_best)
        if attempt_index > 0:
            return (
                None,
                FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL,
                "material ambiguity after retry",
                audit,
            )
        return (
            None,
            FAILURE_FRAGMENT_AMBIGUOUS,
            "material ambiguity requires semantic retry",
            audit,
        )

    if fingerprint_best:
        fingerprint = next(iter(fingerprint_best))
        chosen, _ = fingerprint_best[fingerprint]
        audit["ambiguity_class"] = "unique" if complete_count == 1 else "equivalent"
        return chosen, "", "", audit

    if partial_exists:
        reason = "substantive source not fully covered"
        audit["failure_reason"] = reason
        return None, FAILURE_SIR_SUBSTANTIVE_OMISSION, reason, audit

    reason = "no non-overlapping placement for excerpts"
    audit["failure_reason"] = reason
    return None, FAILURE_SIR_OVERLAP_CONFLICT, reason, audit


def _resolve_assignment(
    source: str,
    units: list[_SirUnit],
    *,
    attempt_index: int,
) -> tuple[list[tuple[_SirUnit, _Span]] | None, str, str, dict[str, Any]]:
    return _search_and_resolve_assignment(source, units, attempt_index=attempt_index)


def normalize_player_semantic_decomposition(
    *,
    content: str,
    speaker: str,
    semantic_decomposition: dict[str, Any] | None,
    generation: dict[str, Any] | None = None,
    attempt_index: int = 0,
) -> dict[str, Any]:
    normalized_source = normalize_source_for_indexing(content)
    generation_payload = dict(generation or {})
    generation_payload.setdefault("semantic_decomposition", semantic_decomposition)

    units, parse_reason = _parse_sir_units(semantic_decomposition)
    if parse_reason:
        return _failure_result(
            failure_class=FAILURE_SIR_MALFORMED,
            reason=parse_reason,
            attempt_index=attempt_index,
            generation=generation_payload,
            normalization_audit={"version": NORMALIZER_VERSION, "stage": "sir_parse"},
        )

    if not units and normalized_source and any(
        _is_substantive_char(char) for char in normalized_source
    ):
        return _failure_result(
            failure_class=FAILURE_SIR_SUBSTANTIVE_OMISSION,
            reason="no semantic units for substantive source",
            attempt_index=attempt_index,
            generation=generation_payload,
            normalization_audit={"version": NORMALIZER_VERSION, "stage": "completeness"},
        )

    assignment, failure_class, reason, match_audit = _resolve_assignment(
        normalized_source,
        units,
        attempt_index=attempt_index,
    )
    if failure_class or assignment is None:
        return _failure_result(
            failure_class=failure_class or FAILURE_NORMALIZATION_IMPOSSIBLE,
            reason=reason or "normalization failed",
            attempt_index=attempt_index,
            generation=generation_payload,
            normalization_audit=match_audit,
        )

    normalization_audit = {
        **match_audit,
        "assignments": [
            {
                "sir_index": unit.index,
                "char_start": span.start,
                "char_end": span.end,
                "kind": unit.kind,
            }
            for unit, span in sorted(
                assignment,
                key=lambda item: (item[1].start, item[1].end, item[0].index),
            )
        ],
    }
    player_decomposition = _build_player_decomposition(
        normalized_source,
        assignment,
        generation=generation_payload,
        normalization_audit=normalization_audit,
    )

    _, validation_audit = validate_player_perceptual_decomposition(
        content=content,
        speaker=speaker,
        decomposition=player_decomposition,
    )
    if not validation_audit.get("accepted"):
        return _failure_result(
            failure_class=FAILURE_VALIDATION_REJECTED,
            reason=str(validation_audit.get("reason", "") or "validation rejected"),
            attempt_index=attempt_index,
            generation=player_decomposition.get("generation", generation_payload),
            normalization_audit=normalization_audit,
            validation_audit=validation_audit,
            player_decomposition=player_decomposition,
        )

    return {
        "accepted": True,
        "player_decomposition": player_decomposition,
        "failure_class": None,
        "retry_eligible": False,
        "normalization_audit": normalization_audit,
        "validation_audit": validation_audit,
    }


def _failure_result(
    *,
    failure_class: str,
    reason: str,
    attempt_index: int,
    generation: dict[str, Any],
    normalization_audit: dict[str, Any],
    validation_audit: dict[str, Any] | None = None,
    player_decomposition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retry_eligible = failure_class in RETRY_ELIGIBLE_FAILURES
    if failure_class == FAILURE_FRAGMENT_AMBIGUOUS and attempt_index > 0:
        retry_eligible = False
    if failure_class == FAILURE_SEARCH_BUDGET_EXCEEDED and attempt_index > 0:
        retry_eligible = False
    return {
        "accepted": False,
        "player_decomposition": player_decomposition,
        "failure_class": failure_class,
        "reason": reason,
        "retry_eligible": retry_eligible,
        "normalization_audit": normalization_audit,
        "validation_audit": validation_audit,
    }


def build_failure_decomposition(
    *,
    failure_class: str,
    reason: str,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "failure_class": failure_class,
        "reason": reason,
        "generation": dict(generation or {}),
    }
