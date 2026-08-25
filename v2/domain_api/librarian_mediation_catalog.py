"""Build bounded mediation catalogs for DSH Librarian inference (#34 S2a)."""

from __future__ import annotations

from dataclasses import dataclass

from .librarian_authoritative_input import AuthoritativeWorkingItem
from .librarian_contract import MediationCatalogItem
from .librarian_mediation import MediationCandidate
from .retrieval_contract import RetrievalCandidate


@dataclass(frozen=True)
class MediationWorkingSet:
    catalog: dict[str, MediationCatalogItem]
    mediation_items: list[MediationCandidate]
    candidate_ids: tuple[str, ...]


def _catalog_id_for_candidate(candidate: RetrievalCandidate) -> str:
    return f"lmi:cand:{candidate.candidate_id}"


def _catalog_id_for_authoritative(item: AuthoritativeWorkingItem, index: int) -> str:
    kind = item.contribution.source_kind
    primary = item.contribution.knowledge_ids[0] if item.contribution.knowledge_ids else str(index)
    safe = str(primary).replace(":", "_")
    return f"lmi:auth:{kind}:{safe}"


def build_mediation_working_set(
    authoritative_items: list[AuthoritativeWorkingItem],
    retrieval_candidates: list[RetrievalCandidate],
) -> MediationWorkingSet:
    catalog: dict[str, MediationCatalogItem] = {}
    mediation_items: list[MediationCandidate] = []

    for index, item in enumerate(authoritative_items):
        source_id = _catalog_id_for_authoritative(item, index)
        contribution = item.contribution
        catalog[source_id] = MediationCatalogItem(
            source_id=source_id,
            source_kind=contribution.source_kind,
            stable_ref=str(contribution.knowledge_ids[0] if contribution.knowledge_ids else source_id),
            content=contribution.content,
            information_class=(
                "authored_static"
                if contribution.source_kind == "scene_setup"
                else "authoritative_live"
            ),
            authority_class="authoritative",
            visibility_scope=str(contribution.provenance.get("visibility", "scene_orchestration")),
            source_tier=item.source_tier,
            provenance=dict(contribution.provenance),
            temporal_relationship=item.temporal_relationship,
        )
        mediation_items.append(
            MediationCandidate(
                candidate=None,
                authoritative_item=item,
                source_kind=contribution.source_kind,
            )
        )

    candidate_ids: list[str] = []
    for candidate in retrieval_candidates:
        source_id = _catalog_id_for_candidate(candidate)
        candidate_ids.append(candidate.candidate_id)
        catalog[source_id] = MediationCatalogItem(
            source_id=source_id,
            source_kind="retrieval_candidate",
            stable_ref=candidate.candidate_id,
            content=candidate.payload.content,
            information_class=str(candidate.information_class),
            authority_class=candidate.authority_class,
            visibility_scope=str(candidate.visibility or "public"),
            source_tier="retrieval_candidate",
            provenance=dict(candidate.provenance),
            temporal_relationship=(
                "timeless_authored"
                if candidate.information_class in {"authored_static", "compiled_index"}
                else "recent"
            ),
        )
        mediation_items.append(
            MediationCandidate(
                candidate=candidate,
                authoritative_item=None,
                source_kind="retrieval_candidate",
            )
        )

    return MediationWorkingSet(
        catalog=catalog,
        mediation_items=mediation_items,
        candidate_ids=tuple(candidate_ids),
    )


def catalog_item_for_source_id(
    working_set: MediationWorkingSet,
    source_id: str,
) -> MediationCatalogItem | None:
    return working_set.catalog.get(source_id)
