"""Issue #251 — S1/S2/S3/S4 metrics helpers."""

from __future__ import annotations

from typing import Any


def s2_structural_legality_pass(attempt: dict[str, Any] | None) -> bool:
    if not attempt:
        return False
    if not attempt.get("parse_ok"):
        return False
    if not attempt.get("ingress_pass"):
        return False
    schema_valid = attempt.get("schema_valid")
    if schema_valid is False:
        return False
    return True


def s1_semantic_intent_correct(
    attempt: dict[str, Any] | None, doctrine_expected: str
) -> bool | None:
    if not attempt or not attempt.get("parse_ok"):
        return False
    decision = attempt.get("decision")
    kinds = list(attempt.get("proposal_kinds") or [])
    if doctrine_expected == "off_focal":
        return decision == "covered_change" and kinds == ["off_focal"]
    if doctrine_expected == "no_covered_change":
        if "off_focal" in kinds:
            return False
        return decision == "no_covered_change"
    if doctrine_expected == "off_focal_or_reentry":
        if decision != "covered_change":
            return False
        return kinds and kinds[0] in {"off_focal", "reentry"} and "off_focal" not in kinds[1:]
    if doctrine_expected == "covered_change":
        return decision == "covered_change" and bool(kinds)
    return None


def s3_authority_reached(attempt: dict[str, Any] | None) -> bool:
    if not attempt:
        return False
    return bool(attempt.get("authority_reached"))


def s4_committed_summary(attempt: dict[str, Any] | None) -> dict[str, Any]:
    if not attempt:
        return {"decision": None, "proposal_kinds": []}
    return {
        "decision": attempt.get("decision"),
        "proposal_kinds": attempt.get("proposal_kinds") or [],
    }


def enrich_attempt_metrics(
    attempt: dict[str, Any], doctrine_expected: str
) -> dict[str, Any]:
    out = dict(attempt)
    out["S1_semantic_intent_correct"] = s1_semantic_intent_correct(
        attempt, doctrine_expected
    )
    out["S2_structural_legality_pass"] = s2_structural_legality_pass(attempt)
    out["S3_authority_accept_reached"] = s3_authority_reached(attempt)
    out["S4_committed"] = s4_committed_summary(attempt)
    out["issue251_genuine_miss"] = (
        doctrine_expected in {"off_focal", "covered_change", "off_focal_or_reentry"}
        and out["S1_semantic_intent_correct"] is False
        and out["S2_structural_legality_pass"] is True
    )
    out["route_to_249"] = (
        out["S1_semantic_intent_correct"] is True
        and out["S2_structural_legality_pass"] is False
    )
    return out


def false_off_focal(attempt: dict[str, Any] | None) -> bool:
    if not attempt:
        return False
    return "off_focal" in (attempt.get("proposal_kinds") or [])
