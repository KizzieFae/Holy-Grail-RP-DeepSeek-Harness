"""Single source of truth for Audit V2 dimension ids, check mapping, and escalation.

Builders emit raw metrics; this module assigns pass/fail/border (and documented
non-tri-state exclusions), detects same-dimension conflict, and lists escalation reasons.
Thresholds live only here.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# --- Dimension ids (character) ---
DIM_CHARACTER_INTRA_MOVE = "character_intra_move_coherence"
DIM_CHARACTER_REPETITION = "character_structural_repetition"
DIM_CHARACTER_DECLARED_FIELDS = "character_declared_pressure_fields"
# Observability-only; check tri-state is always pass (GitHub #73 — no product escalation).
DIM_CHARACTER_MASKED_PROGRESSION = "character_masked_progression_signal"

# --- Dimension ids (narrator output) ---
DIM_NARRATOR_ACTION_GROUNDING = "narrator_action_grounding"
DIM_NARRATOR_ENVIRONMENT_CUE = "narrator_environment_cue"
# Legacy dimension id retained for log shape; `nar_scope_proxy` is non-gating (GitHub #9).
DIM_NARRATOR_SCOPE_PROXY = "narrator_scope_proxy"

# --- Dimension ids (prose) ---
DIM_PROSE_READABILITY = "prose_readability"
DIM_PROSE_REDUNDANCY = "prose_redundancy_vs_prior"
DIM_PROSE_DIALOGUE_INTEGRATION = "prose_dialogue_integration"
DIM_PROSE_ATTRIBUTION = "prose_attribution"
DIM_PROSE_TONE = "prose_tone_local"

# --- GitHub #42: CA1/CA2 excluded from escalation (deprecated after Issue #13) ---
# Logged on scored rows; omitted from dimension aggregation; not a success "pass".
CHECK_RESULT_EXCLUDED_DEPRECATED = "excluded_deprecated"
# Intra-move dimension has no escalation-active checks after CA1/CA2 exclusion.
DIMENSION_AGGREGATE_NOT_APPLICABLE = "not_applicable"
_CHECK_IDS_EXCLUDED_FROM_ESCALATION_AGGREGATION: frozenset[str] = frozenset(
    {"char_ca1_motivation_action", "char_ca2_dialogue_action"}
)

CHECK_TO_DIMENSION: dict[str, str] = {
    "char_ca1_motivation_action": DIM_CHARACTER_INTRA_MOVE,
    "char_ca2_dialogue_action": DIM_CHARACTER_INTRA_MOVE,
    "char_ca4_repetition": DIM_CHARACTER_REPETITION,
    "char_ca7_declared_fields": DIM_CHARACTER_DECLARED_FIELDS,
    "char_masked_progression_strict": DIM_CHARACTER_MASKED_PROGRESSION,
    "nar_strict_action_overlap": DIM_NARRATOR_ACTION_GROUNDING,
    "nar_v1_action_passes_bar": DIM_NARRATOR_ACTION_GROUNDING,
    "nar_environment_cue": DIM_NARRATOR_ENVIRONMENT_CUE,
    "nar_scope_proxy": DIM_NARRATOR_SCOPE_PROXY,
    "prose_readability": DIM_PROSE_READABILITY,
    "prose_redundancy": DIM_PROSE_REDUNDANCY,
    "prose_dialogue_integration": DIM_PROSE_DIALOGUE_INTEGRATION,
    "prose_attribution": DIM_PROSE_ATTRIBUTION,
    "prose_tone": DIM_PROSE_TONE,
}

# Prose redundancy jaccard: border band for escalation
PROSE_REDUNDANCY_BORDER_LOW = 0.55
PROSE_REDUNDANCY_BORDER_HIGH = 0.65


def _tri_state_ca1_ca2_excluded(_payload: dict[str, Any]) -> str:
    """Character Audit v1 CA1/CA2 are deprecated for Audit v2 escalation (Issues #13, #42).

    Raw payloads remain on scored rows for observability; this value is **not** a
    successful pass and must not be aggregated into dimension rollup.
    """
    return CHECK_RESULT_EXCLUDED_DEPRECATED


def _tri_state_ca4(payload: dict[str, Any]) -> str:
    band = str(payload.get("band", "") or "")
    if band == "high":
        return "fail"
    if band == "moderate":
        return "border"
    return "pass"


def _tri_state_ca7(payload: dict[str, Any]) -> str:
    cls = str(payload.get("classification", "") or "")
    fields = payload.get("fields_present")
    has_fields = isinstance(fields, list) and len(fields) > 0
    if has_fields and cls == "unclear":
        return "border"
    return "pass"


def _tri_state_nar_strict_overlap(payload: dict[str, Any]) -> str:
    ratio = float(payload.get("action_token_overlap_ratio", 0.0) or 0.0)
    action_empty = bool(payload.get("action_empty", False))
    if action_empty:
        return "pass"
    if ratio >= 0.12:
        return "pass"
    if ratio >= 0.05:
        return "border"
    return "fail"


def _tri_state_nar_v1_passes(payload: dict[str, Any]) -> str:
    return "pass" if payload.get("passes_bar") is True else "fail"


def _tri_state_nar_env(payload: dict[str, Any]) -> str:
    if not payload.get("environment_event_present"):
        return "pass"
    if int(payload.get("token_hits_in_render", 0) or 0) > 0:
        return "pass"
    return "fail"


def _tri_state_nar_scope(_payload: dict[str, Any]) -> str:
    """`nar_scope_proxy` / `single_actor_scope_heuristic` retired for gating (GitHub #9).

    Raw `passes_bar` / `other_cast_names_found` remain in payloads for historical review;
    escalation and dimension rollup always treat this check as **pass** so it cannot
    qualify LLM audit escalation on scope noise alone.
    """
    return "pass"


def _tri_state_masked_progression_observation(_payload: dict[str, Any]) -> str:
    """Strict masked progression is log-only observability (GitHub #73).

    Payload may record ``observation`` ``fired`` / ``clear`` / ``skipped``; tri-state for
    escalation is always **pass** so this never qualifies LLM audit or product failure.
    """
    return "pass"


def _tri_state_prose_bool_passes(payload: dict[str, Any]) -> str:
    return "pass" if payload.get("passes_bar") is True else "fail"


def _tri_state_prose_redundancy(payload: dict[str, Any]) -> str:
    if int(payload.get("prior_turns_used", 0) or 0) == 0:
        return "pass"
    j = float(payload.get("jaccard_word_overlap", 0.0) or 0.0)
    if j >= PROSE_REDUNDANCY_BORDER_HIGH:
        return "fail"
    if PROSE_REDUNDANCY_BORDER_LOW <= j < PROSE_REDUNDANCY_BORDER_HIGH:
        return "border"
    return "pass"


_CHECK_EVALUATORS: dict[str, Any] = {
    "char_ca1_motivation_action": _tri_state_ca1_ca2_excluded,
    "char_ca2_dialogue_action": _tri_state_ca1_ca2_excluded,
    "char_ca4_repetition": _tri_state_ca4,
    "char_ca7_declared_fields": _tri_state_ca7,
    "nar_strict_action_overlap": _tri_state_nar_strict_overlap,
    "nar_v1_action_passes_bar": _tri_state_nar_v1_passes,
    "nar_environment_cue": _tri_state_nar_env,
    "nar_scope_proxy": _tri_state_nar_scope,
    "char_masked_progression_strict": _tri_state_masked_progression_observation,
    "prose_readability": _tri_state_prose_bool_passes,
    "prose_redundancy": _tri_state_prose_redundancy,
    "prose_dialogue_integration": _tri_state_prose_bool_passes,
    "prose_attribution": _tri_state_prose_bool_passes,
    "prose_tone": _tri_state_prose_bool_passes,
}


def evaluate_check_result(*, check_id: str, payload: dict[str, Any]) -> str:
    fn = _CHECK_EVALUATORS.get(check_id)
    if fn is None:
        return "pass"
    return fn(payload)


def _dimension_aggregate(results: list[str]) -> str:
    """Single dimension rollup: fail > border > pass conflict detection."""
    s = set(results)
    if "fail" in s and "pass" in s:
        return "conflict"
    if "fail" in s and "border" in s:
        return "conflict"
    if len(s) > 1 and s == {"pass", "border"}:
        # pass + border only: treat as border (no escalation conflict)
        return "border"
    if "fail" in s:
        return "fail"
    if "border" in s:
        return "border"
    return "pass"


def _ca1_ca2_results(scored: list[dict[str, Any]]) -> tuple[str, str]:
    r1, r2 = "unknown", "unknown"
    for row in scored:
        cid = str(row.get("check_id", "") or "")
        if cid == "char_ca1_motivation_action":
            r1 = str(row.get("result", "") or "")
        elif cid == "char_ca2_dialogue_action":
            r2 = str(row.get("result", "") or "")
    return r1, r2


def build_intra_move_summary(
    *,
    ca1_result: str,
    ca2_result: str,
    intra_move_aggregate: str,
) -> dict[str, Any]:
    """P2: derived from CA1/CA2 scored results and intra dimension aggregate."""
    intra = intra_move_aggregate
    if intra == DIMENSION_AGGREGATE_NOT_APPLICABLE:
        pattern = "intra_move_not_applicable"
        human_readable = (
            "Character Audit v1 CA1/CA2 are excluded from Audit v2 escalation (deprecated, "
            "Issues #13 / #42); character_intra_move_coherence has no active escalation "
            "contributors. Raw CA1/CA2 metrics remain on checks[].payload for observability."
        )
    elif intra == "conflict":
        pattern = "intra_move_conflict"
        human_readable = (
            "CA1 and CA2 disagree on intra-move coherence (pass vs fail/border); "
            "treated as a conflict under escalation policy."
        )
    elif intra == "border":
        pattern = "intra_move_border"
        human_readable = (
            "Intra-move aggregate is border (mixed pass/border on CA1/CA2)."
        )
    elif intra == "fail":
        pattern = "intra_move_fail_aligned"
        human_readable = (
            "CA1 and CA2 both failed; intra-move aggregate is fail-only (aligned). "
            "Escalation on intra-move alone does not apply; compound rules may still qualify."
        )
    elif intra == "pass":
        pattern = "intra_move_pass"
        human_readable = "CA1 and CA2 both pass intra-move coherence checks."
    else:
        pattern = "intra_move_mixed"
        human_readable = f"Unexpected intra-move aggregate state: {intra!r}."
    return {
        "schema_version": 1,
        "pattern": pattern,
        "human_readable": human_readable[:512],
        "ca1_result": ca1_result,
        "ca2_result": ca2_result,
        "intra_move_aggregate": intra,
    }


def _maybe_compound_intra_move_ambiguity(
    *, layer: str, dim_agg: dict[str, str]
) -> dict[str, Any] | None:
    """P1: intra fail + other character dimension border|conflict; exclude repetition-fail-only."""
    if layer != "character_decision":
        return None
    if dim_agg.get(DIM_CHARACTER_INTRA_MOVE) != "fail":
        return None
    rep = dim_agg.get(DIM_CHARACTER_REPETITION)
    decl = dim_agg.get(DIM_CHARACTER_DECLARED_FIELDS)
    # EXCLUDE: structural_repetition == "fail" alone does not satisfy B (no declared ambiguity).
    if rep == "fail" and decl not in ("border", "conflict"):
        return None
    secondary: list[str] = []
    for d in (DIM_CHARACTER_REPETITION, DIM_CHARACTER_DECLARED_FIELDS):
        v = dim_agg.get(d)
        if v in ("border", "conflict"):
            secondary.append(d)
    if not secondary:
        return None
    return {
        "code": "compound_intra_move_ambiguity",
        "layer": "character_decision",
        "dimension_id": DIM_CHARACTER_INTRA_MOVE,
        "detail": {
            "intra_move_aggregate": "fail",
            "secondary_ambiguous_dimensions": secondary,
            "secondary_aggregates": {
                DIM_CHARACTER_REPETITION: rep or "",
                DIM_CHARACTER_DECLARED_FIELDS: decl or "",
            },
        },
    }


def compute_escalation_for_layer(
    *,
    layer: str,
    checks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Score checks and compute escalation reasons.

    Each check dict must have: check_id, dimension_id, payload (metrics dict).
    Returns (scored_checks, escalation_summary, layer_extras).

    layer_extras is non-empty only for character_decision (intra_move_summary before P1).
    """
    scored: list[dict[str, Any]] = []
    for c in checks:
        cid = str(c.get("check_id", "") or "")
        dim = str(c.get("dimension_id", "") or "") or CHECK_TO_DIMENSION.get(
            cid, ""
        )
        payload = c.get("payload") if isinstance(c.get("payload"), dict) else {}
        result = evaluate_check_result(check_id=cid, payload=payload)
        scored.append(
            {
                "check_id": cid,
                "dimension_id": dim,
                "result": result,
                "payload": dict(payload),
            }
        )

    by_dim: dict[str, list[str]] = defaultdict(list)
    for row in scored:
        cid = str(row.get("check_id", "") or "")
        if cid in _CHECK_IDS_EXCLUDED_FROM_ESCALATION_AGGREGATION:
            continue
        dim_id = str(row.get("dimension_id", "") or "")
        if not dim_id:
            continue
        by_dim[dim_id].append(str(row["result"]))

    reasons: list[dict[str, Any]] = []
    dim_agg: dict[str, str] = {}
    for dim, res_list in by_dim.items():
        if not dim:
            continue
        agg = _dimension_aggregate(res_list)
        dim_agg[dim] = agg
        if agg == "conflict":
            reasons.append(
                {
                    "code": "same_dimension_conflict",
                    "dimension_id": dim,
                    "layer": layer,
                }
            )

    if layer == "character_decision" and DIM_CHARACTER_INTRA_MOVE not in dim_agg:
        dim_agg[DIM_CHARACTER_INTRA_MOVE] = DIMENSION_AGGREGATE_NOT_APPLICABLE

    for row in scored:
        if row["result"] == "border":
            reasons.append(
                {
                    "code": "border_band",
                    "dimension_id": row["dimension_id"],
                    "check_id": row["check_id"],
                    "layer": layer,
                }
            )

    layer_extras: dict[str, Any] = {}
    if layer == "character_decision":
        ca1_r, ca2_r = _ca1_ca2_results(scored)
        intra = dim_agg.get(DIM_CHARACTER_INTRA_MOVE, "")
        layer_extras["intra_move_summary"] = build_intra_move_summary(
            ca1_result=ca1_r,
            ca2_result=ca2_r,
            intra_move_aggregate=intra,
        )

    qualified = bool(reasons)
    compound = _maybe_compound_intra_move_ambiguity(layer=layer, dim_agg=dim_agg)
    if compound is not None:
        reasons.append(compound)
        qualified = True

    escalation_summary = {
        "qualified": qualified,
        "reasons": reasons,
        "dimension_aggregate": dim_agg,
    }

    return scored, escalation_summary, layer_extras


def dimensions_for_layer(layer: str) -> list[str]:
    if layer == "character_decision":
        return [
            DIM_CHARACTER_INTRA_MOVE,
            DIM_CHARACTER_REPETITION,
            DIM_CHARACTER_DECLARED_FIELDS,
            DIM_CHARACTER_MASKED_PROGRESSION,
        ]
    if layer == "narrator_output":
        return [
            DIM_NARRATOR_ACTION_GROUNDING,
            DIM_NARRATOR_ENVIRONMENT_CUE,
            DIM_NARRATOR_SCOPE_PROXY,
        ]
    if layer == "prose_dialogue":
        return [
            DIM_PROSE_READABILITY,
            DIM_PROSE_REDUNDANCY,
            DIM_PROSE_DIALOGUE_INTEGRATION,
            DIM_PROSE_ATTRIBUTION,
            DIM_PROSE_TONE,
        ]
    return []
