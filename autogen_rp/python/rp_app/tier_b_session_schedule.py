"""Tier B (GitHub #214) — deterministic session mutation schedule for headless scenarios.

Maps scenario JSON ``tier_b_session_mutation_schedule`` to per-turn
``MutationRequest`` lists (S-class / ``session_mutation_candidates``), resolved through
the normal ``ContinuityManager.process_turn`` / Issue #81 pipeline.
"""

from __future__ import annotations

from typing import Any

from continuity_mutation_pipeline import (
    CanonicalAtom,
    ContinuityMutationType,
    MutationRequest,
    MutationSourceClass,
)

_MUTATION_TYPES: dict[str, ContinuityMutationType] = {
    "EXCURSION_OPEN": ContinuityMutationType.EXCURSION_OPEN,
    "EXCURSION_UPDATE": ContinuityMutationType.EXCURSION_UPDATE,
    "EXCURSION_CLOSE": ContinuityMutationType.EXCURSION_CLOSE,
}


def _mutation_request_from_jsonable(
    item: dict[str, Any],
    *,
    card_to_agent: dict[str, str],
    scenario_id: str,
) -> MutationRequest:
    mt_raw = str(item.get("mutation_type") or "").strip().upper()
    mt = _MUTATION_TYPES.get(mt_raw)
    if mt is None:
        raise ValueError(
            f"Scenario {scenario_id!r}: unknown tier_b mutation_type {mt_raw!r} "
            f"(expected one of {sorted(_MUTATION_TYPES)})"
        )
    payload_in = item.get("payload")
    if not isinstance(payload_in, dict):
        raise ValueError(
            f"Scenario {scenario_id!r}: tier_b mutation entry requires object payload"
        )
    payload: dict[str, Any] = dict(payload_in)
    if mt == ContinuityMutationType.EXCURSION_OPEN:
        raw_cards = payload.get("participant_card_ids")
        if isinstance(raw_cards, list) and raw_cards:
            agents: list[str] = []
            for c in raw_cards:
                ck = str(c or "").strip()
                if not ck:
                    continue
                ag = card_to_agent.get(ck)
                if not ag:
                    raise ValueError(
                        f"Scenario {scenario_id!r}: participant_card_id {ck!r} "
                        f"not in character_card_ids / cast"
                    )
                agents.append(ag)
            if not agents:
                raise ValueError(
                    f"Scenario {scenario_id!r}: EXCURSION_OPEN needs non-empty "
                    f"participant_card_ids"
                )
            payload = {**payload, "participant_character_ids": agents}
            payload.pop("participant_card_ids", None)
        atom = CanonicalAtom.EXCURSION_LIFECYCLE
    elif mt == ContinuityMutationType.EXCURSION_UPDATE:
        atom = CanonicalAtom.EXCURSION_LIFECYCLE
        raw_cards = payload.get("participant_card_ids")
        if isinstance(raw_cards, list):
            agents = []
            for c in raw_cards:
                ck = str(c or "").strip()
                if not ck:
                    continue
                ag = card_to_agent.get(ck)
                if not ag:
                    raise ValueError(
                        f"Scenario {scenario_id!r}: participant_card_id {ck!r} "
                        f"not in character_card_ids"
                    )
                agents.append(ag)
            payload = {**payload, "participant_character_ids": agents}
            payload.pop("participant_card_ids", None)
    elif mt == ContinuityMutationType.EXCURSION_CLOSE:
        atom = CanonicalAtom.EXCURSION_LIFECYCLE
    else:
        raise ValueError(f"unhandled mutation type {mt!r}")
    return MutationRequest(
        mutation_type=mt,
        atom=atom,
        source=MutationSourceClass.S,
        payload=payload,
    )


def parse_tier_b_session_mutation_schedule(
    raw: dict[str, Any],
    *,
    card_to_agent: dict[str, str],
) -> dict[int, list[MutationRequest]]:
    """Return orchestration_turn → ``MutationRequest`` list from scenario dict."""
    scenario_id = str(raw.get("id") or "scenario")
    sched = raw.get("tier_b_session_mutation_schedule")
    if sched is None:
        return {}
    if not isinstance(sched, list) or not sched:
        raise ValueError(
            f"Scenario {scenario_id!r}: tier_b_session_mutation_schedule must be a non-empty list"
        )
    by_turn: dict[int, list[MutationRequest]] = {}
    seen_turns: set[int] = set()
    for entry in sched:
        if not isinstance(entry, dict):
            raise ValueError(
                f"Scenario {scenario_id!r}: tier_b schedule entries must be objects"
            )
        ot = entry.get("orchestration_turn")
        if not isinstance(ot, int) or ot < 1:
            raise ValueError(
                f"Scenario {scenario_id!r}: orchestration_turn must be int >= 1, got {ot!r}"
            )
        if ot in seen_turns:
            raise ValueError(
                f"Scenario {scenario_id!r}: duplicate orchestration_turn {ot} in tier_b schedule"
            )
        seen_turns.add(ot)
        muts = entry.get("mutations")
        if not isinstance(muts, list) or not muts:
            raise ValueError(
                f"Scenario {scenario_id!r}: schedule turn {ot} needs non-empty mutations[]"
            )
        resolved: list[MutationRequest] = []
        for m in muts:
            if not isinstance(m, dict):
                raise ValueError(
                    f"Scenario {scenario_id!r}: mutations must be objects (turn {ot})"
                )
            resolved.append(
                _mutation_request_from_jsonable(
                    m, card_to_agent=dict(card_to_agent), scenario_id=scenario_id
                )
            )
        by_turn[ot] = resolved
    return by_turn


def session_mutation_candidates_for_turn(st_module: Any, orchestration_turn: int) -> list[Any] | None:
    """Return S-class candidates for this orchestration turn, or None when absent."""
    raw = st_module.session_state.get("tier_b_session_mutation_by_turn")
    if not isinstance(raw, dict):
        return None
    cands = raw.get(int(orchestration_turn))
    if not cands:
        return None
    return list(cands)


def build_audit_scenario_metadata_for_manifest(
    scenario_raw: dict[str, Any] | None,
    *,
    card_to_agent: dict[str, str],
) -> dict[str, Any] | None:
    """Emit manifest ``audit_scenario_metadata`` for Tier B gate expectations (resolved agents)."""
    if scenario_raw is None:
        return None
    tier = str(scenario_raw.get("audit_validation_tier") or "").strip().lower()
    if tier != "tier_b_continuity_grounded":
        return None
    gate = scenario_raw.get("tier_b_continuity_gate")
    if not isinstance(gate, dict):
        return None
    cid = str(gate.get("excursion_participant_card_id") or "").strip()
    eid = str(gate.get("excursion_id") or "").strip()
    if not cid or not eid:
        return None
    agent = card_to_agent.get(cid)
    if not agent:
        raise ValueError(
            f"Scenario {scenario_raw.get('id')!r}: tier_b_continuity_gate "
            f"excursion_participant_card_id {cid!r} not in cast"
        )
    return {
        "audit_validation_tier": tier,
        "audit_program_issue": str(scenario_raw.get("audit_program_issue") or ""),
        "tier_b_continuity_gate": {
            "excursion_id": eid,
            "excursion_participant_agent": agent,
        },
    }
