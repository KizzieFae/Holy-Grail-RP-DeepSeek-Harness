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

NORMALIZER_VERSION = 1
PLAYER_UNIT_SOURCE = "player_decomposition"

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
FAILURE_VALIDATION_REJECTED = "validation_rejected"

RETRY_ELIGIBLE_FAILURES = frozenset(
    {
        FAILURE_SIR_MALFORMED,
        FAILURE_SIR_INVALID_SEMANTICS,
        FAILURE_SIR_NON_VERBATIM,
        FAILURE_SIR_SUBSTANTIVE_OMISSION,
        FAILURE_SIR_OVERLAP_CONFLICT,
        FAILURE_FRAGMENT_AMBIGUOUS,
        FAILURE_VALIDATION_REJECTED,
    }
)


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


def _find_occurrences(source: str, text: str) -> list[_Span]:
    if not text:
        return []
    spans: list[_Span] = []
    start = 0
    while True:
        index = source.find(text, start)
        if index < 0:
            break
        spans.append(_Span(index, index + len(text)))
        start = index + 1
    return spans


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


def _search_assignments(
    source: str,
    units: list[_SirUnit],
) -> tuple[list[list[tuple[_SirUnit, _Span]]], str, str]:
    if not units:
        if any(_is_substantive_char(char) for char in source):
            return [], FAILURE_SIR_SUBSTANTIVE_OMISSION, "empty units with substantive source"
        return [[]], "", ""

    candidates: list[list[_Span]] = []
    for unit in units:
        occurrences = _find_occurrences(source, unit.text)
        if not occurrences:
            return [], FAILURE_SIR_NON_VERBATIM, f"unit {unit.index} excerpt not found in source"
        candidates.append(occurrences)

    order = sorted(range(len(units)), key=lambda idx: len(candidates[idx]))
    complete: list[list[tuple[_SirUnit, _Span]]] = []
    partial_exists = False

    def visit(position: int, chosen: list[tuple[_SirUnit, _Span]], occupied: list[_Span]) -> None:
        nonlocal partial_exists
        if position >= len(order):
            spans = [span for _, span in chosen]
            if _substantive_complete(source, spans):
                complete.append(list(chosen))
            else:
                partial_exists = True
            return

        unit_index = order[position]
        unit = units[unit_index]
        for span in candidates[unit_index]:
            if any(span.overlaps(existing) for existing in occupied):
                partial_exists = True
                continue
            chosen.append((unit, span))
            occupied.append(span)
            visit(position + 1, chosen, occupied)
            occupied.pop()
            chosen.pop()

    visit(0, [], [])

    if complete:
        return complete, "", ""
    if partial_exists:
        return [], FAILURE_SIR_SUBSTANTIVE_OMISSION, "substantive source not fully covered"
    return [], FAILURE_SIR_OVERLAP_CONFLICT, "no non-overlapping placement for excerpts"


def _resolve_assignment(
    source: str,
    units: list[_SirUnit],
    *,
    attempt_index: int,
) -> tuple[list[tuple[_SirUnit, _Span]] | None, str, str, dict[str, Any]]:
    assignments, failure_class, reason = _search_assignments(source, units)
    audit: dict[str, Any] = {
        "version": NORMALIZER_VERSION,
        "assignment_count": len(assignments),
    }
    if failure_class:
        audit["failure_reason"] = reason
        return None, failure_class, reason, audit

    if not assignments:
        return None, FAILURE_NORMALIZATION_IMPOSSIBLE, "no assignments", audit

    fingerprints: dict[tuple[Any, ...], list[tuple[list[tuple[_SirUnit, _Span]], tuple[Any, ...]]]] = {}
    for assignment in assignments:
        fingerprint = _canonical_semantic_fingerprint(source, assignment)
        fingerprints.setdefault(fingerprint, []).append((assignment, _assignment_key(assignment)))

    unique_fingerprints = list(fingerprints.keys())
    if len(unique_fingerprints) == 1:
        candidates = fingerprints[unique_fingerprints[0]]
        chosen = min(candidates, key=lambda item: item[1])[0]
        audit["ambiguity_class"] = "unique" if len(candidates) == 1 else "equivalent"
        return chosen, "", "", audit

    audit["ambiguity_class"] = "material"
    audit["material_assignment_count"] = len(unique_fingerprints)
    if attempt_index > 0:
        return None, FAILURE_FRAGMENT_AMBIGUOUS_TERMINAL, "material ambiguity after retry", audit
    return None, FAILURE_FRAGMENT_AMBIGUOUS, "material ambiguity requires semantic retry", audit


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
