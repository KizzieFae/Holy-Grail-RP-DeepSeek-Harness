"""Deterministic StorytellerAdvisoryPackage → PromptContribution mapping (#32 S3b).

Packaging maps bounded advisory slices into suggestive manifest lanes without semantic
reranking, authority elevation, or Storyteller regeneration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .contract import AuthorityClass, PromptContribution, SourceKind
from .librarian_packaging_validity import PackagingBindingContext
from .storyteller_contract import (
    NarrativeObservation,
    NarrativePriority,
    NarrativeTension,
    ProgressionOpportunity,
    PROHIBITED_STORYTELLER_FIELDS,
    StorytellerAdvisoryPackage,
    UncertaintyRecord,
    UnresolvedThread,
    validate_storyteller_payload,
)
from .storyteller_packaging_policy import (
    StorytellerPackagingConsumer,
    StorytellerPackagingPolicy,
    policy_for_storyteller_consumer,
)
from .storyteller_packaging_validity import (
    StorytellerPackagingEligibility,
    assess_storyteller_packaging_eligibility,
)

_CATEGORY_SOURCE_KIND: dict[tuple[StorytellerPackagingConsumer, str], SourceKind] = {
    ("director", "narrative_priorities"): "storyteller_narrative_priorities",
    ("director", "active_tensions"): "storyteller_active_tensions",
    ("director", "progression_opportunities"): "storyteller_progression_opportunities",
    ("director", "unresolved_threads"): "storyteller_unresolved_threads",
    ("character", "observations"): "storyteller_thematic_context",
    ("character", "active_tensions"): "storyteller_active_tensions",
    ("character", "progression_opportunities"): "storyteller_progression_hooks",
    ("narrator", "observations"): "storyteller_emphasis_guidance",
    ("narrator", "active_tensions"): "storyteller_emphasis_guidance",
}


@dataclass(frozen=True)
class StorytellerPackagingResult:
    contributions: tuple[PromptContribution, ...]
    eligibility: StorytellerPackagingEligibility
    items_considered: int
    items_mapped: int
    chars_mapped: int
    omitted_reason: str | None = None


def map_storyteller_package_to_contributions(
    package: StorytellerAdvisoryPackage,
    *,
    manifest_id: str,
    consumer_target: StorytellerPackagingConsumer,
    binding: PackagingBindingContext,
    policy: StorytellerPackagingPolicy | None = None,
    character_id: str | None = None,
) -> StorytellerPackagingResult:
    active_policy = policy or policy_for_storyteller_consumer(consumer_target)
    eligibility = assess_storyteller_packaging_eligibility(package, binding)
    if not eligibility.accepted:
        return StorytellerPackagingResult(
            contributions=(),
            eligibility=eligibility,
            items_considered=_count_items(package),
            items_mapped=0,
            chars_mapped=0,
            omitted_reason=eligibility.reason,
        )

    if not _degradation_allowed(package, active_policy):
        return StorytellerPackagingResult(
            contributions=(),
            eligibility=eligibility,
            items_considered=_count_items(package),
            items_mapped=0,
            chars_mapped=0,
            omitted_reason=f"degradation_blocked:{package.degradation.level}",
        )

    candidates = _collect_candidates(
        package,
        consumer_target=consumer_target,
        policy=active_policy,
        character_id=character_id,
    )
    contributions: list[PromptContribution] = []
    chars_used = 0
    priority_index = 0

    for candidate in candidates:
        if len(contributions) >= active_policy.max_entries:
            break
        ok, violations = validate_storyteller_payload({"text": candidate["text"]})
        if not ok:
            continue
        if _contains_prohibited_language(candidate["text"]):
            continue

        content = _format_advisory_content(candidate, package)
        if not content.strip():
            continue
        if chars_used + len(content) > active_policy.max_chars and contributions:
            break
        if chars_used + len(content) > active_policy.max_chars and not contributions:
            content = content[: active_policy.max_chars]

        source_kind = _CATEGORY_SOURCE_KIND.get(
            (consumer_target, candidate["category"]),
            "storyteller_emphasis_guidance",
        )
        contribution_id = (
            f"{manifest_id}-storyteller-{candidate['category']}-{candidate['item_id']}"
        )
        contributions.append(
            PromptContribution(
                contribution_id=contribution_id,
                source_kind=source_kind,
                authority_class="suggestive",
                knowledge_ids=_knowledge_ids_for_item(package, candidate),
                priority=active_policy.base_priority + priority_index,
                content=content,
                provenance=_provenance_for_item(package, candidate, consumer_target, character_id),
            )
        )
        chars_used += len(content)
        priority_index += 1

    if (
        active_policy.include_uncertainty_when_degraded
        and package.degradation.level in {"partial", "degraded"}
        and len(contributions) < active_policy.max_entries
        and package.uncertainty
    ):
        uncertainty = _format_uncertainty_block(package.uncertainty, active_policy)
        if uncertainty and chars_used + len(uncertainty) <= active_policy.max_chars:
            contributions.append(
                PromptContribution(
                    contribution_id=f"{manifest_id}-storyteller-uncertainty",
                    source_kind="storyteller_emphasis_guidance"
                    if consumer_target == "narrator"
                    else "storyteller_active_tensions",
                    authority_class="suggestive",
                    knowledge_ids=(f"storyteller:{package.package_id}:uncertainty",),
                    priority=active_policy.base_priority + priority_index,
                    content=uncertainty,
                    provenance={
                        "package_id": package.package_id,
                        "consumer_target": consumer_target,
                        "advisory_category": "uncertainty",
                        "projection_kind": "storyteller_packaging_mapper",
                        "degradation_level": package.degradation.level,
                        "degradation_mode": package.degradation.mode,
                    },
                )
            )
            chars_used += len(uncertainty)

    return StorytellerPackagingResult(
        contributions=tuple(contributions),
        eligibility=eligibility,
        items_considered=len(candidates),
        items_mapped=len(contributions),
        chars_mapped=chars_used,
    )


def _count_items(package: StorytellerAdvisoryPackage) -> int:
    return (
        len(package.narrative_priorities)
        + len(package.active_tensions)
        + len(package.progression_opportunities)
        + len(package.unresolved_threads)
        + len(package.observations)
    )


def _degradation_allowed(
    package: StorytellerAdvisoryPackage,
    policy: StorytellerPackagingPolicy,
) -> bool:
    if package.degradation.level in {"none", "partial"}:
        return True
    if package.degradation.level == "degraded":
        return policy.allow_degraded
    return False


def _collect_candidates(
    package: StorytellerAdvisoryPackage,
    *,
    consumer_target: StorytellerPackagingConsumer,
    policy: StorytellerPackagingPolicy,
    character_id: str | None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if "narrative_priorities" in policy.allowed_categories:
        for index, item in enumerate(package.narrative_priorities[: policy.max_priorities]):
            items.append(_priority_candidate(item, index))

    if "active_tensions" in policy.allowed_categories:
        for index, item in enumerate(package.active_tensions[: policy.max_tensions]):
            if policy.require_character_scope and not _character_applicable(item, character_id):
                continue
            items.append(_tension_candidate(item, index))

    if "progression_opportunities" in policy.allowed_categories:
        for index, item in enumerate(package.progression_opportunities[: policy.max_opportunities]):
            if policy.require_character_scope and not _character_applicable(item, character_id):
                continue
            items.append(_opportunity_candidate(item, index))

    if "unresolved_threads" in policy.allowed_categories:
        for index, item in enumerate(package.unresolved_threads[: policy.max_threads]):
            items.append(_thread_candidate(item, index))

    if "observations" in policy.allowed_categories:
        for index, item in enumerate(package.observations[: policy.max_observations]):
            if policy.require_character_scope and not _character_applicable(item, character_id):
                continue
            items.append(_observation_candidate(item, index))

    return [item for item in items if item["category"] in policy.allowed_categories]


def _priority_candidate(item: NarrativePriority, index: int) -> dict[str, Any]:
    return {
        "category": "narrative_priorities",
        "item_id": f"priority-{index}",
        "text": f"{item.focus} — {item.why_it_matters}",
        "header": "STORYTELLER NARRATIVE PRIORITY (advisory; attend to, not required):",
        "confidence": item.confidence,
        "evidence_refs": item.evidence_refs,
    }


def _tension_candidate(item: NarrativeTension, index: int) -> dict[str, Any]:
    return {
        "category": "active_tensions",
        "item_id": f"tension-{index}",
        "text": f"{item.label}: {item.interpretive_note}",
        "header": "STORYTELLER ACTIVE TENSION (advisory interpretation):",
        "confidence": "likely",
        "evidence_refs": item.evidence_refs,
        "issue_refs": item.issue_refs,
    }


def _opportunity_candidate(item: ProgressionOpportunity, index: int) -> dict[str, Any]:
    return {
        "category": "progression_opportunities",
        "item_id": f"opportunity-{index}",
        "text": f"{item.opportunity_label} — {item.narrative_hook}",
        "header": "STORYTELLER PROGRESSION OPPORTUNITY (possibility, not mandate):",
        "confidence": item.confidence,
        "evidence_refs": item.evidence_refs,
    }


def _thread_candidate(item: UnresolvedThread, index: int) -> dict[str, Any]:
    return {
        "category": "unresolved_threads",
        "item_id": f"thread-{index}",
        "text": f"{item.thread_label} — neglect risk: {item.neglect_risk}",
        "header": "STORYTELLER UNRESOLVED THREAD (orchestration-relevant advisory):",
        "confidence": "likely",
        "evidence_refs": item.evidence_refs,
    }


def _observation_candidate(item: NarrativeObservation, index: int) -> dict[str, Any]:
    return {
        "category": "observations",
        "item_id": f"observation-{index}",
        "text": item.text,
        "header": "STORYTELLER THEMATIC CONTEXT (advisory interpretation):",
        "confidence": item.confidence,
        "evidence_refs": item.evidence_refs,
    }


def _character_applicable(item: Any, character_id: str | None) -> bool:
    if not character_id:
        return False
    needle = character_id.strip().lower()
    if not needle:
        return False
    haystacks: list[str] = []
    for attr in ("text", "focus", "why_it_matters", "label", "interpretive_note", "opportunity_label", "narrative_hook"):
        value = getattr(item, attr, None)
        if value:
            haystacks.append(str(value).lower())
    for ref in getattr(item, "evidence_refs", ()) or ():
        for part in (ref.display_hint, ref.stable_ref):
            if part:
                haystacks.append(str(part).lower())
    for issue_ref in getattr(item, "issue_refs", ()) or ():
        haystacks.append(str(issue_ref).lower())
    return any(needle in hay for hay in haystacks)


def _contains_prohibited_language(text: str) -> bool:
    lowered = text.lower()
    for token in (
        "next_actor",
        "must act",
        "must say",
        "must do",
        "mandated beat",
        "required action",
        "structured_move",
    ):
        if token in lowered:
            return True
    for field in PROHIBITED_STORYTELLER_FIELDS:
        if re.search(rf"\b{re.escape(field)}\b", lowered):
            return True
    return False


def _format_advisory_content(candidate: dict[str, Any], package: StorytellerAdvisoryPackage) -> str:
    lines = [str(candidate["header"]), str(candidate["text"]).strip()]
    confidence = candidate.get("confidence")
    if confidence:
        lines.append(f"Confidence: {confidence}")
    refs = candidate.get("evidence_refs") or ()
    if refs:
        ref_labels = [
            str(ref.display_hint or ref.stable_ref).strip()
            for ref in refs
            if str(ref.display_hint or ref.stable_ref).strip()
        ]
        if ref_labels:
            lines.append("Evidence refs: " + ", ".join(ref_labels[:4]))
    if package.degradation.level != "none":
        lines.append(
            f"Storyteller degradation: {package.degradation.level} ({package.degradation.mode})."
        )
    return "\n".join(line for line in lines if line).strip()


def _format_uncertainty_block(
    records: tuple[UncertaintyRecord, ...],
    policy: StorytellerPackagingPolicy,
) -> str:
    lines = ["STORYTELLER UNCERTAINTY (advisory; not authoritative):"]
    for record in records[:2]:
        lines.append(f"- {record.topic}: {record.reason}")
    return "\n".join(lines).strip()


def _knowledge_ids_for_item(
    package: StorytellerAdvisoryPackage,
    candidate: dict[str, Any],
) -> tuple[str, ...]:
    ids = [f"storyteller:{package.package_id}:{candidate['item_id']}"]
    bundle_id = str(package.bundle_refs.primary_bundle_id or "").strip()
    if bundle_id:
        ids.append(f"librarian:{bundle_id}")
    for ref in candidate.get("evidence_refs") or ():
        stable = str(ref.stable_ref or "").strip()
        if stable:
            ids.append(stable)
    return tuple(dict.fromkeys(ids))


def _provenance_for_item(
    package: StorytellerAdvisoryPackage,
    candidate: dict[str, Any],
    consumer_target: StorytellerPackagingConsumer,
    character_id: str | None,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "package_id": package.package_id,
        "assessment_id": package.assessment_id,
        "orientation_id": package.orientation_id,
        "bundle_id": package.bundle_refs.primary_bundle_id,
        "bundle_request_id": package.bundle_refs.primary_request_id,
        "consumer_target": consumer_target,
        "advisory_category": candidate["category"],
        "binding_level": "advisory",
        "authority_class": "suggestive",
        "projection_kind": "storyteller_packaging_mapper",
        "degradation_level": package.degradation.level,
        "degradation_mode": package.degradation.mode,
        "validity_scope": package.validity.validity_scope,
        "valid_from_authoritative_snapshot_id": package.validity.valid_from_authoritative_snapshot_id,
    }
    if character_id:
        provenance["character_id"] = character_id
    inference_ids = list(package.audit.inference_ids or ())
    if inference_ids:
        provenance["storyteller_inference_ids"] = inference_ids
    evidence_refs = [
        {
            "ref_kind": ref.ref_kind,
            "stable_ref": ref.stable_ref,
            "display_hint": ref.display_hint,
        }
        for ref in candidate.get("evidence_refs") or ()
    ]
    if evidence_refs:
        provenance["evidence_refs"] = evidence_refs
    return provenance
