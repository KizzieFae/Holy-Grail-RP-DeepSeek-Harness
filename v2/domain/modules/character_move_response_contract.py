"""Canonical Character move response contract — structural authority (#136).

Declarative structural requirements for live Character move JSON. Consumed by
ingress validation constants and Host prompt projection. Not ingress procedure.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from issue240_semantic_evaluation import SEMANTIC_EVALUATION_DECISIONS

RESPONSE_CONTRACT_REVISION = "character_move_response_contract_v1"

V2_ROOT_ALLOWLIST = frozenset(
    {
        "move_schema_version",
        "beats",
        "motivation",
        "scene_state_updates",
        "semantic_proposals",
    }
)

MOTIVATION_REQUIRED_FIELDS = ("goal", "tactic", "emotional_driver", "risk_level")

RISK_LEVEL_VALUES = frozenset({"low", "medium", "high"})

BEAT_TYPES = frozenset({"action", "speech"})

ACTION_BEAT_ALLOWED_KEYS = frozenset({"type", "action", "recipients"})
SPEECH_BEAT_ALLOWED_KEYS = frozenset({"type", "dialogue", "audibility", "audience"})

PROHIBITED_ROOT_KEYS = frozenset({"action", "dialogue", "audibility", "audience"})

PROHIBITED_BEAT_FIELD_NAMES = frozenset({"description", "key"})

STRUCTURAL_PROHIBITIONS = (
    "Do not use root-level action, dialogue, audibility, or audience.",
    "Do not use beat fields description or key.",
    "Action beats must use type action with field action (not description or key).",
    "Speech beats must use type speech with field dialogue (not description or key).",
)

CANONICAL_EXEMPLAR: dict[str, Any] = {
    "move_schema_version": 2,
    "beats": [
        {"type": "action", "action": "..."},
        {"type": "speech", "dialogue": "..."},
    ],
    "motivation": {
        "goal": "...",
        "tactic": "...",
        "emotional_driver": "...",
        "risk_level": "medium",
    },
    "semantic_evaluation": {"decision": "no_covered_change"},
}


def beat_allowed_keys_for_type(bt: Any) -> frozenset[str]:
    if bt == "action":
        return ACTION_BEAT_ALLOWED_KEYS
    if bt == "speech":
        return SPEECH_BEAT_ALLOWED_KEYS
    return frozenset()


def _canonical_digest_payload() -> dict[str, Any]:
    return {
        "revision": RESPONSE_CONTRACT_REVISION,
        "root_allowlist": sorted(V2_ROOT_ALLOWLIST),
        "motivation_required": list(MOTIVATION_REQUIRED_FIELDS),
        "risk_level_values": sorted(RISK_LEVEL_VALUES),
        "beat_types": sorted(BEAT_TYPES),
        "action_beat_keys": sorted(ACTION_BEAT_ALLOWED_KEYS),
        "speech_beat_keys": sorted(SPEECH_BEAT_ALLOWED_KEYS),
        "prohibited_root_keys": sorted(PROHIBITED_ROOT_KEYS),
        "prohibited_beat_fields": sorted(PROHIBITED_BEAT_FIELD_NAMES),
        "semantic_decisions": sorted(SEMANTIC_EVALUATION_DECISIONS),
        "exemplar": CANONICAL_EXEMPLAR,
        "prohibitions": list(STRUCTURAL_PROHIBITIONS),
    }


def response_contract_digest() -> str:
    payload = json.dumps(_canonical_digest_payload(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def character_move_response_contract_provenance() -> dict[str, str]:
    return {
        "response_contract_revision": RESPONSE_CONTRACT_REVISION,
        "response_contract_digest": response_contract_digest(),
    }


def project_character_move_response_contract_text() -> str:
    exemplar_json = json.dumps(CANONICAL_EXEMPLAR, indent=2, sort_keys=True)
    risk_line = ", ".join(sorted(RISK_LEVEL_VALUES))
    decision_line = " | ".join(sorted(SEMANTIC_EVALUATION_DECISIONS))
    prohibition_lines = "\n".join(f"- {line}" for line in STRUCTURAL_PROHIBITIONS)
    motivation_fields = ", ".join(MOTIVATION_REQUIRED_FIELDS)
    return (
        "Character move response contract (structural JSON only):\n"
        f"Required root: move_schema_version 2, non-empty beats[], motivation object"
        f" ({motivation_fields}), and semantic_evaluation when topology requires it.\n"
        "Canonical exemplar:\n"
        f"{exemplar_json}\n"
        f"risk_level must be exactly one of: {risk_line}.\n"
        f"semantic_evaluation.decision must be one of: {decision_line}.\n"
        "Prohibitions:\n"
        f"{prohibition_lines}"
    )
