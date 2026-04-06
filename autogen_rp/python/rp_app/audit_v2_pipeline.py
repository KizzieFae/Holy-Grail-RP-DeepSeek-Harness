"""Orchestrate Audit V2 deterministic + optional LLM for a single turn (log-only)."""

from __future__ import annotations

from typing import Any, Mapping

from audit_v2_deterministic import (
    ALLOWED_EXPANSION_POLICY_TEXT,
    assemble_audit_v2_layer_block,
    build_character_audit_v2_deterministic,
    build_narrator_audit_v2_deterministic,
    build_prose_audit_v2_deterministic,
    format_move_for_llm_closed,
)
from audit_v2_llm import (
    build_character_llm_prompt,
    build_narrator_llm_prompt,
    build_prose_llm_prompt,
    build_llm_skipped_payload,
    run_audit_v2_llm,
)


async def build_audit_v2_character_bundle(
    *,
    move: dict[str, Any],
    next_actor: str,
    orchestration_state: Mapping[str, Any],
    llm_audit_enabled: bool,
    model_client: Any,
    cancellation_token: Any,
) -> dict[str, Any]:
    det = build_character_audit_v2_deterministic(
        move=move,
        next_actor=next_actor,
        orchestration_state=orchestration_state,
    )
    esc = det.get("escalation") if isinstance(det.get("escalation"), dict) else {}
    qualified = bool(esc.get("qualified", False))
    reasons = list(esc.get("reasons", []) or [])

    if not llm_audit_enabled or not qualified:
        llm = build_llm_skipped_payload(
            llm_audit_enabled=llm_audit_enabled,
            escalation_qualified=qualified,
            escalation_reasons=reasons,
        )
    else:
        prompt = build_character_llm_prompt(
            move_json=format_move_for_llm_closed(dict(move)),
            escalation_reasons=reasons,
        )
        llm = await run_audit_v2_llm(
            layer="character_decision",
            model_client=model_client,
            cancellation_token=cancellation_token,
            user_prompt=prompt,
        )
        llm.setdefault("would_escalate", True)
        llm.setdefault("escalation_reasons_if_enabled", reasons)

    return {
        "character_decision": assemble_audit_v2_layer_block(
            deterministic=det,
            llm=llm,
        )
    }


async def build_audit_v2_narrator_prose_bundle(
    *,
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    rendered_final: str,
    char_names: list[str],
    acting_display_name: str,
    prior_assistant_content: str | None,
    llm_audit_enabled: bool,
    model_client: Any,
    cancellation_token: Any,
    previous_narrator_other_cast_names: frozenset[str] | None = None,
) -> dict[str, Any]:
    det_nar = build_narrator_audit_v2_deterministic(
        next_actor=next_actor,
        move=move,
        decision=decision,
        rendered_final=rendered_final,
        char_names=char_names,
        acting_display_name=acting_display_name,
        previous_narrator_other_cast_names=previous_narrator_other_cast_names,
    )
    det_prose = build_prose_audit_v2_deterministic(
        next_actor=next_actor,
        move=move,
        rendered_final=rendered_final,
        prior_assistant_content=prior_assistant_content,
        acting_display_name=acting_display_name,
    )

    esc_n = det_nar.get("escalation") if isinstance(det_nar.get("escalation"), dict) else {}
    qual_n = bool(esc_n.get("qualified", False))
    reasons_n = list(esc_n.get("reasons", []) or [])

    if not llm_audit_enabled or not qual_n:
        llm_n = build_llm_skipped_payload(
            llm_audit_enabled=llm_audit_enabled,
            escalation_qualified=qual_n,
            escalation_reasons=reasons_n,
        )
    else:
        env = str(decision.get("environment_event", "") or "")
        prompt = build_narrator_llm_prompt(
            move_json=format_move_for_llm_closed(dict(move)),
            rendered_final=rendered_final,
            environment_event=env,
            allowed_expansion_policy=ALLOWED_EXPANSION_POLICY_TEXT,
            escalation_reasons=reasons_n,
        )
        llm_n = await run_audit_v2_llm(
            layer="narrator_output",
            model_client=model_client,
            cancellation_token=cancellation_token,
            user_prompt=prompt,
        )
        llm_n.setdefault("would_escalate", True)
        llm_n.setdefault("escalation_reasons_if_enabled", reasons_n)

    esc_p = (
        det_prose.get("escalation")
        if isinstance(det_prose.get("escalation"), dict)
        else {}
    )
    qual_p = bool(esc_p.get("qualified", False))
    reasons_p = list(esc_p.get("reasons", []) or [])

    if not llm_audit_enabled or not qual_p:
        llm_p = build_llm_skipped_payload(
            llm_audit_enabled=llm_audit_enabled,
            escalation_qualified=qual_p,
            escalation_reasons=reasons_p,
        )
    else:
        prompt = build_prose_llm_prompt(
            move_dialogue=str(move.get("dialogue", "") or ""),
            move_action_excerpt=str(move.get("action", "") or ""),
            rendered_final=rendered_final,
            prior_assistant_excerpt=prior_assistant_content,
            acting_label=acting_display_name,
            escalation_reasons=reasons_p,
        )
        llm_p = await run_audit_v2_llm(
            layer="prose_dialogue",
            model_client=model_client,
            cancellation_token=cancellation_token,
            user_prompt=prompt,
        )
        llm_p.setdefault("would_escalate", True)
        llm_p.setdefault("escalation_reasons_if_enabled", reasons_p)

    return {
        "schema_version": 1,
        "narrator_output": assemble_audit_v2_layer_block(
            deterministic=det_nar,
            llm=llm_n,
        ),
        "prose_dialogue": assemble_audit_v2_layer_block(
            deterministic=det_prose,
            llm=llm_p,
        ),
    }