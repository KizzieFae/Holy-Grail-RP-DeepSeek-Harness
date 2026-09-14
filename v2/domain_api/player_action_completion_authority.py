"""Player action completion authority contract for Character semantic evaluation (#193)."""

from __future__ import annotations

from typing import Any

PLAYER_ACTION_COMPLETION_GUARDRAIL_ID = "guardrail:player_action_completion"

PLAYER_ACTION_COMPLETION_GUARDRAIL_TEXT = (
    "Player action completion authority (R16): a Character move must not represent a "
    "Player character action or positional state as completed, accepted, or voluntarily "
    "performed unless authoritative evidence establishes that completion. "
    "Authoritative sources include player_fact:user_post:*, player_fact:decomposition:*, "
    "player_fact:card:*, committed continuity/binding facts, and legitimately successful "
    "NPC-caused outcomes when runtime authority permits representing success. "
    "Invitation, permission (including location_entry_outcome allowed), threat, social "
    "declaration, NPC opinion, and unresolved attempted coercion do NOT establish Player "
    "completion. location_entry_outcome.allowed means the Player MAY enter, not that they "
    "DID enter. R16 inverse (objective regression): a Character move must not objectively "
    "assert that an authoritative completed Player action or positional state did not occur, "
    "remains unperformed, or was undone unless later authoritative evidence establishes "
    "reversal, or the move clearly expresses Character ignorance, mistaken belief, deliberate "
    "deception/manipulation, or a distinct subsequent requirement rather than denying "
    "established world truth. Commands or demands from incomplete perception are not "
    "objective regression. R16 (completion: was the Player action/position accomplished?) "
    "is orthogonal to R02b (authorship: is an asserted Player fact established?) and R14 "
    "(entitlement: may this Character know/use an established fact?)."
)

CHARACTER_GENERATION_STEERING_TEXT = (
    "Player action completion (steering): NPCs may take strong multi-beat initiative "
    "(open doors, speak, invite, threaten, coerce, grab, shove, restrain, attack, or "
    "cause environmental consequences). Do not narrate Player acceptance, entry, agreement, "
    "or positional completion unless authoritative Player or committed continuity evidence "
    "supports it. Invitation and permission are not acceptance or movement. "
    "location_entry_outcome settles permission only, not accomplished movement. "
    "NPC attempts with unresolved success must not be narrated as accomplished Player "
    "movement."
)


def build_player_action_completion_guardrail() -> dict[str, Any]:
    return {
        "ref_id": PLAYER_ACTION_COMPLETION_GUARDRAIL_ID,
        "kind": "guardrail",
        "authority_class": "authoritative",
        "label": "Player action completion",
        "text": PLAYER_ACTION_COMPLETION_GUARDRAIL_TEXT,
        "provenance": {
            "origin_kind": "guardrail",
            "contract": "player_action_completion_authority_v1",
        },
    }


def merge_player_action_completion_authority_references(
    base_refs: list[dict[str, Any]],
    *,
    include_guardrail: bool = True,
) -> list[dict[str, Any]]:
    """Insert R16 guardrail into authority refs (deduped). Does not infer completion."""
    if not include_guardrail:
        return list(base_refs)
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    guardrail = build_player_action_completion_guardrail()
    ordered.append(guardrail)
    seen.add(PLAYER_ACTION_COMPLETION_GUARDRAIL_ID)
    for ref in base_refs:
        ref_id = str(ref.get("ref_id") or "").strip()
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        ordered.append(ref)
    return ordered


def project_player_action_completion_generation_guidance() -> str:
    return CHARACTER_GENERATION_STEERING_TEXT
