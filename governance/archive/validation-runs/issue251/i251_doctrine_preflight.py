"""Issue #251 — scoped active-doctrine preflight (physical/perceptual severance).



Scans injected doctrine regions only; ignores inert frozen-audit historical text.

"""



from __future__ import annotations



import re

from typing import Any



from prompt_topology_issue240 import (

    ISSUE240_SEMANTIC_BLOCK_HEADER,

    ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER,

    ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_MARKER,

    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,

    ISSUE251_AWARENESS_CLEAN_MARKER,

    ISSUE251_AWARENESS_DOCTRINE_MARKER,

    ISSUE251_CANONICAL_SEVERANCE_DOCTRINE_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_GUARDED_DOCTRINE_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

    ISSUE251_REJECTED_CONTINUITY_PRESERVATION_PHRASE,

    build_issue251_physical_severance_doctrine_block,

    build_issue251_physical_severance_guarded_doctrine_block,

)



PREFLIGHT_SCHEMA = "issue251_active_doctrine_preflight.v1"



_ACTIVE_FORBIDDEN_MARKERS: tuple[str, ...] = (

    ISSUE251_AWARENESS_DOCTRINE_MARKER,

    ISSUE251_AWARENESS_CLEAN_MARKER,

    ISSUE251_CANONICAL_SEVERANCE_DOCTRINE_MARKER,

    ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER,

    ISSUE240_V1_NEXT7_PARTICIPATION_BOUNDARY_B_MARKER,

)



_ACTIVE_FORBIDDEN_PHRASES: tuple[str, ...] = (

    "all four",

    "shared-awareness continuity",

    "shared scene awareness continuity ends",

    "awareness continuity ends",

    "temporary-task framing alone",

    "physical displacement alone",

    "doorway tether",

    "Margin, doorway tether, or temporary-task framing without shared-awareness severance",

    "no longer participate in the live exchange",

    "continue/deepen/reverse",

    "partially withdrawn",

    "margin withdrawal/rejoin",

    ISSUE251_REJECTED_CONTINUITY_PRESERVATION_PHRASE,

)



_ARM_B_REQUIRED_MARKERS: tuple[str, ...] = (

    ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER,

    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,

)



_ARM_C_REQUIRED_MARKERS: tuple[str, ...] = (

    ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_GUARDED_DOCTRINE_MARKER,

    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,

)



_ARM_C_REQUIRED_PHRASES: tuple[str, ...] = (
    "Do not complete or assume exits the beat does not complete.",
    "fully left the shared scene",
    "outside the shared scene space",
    "live exchange with those who remain no longer continuing",
    "not ``off_focal`` by themselves",
)



_ARM_C_FORBIDDEN_ARM_B_MARKERS: tuple[str, ...] = (

    ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER,

    ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

)





def extract_active_doctrine_slices(

    prompt: str,

    *,

    isolation_marker: str = ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

) -> dict[str, str]:

    """Return injected opening + semantic/doctrine regions (not full frozen audit body)."""

    opening_end = 2500

    iso_idx = prompt.find(isolation_marker)

    if iso_idx >= 0:

        opening_end = min(len(prompt), iso_idx + 800)

    opening_slice = prompt[:opening_end]



    semantic_match = re.search(

        rf"{re.escape(ISSUE240_SEMANTIC_BLOCK_HEADER)}.*?Do not explain this analysis in dialogue or action beats\.",

        prompt,

        flags=re.DOTALL,

    )

    semantic_slice = semantic_match.group(0) if semantic_match else ""



    output_match = re.search(r"OUTPUT RULES:.*\Z", prompt, flags=re.DOTALL)

    output_slice = output_match.group(0)[:4000] if output_match else ""



    combined = "\n".join(s for s in (opening_slice, semantic_slice, output_slice) if s)

    return {

        "opening_slice": opening_slice,

        "semantic_doctrine_slice": semantic_slice,

        "output_rules_slice": output_slice,

        "active_doctrine_combined": combined,

    }





def _contamination_hits(

    prompt: str,

    *,

    required_markers: tuple[str, ...],

    required_phrases: tuple[str, ...] = (),

    forbidden_arm_markers: tuple[str, ...] = (),

    isolation_marker: str,

    doctrine_block: str,

) -> list[str]:

    slices = extract_active_doctrine_slices(prompt, isolation_marker=isolation_marker)

    active = slices["active_doctrine_combined"]

    if not active.strip():

        return ["missing:active_doctrine_slices"]



    hits: list[str] = []

    for marker in required_markers:

        if marker not in active:

            hits.append(f"missing:{marker}")

    for phrase in required_phrases:

        if phrase not in active:

            hits.append(f"missing_phrase:{phrase}")

    for marker in _ACTIVE_FORBIDDEN_MARKERS:

        if marker in active:

            hits.append(f"forbidden_marker:{marker}")

    for marker in forbidden_arm_markers:

        if marker in active:

            hits.append(f"forbidden_arm_marker:{marker}")

    for phrase in _ACTIVE_FORBIDDEN_PHRASES:

        if phrase in active:

            hits.append(f"forbidden_phrase:{phrase}")

    semantic = slices["semantic_doctrine_slice"]

    if doctrine_block and doctrine_block not in semantic:

        hits.append("doctrine_block_mismatch")

    return hits





def active_physical_severance_contamination_hits(prompt: str) -> list[str]:

    """Contamination hits limited to active injected doctrine slices (Arm B)."""

    return _contamination_hits(

        prompt,

        required_markers=_ARM_B_REQUIRED_MARKERS,

        isolation_marker=ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

        doctrine_block=build_issue251_physical_severance_doctrine_block(),

    )





def active_physical_severance_guarded_contamination_hits(prompt: str) -> list[str]:

    """Contamination hits limited to active injected doctrine slices (Arm C)."""

    return _contamination_hits(

        prompt,

        required_markers=_ARM_C_REQUIRED_MARKERS,

        required_phrases=_ARM_C_REQUIRED_PHRASES,

        forbidden_arm_markers=_ARM_C_FORBIDDEN_ARM_B_MARKERS,

        isolation_marker=ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER,

        doctrine_block=build_issue251_physical_severance_guarded_doctrine_block(),

    )





def _build_preflight(

    prompt: str,

    *,

    topology: str,

    doctrine_schema_version: str,

    contamination_hits_fn,

    required_markers: tuple[str, ...],

    doctrine_block: str,

    isolation_marker: str,

) -> dict[str, Any]:

    slices = extract_active_doctrine_slices(prompt, isolation_marker=isolation_marker)

    hits = contamination_hits_fn(prompt)

    semantic = slices["semantic_doctrine_slice"]

    doctrine_excerpt = semantic[:1200] if semantic else ""

    return {

        "schema_version": PREFLIGHT_SCHEMA,

        "topology": topology,

        "doctrine_schema_version": doctrine_schema_version,

        "scan_scope": "active_injected_doctrine_only",

        "scan_regions": [

            "opening_through_isolation_marker",

            "semantic_self_report_block",

            "output_rules_tail",

        ],

        "ignored_regions": [

            "frozen_audit_scene_history",

            "archived_participation_ontology_in_audit_body",

            "inert_source_artifact_text_outside_injected_slices",

        ],

        "required_markers_present": {

            m: m in slices["active_doctrine_combined"]

            for m in required_markers

        },

        "forbidden_active_doctrine_absent": {

            m: m not in slices["active_doctrine_combined"]

            for m in _ACTIVE_FORBIDDEN_MARKERS

        },

        "contamination_hits": hits,

        "contamination_clean": hits == [],

        "doctrine_block_matches_spec": doctrine_block in semantic,

        "active_doctrine_excerpt": doctrine_excerpt,

        "slice_lengths": {k: len(v) for k, v in slices.items()},

    }





def build_physical_severance_preflight(

    prompt: str,

    *,

    topology: str = "v1_next7_issue251_physical_severance_v1",

    doctrine_schema_version: str = "physical_severance_v1",

) -> dict[str, Any]:

    return _build_preflight(

        prompt,

        topology=topology,

        doctrine_schema_version=doctrine_schema_version,

        contamination_hits_fn=active_physical_severance_contamination_hits,

        required_markers=_ARM_B_REQUIRED_MARKERS,

        doctrine_block=build_issue251_physical_severance_doctrine_block(),

        isolation_marker=ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,

    )





def build_physical_severance_guarded_preflight(

    prompt: str,

    *,

    topology: str = "v1_next7_issue251_physical_severance_guarded_v1",

    doctrine_schema_version: str = "physical_severance_guarded_v1",

) -> dict[str, Any]:

    return _build_preflight(

        prompt,

        topology=topology,

        doctrine_schema_version=doctrine_schema_version,

        contamination_hits_fn=active_physical_severance_guarded_contamination_hits,

        required_markers=_ARM_C_REQUIRED_MARKERS,

        doctrine_block=build_issue251_physical_severance_guarded_doctrine_block(),

        isolation_marker=ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER,

    )


