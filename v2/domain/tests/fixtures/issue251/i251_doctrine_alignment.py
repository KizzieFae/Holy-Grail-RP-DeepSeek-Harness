"""Issue #251 — L3 doctrine-alignment overlay (observational; not runtime authority).

Separate from L1 deterministic metrics and L2 #243-B adjudication.
"""

from __future__ import annotations

from typing import Any

DOCTRINE_ALIGNMENT_SCHEMA = "issue251_doctrine_alignment.v1"

_ARM_RUBRICS = {
    "hybrid_awareness_v1": (
        "Hybrid shared-awareness: off_focal requires all four awareness factors "
        "at beat end; temporary-task/doorway tether without awareness severance → no_covered_change."
    ),
    "physical_severance_v1": (
        "Physical/perceptual severance: off_focal when beat completes spatial departure "
        "and perceptual severance; temporary framing does not block if severance completes."
    ),
    "physical_severance_guarded_v1": (
        "Guarded structural severance: off_focal when character fully left shared scene "
        "and live exchange no longer continuing at beat end; do not complete exits "
        "the beat does not complete; threshold/doorway/disengagement alone not off_focal."
    ),
}


def _expected_emission(
    doctrine_expected: str,
) -> tuple[str | None, list[str]]:
    if doctrine_expected == "off_focal":
        return "covered_change", ["off_focal"]
    if doctrine_expected == "no_covered_change":
        return "no_covered_change", []
    return None, []


def evaluate_doctrine_alignment(
    *,
    doctrine_arm: str,
    doctrine_schema_version: str,
    doctrine_expected: str,
    attempt: dict[str, Any] | None,
    expected_label: str | None = None,
    l3_rubric: str | None = None,
) -> dict[str, Any]:
    """L3 overlay: replay output vs active arm doctrine rubric."""
    fa = attempt or {}
    exp_decision, exp_kinds = _expected_emission(doctrine_expected)
    decision = fa.get("decision")
    kinds = list(fa.get("proposal_kinds") or [])

    rubric = l3_rubric or _ARM_RUBRICS.get(
        doctrine_schema_version,
        f"doctrine schema {doctrine_schema_version}",
    )

    if not fa.get("parse_ok"):
        return {
            "schema_version": DOCTRINE_ALIGNMENT_SCHEMA,
            "doctrine_arm": doctrine_arm,
            "doctrine_schema_version": doctrine_schema_version,
            "expected_under_arm": expected_label or doctrine_expected,
            "expected_decision": exp_decision,
            "expected_proposal_kinds": exp_kinds,
            "actual_decision": decision,
            "actual_proposal_kinds": kinds,
            "doctrine_aligned": False,
            "rationale": f"Unparsed replay output; cannot align to {doctrine_schema_version} rubric.",
            "rubric_summary": rubric,
            "limitations": [
                "observational_only: not runtime authority",
                "does_not_override_L2_adjudication",
            ],
        }

    if doctrine_expected == "off_focal":
        aligned = decision == "covered_change" and kinds == ["off_focal"]
        if aligned:
            rationale = (
                f"Replay matches {doctrine_arm} exit rubric: covered_change + off_focal."
            )
        elif decision == "no_covered_change" and not kinds:
            rationale = (
                f"Miss under {doctrine_schema_version}: no_covered_change without off_focal "
                f"when exit expected ({expected_label or 'off_focal'})."
            )
        else:
            rationale = (
                f"Mismatch under {doctrine_schema_version}: decision={decision!r}, "
                f"kinds={kinds}; expected covered_change + ['off_focal']."
            )
    elif doctrine_expected == "no_covered_change":
        aligned = decision == "no_covered_change" and "off_focal" not in kinds
        if aligned:
            rationale = (
                f"Replay matches {doctrine_arm} non-exit rubric: no_covered_change without off_focal."
            )
        elif "off_focal" in kinds:
            rationale = (
                f"False positive under {doctrine_schema_version}: off_focal emitted on non-exit case."
            )
        else:
            rationale = (
                f"Mismatch under {doctrine_schema_version}: decision={decision!r}, kinds={kinds}."
            )
    else:
        aligned = None
        rationale = f"Unknown doctrine_expected={doctrine_expected!r}."

    return {
        "schema_version": DOCTRINE_ALIGNMENT_SCHEMA,
        "doctrine_arm": doctrine_arm,
        "doctrine_schema_version": doctrine_schema_version,
        "expected_under_arm": expected_label or doctrine_expected,
        "expected_decision": exp_decision,
        "expected_proposal_kinds": exp_kinds,
        "actual_decision": decision,
        "actual_proposal_kinds": kinds,
        "doctrine_aligned": aligned,
        "rationale": rationale,
        "rubric_summary": rubric,
        "limitations": [
            "observational_only: not runtime authority",
            "does_not_override_L2_adjudication",
            "continuity_authority_224_preserved",
        ],
    }


def summarize_doctrine_alignment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate L3 alignment rates by arm and cohort."""
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        arm = str(row.get("doctrine_arm") or "")
        by_arm.setdefault(arm, []).append(row)

    def arm_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
        clean = [
            r
            for r in items
            if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")
            and (r.get("preflight") or {}).get("contamination_clean")
        ]
        l3 = [r.get("doctrine_alignment") or {} for r in items]
        aligned = [x for x in l3 if x.get("doctrine_aligned") is True]
        clean_l3 = [
            r.get("doctrine_alignment") or {}
            for r in clean
            if (r.get("doctrine_alignment") or {}).get("doctrine_aligned") is not None
        ]
        clean_aligned = [x for x in clean_l3 if x.get("doctrine_aligned") is True]
        gm3 = [
            r
            for r in items
            if r.get("case_id") == "EXIT-C-GM3"
            and (r.get("preflight") or {}).get("contamination_clean")
        ]
        gm3_clean = [
            r
            for r in gm3
            if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")
        ]
        return {
            "n_samples": len(items),
            "n_contamination_clean": sum(
                1 for r in items if (r.get("preflight") or {}).get("contamination_clean")
            ),
            "L3_alignment_rate": (
                round(len(aligned) / len(l3), 3) if l3 else None
            ),
            "L3_alignment_rate_S2_clean": (
                round(len(clean_aligned) / len(clean_l3), 3) if clean_l3 else None
            ),
            "S1_rate": (
                round(
                    sum(
                        1
                        for r in items
                        if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
                    )
                    / len(items),
                    3,
                )
                if items
                else None
            ),
            "S2_clean_S1_rate": (
                round(
                    sum(
                        1
                        for r in clean
                        if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
                    )
                    / len(clean),
                    3,
                )
                if clean
                else None
            ),
            "GM3_n": len(gm3),
            "GM3_S2_clean_S1_rate": (
                round(
                    sum(
                        1
                        for r in gm3_clean
                        if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
                    )
                    / len(gm3_clean),
                    3,
                )
                if gm3_clean
                else None
            ),
            "GM3_L3_alignment_rate": (
                round(
                    sum(
                        1
                        for r in gm3
                        if (r.get("doctrine_alignment") or {}).get("doctrine_aligned")
                    )
                    / len(gm3),
                    3,
                )
                if gm3
                else None
            ),
            "guard_false_off_focal_rate": (
                round(
                    sum(
                        1
                        for r in items
                        if r.get("cohort") == "non_exit"
                        and "off_focal"
                        in ((r.get("first_attempt") or {}).get("proposal_kinds") or [])
                    )
                    / max(
                        sum(1 for r in items if r.get("cohort") == "non_exit"),
                        1,
                    ),
                    3,
                )
            ),
        }

    arm_summaries = {arm: arm_stats(items) for arm, items in by_arm.items()}
    delta: dict[str, Any] = {}
    if "A" in arm_summaries and "B" in arm_summaries:
        a = arm_summaries["A"]
        b = arm_summaries["B"]
        for key in ("GM3_S2_clean_S1_rate", "GM3_L3_alignment_rate", "S2_clean_S1_rate"):
            av = a.get(key)
            bv = b.get(key)
            if av is not None and bv is not None:
                delta[f"{key}_delta_B_minus_A"] = round(bv - av, 3)

    return {
        "by_arm": arm_summaries,
        "A_vs_B_delta": delta,
    }
