"""Per-character epistemic envelope helpers (#38, #62 basis resolution)."""

from __future__ import annotations

import hashlib
from typing import Any

from .librarian_contract import StableReference
from .plot_cognition_projection_contract import BasisExposureResult
from .session_state import LiveSession


def compute_known_by_snapshot_id(fixture: LiveSession, character_id: str) -> str:
    """Stable fingerprint of which public events the character currently knows."""
    mgr = fixture.manager
    event_ids: list[str] = []
    for event in getattr(mgr, "public_events", []) or []:
        known_by = list(getattr(event, "known_by", []) or [])
        if character_id in known_by:
            event_ids.append(str(getattr(event, "event_id", "") or ""))
    payload = ",".join(sorted(item for item in event_ids if item))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"known_by:{character_id}:{digest}"


def character_may_know_candidate(
    *,
    character_id: str,
    provenance: dict[str, Any] | None,
    host_internal_metadata: dict[str, Any] | None,
) -> bool:
    """Reject retrieval candidates tagged with known_by lists the character is not on."""
    for source in (provenance or {}, host_internal_metadata or {}):
        known_by = source.get("known_by")
        if known_by is None:
            continue
        if isinstance(known_by, list):
            if character_id not in {str(item) for item in known_by}:
                return False
        elif isinstance(known_by, str) and known_by.strip():
            if character_id != known_by.strip():
                return False
    required_knower = (provenance or {}).get("required_knower")
    if required_knower and str(required_knower).strip() not in {"", character_id}:
        return False
    return True


def _character_card_facet_owner(stable_ref: str) -> str | None:
    text = str(stable_ref or "").strip()
    if ":" not in text:
        return None
    return text.split(":", 1)[0].strip() or None


def _event_known_by_character(fixture: LiveSession, character_id: str, event_ref: str) -> bool:
    mgr = fixture.manager
    needle = str(event_ref or "").strip()
    if not needle:
        return False
    for event in getattr(mgr, "public_events", []) or []:
        event_id = str(getattr(event, "event_id", "") or "")
        if event_id != needle and not event_id.endswith(needle):
            continue
        known_by = {str(item) for item in (getattr(event, "known_by", []) or [])}
        return character_id in known_by
    return False


def resolve_basis_exposure(
    fixture: LiveSession,
    *,
    character_id: str,
    basis_refs: tuple[StableReference, ...],
) -> BasisExposureResult:
    """Deterministic basis-ref resolution for Layer A structural eligibility."""
    if not basis_refs:
        return BasisExposureResult(
            resolved=True,
            exposable_facet_ids=(),
            withheld_facet_ids=(),
            has_hidden_basis=False,
            epistemic_eligible=True,
            rationale="no basis refs; storyteller-originated prospective path permitted",
        )

    exposable: list[str] = []
    withheld: list[str] = []
    unresolved = False
    for ref in basis_refs:
        facet_id = f"{ref.ref_kind}:{ref.stable_ref}"
        ref_kind = str(ref.ref_kind or "").strip()
        stable_ref = str(ref.stable_ref or "").strip()
        if not ref_kind or not stable_ref:
            unresolved = True
            withheld.append(facet_id)
            continue
        if ref_kind == "character_card":
            owner = _character_card_facet_owner(stable_ref)
            if owner is None:
                unresolved = True
                withheld.append(facet_id)
                continue
            if owner.lower() == character_id.lower():
                exposable.append(facet_id)
            else:
                withheld.append(facet_id)
            continue
        if ref_kind in {"public_event", "committed_event", "event"}:
            if _event_known_by_character(fixture, character_id, stable_ref):
                exposable.append(facet_id)
            else:
                withheld.append(facet_id)
            continue
        if ref_kind == "character_scope":
            if stable_ref.strip().lower() == character_id.strip().lower():
                exposable.append(facet_id)
            else:
                withheld.append(facet_id)
            continue
        unresolved = True
        withheld.append(facet_id)

    has_hidden = bool(withheld)
    epistemic_eligible = bool(exposable) or (not unresolved and not has_hidden)
    return BasisExposureResult(
        resolved=not unresolved,
        exposable_facet_ids=tuple(exposable),
        withheld_facet_ids=tuple(withheld),
        has_hidden_basis=has_hidden,
        epistemic_eligible=epistemic_eligible,
        rationale=(
            "basis unresolved"
            if unresolved
            else "hidden basis present"
            if has_hidden and exposable
            else "basis withheld"
            if has_hidden
            else "basis fully exposable"
        ),
    )


def build_character_visibility_envelope(
    fixture: LiveSession,
    *,
    character_id: str,
    hg_round_id: str,
) -> dict[str, Any]:
    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    return {
        "viewer_role": "character",
        "authority_ceiling_enforced": "derived",
        "viewer_character_id": character_id,
        "subject_character_id": character_id,
        "session_template_id": template_id,
        "perception_gates_ref": f"perception:{character_id}:{hg_round_id}",
        "known_by_snapshot_id": compute_known_by_snapshot_id(fixture, character_id),
    }
