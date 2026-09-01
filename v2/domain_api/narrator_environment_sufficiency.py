"""Post-mediation sufficiency reconciliation and presentation obligations (#89).

Separates Librarian retrieval relevance (``match``) from render sufficiency.
Environmental cognition owns semantic sufficiency; Host retains structural B2 gates.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from domain_api.narrator_environment_authority import mediation_blocks_invention
from domain_api.narrator_environment_contract import (
    EnvironmentalCurrentView,
    EnvironmentalResponseObligation,
    EnvironmentalResponseSufficiency,
    NarratorEnvironmentN1Result,
    NarratorEnvironmentResolution,
    NarratorInformationNeed,
)

SufficiencyState = Literal["sufficient", "insufficient", "failure", "forbidden", "unresolved"]

_SAFE_MEDIATION_FOR_ESTABLISHMENT = frozenset({"match", "no_match"})


def _librarian_outcome_for_need(
    need_id: str | None,
    librarian_outcomes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not need_id:
        return None
    for outcome in librarian_outcomes:
        if outcome.get("need_id") == need_id:
            return outcome
    return None


def extract_composed_grounding_from_librarian(
    librarian_outcome: dict[str, Any] | None,
) -> str:
    if not librarian_outcome:
        return ""
    parts: list[str] = []
    for key in (
        "composed_grounding",
        "synthesis",
        "matched_detail",
        "grounded_summary",
        "rationale",
    ):
        text = str(librarian_outcome.get(key) or "").strip()
        if text:
            parts.append(text)
    for entry in list(librarian_outcome.get("entries") or []):
        if not isinstance(entry, dict):
            continue
        content = str(entry.get("content") or entry.get("text") or "").strip()
        if content:
            parts.append(content)
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part not in seen:
            seen.add(part)
            deduped.append(part)
    return "; ".join(deduped)


def _resolution_raw_for_need(
    need_id: str | None,
    n2_raw_items: list[dict[str, Any]],
) -> dict[str, Any]:
    for item in n2_raw_items:
        if item.get("need_id") == need_id:
            return item
    return {}


def _infer_response_sufficient(
    *,
    resolution: NarratorEnvironmentResolution,
    raw: dict[str, Any],
    mediation_outcome: str | None,
    composed_grounding: str,
) -> bool:
    if "response_sufficient" in raw:
        return bool(raw.get("response_sufficient"))
    if raw.get("insufficient_for_render") is True:
        return False
    if raw.get("insufficient_for_render") is False:
        return True
    if resolution.category == "A":
        return True
    if resolution.category == "B1":
        return True
    if resolution.category == "B2":
        return False
    if resolution.category == "cannot_safely_resolve":
        if mediation_outcome == "match" and composed_grounding:
            return False
        return False
    return bool(composed_grounding)


def _sufficiency_state(
    *,
    response_sufficient: bool,
    mediation_outcome: str | None,
    category: str,
) -> SufficiencyState:
    if mediation_outcome == "forbidden":
        return "forbidden"
    if mediation_blocks_invention(mediation_outcome):
        return "failure"
    if response_sufficient:
        return "sufficient"
    if category == "cannot_safely_resolve":
        return "unresolved"
    return "insufficient"


def _render_behavior_for_state(
    *,
    sufficiency_state: SufficiencyState,
    response_sufficient: bool,
    category: str,
) -> Literal["communicate_grounded", "bounded_refusal", "no_material_obligation"]:
    if sufficiency_state in {"failure", "forbidden", "unresolved"}:
        return "bounded_refusal"
    if response_sufficient or category in {"A", "B1"}:
        return "communicate_grounded"
    if category == "B2":
        return "communicate_grounded"
    return "bounded_refusal"


def reconcile_post_mediation_environmental_resolutions(
    *,
    n1: NarratorEnvironmentN1Result,
    resolutions: list[NarratorEnvironmentResolution],
    librarian_outcomes: list[dict[str, Any]] | None,
    n2_raw_items: list[dict[str, Any]],
    current_view: EnvironmentalCurrentView,
) -> tuple[
    list[NarratorEnvironmentResolution],
    list[EnvironmentalResponseSufficiency],
    list[EnvironmentalResponseObligation],
]:
    librarian_outcomes = list(librarian_outcomes or [])
    by_need: dict[str | None, NarratorEnvironmentResolution] = {
        res.need_id: res for res in resolutions
    }
    reconciled: list[NarratorEnvironmentResolution] = []
    sufficiency_records: list[EnvironmentalResponseSufficiency] = []
    obligations: list[EnvironmentalResponseObligation] = []

    if n1.baseline_sufficient and not n1.information_needs:
        obligations.append(
            EnvironmentalResponseObligation(
                obligation_id=f"env-obl-baseline-{uuid.uuid4().hex[:8]}",
                need_id=None,
                rendering_question="",
                render_behavior="no_material_obligation",
                grounded_material=(),
                resolution_category="A",
                response_sufficient=True,
                mediation_outcome=None,
                sufficiency_state="sufficient",
            )
        )
        return list(resolutions), sufficiency_records, obligations

    for need in n1.information_needs:
        resolution = by_need.get(need.need_id)
        if resolution is None:
            resolution = NarratorEnvironmentResolution(
                need_id=need.need_id,
                category="cannot_safely_resolve",
                detail="No N2 resolution provided for information need",
            )
        raw = _resolution_raw_for_need(need.need_id, n2_raw_items)
        lib = _librarian_outcome_for_need(need.need_id, librarian_outcomes)
        mediation = None
        if lib is not None:
            mediation = lib.get("mediation_outcome")
        if mediation is None:
            mediation = resolution.mediation_outcome
        resolution.mediation_outcome = mediation  # type: ignore[assignment]

        composed = extract_composed_grounding_from_librarian(lib)
        if not composed:
            composed = str(resolution.detail or "").strip()
        if not composed:
            for desc in current_view.effective_descriptors.values():
                composed = f"{desc.property_key}: {desc.value}"
                break

        response_sufficient = _infer_response_sufficient(
            resolution=resolution,
            raw=raw,
            mediation_outcome=mediation,
            composed_grounding=composed,
        )

        if mediation_blocks_invention(mediation):
            resolution.category = "cannot_safely_resolve"
            if not resolution.detail:
                resolution.detail = f"Blocked by mediation outcome: {mediation}"
            sufficiency_state: SufficiencyState = "failure"
            sufficiency_records.append(
                EnvironmentalResponseSufficiency(
                    need_id=need.need_id,
                    response_sufficient=False,
                    mediation_outcome=mediation,  # type: ignore[arg-type]
                    composed_grounding=composed,
                    sufficiency_state=sufficiency_state,
                    reconciliation_notes="mediation_failure_blocks_origination",
                )
            )
            obligations.append(
                EnvironmentalResponseObligation(
                    obligation_id=f"env-obl-{need.need_id}-{uuid.uuid4().hex[:8]}",
                    need_id=need.need_id,
                    rendering_question=need.question,
                    render_behavior="bounded_refusal",
                    grounded_material=(composed,) if composed else (),
                    resolution_category="cannot_safely_resolve",
                    response_sufficient=False,
                    mediation_outcome=mediation,  # type: ignore[arg-type]
                    sufficiency_state=sufficiency_state,
                    refusal_reason=f"mediation_{mediation}",
                )
            )
            reconciled.append(resolution)
            continue

        if mediation == "forbidden":
            resolution.category = "cannot_safely_resolve"
            sufficiency_state = "forbidden"
        elif response_sufficient:
            if mediation == "match" or resolution.category in {"A", "B1", "cannot_safely_resolve"}:
                resolution.category = "A"
            if composed:
                resolution.detail = composed
            sufficiency_state = "sufficient"
        elif resolution.category == "B2" and mediation in _SAFE_MEDIATION_FOR_ESTABLISHMENT:
            sufficiency_state = "insufficient"
        elif resolution.category == "cannot_safely_resolve" and mediation == "match" and composed:
            sufficiency_state = "unresolved"
        else:
            sufficiency_state = _sufficiency_state(
                response_sufficient=response_sufficient,
                mediation_outcome=mediation,
                category=resolution.category,
            )

        sufficiency_records.append(
            EnvironmentalResponseSufficiency(
                need_id=need.need_id,
                response_sufficient=response_sufficient,
                mediation_outcome=mediation,  # type: ignore[arg-type]
                composed_grounding=composed,
                sufficiency_state=sufficiency_state,
                reconciliation_notes=str(raw.get("reasoning_summary") or ""),
            )
        )

        render_behavior = _render_behavior_for_state(
            sufficiency_state=sufficiency_state,
            response_sufficient=response_sufficient,
            category=resolution.category,
        )
        grounded_material = tuple(
            item for item in (composed, str(resolution.detail or "").strip()) if item
        )
        obligations.append(
            EnvironmentalResponseObligation(
                obligation_id=f"env-obl-{need.need_id}-{uuid.uuid4().hex[:8]}",
                need_id=need.need_id,
                rendering_question=need.question,
                render_behavior=render_behavior,
                grounded_material=grounded_material,
                resolution_category=resolution.category,
                response_sufficient=response_sufficient,
                mediation_outcome=mediation,  # type: ignore[arg-type]
                sufficiency_state=sufficiency_state,
                established_b2_property_key=resolution.property_key,
                established_b2_value=resolution.value,
                refusal_reason=(
                    resolution.detail
                    if render_behavior == "bounded_refusal"
                    else None
                ),
            )
        )
        reconciled.append(resolution)

    if not reconciled:
        reconciled = list(resolutions)
    return reconciled, sufficiency_records, obligations


def refresh_obligations_after_b2(
    obligations: list[EnvironmentalResponseObligation],
    *,
    resolutions: list[NarratorEnvironmentResolution],
    establishment_decisions: list[dict[str, Any]],
) -> list[EnvironmentalResponseObligation]:
    accepted_by_need: dict[str | None, dict[str, Any]] = {}
    for decision in establishment_decisions:
        if not decision.get("accepted"):
            continue
        need_id = decision.get("resolution_need_id")
        if need_id is None:
            proposal = (decision.get("authority_decision") or {}).get("narrator_proposal") or {}
            need_id = proposal.get("need_id")
        accepted_by_need[need_id] = decision

    refreshed: list[EnvironmentalResponseObligation] = []
    for obligation in obligations:
        if obligation.render_behavior != "communicate_grounded":
            refreshed.append(obligation)
            continue
        decision = accepted_by_need.get(obligation.need_id)
        resolution = next(
            (item for item in resolutions if item.need_id == obligation.need_id),
            None,
        )
        if decision and resolution and resolution.category == "B2":
            material = list(obligation.grounded_material)
            if resolution.property_key and resolution.value:
                material.append(f"{resolution.property_key}: {resolution.value}")
            refreshed.append(
                EnvironmentalResponseObligation(
                    obligation_id=obligation.obligation_id,
                    need_id=obligation.need_id,
                    rendering_question=obligation.rendering_question,
                    render_behavior="communicate_grounded",
                    grounded_material=tuple(dict.fromkeys(material)),
                    resolution_category="B2",
                    response_sufficient=True,
                    mediation_outcome=obligation.mediation_outcome,
                    sufficiency_state="sufficient",
                    established_b2_property_key=resolution.property_key,
                    established_b2_value=resolution.value,
                )
            )
            continue
        if (
            obligation.sufficiency_state == "insufficient"
            and resolution
            and resolution.category == "B2"
            and not decision
        ):
            refreshed.append(
                EnvironmentalResponseObligation(
                    obligation_id=obligation.obligation_id,
                    need_id=obligation.need_id,
                    rendering_question=obligation.rendering_question,
                    render_behavior="bounded_refusal",
                    grounded_material=obligation.grounded_material,
                    resolution_category=resolution.category,
                    response_sufficient=False,
                    mediation_outcome=obligation.mediation_outcome,
                    sufficiency_state="unresolved",
                    established_b2_property_key=resolution.property_key,
                    established_b2_value=resolution.value,
                    refusal_reason="b2_establishment_not_accepted",
                )
            )
            continue
        refreshed.append(obligation)
    return refreshed


def format_environmental_response_obligations(
    obligations: list[EnvironmentalResponseObligation],
) -> str:
    if not obligations:
        return ""
    lines = [
        "ENVIRONMENTAL RESPONSE OBLIGATIONS (resolved cognition — authoritative for this turn):",
    ]
    for item in obligations:
        lines.append(f"- obligation_id: {item.obligation_id}")
        if item.rendering_question:
            lines.append(f"  question: {item.rendering_question}")
        lines.append(f"  render_behavior: {item.render_behavior}")
        lines.append(f"  sufficiency_state: {item.sufficiency_state}")
        lines.append(f"  response_sufficient: {item.response_sufficient}")
        if item.mediation_outcome:
            lines.append(f"  mediation_outcome: {item.mediation_outcome}")
        lines.append(f"  resolution_category: {item.resolution_category}")
        if item.grounded_material:
            lines.append("  grounded_material:")
            for material in item.grounded_material:
                lines.append(f"    - {material}")
        if item.established_b2_property_key and item.established_b2_value:
            lines.append(
                "  host_accepted_detail: "
                f"{item.established_b2_property_key}={item.established_b2_value}"
            )
        if item.refusal_reason and item.render_behavior == "bounded_refusal":
            lines.append(f"  refusal_reason: {item.refusal_reason}")
    lines.append(
        "Render communicate_grounded obligations concretely in narration. "
        "Do not substitute inferred purpose for requested observable detail when grounded_material "
        "or host_accepted_detail answers the question. "
        "For bounded_refusal, omit unsupported detail without inventing."
    )
    return "\n".join(lines)
