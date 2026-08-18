"""Issue #240 v1_next5+ — mandatory semantic_evaluation wire (production default #230)."""

from __future__ import annotations

import json
import os
from typing import Any

_ISSUE240_ENV = "RP_ISSUE240_PROMPT_TOPOLOGY"
_V1_NEXT5_TRUTHY = frozenset({"v1_next5", "v1-next5", "v1next5"})
_V1_NEXT6_TRUTHY = frozenset({"v1_next6", "v1-next6", "v1next6"})
_V1_NEXT7_TRUTHY = frozenset({"v1_next7", "v1-next7", "v1next7"})
_V1_NEXT7_PARTICIPATION_CALIBRATION_A_TRUTHY = frozenset(
    {
        "v1_next7_participation_calibration_a",
        "v1-next7-participation-calibration-a",
        "v1next7participationcalibrationa",
    }
)
_V1_NEXT7_PROPOSAL_SCHEMA_A_TRUTHY = frozenset(
    {
        "v1_next7_proposal_schema_a",
        "v1-next7-proposal-schema-a",
        "v1next7proposalschemaa",
    }
)
_V1_NEXT7_PARTICIPATION_BOUNDARY_B_TRUTHY = frozenset(
    {
        "v1_next7_participation_boundary_b",
        "v1-next7-participation-boundary-b",
        "v1next7participationboundaryb",
    }
)
_V1_NEXT7_PARTICIPATION_BOUNDARY_B_CLEAN_TRUTHY = frozenset(
    {
        "v1_next7_participation_boundary_b_clean",
        "v1-next7-participation-boundary-b-clean",
        "v1next7participationboundarybclean",
    }
)
_SEMANTIC_EVAL_TOPOLOGIES = (
    _V1_NEXT5_TRUTHY
    | _V1_NEXT6_TRUTHY
    | _V1_NEXT7_TRUTHY
    | _V1_NEXT7_PARTICIPATION_CALIBRATION_A_TRUTHY
    | _V1_NEXT7_PROPOSAL_SCHEMA_A_TRUTHY
    | _V1_NEXT7_PARTICIPATION_BOUNDARY_B_TRUTHY
    | _V1_NEXT7_PARTICIPATION_BOUNDARY_B_CLEAN_TRUTHY
)
_PRODUCTION_LEGACY_TRUTHY = frozenset({"production_legacy", "legacy", "off"})

SEMANTIC_EVALUATION_DECISIONS = frozenset({"covered_change", "no_covered_change"})
_V2_PROPOSAL_KINDS = frozenset({"off_focal", "reentry", "excursion_lifecycle"})
_V2_EXCURSION_OPERATIONS = frozenset({"open", "update", "close"})
_V2_PROPOSAL_ITEM_KEYS = frozenset({"kind", "character", "operation"})
_MAX_V2_SEMANTIC_PROPOSALS = 8
_MAX_V2_PROPOSAL_TEXT_CODEPOINTS = 256


def issue240_semantic_evaluation_enabled() -> bool:
    raw = os.environ.get(_ISSUE240_ENV, "").strip().lower()
    if raw in _PRODUCTION_LEGACY_TRUTHY:
        return False
    if not raw:
        return True
    return raw in _SEMANTIC_EVAL_TOPOLOGIES


def issue240_v2_root_allowlist_extra() -> frozenset[str]:
    if issue240_semantic_evaluation_enabled():
        return frozenset({"semantic_evaluation"})
    return frozenset()


def validate_semantic_evaluation_block(ev: Any) -> str:
    if not isinstance(ev, dict):
        return "semantic_evaluation must be a JSON object when present"
    unknown = [k for k in ev if k not in {"decision", "proposals"}]
    if unknown:
        return f"unknown fields on semantic_evaluation: {unknown}"
    decision = ev.get("decision")
    if decision not in SEMANTIC_EVALUATION_DECISIONS:
        return (
            "semantic_evaluation.decision must be covered_change or no_covered_change; "
            f"got {decision!r}"
        )
    proposals = ev.get("proposals", None)
    if decision == "covered_change":
        if not isinstance(proposals, list) or len(proposals) < 1:
            return (
                "semantic_evaluation.proposals must be a non-empty array when "
                "decision is covered_change"
            )
        if len(proposals) > _MAX_V2_SEMANTIC_PROPOSALS:
            return f"semantic_evaluation.proposals exceeds cap ({_MAX_V2_SEMANTIC_PROPOSALS})"
        for i, item in enumerate(proposals):
            if not isinstance(item, dict):
                return f"semantic_evaluation.proposals[{i}] must be an object"
            unknown_item = [k for k in item if k not in _V2_PROPOSAL_ITEM_KEYS]
            if unknown_item:
                return f"unknown fields on semantic_evaluation.proposals[{i}]: {unknown_item}"
            kind = item.get("kind")
            if kind not in _V2_PROPOSAL_KINDS:
                return f"invalid semantic_evaluation.proposals[{i}].kind: {kind!r}"
            char = str(item.get("character", "") or "").strip()
            if not char:
                return f"semantic_evaluation.proposals[{i}].character must be non-empty"
            if len(char) > _MAX_V2_PROPOSAL_TEXT_CODEPOINTS:
                return "semantic_evaluation.proposals character string exceeds cap"
            op = item.get("operation", None)
            if kind == "excursion_lifecycle":
                if not isinstance(op, str) or op not in _V2_EXCURSION_OPERATIONS:
                    return (
                        f"semantic_evaluation.proposals[{i}] requires operation "
                        "open|update|close for excursion_lifecycle"
                    )
            elif op is not None:
                return (
                    f"semantic_evaluation.proposals[{i}] must not include operation "
                    f"for kind {kind!r}"
                )
        from character_move_ingress import _validate_semantic_proposals_v2

        return _validate_semantic_proposals_v2({"semantic_proposals": proposals})
    if proposals is not None:
        if isinstance(proposals, list) and len(proposals) > 0:
            return (
                "semantic_evaluation.proposals must be omitted when decision is "
                "no_covered_change"
            )
        if not isinstance(proposals, list):
            return "semantic_evaluation.proposals must be omitted when decision is no_covered_change"
    return ""


def validate_issue240_semantic_evaluation_ingress(m: dict[str, Any]) -> str:
    if not issue240_semantic_evaluation_enabled():
        return ""
    sp = m.get("semantic_proposals", None)
    if isinstance(sp, list) and len(sp) == 0 and "semantic_evaluation" not in m:
        return (
            "semantic_proposals: [] is not allowed under Issue #240 v1_next5; "
            "use semantic_evaluation with decision no_covered_change"
        )
    if "semantic_evaluation" in m and "semantic_proposals" in m:
        return (
            "semantic_evaluation and root semantic_proposals are mutually exclusive; "
            "put proposals inside semantic_evaluation only"
        )
    if "semantic_evaluation" not in m:
        return ""
    return validate_semantic_evaluation_block(m.get("semantic_evaluation"))


def normalize_issue240_semantic_evaluation_for_continuity(move: dict[str, Any]) -> dict[str, Any]:
    """Promote v1_next5 semantic_evaluation to root semantic_proposals for continuity."""
    out = dict(move)
    ev = out.pop("semantic_evaluation", None)
    if not isinstance(ev, dict):
        return out
    decision = ev.get("decision")
    if decision == "covered_change":
        proposals = ev.get("proposals")
        if isinstance(proposals, list) and proposals:
            out["semantic_proposals"] = list(proposals)
    elif decision == "no_covered_change":
        out.pop("semantic_proposals", None)
    return out


def extract_semantic_evaluation_decision(move: dict[str, Any] | None) -> str | None:
    if not isinstance(move, dict):
        return None
    ev = move.get("semantic_evaluation")
    if not isinstance(ev, dict):
        return None
    decision = str(ev.get("decision") or "").strip()
    return decision if decision in SEMANTIC_EVALUATION_DECISIONS else None


# Issue #250 repair lane — strip only; first-pass ingress unchanged.
_FORBIDDEN_PROPOSAL_HELPER_KEYS = frozenset(
    {"reason", "strategy", "rationale", "explanation", "justification"}
)


def _proposal_kinds_from_loose(loose: dict[str, Any]) -> list[str]:
    kinds: list[str] = []
    ev = loose.get("semantic_evaluation")
    if isinstance(ev, dict):
        props = ev.get("proposals")
        if isinstance(props, list):
            for item in props:
                if isinstance(item, dict):
                    k = str(item.get("kind", "") or "").strip()
                    if k:
                        kinds.append(k)
    sp = loose.get("semantic_proposals")
    if isinstance(sp, list):
        for item in sp:
            if isinstance(item, dict):
                k = str(item.get("kind", "") or "").strip()
                if k:
                    kinds.append(k)
    return kinds


def extract_parse_repair_semantic_snapshot(loose: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(loose, dict):
        return {
            "semantic_decision": None,
            "proposal_kinds": [],
        }
    decision = extract_semantic_evaluation_decision(loose)
    if decision is None:
        sp = loose.get("semantic_proposals")
        if isinstance(sp, list) and sp:
            decision = "covered_change"
    return {
        "semantic_decision": decision,
        "proposal_kinds": _proposal_kinds_from_loose(loose),
    }


def _strip_proposal_item(item: dict[str, Any], *, acting_character: str) -> dict[str, Any]:
    out = {k: v for k, v in item.items() if k in _V2_PROPOSAL_ITEM_KEYS}
    if not str(out.get("character", "") or "").strip():
        actor = str(acting_character or "").strip()
        if actor:
            out["character"] = actor
    return out


def _repair_semantic_evaluation_block(
    ev: dict[str, Any], *, acting_character: str
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    decision = ev.get("decision")
    if decision in SEMANTIC_EVALUATION_DECISIONS:
        out["decision"] = decision
    props = ev.get("proposals")
    if isinstance(props, list) and props:
        cleaned: list[dict[str, Any]] = []
        for item in props:
            if isinstance(item, dict):
                cleaned.append(_strip_proposal_item(item, acting_character=acting_character))
        if cleaned:
            out["proposals"] = cleaned
    return out


def attempt_deterministic_ingress_repair(
    loose: dict[str, Any],
    *,
    acting_character: str,
) -> tuple[Any | None, str]:
    """Repair-lane only (#250). Returns (CanonicalV2Move|None, error)."""
    from character_move_ingress import ingest_character_move_json_object

    if not isinstance(loose, dict):
        return None, "repair requires a JSON object"
    from character_move_ingress import (
        V2_ROOT_ALLOWLIST,
        _beat_allowed_keys,
        issue240_v2_root_allowlist_extra,
    )

    work = json.loads(json.dumps(loose))
    allow_root = V2_ROOT_ALLOWLIST | issue240_v2_root_allowlist_extra()
    work = {k: v for k, v in work.items() if k in allow_root}
    beats = work.get("beats")
    if isinstance(beats, list):
        cleaned_beats: list[dict[str, Any]] = []
        for b in beats:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            allowed = _beat_allowed_keys(bt)
            cleaned_beats.append({k: v for k, v in b.items() if k in allowed})
        work["beats"] = cleaned_beats
    if "semantic_evaluation" in work and "semantic_proposals" in work:
        work.pop("semantic_proposals", None)
    ev_raw = work.get("semantic_evaluation")
    if isinstance(ev_raw, dict):
        work["semantic_evaluation"] = _repair_semantic_evaluation_block(
            ev_raw, acting_character=acting_character
        )
    sp_raw = work.get("semantic_proposals")
    if isinstance(sp_raw, list):
        work["semantic_proposals"] = [
            _strip_proposal_item(item, acting_character=acting_character)
            for item in sp_raw
            if isinstance(item, dict)
        ]
    return ingest_character_move_json_object(work)
