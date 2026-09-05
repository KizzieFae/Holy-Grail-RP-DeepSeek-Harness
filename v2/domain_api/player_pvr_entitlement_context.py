"""PlayerPvrEntitlementContextV1 assembly for full player PVR (#125).

Purpose
-------
Supply the minimum authoritative session/scene facts full player PVR needs to
interpret roster-, presence-, offstage-, and role-dependent recipient semantics
without inventing geometry, co-location, audibility, or unsupported private
entitlement. Successor to #112 entitlement-context gap; coordinates with #120
(semantic kinds), #121 (triage routing), and #124 (deterministic normalization).

Assembly point
----------------
Host ``prepare_player_decomposition_context`` (``player_decomposition_context.py``)
adds one authoritative manifest contribution before the decomposition instruction.

Contract (V1)
-------------
``schema_version``, ``session_cast``, ``present_characters``, ``offstage_characters``,
``role_assignments``.

Authority sources
-----------------
- ``session_cast`` ← ``LiveSession.cast`` (authoritative session cast)
- ``present_characters`` ← ``ContinuityManager.scene_state.present_characters``
- ``offstage_characters`` ← ``Continuity.scene_state.offstage_characters``
- ``role_assignments`` ← ``Continuity.scene_state.role_assignments``

Semantics
---------
- ``present_characters``: focal immediate-shared-space population for ``present`` /
  ``public`` scope only; empty list preserved (no cast fallback).
- ``offstage_characters``: in-scene but outside that focal set; not present/public members.
- Neither field establishes co-location, line of sight, audibility, door/room geometry,
  or named private-recipient entitlement.
- ``session_cast`` bounds named ``recipients.characters``.
- ``role_assignments`` may support ``role_private`` when player source supports it.
- Unknown remains unknown; no synthesis from incomplete categories.

Deliberate exclusions
---------------------
No ``location_label``, presence annotations/constraints, grounding, transcript,
knowledge, Librarian/retrieval, Director/Storyteller advisory, or spatial simulation.

Forensic evidence
-----------------
Manifest contribution ``source_kind: player_pvr_entitlement_context`` with full JSON
content and ``provenance.context`` is persisted via existing execution-evidence /
request-contributions linkage (``generation.inference_id`` / ``evidence_id``).
Deterministic normalization, canonical PVR, and viewer projection remain downstream.

Celina/Harley diagnostic
------------------------
Historical Celina entitlement from pre-#125 tests is not normative; re-baseline to
authoritative facts actually supplied. Player prose may support semantic private scope;
presence membership alone does not prove fine-grained private entitlement.
"""

from __future__ import annotations

import json
from typing import Any

from .contract import PromptContribution
from .session_state import LiveSession

PLAYER_PVR_ENTITLEMENT_CONTEXT_SCHEMA_VERSION = 1
PLAYER_PVR_ENTITLEMENT_CONTEXT_SOURCE_KIND = "player_pvr_entitlement_context"

PLAYER_PVR_ENTITLEMENT_INTERPRETATION_INSTRUCTION = """
ENTITLEMENT INTERPRETATION (bound to PlayerPvrEntitlementContextV1 above):
- session_cast: the only character names you may use in recipients.characters.
- present_characters: authoritative focal population for present/public scope semantics only.
- offstage_characters: in-scene characters outside that immediate shared space; not present/public members.
- role_assignments: authoritative roles for role_private targeting when player source supports it.
- Preserve authoritative empties; do not substitute cast for empty presence or synthesize missing facts.
- Presence facts constrain scope semantics; they do not manufacture named private entitlement.
- Membership in present_characters is NOT sufficient to justify a named private or directed recipient.
- Neither present_characters nor offstage_characters establish co-location, line of sight, audibility,
  door/room geometry, or private-recipient entitlement.
- Named private/directed recipients require support from the player-authored source or another explicit
  authoritative recipient fact supplied outside this context.
- Do not infer geometry or perceptual facts from coarse presence categories.
- Deterministic downstream normalization, validation, and viewer projection remain outside semantic PVR.
"""


def assemble_player_pvr_entitlement_context_v1(fixture: LiveSession) -> dict[str, Any]:
    """Project the minimum authoritative entitlement context from session + Continuity scene state."""
    mgr = fixture.manager
    assert mgr.scene_state is not None
    return {
        "schema_version": PLAYER_PVR_ENTITLEMENT_CONTEXT_SCHEMA_VERSION,
        "session_cast": list(fixture.cast),
        "present_characters": list(mgr.scene_state.present_characters),
        "offstage_characters": list(mgr.scene_state.offstage_characters),
        "role_assignments": dict(mgr.scene_state.role_assignments),
    }


def format_player_pvr_entitlement_context_content(context: dict[str, Any]) -> str:
    payload = json.dumps(context, indent=2, sort_keys=True)
    return (
        "AUTHORITATIVE ENTITLEMENT CONTEXT (PlayerPvrEntitlementContextV1):\n"
        "Use ONLY these facts for roster, presence, offstage, and role-dependent recipient semantics.\n"
        "Do not infer room geometry, line of sight, audibility, co-location, or named private-recipient "
        "entitlement from presence lists alone.\n\n"
        f"{payload}\n"
    )


def build_player_pvr_entitlement_context_contribution(
    *,
    manifest_id: str,
    inference_id: str,
    fixture: LiveSession,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
) -> PromptContribution:
    context = assemble_player_pvr_entitlement_context_v1(fixture)
    mgr = fixture.manager
    assert mgr.scene_state is not None
    return PromptContribution(
        contribution_id=f"{manifest_id}-entitlement-context",
        source_kind=PLAYER_PVR_ENTITLEMENT_CONTEXT_SOURCE_KIND,
        authority_class="authoritative",
        knowledge_ids=(f"scene:{hg_scene_id}",),
        priority=5,
        content=format_player_pvr_entitlement_context_content(context),
        provenance={
            "inference_id": inference_id,
            "role": "player_decomposition",
            "projection_kind": "player_pvr_entitlement_context_v1",
            "schema_version": PLAYER_PVR_ENTITLEMENT_CONTEXT_SCHEMA_VERSION,
            "authoritative_sources": {
                "session_cast": "session.cast",
                "present_characters": "continuity.scene_state.present_characters",
                "offstage_characters": "continuity.scene_state.offstage_characters",
                "role_assignments": "continuity.scene_state.role_assignments",
            },
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "turn_index": turn_index,
            "continuity_version": fixture.continuity_version,
            "context": context,
        },
    )
