"""Turn metadata audit payload for resolved mutations (#170)."""

from __future__ import annotations

from typing import Any

from continuity_mutation_pipeline_types import MutationRequest, MutationResolutionKey


def resolved_mutations_audit_payload(
    resolved: dict[MutationResolutionKey, MutationRequest],
) -> dict[str, Any]:
    """Structured snapshot for ``turn_metadata`` / audits."""
    out: dict[str, Any] = {}
    for key, req in resolved.items():
        out[key.audit_slug()] = {
            "mutation_type": req.mutation_type.value,
            "source": req.source.value,
            "payload": dict(req.payload),
        }
    return out
