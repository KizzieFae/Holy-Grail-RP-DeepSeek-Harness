"""Canonical Storyteller assessment response contract — structural authority (#146).

Declarative structural requirements for live Storyteller assessment JSON. Consumed by
Host parser constants and Host prompt projection. Not parser procedure.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

RESPONSE_CONTRACT_REVISION = "storyteller_assessment_response_contract_v1"

STORYTELLER_ASSESSMENT_SCHEMA = "hg_storyteller_assessment_v1"

REQUIRED_ROOT_FIELDS = ("schema",)

CANONICAL_SECTION_NAMES = frozenset(
    {
        "observations",
        "active_tensions",
        "narrative_priorities",
        "progression_opportunities",
        "unresolved_threads",
        "uncertainty",
        "information_gaps",
        "preservation_signals",
        "evidence_refs",
    }
)

PROHIBITION_SUMMARY = (
    "Do not include mandate fields such as next_actor, dialogue, narration, "
    "structured_move, or continuity mutations."
)

CANONICAL_EXEMPLAR: dict[str, Any] = {
    "schema": STORYTELLER_ASSESSMENT_SCHEMA,
    "observations": [
        {
            "text": "A narratively significant pattern is visible in the bundle.",
        }
    ],
    "progression_opportunities": [
        {
            "opportunity_label": "Optional narrative hook",
            "narrative_hook": "An opportunity the scene could develop without mandating action.",
        }
    ],
}

_ALLOWED_SECTIONS_LINE = (
    "active_tensions, narrative_priorities, unresolved_threads, uncertainty, "
    "information_gaps, preservation_signals, evidence_refs."
)


def _canonical_digest_payload() -> dict[str, Any]:
    return {
        "revision": RESPONSE_CONTRACT_REVISION,
        "schema": STORYTELLER_ASSESSMENT_SCHEMA,
        "required_fields": list(REQUIRED_ROOT_FIELDS),
        "canonical_section_names": sorted(CANONICAL_SECTION_NAMES),
        "exemplar": CANONICAL_EXEMPLAR,
        "prohibition_summary": PROHIBITION_SUMMARY,
    }


def response_contract_digest() -> str:
    payload = json.dumps(_canonical_digest_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def storyteller_assessment_response_contract_provenance() -> dict[str, str]:
    return {
        "response_contract_revision": RESPONSE_CONTRACT_REVISION,
        "response_contract_digest": response_contract_digest(),
    }


def project_storyteller_assessment_response_contract_text() -> str:
    exemplar_json = json.dumps(CANONICAL_EXEMPLAR, indent=2, sort_keys=True)
    return (
        "Storyteller assessment response contract (structural JSON only):\n"
        f'Required: schema "{STORYTELLER_ASSESSMENT_SCHEMA}".\n'
        "Return one JSON object only. No markdown or commentary.\n"
        'Do not use top-level keys "assessment" or "opportunities" — use canonical '
        "section names below.\n"
        "Canonical exemplar:\n"
        f"{exemplar_json}\n"
        "Other allowed sections (include only when applicable; do not emit empty arrays):\n"
        f"{_ALLOWED_SECTIONS_LINE}\n"
        f"{PROHIBITION_SUMMARY}"
    )
