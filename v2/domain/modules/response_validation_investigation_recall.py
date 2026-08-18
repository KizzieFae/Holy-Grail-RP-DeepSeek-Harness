"""Deterministic validation for scenario ``investigation`` recall contracts.

Mirrors the failure predicates used by ``issue29_investigation.compute_t_beh`` so
post-run machine analysis and runtime acceptance stay aligned. Does not import
``issue29_investigation`` (avoid coupling validation to audit tooling).
"""

from __future__ import annotations

from typing import Any


def _combined_move(move: dict[str, Any] | None) -> str:
    if not isinstance(move, dict):
        return ""
    return f"{move.get('dialogue', '')}\n{move.get('action', '')}"


def _behavior_fail_negotiation(move: dict[str, Any] | None, tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return True
    c = _combined_move(move)
    return not (tokens[0] in c and tokens[1] in c)


def _behavior_fail_transformation(move: dict[str, Any] | None, tokens: list[str]) -> bool:
    if not tokens:
        return True
    c = _combined_move(move)
    if "FORM_RELEASE_ISSUE29" in c:
        return True
    return tokens[0] not in c


def _behavior_fail_object(move: dict[str, Any] | None, tokens: list[str]) -> bool:
    uid = tokens[0] if tokens else ""
    alt = "OBJECT_ISSUE29_ALTKEY"
    c = _combined_move(move)
    if uid and alt in c and uid in c:
        return True
    return uid not in c


def _behavior_fail_instruction(
    move: dict[str, Any] | None,
    tokens: list[str],
    effective_user_trigger: str,
    character_system_prompt: str,
) -> bool:
    trig = effective_user_trigger or ""
    c = _combined_move(move)
    p = character_system_prompt or ""
    failed = False
    if "PROBE_RED_ISSUE29" in trig:
        if "NO_RED_ACCESS" not in c:
            failed = True
        if "RULE_ISSUE29_NO_RED" not in p:
            failed = True
    if "PAYMENT_ISSUE29" in trig:
        if "RULE_ISSUE29_CODA_Q9" not in c:
            failed = True
        elif "payment" in c.lower() and c.find("RULE_ISSUE29_CODA_Q9") > c.lower().find(
            "payment"
        ):
            failed = True
    return failed


def _behavior_fail_cross_scene(move: dict[str, Any] | None, tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return True
    c = _combined_move(move)
    return not (tokens[0] in c and tokens[1] in c)


def _behavior_fail_multi_thread(move: dict[str, Any] | None, tokens: list[str]) -> bool:
    c = _combined_move(move)
    return not all(t in c for t in tokens)


def format_investigation_anchor_retry_note(
    *,
    turn_number: int,
    behavior_kind: str,
    tokens: list[str],
) -> str:
    shown = ", ".join(tokens[:8])
    if len(tokens) > 8:
        shown += ", …"
    return (
        "IMPORTANT: Your previous attempt failed the scenario investigation recall contract. "
        f"On orchestration turn {turn_number} ({behavior_kind}), include every required literal "
        f"token in your JSON `dialogue` and/or `action` exactly as given in the scene text: {shown}."
    )


def validate_investigation_recall_contract(
    *,
    move: dict[str, Any] | None,
    orchestration_turn_number: int,
    scenario_raw: dict[str, Any],
    effective_user_trigger: str = "",
    character_system_prompt: str | None = None,
) -> tuple[bool, str]:
    """Return ``(True, \"\")`` if valid or no contract applies; else ``(False, reason)``."""
    inv = scenario_raw.get("investigation")
    if not isinstance(inv, dict) or not inv:
        return True, ""
    tokens_raw = scenario_raw.get("investigation_anchor_tokens") or []
    if not isinstance(tokens_raw, list) or not tokens_raw:
        return True, ""
    recall_turns = inv.get("recall_turn_numbers")
    if not isinstance(recall_turns, list) or not recall_turns:
        return True, ""
    recall_set: set[int] = set()
    for x in recall_turns:
        if isinstance(x, int):
            recall_set.add(x)
        elif isinstance(x, str) and str(x).isdigit():
            recall_set.add(int(x))
    if orchestration_turn_number not in recall_set:
        return True, ""
    kind = str(inv.get("behavior_kind", "") or "")
    tokens = [str(t).strip() for t in tokens_raw if str(t).strip()]
    p = character_system_prompt if character_system_prompt is not None else ""

    if kind == "negotiation_dual_token_recall":
        fail = _behavior_fail_negotiation(move, tokens)
    elif kind == "transformation_form_token_recall":
        fail = _behavior_fail_transformation(move, tokens)
    elif kind == "object_uid_recall":
        fail = _behavior_fail_object(move, tokens)
    elif kind == "instruction_probe_recall":
        fail = _behavior_fail_instruction(move, tokens, effective_user_trigger, p)
    elif kind == "cross_scene_carry_recall":
        fail = _behavior_fail_cross_scene(move, tokens)
    elif kind == "multi_thread_recall":
        fail = _behavior_fail_multi_thread(move, tokens)
    else:
        return True, ""

    if fail:
        shown = ", ".join(tokens[:6])
        if len(tokens) > 6:
            shown += ", …"
        return (
            False,
            f"[INVESTIGATION_ANCHOR] turn {orchestration_turn_number} behavior_kind={kind!r}: "
            f"required literal token(s) missing from dialogue/action ({shown}).",
        )
    return True, ""
