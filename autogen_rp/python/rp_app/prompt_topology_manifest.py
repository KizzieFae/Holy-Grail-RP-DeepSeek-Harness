"""Issue #242 — observational prompt topology manifest (offline only)."""

from __future__ import annotations

from typing import Any

from prompt_topology_issue240 import (
    ISSUE240_DOCTRINE_PHRASE,
    ISSUE240_SEMANTIC_BLOCK_HEADER,
    ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER,
    ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER,
    ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER,
    ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER,
    ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER,
    ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER,
    ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER,
    ISSUE240_V1_OPENING_MARKER,
    _ISSUE240_COMPRESS_NOTE,
)

PRODUCTION_OPENING = "You are taking your next turn in an ongoing roleplay scene."
TRIGGER_HEADER = "TRIGGER FOR THIS BEAT:"
PRIVATE_STATE_HEADER = "YOUR PRIVATE STATE:"
OUTPUT_RULES_HEADER = "OUTPUT RULES:"
PRIORITIES_FULL_MARKER = "Treat absent-but-relevant characters as continuity context only"
PRIORITIES_COMPRESSED_MARKER = "5. SOCIAL REALISM"
PRODUCTION_SEMANTIC_PROPOSALS_RULE = "Covered semantic intent (``semantic_proposals``)"
SLIM_OUTPUT_RULES_MARKER = "sleeping_surface_assignment"
BINDING_CONSTRAINTS_MARKER = "BINDING CONSTRAINTS"
EVIDENCE_DISCIPLINE_MARKER = "EVIDENCE & AUTHORITY DISCIPLINE"
SEMANTIC_EVAL_EXAMPLES_MARKER = "``no_covered_change``"
BEAT_SHIFT_SUFFIX_MARKER = "BEAT SHIFT (ACTIVE):"
PROGRESSION_SUFFIX_MARKER = "PROGRESSION ADVISORY:"

MARKER_KEYS: tuple[str, ...] = (
    "opening_production",
    "opening_dual_role",
    "semantic_self_report",
    "participation_frame",
    "semantic_evaluation_required",
    "semantic_evaluation_examples",
    "threshold_bridge_v1_next6",
    "threshold_calibration_v1_next7",
    "participation_arc",
    "social_focus_capsule",
    "active_focus_capsule",
    "doctrine_phrase",
    "priorities_compressed_5_7",
    "output_rules_slim",
    "output_rules_production_semantic_proposals",
    "binding_constraints",
    "evidence_authority_discipline",
    "long_prompt_compression_note",
    "beat_shift_suffix",
    "progression_advisory_suffix",
)

ORDERING_SECTIONS: tuple[str, ...] = (
    "opening_dual_role",
    "opening_production",
    "trigger",
    "semantic_self_report",
    "participation_frame",
    "threshold_calibration",
    "participation_arc",
    "threshold_bridge",
    "active_focus",
    "social_focus",
    "private_state",
    "priorities",
    "output_rules",
    "beat_shift_suffix",
    "progression_suffix",
)


def _find_offset(text: str, needle: str) -> int | None:
    idx = text.find(needle)
    return idx if idx >= 0 else None


def _infer_present_character_count(system_text: str) -> int | None:
    import json
    import re

    state_match = re.search(
        r"CURRENT SCENE STATE:\n(\{.*?\})\n\nSCENE TEMPLATE:",
        system_text,
        flags=re.DOTALL,
    )
    if state_match:
        try:
            state = json.loads(state_match.group(1))
            present = state.get("present_characters")
            if isinstance(present, list) and present:
                return len([x for x in present if str(x or "").strip()])
        except json.JSONDecodeError:
            pass

    for line in system_text.splitlines():
        if line.startswith("OTHER PRESENT CHARACTERS:"):
            tail = line.split(":", 1)[-1].strip()
            if not tail:
                return 0
            parts = [p.strip() for p in tail.split(",") if p.strip()]
            return len(parts)
    return None


def _infer_topology(markers: dict[str, bool]) -> str:
    if markers.get("threshold_calibration_v1_next7") and markers.get(
        "semantic_evaluation_required"
    ):
        return "v1_next7"
    if markers.get("semantic_evaluation_required"):
        return "v1_next5_plus"
    if markers.get("opening_dual_role") and markers.get("semantic_self_report"):
        return "v1_issue240"
    if markers.get("opening_production"):
        return "production"
    return "unknown"


def _marker_fingerprint(markers: dict[str, bool]) -> str:
    present = [key for key in MARKER_KEYS if markers.get(key)]
    short = {
        "opening_production": "opening.prod",
        "opening_dual_role": "opening.dual",
        "semantic_self_report": "semantic.block",
        "participation_frame": "frame",
        "semantic_evaluation_required": "eval.required",
        "semantic_evaluation_examples": "eval.examples",
        "threshold_bridge_v1_next6": "bridge.v6",
        "threshold_calibration_v1_next7": "cal.v7",
        "participation_arc": "arc",
        "social_focus_capsule": "social.focus",
        "active_focus_capsule": "active.focus",
        "doctrine_phrase": "doctrine",
        "priorities_compressed_5_7": "priorities.comp",
        "output_rules_slim": "output.slim",
        "output_rules_production_semantic_proposals": "output.prod.sem",
        "binding_constraints": "binding",
        "evidence_authority_discipline": "evidence",
        "long_prompt_compression_note": "compress.note",
        "beat_shift_suffix": "suffix.beat_shift",
        "progression_advisory_suffix": "suffix.progression",
    }
    return "|".join(short[k] for k in present)


def _output_rules_slice(system_text: str) -> str:
    idx = system_text.find(OUTPUT_RULES_HEADER)
    if idx < 0:
        return ""
    return system_text[idx:]


def _detect_markers(system_text: str) -> dict[str, bool]:
    output_rules = _output_rules_slice(system_text)
    output_rules_idx = _find_offset(system_text, OUTPUT_RULES_HEADER)
    beat_shift_idx = _find_offset(system_text, BEAT_SHIFT_SUFFIX_MARKER)
    progression_idx = _find_offset(system_text, PROGRESSION_SUFFIX_MARKER)

    def _suffix_after_output_rules(marker: str) -> bool:
        idx = _find_offset(system_text, marker)
        if idx is None or output_rules_idx is None:
            return idx is not None
        return idx > output_rules_idx

    return {
        "opening_production": PRODUCTION_OPENING in system_text,
        "opening_dual_role": ISSUE240_V1_OPENING_MARKER in system_text,
        "semantic_self_report": ISSUE240_SEMANTIC_BLOCK_HEADER in system_text,
        "participation_frame": ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER in system_text,
        "semantic_evaluation_required": (
            ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER in system_text
            or "required ``semantic_evaluation``" in system_text
        ),
        "semantic_evaluation_examples": SEMANTIC_EVAL_EXAMPLES_MARKER in system_text,
        "threshold_bridge_v1_next6": ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER in system_text,
        "threshold_calibration_v1_next7": ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER
        in system_text,
        "participation_arc": ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER in system_text,
        "social_focus_capsule": ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER in system_text,
        "active_focus_capsule": ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER in system_text,
        "doctrine_phrase": ISSUE240_DOCTRINE_PHRASE in system_text,
        "priorities_compressed_5_7": (
            PRIORITIES_COMPRESSED_MARKER in system_text
            and PRIORITIES_FULL_MARKER not in system_text
        ),
        "output_rules_slim": (
            output_rules != "" and SLIM_OUTPUT_RULES_MARKER not in output_rules
        ),
        "output_rules_production_semantic_proposals": (
            PRODUCTION_SEMANTIC_PROPOSALS_RULE in output_rules
        ),
        "binding_constraints": BINDING_CONSTRAINTS_MARKER in system_text,
        "evidence_authority_discipline": EVIDENCE_DISCIPLINE_MARKER in system_text,
        "long_prompt_compression_note": _ISSUE240_COMPRESS_NOTE in system_text,
        "beat_shift_suffix": _suffix_after_output_rules(BEAT_SHIFT_SUFFIX_MARKER)
        if beat_shift_idx is not None
        else False,
        "progression_advisory_suffix": _suffix_after_output_rules(PROGRESSION_SUFFIX_MARKER)
        if progression_idx is not None
        else False,
    }


def _ordering_offsets(system_text: str, markers: dict[str, bool]) -> dict[str, int | None]:
    offsets: dict[str, int | None] = {
        "trigger": _find_offset(system_text, TRIGGER_HEADER),
        "semantic_self_report": _find_offset(system_text, ISSUE240_SEMANTIC_BLOCK_HEADER)
        if markers["semantic_self_report"]
        else None,
        "participation_frame": _find_offset(
            system_text, ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER
        )
        if markers["participation_frame"]
        else None,
        "threshold_calibration": _find_offset(
            system_text, ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER
        )
        if markers["threshold_calibration_v1_next7"]
        else None,
        "participation_arc": _find_offset(
            system_text, ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER
        )
        if markers["participation_arc"]
        else None,
        "threshold_bridge": _find_offset(
            system_text, ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER
        )
        if markers["threshold_bridge_v1_next6"]
        else None,
        "active_focus": _find_offset(system_text, ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER)
        if markers["active_focus_capsule"]
        else None,
        "social_focus": _find_offset(system_text, ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER)
        if markers["social_focus_capsule"]
        else None,
        "private_state": _find_offset(system_text, PRIVATE_STATE_HEADER),
        "output_rules": _find_offset(system_text, OUTPUT_RULES_HEADER),
        "beat_shift_suffix": _find_offset(system_text, BEAT_SHIFT_SUFFIX_MARKER)
        if markers["beat_shift_suffix"]
        else None,
        "progression_suffix": _find_offset(system_text, PROGRESSION_SUFFIX_MARKER)
        if markers["progression_advisory_suffix"]
        else None,
        "prompt_end": len(system_text),
    }
    if markers["opening_dual_role"]:
        offsets["opening_dual_role"] = _find_offset(system_text, ISSUE240_V1_OPENING_MARKER)
    elif markers["opening_production"]:
        offsets["opening_production"] = _find_offset(system_text, PRODUCTION_OPENING)
    else:
        offsets["opening_dual_role"] = None
        offsets["opening_production"] = None
    priorities_idx = _find_offset(system_text, PRIORITIES_COMPRESSED_MARKER)
    offsets["priorities"] = priorities_idx
    return offsets


def _section_sequence(offsets: dict[str, int | None]) -> list[str]:
    named = [
        (name, offsets.get(name))
        for name in ORDERING_SECTIONS
        if offsets.get(name) is not None
    ]
    named.sort(key=lambda item: item[1] or 0)
    return [name for name, _ in named]


def _adjacency(
    system_text: str,
    offsets: dict[str, int | None],
    markers: dict[str, bool],
) -> dict[str, Any]:
    trig = offsets.get("trigger")
    sem = offsets.get("semantic_self_report")
    priv = offsets.get("private_state")
    out_rules = offsets.get("output_rules")
    end = offsets.get("prompt_end")

    trigger_to_semantic: int | None = None
    if trig is not None and sem is not None and sem >= trig:
        trigger_to_semantic = sem - trig

    semantic_cluster_end = sem
    for key in (
        "participation_frame",
        "threshold_calibration",
        "participation_arc",
        "threshold_bridge",
        "active_focus",
        "social_focus",
    ):
        idx = offsets.get(key)
        if idx is not None and (semantic_cluster_end is None or idx > semantic_cluster_end):
            semantic_cluster_end = idx

    semantic_cluster_span: int | None = None
    if sem is not None and semantic_cluster_end is not None:
        semantic_cluster_span = semantic_cluster_end - sem

    private_to_output: int | None = None
    if priv is not None and out_rules is not None and out_rules >= priv:
        private_to_output = out_rules - priv

    output_to_end: int | None = None
    if out_rules is not None and end is not None:
        output_to_end = end - out_rules

    trigger_window_ok = False
    if trig is not None and sem is not None:
        window = system_text[trig:sem]
        trigger_window_ok = TRIGGER_HEADER in window

    arc = offsets.get("participation_arc")
    eval_marker_idx = _find_offset(system_text, ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER)
    arc_to_eval: int | None = None
    if arc is not None and eval_marker_idx is not None:
        arc_to_eval = abs(arc - eval_marker_idx)

    return {
        "trigger_to_semantic_self_report_chars": trigger_to_semantic,
        "semantic_cluster_span_chars": semantic_cluster_span,
        "participation_arc_to_semantic_eval_marker_chars": arc_to_eval,
        "private_state_to_output_rules_chars": private_to_output,
        "output_rules_to_prompt_end_chars": output_to_end,
        "semantic_self_report_before_private_state": (
            sem is not None and priv is not None and sem < priv
        ),
        "semantic_self_report_before_output_rules": (
            sem is not None and out_rules is not None and sem < out_rules
        ),
        "trigger_text_contained_in_trigger_to_semantic_window": trigger_window_ok,
    }


def _expected_profile_id(
    *,
    topology_inferred: str,
    present_character_count: int | None,
) -> str:
    if topology_inferred in {"v1_next7", "v1_next5_plus", "v1_issue240"}:
        if present_character_count is not None and present_character_count >= 3:
            return "v1_next7_3char_plus"
        return "v1_next7_2char"
    if topology_inferred == "production":
        return "production_baseline"
    return "unknown"


def _profile_requirements(profile_id: str) -> tuple[frozenset[str], list[tuple[str, str]]]:
    """Return required markers and ordering pairs (left before right)."""
    common_v1_next7 = frozenset(
        {
            "opening_dual_role",
            "semantic_self_report",
            "participation_frame",
            "semantic_evaluation_required",
            "threshold_calibration_v1_next7",
            "priorities_compressed_5_7",
            "output_rules_slim",
        }
    )
    three_char_extra = frozenset(
        {
            "participation_arc",
            "threshold_bridge_v1_next6",
            "active_focus_capsule",
        }
    )
    ordering_2char = [
        ("trigger", "semantic_self_report"),
        ("semantic_self_report", "participation_frame"),
        ("participation_frame", "threshold_calibration"),
        ("threshold_calibration", "private_state"),
        ("private_state", "output_rules"),
    ]
    ordering_3char = [
        ("semantic_self_report", "participation_frame"),
        ("participation_frame", "threshold_calibration"),
        ("threshold_calibration", "participation_arc"),
        ("participation_arc", "threshold_bridge"),
        ("threshold_bridge", "active_focus"),
        ("active_focus", "private_state"),
    ]
    production_required = frozenset(
        {
            "opening_production",
            "output_rules_production_semantic_proposals",
        }
    )
    if profile_id == "v1_next7_3char_plus":
        return common_v1_next7 | three_char_extra, ordering_3char
    if profile_id == "v1_next7_2char":
        return common_v1_next7, ordering_2char
    if profile_id == "production_baseline":
        return production_required, []
    return frozenset(), []


def _profile_match(
    *,
    profile_id: str,
    markers: dict[str, bool],
    offsets: dict[str, int | None],
) -> tuple[bool, list[str]]:
    required, ordering_pairs = _profile_requirements(profile_id)
    deviations: list[str] = []
    for key in sorted(required):
        if not markers.get(key):
            deviations.append(f"missing_marker:{key}")
    for left, right in ordering_pairs:
        l_idx = offsets.get(left)
        r_idx = offsets.get(right)
        if l_idx is None or r_idx is None:
            continue
        if not l_idx < r_idx:
            deviations.append(f"ordering_violation:{left}_not_before_{right}")
    return (len(deviations) == 0, deviations)


def extract_topology_manifest(
    system_text: str,
    *,
    present_character_count: int | None = None,
) -> dict[str, Any]:
    """Pure observational topology manifest from a character turn system prompt."""
    text = str(system_text or "")
    markers = _detect_markers(text)
    topology_inferred = _infer_topology(markers)
    if present_character_count is None:
        present_character_count = _infer_present_character_count(text)

    offsets = _ordering_offsets(text, markers)
    adjacency = _adjacency(text, offsets, markers)
    profile_id = _expected_profile_id(
        topology_inferred=topology_inferred,
        present_character_count=present_character_count,
    )
    match, deviations = _profile_match(
        profile_id=profile_id,
        markers=markers,
        offsets=offsets,
    )

    output_rules_idx = offsets.get("output_rules")
    prompt_end = offsets.get("prompt_end") or len(text)
    output_rules_chars = (
        prompt_end - output_rules_idx if output_rules_idx is not None else None
    )

    return {
        "present_character_count": present_character_count,
        "topology_inferred": topology_inferred,
        "size": {
            "system_chars": len(text),
            "output_rules_chars": output_rules_chars,
            "output_rules_pct_from_end": round(100 * output_rules_chars / len(text), 1)
            if output_rules_chars is not None and text
            else None,
        },
        "markers": markers,
        "ordering": {
            "section_sequence": _section_sequence(offsets),
            "offsets": {k: v for k, v in offsets.items() if k != "prompt_end"},
        },
        "adjacency": adjacency,
        "topology_fingerprint": _marker_fingerprint(markers),
        "expected_profile_id": profile_id,
        "profile_match": match,
        "profile_deviations": deviations,
    }


def aggregate_topology_manifest_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Session-level aggregate from per-turn topology rows."""
    if not rows:
        return {
            "turn_count": 0,
            "profile_match_rate": None,
            "ordering_violation_count": 0,
            "dominant_fingerprint": None,
            "fingerprint_unique_count": 0,
        }

    fingerprints = [str(r.get("topology_fingerprint") or "") for r in rows]
    fp_counts: dict[str, int] = {}
    for fp in fingerprints:
        fp_counts[fp] = fp_counts.get(fp, 0) + 1
    dominant = max(fp_counts, key=fp_counts.get)

    profile_matches = [bool(r.get("profile_match")) for r in rows]
    ordering_violations = sum(
        1
        for r in rows
        for d in r.get("profile_deviations") or []
        if str(d).startswith("ordering_violation:")
    )

    def _rate(marker_key: str) -> float:
        hits = sum(1 for r in rows if (r.get("markers") or {}).get(marker_key))
        return round(hits / len(rows), 3)

    trigger_to_sem = [
        (r.get("adjacency") or {}).get("trigger_to_semantic_self_report_chars")
        for r in rows
    ]
    trigger_to_sem = [x for x in trigger_to_sem if isinstance(x, int)]
    output_tail = [
        (r.get("adjacency") or {}).get("output_rules_to_prompt_end_chars") for r in rows
    ]
    output_tail = [x for x in output_tail if isinstance(x, int)]

    def _median(values: list[int]) -> int | None:
        if not values:
            return None
        s = sorted(values)
        mid = len(s) // 2
        if len(s) % 2:
            return s[mid]
        return (s[mid - 1] + s[mid]) // 2

    return {
        "turn_count": len(rows),
        "dominant_fingerprint": dominant,
        "fingerprint_unique_count": len(fp_counts),
        "profile_match_rate": round(sum(profile_matches) / len(profile_matches), 3),
        "ordering_violation_count": ordering_violations,
        "adaptive_capsule_emit_rate": {
            "participation_arc": _rate("participation_arc"),
            "active_focus_capsule": _rate("active_focus_capsule"),
            "social_focus_capsule": _rate("social_focus_capsule"),
        },
        "suffix_emit_rate": {
            "beat_shift": _rate("beat_shift_suffix"),
            "progression": _rate("progression_advisory_suffix"),
        },
        "median_adjacency": {
            "trigger_to_semantic_self_report_chars": _median(trigger_to_sem),
            "output_rules_to_prompt_end_chars": _median(output_tail),
        },
    }
