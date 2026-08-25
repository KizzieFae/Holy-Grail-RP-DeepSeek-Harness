"""Deterministic LibrarianKnowledgeBundle → PromptContribution mapping (#34 S2b).

Packaging maps bounded bundle slices into existing manifest lanes without semantic
reranking, authority elevation, or Librarian/Retrieval invocation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contract import AuthorityClass, PromptContribution, SourceKind
from .librarian_contract import LibrarianBundleEntry, LibrarianKnowledgeBundle, MediationMode
from .librarian_packaging_policy import (
    PROJECTION_DUPLICATE_SOURCE_TIERS,
    LibrarianPackagingPolicy,
    PackagingConsumerTarget,
    policy_for_consumer,
)
from .librarian_packaging_validity import (
    PackagingBindingContext,
    PackagingEligibility,
    assess_bundle_packaging_eligibility,
)


@dataclass(frozen=True)
class LibrarianPackagingResult:
    contributions: tuple[PromptContribution, ...]
    eligibility: PackagingEligibility
    entries_considered: int
    entries_mapped: int
    chars_mapped: int
    omitted_reason: str | None = None


def map_librarian_bundle_to_contributions(
    bundle: LibrarianKnowledgeBundle,
    *,
    manifest_id: str,
    consumer_target: PackagingConsumerTarget,
    binding: PackagingBindingContext,
    policy: LibrarianPackagingPolicy | None = None,
) -> LibrarianPackagingResult:
    active_policy = policy or policy_for_consumer(consumer_target)
    eligibility = assess_bundle_packaging_eligibility(bundle, binding)
    if not eligibility.accepted:
        return LibrarianPackagingResult(
            contributions=(),
            eligibility=eligibility,
            entries_considered=len(bundle.entries),
            entries_mapped=0,
            chars_mapped=0,
            omitted_reason=eligibility.reason,
        )

    if not _mediation_mode_allowed(bundle.mediation_mode, active_policy):
        return LibrarianPackagingResult(
            contributions=(),
            eligibility=eligibility,
            entries_considered=len(bundle.entries),
            entries_mapped=0,
            chars_mapped=0,
            omitted_reason=f"mediation_mode_blocked:{bundle.mediation_mode}",
        )

    filtered = _filter_entries_for_policy(bundle.entries, active_policy)
    contributions: list[PromptContribution] = []
    chars_used = 0
    for index, entry in enumerate(filtered):
        if len(contributions) >= active_policy.max_entries:
            break
        content = _format_entry_content(entry, bundle)
        if not content.strip():
            continue
        if chars_used + len(content) > active_policy.max_chars and contributions:
            break
        if chars_used + len(content) > active_policy.max_chars and not contributions:
            content = content[: active_policy.max_chars]
        chars_used += len(content)
        contributions.append(
            _entry_to_contribution(
                entry,
                bundle=bundle,
                manifest_id=manifest_id,
                consumer_target=consumer_target,
                priority=active_policy.base_priority + index,
                content=content,
            )
        )

    return LibrarianPackagingResult(
        contributions=tuple(contributions),
        eligibility=eligibility,
        entries_considered=len(bundle.entries),
        entries_mapped=len(contributions),
        chars_mapped=chars_used,
    )


def _mediation_mode_allowed(mode: MediationMode, policy: LibrarianPackagingPolicy) -> bool:
    if mode == "deterministic_fallback" and not policy.allow_deterministic_fallback:
        return False
    return True


def _filter_entries_for_policy(
    entries: tuple[LibrarianBundleEntry, ...],
    policy: LibrarianPackagingPolicy,
) -> tuple[LibrarianBundleEntry, ...]:
    kept: list[LibrarianBundleEntry] = []
    for entry in entries:
        if entry.synthesis_meta is not None and not policy.allow_synthesis:
            continue
        if entry.authority_class not in policy.allowed_authority_classes:
            continue
        if (
            policy.allowed_information_classes is not None
            and str(entry.information_class) not in policy.allowed_information_classes
        ):
            continue
        visibility = str(entry.visibility_scope or "")
        if visibility and visibility not in policy.allowed_visibility_scopes:
            continue
        if policy.skip_projection_duplicate_tiers and str(entry.source_tier) in PROJECTION_DUPLICATE_SOURCE_TIERS:
            continue
        kept.append(entry)
    return tuple(kept)


def _format_entry_content(entry: LibrarianBundleEntry, bundle: LibrarianKnowledgeBundle) -> str:
    if entry.synthesis_meta is not None:
        header = "LIBRARIAN SYNTHESIS (suggestive cross-source interpretation; not settled fact):"
    else:
        header = "LIBRARIAN KNOWLEDGE (mediated source material; authority class preserved in provenance):"
    lines = [header, entry.content.strip()]
    annotation = entry.librarian_annotation
    if annotation.salience_note:
        lines.append(f"Salience note: {annotation.salience_note}")
    if bundle.mediation_mode == "deterministic_fallback":
        lines.append("Degradation: deterministic_fallback mediation (degraded semantic path).")
    elif bundle.degradation.deterministic_fallback_used:
        lines.append("Degradation: deterministic fallback was used during bundle construction.")
    return "\n".join(line for line in lines if line).strip()


def _entry_to_contribution(
    entry: LibrarianBundleEntry,
    *,
    bundle: LibrarianKnowledgeBundle,
    manifest_id: str,
    consumer_target: PackagingConsumerTarget,
    priority: int,
    content: str,
) -> PromptContribution:
    source_kind: SourceKind
    if entry.synthesis_meta is not None:
        source_kind = "librarian_synthesis"
        authority: AuthorityClass = "suggestive"
    else:
        source_kind = "librarian_knowledge"
        authority = entry.authority_class

    knowledge_ids = _knowledge_ids_for_entry(entry, bundle)
    provenance = {
        "bundle_id": bundle.bundle_id,
        "bundle_request_id": bundle.request_id,
        "entry_id": entry.entry_id,
        "consumer_target": consumer_target,
        "mediation_mode": bundle.mediation_mode,
        "degradation_mode": bundle.degradation.mode,
        "degradation_level": bundle.degradation.level,
        "deterministic_fallback_used": bundle.degradation.deterministic_fallback_used,
        "information_class": str(entry.information_class),
        "source_tier": str(entry.source_tier),
        "visibility_scope": str(entry.visibility_scope),
        "ref_kind": entry.ref.ref_kind,
        "stable_ref": entry.ref.stable_ref,
        "projection_kind": "librarian_packaging_mapper",
        **dict(entry.provenance or {}),
    }
    if entry.synthesis_meta is not None:
        provenance["synthesis_kind"] = entry.synthesis_meta.synthesis_kind
        provenance["synthesis_source_refs"] = [
            ref.stable_ref for ref in entry.synthesis_meta.source_entry_refs
        ]
        provenance["synthesis_authority"] = entry.synthesis_meta.synthesis_authority

    contribution_id = f"{manifest_id}-librarian-{entry.entry_id}"
    return PromptContribution(
        contribution_id=contribution_id,
        source_kind=source_kind,
        authority_class=authority,
        knowledge_ids=knowledge_ids,
        priority=priority,
        content=content,
        provenance=provenance,
    )


def _knowledge_ids_for_entry(
    entry: LibrarianBundleEntry,
    bundle: LibrarianKnowledgeBundle,
) -> tuple[str, ...]:
    ids: list[str] = [f"librarian:{bundle.bundle_id}:{entry.entry_id}"]
    stable_ref = str(entry.ref.stable_ref or "").strip()
    if stable_ref:
        ids.append(stable_ref)
    if entry.synthesis_meta is not None:
        for ref in entry.synthesis_meta.source_entry_refs:
            value = str(ref.stable_ref or "").strip()
            if value:
                ids.append(value)
    return tuple(dict.fromkeys(ids))
