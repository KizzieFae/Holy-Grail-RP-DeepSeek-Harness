"""Canonical Storyteller orientation response contract — structural authority (#144).

Declarative structural requirements for live Storyteller orientation JSON. Consumed by
Host parser constants and Host prompt projection. Not parser procedure.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

RESPONSE_CONTRACT_REVISION = "storyteller_orientation_response_contract_v1"

STORYTELLER_ORIENTATION_SCHEMA = "hg_storyteller_orientation_v1"

ORIENTATION_TRIGGER_VALUES = frozenset(
    {"round_start", "material_commit_refresh", "follow_up_gap"}
)

TEMPORAL_VALUES = frozenset({"current", "recent", "historical", "session", "arc"})

BREADTH_VALUES = frozenset({"broad", "focused"})

REQUIRED_ROOT_FIELDS = ("schema", "information_gaps")

PROHIBITION_SUMMARY = (
    "Do not include mandate fields such as next_actor, dialogue, narration, "
    "structured_move, or continuity mutations."
)

CANONICAL_EXEMPLAR: dict[str, Any] = {
    "schema": STORYTELLER_ORIENTATION_SCHEMA,
    "information_gaps": [
        "What tensions are active in the scene?",
        "Which relationships need more context?",
    ],
}


def _canonical_digest_payload() -> dict[str, Any]:
    return {
        "revision": RESPONSE_CONTRACT_REVISION,
        "schema": STORYTELLER_ORIENTATION_SCHEMA,
        "required_fields": list(REQUIRED_ROOT_FIELDS),
        "exemplar": CANONICAL_EXEMPLAR,
        "prohibition_summary": PROHIBITION_SUMMARY,
        "trigger_values": sorted(ORIENTATION_TRIGGER_VALUES),
        "temporal_values": sorted(TEMPORAL_VALUES),
        "breadth_values": sorted(BREADTH_VALUES),
    }


def response_contract_digest() -> str:
    payload = json.dumps(_canonical_digest_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def storyteller_orientation_response_contract_provenance() -> dict[str, str]:
    return {
        "response_contract_revision": RESPONSE_CONTRACT_REVISION,
        "response_contract_digest": response_contract_digest(),
    }


def project_storyteller_orientation_response_contract_text() -> str:
    exemplar_json = json.dumps(CANONICAL_EXEMPLAR, indent=2, sort_keys=True)
    return (
        "Storyteller orientation response contract (structural JSON only):\n"
        f'Required root: schema "{STORYTELLER_ORIENTATION_SCHEMA}" and non-empty '
        "information_gaps[] (strings).\n"
        "Return one JSON object only. No markdown or commentary.\n"
        "Canonical exemplar:\n"
        f"{exemplar_json}\n"
        f"{PROHIBITION_SUMMARY}"
    )
