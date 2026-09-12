"""Session-scoped Layer B epistemic evaluation reuse (#166 Lane 2)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .plot_cognition_orchestration_contract import CharacterEpistemicContextEnvelope


@dataclass(frozen=True)
class LayerBEpistemicReuseEntry:
    reuse_key_digest: str
    semantic: dict[str, Any]
    inference_evidence_id: str | None
    forensic_record_id: str | None = None


_LAYER_B_REUSE_BY_SCOPE: dict[str, dict[str, LayerBEpistemicReuseEntry]] = {}


def clear_layer_b_reuse_for_tests() -> None:
    _LAYER_B_REUSE_BY_SCOPE.clear()


def _canonical_withheld_basis_index(
    withheld_basis_index: tuple[dict[str, str], ...],
) -> list[dict[str, str]]:
    return sorted(
        [dict(item) for item in withheld_basis_index],
        key=lambda item: (
            str(item.get("facet_id", "")),
            str(item.get("category", "")),
            str(item.get("reason", "")),
        ),
    )


def compute_layer_b_eval_reuse_key(
    *,
    plot_cognition_scope_id: str,
    character_id: str,
    candidate_id: str,
    visibility_digest: str,
    withheld_basis_index: tuple[dict[str, str], ...],
    known_by_snapshot_id: str,
    overlay_revision: int | None,
    assimilated_authority_source_fingerprint: str | None,
) -> str:
    body = {
        "plot_cognition_scope_id": plot_cognition_scope_id,
        "character_id": character_id,
        "candidate_id": candidate_id,
        "visibility_digest": visibility_digest,
        "withheld_basis_index": _canonical_withheld_basis_index(withheld_basis_index),
        "known_by_snapshot_id": known_by_snapshot_id,
        "overlay_revision": overlay_revision,
        "assimilated_authority_source_fingerprint": assimilated_authority_source_fingerprint or "",
    }
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_layer_b_eval_reuse_key_from_envelope(
    envelope: CharacterEpistemicContextEnvelope,
    *,
    plot_cognition_scope_id: str,
    assimilated_authority_source_fingerprint: str | None,
) -> str:
    return compute_layer_b_eval_reuse_key(
        plot_cognition_scope_id=plot_cognition_scope_id,
        character_id=envelope.character_id,
        candidate_id=envelope.candidate_id,
        visibility_digest=envelope.visibility_digest,
        withheld_basis_index=envelope.withheld_basis_index,
        known_by_snapshot_id=envelope.known_by_snapshot_id,
        overlay_revision=envelope.overlay_revision,
        assimilated_authority_source_fingerprint=assimilated_authority_source_fingerprint,
    )


def consult_layer_b_reuse(
    *,
    plot_cognition_scope_id: str,
    reuse_key_digest: str,
) -> LayerBEpistemicReuseEntry | None:
    scope_entries = _LAYER_B_REUSE_BY_SCOPE.get(plot_cognition_scope_id)
    if not scope_entries:
        return None
    return scope_entries.get(reuse_key_digest)


def store_layer_b_reuse(
    *,
    plot_cognition_scope_id: str,
    reuse_key_digest: str,
    semantic: dict[str, Any],
    inference_evidence_id: str | None,
    forensic_record_id: str | None = None,
) -> None:
    scope_entries = _LAYER_B_REUSE_BY_SCOPE.setdefault(plot_cognition_scope_id, {})
    scope_entries[reuse_key_digest] = LayerBEpistemicReuseEntry(
        reuse_key_digest=reuse_key_digest,
        semantic=dict(semantic),
        inference_evidence_id=inference_evidence_id,
        forensic_record_id=forensic_record_id,
    )
