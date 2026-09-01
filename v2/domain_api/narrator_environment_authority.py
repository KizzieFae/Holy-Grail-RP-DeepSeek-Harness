"""Host deterministic authority for Narrator-proposed B2 environmental descriptors (#49).

Narrator N2 may *propose* continuity-bearing environmental detail; Host validation
(established pattern: deterministic rules, not LLM) is the repository-native acceptance
seam before #50 persistence. Mirrors Host validation in librarian proposal batches.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from domain_api.narrator_environment_contract import EnvironmentalCurrentView
from domain_api.story_knowledge_contract import EpistemicAuthorityRef


def validate_b2_proposal(
    *,
    property_key: str,
    value: str,
    stable_refs: tuple[str, ...],
) -> tuple[bool, str]:
    key = str(property_key or "").strip()
    val = str(value or "").strip()
    if not key:
        return False, "property_key required"
    if not val:
        return False, "value required"
    if not stable_refs:
        return False, "stable_refs required for continuity-bearing environmental detail"
    return True, ""


def mediation_allows_bounded_composition(outcome: str | None) -> bool:
    """Safe mediation states that may accompany bounded B2 when cognition finds insufficiency."""
    return outcome in {"match", "no_match"}


def mediation_blocks_invention(outcome: str | None) -> bool:
    return outcome in {
        "ambiguous",
        "forbidden",
        "retrieval_failure",
        "mediation_failure",
        None,
    }


@dataclass(frozen=True)
class NarratorEnvironmentalB2Proposal:
    """Narrator N2 proposal — not authoritative until Host accepts."""

    cognition_id: str
    need_id: str | None
    property_key: str
    value: str
    stable_refs: tuple[str, ...]
    mediation_outcome: str | None
    detail: str = ""
    supersedes: str | None = None


@dataclass(frozen=True)
class EnvironmentalB2EstablishmentDecision:
    """Durable Host establishment decision — distinct from Narrator proposal."""

    decision_id: str
    authorized: bool
    authority_kind: str = "host_environmental_b2_validation"
    reason_code: str = ""
    reason_detail: str = ""
    proposal: NarratorEnvironmentalB2Proposal | None = None

    def to_audit_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "decision_id": self.decision_id,
            "authorized": self.authorized,
            "authority_kind": self.authority_kind,
            "reason_code": self.reason_code,
            "reason_detail": self.reason_detail,
        }
        if self.proposal is not None:
            payload["narrator_proposal"] = {
                "cognition_id": self.proposal.cognition_id,
                "need_id": self.proposal.need_id,
                "property_key": self.proposal.property_key,
                "value": self.proposal.value,
                "stable_refs": list(self.proposal.stable_refs),
                "mediation_outcome": self.proposal.mediation_outcome,
                "detail": self.proposal.detail,
                "supersedes": self.proposal.supersedes,
            }
        return payload


def new_establishment_decision_id(
    *,
    cognition_id: str,
    need_id: str | None,
    property_key: str,
) -> str:
    suffix = uuid.uuid4().hex[:10]
    need = need_id or "direct"
    return f"host-env-b2-{cognition_id}-{need}-{property_key}-{suffix}"


def evaluate_host_environmental_b2_establishment(
    proposal: NarratorEnvironmentalB2Proposal,
    *,
    current_view: EnvironmentalCurrentView | None = None,
) -> EnvironmentalB2EstablishmentDecision:
    """Deterministic Host validation — separate from Narrator N2 self-classification."""
    decision_id = new_establishment_decision_id(
        cognition_id=proposal.cognition_id,
        need_id=proposal.need_id,
        property_key=proposal.property_key,
    )

    if mediation_blocks_invention(proposal.mediation_outcome):
        return EnvironmentalB2EstablishmentDecision(
            decision_id=decision_id,
            authorized=False,
            reason_code=f"blocked_by_mediation:{proposal.mediation_outcome or 'missing'}",
            reason_detail="Librarian outcome does not permit bounded environmental origination",
            proposal=proposal,
        )

    if not mediation_allows_bounded_composition(proposal.mediation_outcome):
        return EnvironmentalB2EstablishmentDecision(
            decision_id=decision_id,
            authorized=False,
            reason_code="unsafe_mediation_for_establishment",
            reason_detail=(
                "Bounded B2 requires safe mediation state (match or no_match); "
                f"got {proposal.mediation_outcome or 'missing'}"
            ),
            proposal=proposal,
        )

    ok, reason = validate_b2_proposal(
        property_key=proposal.property_key,
        value=proposal.value,
        stable_refs=proposal.stable_refs,
    )
    if not ok:
        return EnvironmentalB2EstablishmentDecision(
            decision_id=decision_id,
            authorized=False,
            reason_code="invalid_proposal_shape",
            reason_detail=reason,
            proposal=proposal,
        )

    if current_view is not None:
        existing = current_view.effective_descriptors.get(proposal.property_key)
        if (
            existing is not None
            and existing.value == proposal.value
            and not proposal.supersedes
        ):
            return EnvironmentalB2EstablishmentDecision(
                decision_id=decision_id,
                authorized=False,
                reason_code="redundant_established_property",
                reason_detail=(
                    "Property already established with same value; use category A"
                ),
                proposal=proposal,
            )

    return EnvironmentalB2EstablishmentDecision(
        decision_id=decision_id,
        authorized=True,
        reason_code="host_accepted",
        reason_detail="Host deterministic validation accepted bounded B2 origination",
        proposal=proposal,
    )


def epistemic_authority_for_b2_decision(
    decision: EnvironmentalB2EstablishmentDecision,
    *,
    source_domain_commit_id: str,
    cognition_id: str | None = None,
) -> EpistemicAuthorityRef:
    """Build resolvable establishment_decision ref from Host decision (not Narrator wish)."""
    return EpistemicAuthorityRef(
        ref_kind="establishment_decision",
        ref_payload={
            "decision_id": decision.decision_id,
            "authorized": bool(decision.authorized),
            "orchestration_only": True,
            "establishment_kind": "narrator_environmental_b2",
            "authority_kind": decision.authority_kind,
            "domain_commit_id": source_domain_commit_id,
            "cognition_id": cognition_id,
        },
    )
