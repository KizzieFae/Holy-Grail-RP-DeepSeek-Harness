"""Character-turn attempt phase: prompt/retry garnish, agent call, parse, validate, retries, continuity, audits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from autogen_agentchat.messages import TextMessage

from anti_regression_advisory import get_cached_anti_regression_advisory
from audit_v2_pipeline import build_audit_v2_character_bundle
from character_audits_v1 import build_character_audit_v1
from character_move_adapters import legacy_move_text_for_validation
from continuity_manager import ContinuityManager
from perception_audibility import normalize_move_audibility
from progression_advisory import get_cached_progression_advisory
from progression_enforcement import (
    collect_issue_signatures,
    progression_delta_required,
    qualifies_as_progression_delta,
)
from progression_run_metrics import maybe_record_sim_progression_metric
from progression_simulation_scenarios import load_scenario
from response_validation_binding_sleeping_surface import (
    binding_sleeping_surface_id_for_actor,
    format_binding_sleeping_surface_retry_note,
)
from response_validation_investigation_recall import (
    format_investigation_anchor_retry_note,
)
from response_validation_proposal_coherence import (
    PROPOSAL_COHERENCE_TAG,
    format_proposal_coherence_retry_note,
    is_proposal_rejection_reason,
    validate_proposal_structural_coherence,
)
from response_validation_proposal_legality import (
    format_proposal_legality_rejection,
    format_proposal_legality_retry_note,
    is_proposal_legality_rejection_reason,
)
from continuity_semantic_proposals import (
    ProposalAuthorityContext,
    ProposalAuthorityOutcome,
    evaluate_proposal_legality,
)
from audit_semantic_proposal_decision import (
    build_semantic_proposal_decision,
    should_emit_semantic_proposal_decision,
)
from semantic_validation import record_proposal_coherence_stats
from tier_b_session_schedule import session_mutation_candidates_for_turn
from turn_runner_audit import log_character_turn_audit

DEFAULT_MAX_CHARACTER_ATTEMPTS = 3

_CHARACTER_MOVE_PARSE_JSON_DISCIPLINE_NOTE = (
    "IMPORTANT: Your previous response could not be parsed as valid JSON for the required "
    "character move schema (v2). Reply with a single JSON object: integer move_schema_version 2, "
    "non-empty beats[] (type action / type speech), motivation, optional scene_state_updates — "
    "no root-level action or dialogue keys, and no surrounding prose or markdown/code fences."
)


class CharacterAttemptOutcome:
    __slots__ = (
        "move",
        "continuity_applied_in_execute",
        "continuity_transaction_snapshot",
        "turn_execution_metadata",
    )

    def __init__(
        self,
        *,
        move: dict[str, Any],
        continuity_applied_in_execute: bool,
        continuity_transaction_snapshot: dict[str, Any] | None,
        turn_execution_metadata: dict[str, Any],
    ) -> None:
        self.move = move
        self.continuity_applied_in_execute = continuity_applied_in_execute
        self.continuity_transaction_snapshot = continuity_transaction_snapshot
        self.turn_execution_metadata = turn_execution_metadata


_StructuredRetryKind = Literal[
    "duplicate", "binding", "investigation", "proposal_coherence", "proposal_legality"
]


def _evaluate_proposal_authority_for_attempt(
    *,
    move: dict[str, Any],
    next_actor: str,
    continuity_manager: Any,
    scene_state: dict[str, Any],
) -> tuple[bool, str, ProposalAuthorityContext | None]:
    e_active: set[str] = set()
    excursions = None
    if continuity_manager is not None:
        try:
            e_active = set(continuity_manager.active_excursion_character_ids())
        except (AttributeError, TypeError):
            e_active = set()
        excursions = getattr(continuity_manager, "excursions", None)
    ctx = evaluate_proposal_legality(
        move,
        acting_character=next_actor,
        scene_state=scene_state,
        active_excursion_character_ids=e_active,
        excursions=excursions,
    )
    if ctx.outcome == ProposalAuthorityOutcome.REJECT:
        return (
            False,
            format_proposal_legality_rejection(
                reason_code=ctx.reason_code,
                reason_detail=ctx.reason_detail,
            ),
            ctx,
        )
    return True, "", ctx


def _character_audit_metadata_with_proposal_decision(
    base: dict[str, Any],
    *,
    move: dict[str, Any],
    attempt_index: int,
    terminal: bool,
    retry_class: str | None,
    proposal_coherence_assessment: dict[str, Any] | None,
    proposal_authority_context: ProposalAuthorityContext | None,
    legality_evaluated: bool,
    lifecycle_phase: str,
    force_success_character_row: bool = False,
    continuity_turn_index: int | None = None,
    include_commit_proof_pointer: bool = False,
    process_turn_ran: bool | None = None,
) -> dict[str, Any]:
    if not should_emit_semantic_proposal_decision(
        move,
        proposal_authority_context=proposal_authority_context,
        proposal_coherence_assessment=proposal_coherence_assessment,
        legality_evaluated=legality_evaluated,
        force_success_character_row=force_success_character_row,
    ):
        return base
    out = dict(base)
    out["semantic_proposal_decision"] = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=proposal_authority_context,
        lifecycle_phase=lifecycle_phase,
        attempt_index=attempt_index,
        terminal=terminal,
        retry_class=retry_class,
        proposal_coherence_assessment=proposal_coherence_assessment,
        legality_evaluated=legality_evaluated,
        continuity_turn_index=continuity_turn_index,
        include_commit_proof_pointer=include_commit_proof_pointer,
        process_turn_ran=process_turn_ran,
    )
    return out


def _route_structured_validation_retries(
    *,
    is_valid: bool,
    rejection_reason: str,
    has_more_attempts: bool,
    duplicate_retry_consumed: bool,
    binding_retry_consumed: bool,
    investigation_retry_consumed: bool,
    proposal_coherence_retry_consumed: bool,
    proposal_legality_retry_consumed: bool,
) -> _StructuredRetryKind | None:
    if is_valid:
        return None
    if (
        is_proposal_rejection_reason(rejection_reason)
        and not proposal_coherence_retry_consumed
        and has_more_attempts
    ):
        return "proposal_coherence"
    if (
        is_proposal_legality_rejection_reason(rejection_reason)
        and not proposal_legality_retry_consumed
        and has_more_attempts
    ):
        return "proposal_legality"
    if (
        rejection_reason.startswith("[DUPLICATE]")
        and not duplicate_retry_consumed
        and has_more_attempts
    ):
        return "duplicate"
    if (
        rejection_reason.startswith("[BINDING_SLEEPING_SURFACE]")
        and not binding_retry_consumed
        and has_more_attempts
    ):
        return "binding"
    if (
        rejection_reason.startswith("[INVESTIGATION_ANCHOR]")
        and not investigation_retry_consumed
        and has_more_attempts
    ):
        return "investigation"
    return None


def _scene_state_dict_for_attempt(
    continuity_manager: Any, orchestration_state: dict[str, Any]
) -> dict[str, Any]:
    if continuity_manager is not None and continuity_manager.scene_state is not None:
        return continuity_manager.scene_state.to_dict()
    raw = orchestration_state.get("scene_state", {})
    return raw if isinstance(raw, dict) else {}


def _build_character_attempt_prompt(
    *,
    task_prompt: str,
    attempt_index: int,
    st_module: Any,
    continuity_manager: Any,
    next_actor: str,
    turn_number: int,
    parse_retry_triggered: bool,
    duplicate_retry_triggered: bool,
    progression_retry_triggered: bool,
    binding_retry_triggered: bool,
    investigation_retry_triggered: bool,
    proposal_coherence_retry_triggered: bool,
    proposal_coherence_retry_reason: str = "",
    proposal_coherence_retry_reason_code: str = "",
    proposal_legality_retry_triggered: bool = False,
    proposal_legality_retry_reason: str = "",
    proposal_legality_retry_reason_code: str = "",
) -> str:
    attempt_prompt = task_prompt
    if attempt_index < 1:
        return attempt_prompt
    retry_notes: list[str] = []
    if parse_retry_triggered:
        retry_notes.append(_CHARACTER_MOVE_PARSE_JSON_DISCIPLINE_NOTE)
    if duplicate_retry_triggered:
        retry_notes.append(
            "IMPORTANT: Your previous attempt was rejected as a duplicate. "
            "Write a materially different beats[] sequence. Do not repeat previous speech lines verbatim."
        )
    if progression_retry_triggered:
        retry_notes.append(
            "IMPORTANT: Your previous attempt did not produce sufficient scene progression "
            "(no decisive continuity consequence, issue movement, arrival/exit, or bounded settlement). "
            "Revise so this beat changes the situation in a concrete, observable way."
        )
    if binding_retry_triggered:
        sid = binding_sleeping_surface_id_for_actor(
            st_module.session_state.get("scene_grounding"),
            next_actor,
            continuity_manager=continuity_manager,
        )
        retry_notes.append(format_binding_sleeping_surface_retry_note(sid or "unknown"))
    if investigation_retry_triggered:
        inv_note = ""
        sid = st_module.session_state.get("simulation_scenario_id")
        if sid:
            try:
                raw = load_scenario(str(sid).strip())
                inv = raw.get("investigation") if isinstance(raw, dict) else {}
                toks_raw = (
                    raw.get("investigation_anchor_tokens")
                    if isinstance(raw, dict)
                    else None
                )
                if isinstance(inv, dict) and isinstance(toks_raw, list):
                    kind = str(inv.get("behavior_kind", "") or "")
                    tk = [str(t).strip() for t in toks_raw if str(t).strip()]
                    if kind and tk:
                        inv_note = format_investigation_anchor_retry_note(
                            turn_number=turn_number,
                            behavior_kind=kind,
                            tokens=tk,
                        )
            except (OSError, ValueError, KeyError, TypeError):
                inv_note = ""
        if not inv_note:
            inv_note = (
                "IMPORTANT: Your previous attempt failed the scenario investigation recall contract. "
                "Include every required literal anchor token in your JSON dialogue and/or action "
                "exactly as written in the scene materials."
            )
        retry_notes.append(inv_note)
    if proposal_coherence_retry_triggered:
        retry_notes.append(
            format_proposal_coherence_retry_note(
                rejection_reason=proposal_coherence_retry_reason,
                reason_code=proposal_coherence_retry_reason_code,
            )
        )
    if proposal_legality_retry_triggered:
        retry_notes.append(
            format_proposal_legality_retry_note(
                rejection_reason=proposal_legality_retry_reason,
                reason_code=proposal_legality_retry_reason_code,
            )
        )
    if retry_notes:
        attempt_prompt = task_prompt + "\n\n" + "\n\n".join(retry_notes)
    return attempt_prompt


def _normalize_parsed_move(
    move: dict[str, Any],
    *,
    next_actor: str,
    present_for_norm: list[str],
) -> dict[str, Any]:
    if int(str(move.get("move_schema_version", 0) or 0) or 0) == 2:
        return move
    return normalize_move_audibility(dict(move), next_actor, list(present_for_norm))


@dataclass(frozen=True)
class _ContinuityGateResult:
    kind: Literal["accepted", "progression_retry", "progression_terminal"]
    character_audit_v1: dict[str, Any] | None = None
    continuity_applied_in_execute: bool = False
    continuity_transaction_snapshot: dict[str, Any] | None = None
    audit_v2_continuity_context: dict[str, Any] | None = None


def _apply_continuity_and_progression_gate(
    *,
    st_module: Any,
    cm_exec: Any,
    move: dict[str, Any],
    decision: dict[str, Any],
    next_actor: str,
    char_names: list[str],
    trigger_text: str,
    attempt_index: int,
    orchestration_state: dict[str, Any],
    round_number: int,
    turn_number: int,
    attempt_prompt: str,
    char_raw_response: str,
    character_summary_block_audit: dict[str, Any],
    effective_user_trigger: str,
    semantic_presence_assessment: Any,
    has_more_attempts: bool,
    progression_retry_consumed: bool,
    proposal_authority_context: ProposalAuthorityContext | None,
    log_turn_failure_fn: Any,
    sync_orchestration_state_from_continuity_fn: Any,
    actors_failed_this_round: list[str],
) -> tuple[_ContinuityGateResult, bool]:
    """Snapshot → process_turn → progression gate → rollback/accept. Single transactional unit."""
    pre_process_snapshot = cm_exec.to_dict()
    issues_before = collect_issue_signatures(cm_exec)
    gate = progression_delta_required(
        orchestration_state=orchestration_state,
        continuity_manager=cm_exec,
        current_actor=next_actor,
        current_move=dict(move),
    )
    enforcement_disabled = bool(
        st_module.session_state.get("progression_enforcement_disabled")
    )
    gate_effective = gate and not enforcement_disabled
    character_audit_v1 = build_character_audit_v1(
        move=dict(move),
        decision=decision,
        next_actor=next_actor,
        char_names=list(char_names),
        trigger_text=trigger_text,
        attempt_index=attempt_index,
        orchestration_state=orchestration_state,
        continuity_scope="continuity_enabled",
        scene_state_pre_source_dict=cm_exec.scene_state.to_dict(),
        issues_before_signatures=issues_before,
        cm_exec=cm_exec,
    )
    try:
        sched_cand = session_mutation_candidates_for_turn(
            st_module, orchestration_turn=turn_number
        )
        proc_kw2: dict[str, Any] = {}
        if sched_cand:
            proc_kw2["session_mutation_candidates"] = sched_cand
        if proposal_authority_context is not None:
            proc_kw2["proposal_authority_context"] = proposal_authority_context
        cm_exec.process_turn(
            acting_character=next_actor,
            move=dict(move),
            director_decision=decision,
            other_characters=[name for name in char_names if name != next_actor],
            **proc_kw2,
        )
    except Exception:
        st_module.session_state["continuity_manager"] = ContinuityManager.from_dict(
            pre_process_snapshot
        )
        sync_orchestration_state_from_continuity_fn()
        raise
    sync_orchestration_state_from_continuity_fn()
    turn_idx = int(getattr(cm_exec, "turn_counter", 0) or 0)
    meta_by = getattr(cm_exec, "turn_metadata_by_index", {}) or {}
    turn_meta = meta_by.get(turn_idx, {}) if isinstance(meta_by, dict) else {}
    if not isinstance(turn_meta, dict):
        turn_meta = {}
    qualifies = qualifies_as_progression_delta(
        continuity_manager=cm_exec,
        turn_index=turn_idx,
        turn_meta=turn_meta,
        issues_before=issues_before,
        move=dict(move),
    )
    if gate_effective and not qualifies:
        st_module.session_state["continuity_manager"] = ContinuityManager.from_dict(
            pre_process_snapshot
        )
        sync_orchestration_state_from_continuity_fn()
        progression_retry_reason = (
            "Progression enforcement: no qualifying structural delta after process_turn."
        )
        if not progression_retry_consumed and has_more_attempts:
            maybe_record_sim_progression_metric(
                st_module,
                {
                    "kind": "progression_retry",
                    "round_number": round_number,
                    "orchestration_turn_number": turn_number,
                    "next_actor": next_actor,
                    "continuity_turn_index": turn_idx,
                },
            )
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_progression_retry",
                reason=progression_retry_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata=_character_audit_metadata_with_proposal_decision(
                    {
                        "summary_blocks": character_summary_block_audit,
                        "semantic_presence_assessment": semantic_presence_assessment
                        or {},
                    },
                    move=move,
                    attempt_index=attempt_index,
                    terminal=False,
                    retry_class=None,
                    proposal_coherence_assessment=None,
                    proposal_authority_context=proposal_authority_context,
                    legality_evaluated=proposal_authority_context is not None,
                    lifecycle_phase="committed_attempt_rolled_back",
                    process_turn_ran=True,
                ),
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after progression-enforcement rejection."
            )
            return (
                _ContinuityGateResult(kind="progression_retry"),
                True,
            )
        actors_failed_this_round.append(next_actor)
        maybe_record_sim_progression_metric(
            st_module,
            {
                "kind": "progression_failure",
                "round_number": round_number,
                "orchestration_turn_number": turn_number,
                "next_actor": next_actor,
                "continuity_turn_index": turn_idx,
            },
        )
        log_turn_failure_fn(
            round_number=round_number,
            turn_number=turn_number,
            bot_name=next_actor,
            bot_type="character",
            stage="validation",
            reason=progression_retry_reason,
            input_messages=[{"role": "system", "content": attempt_prompt}],
            raw_response=char_raw_response,
            parsed_output=move,
            context_snapshot={
                "director_decision": decision,
                "character_names": char_names,
                "attempt_index": attempt_index,
            },
            metadata=_character_audit_metadata_with_proposal_decision(
                {
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
                move=move,
                attempt_index=attempt_index,
                terminal=True,
                retry_class=None,
                proposal_coherence_assessment=None,
                proposal_authority_context=proposal_authority_context,
                legality_evaluated=proposal_authority_context is not None,
                lifecycle_phase="committed_attempt_rolled_back",
                process_turn_ran=True,
            ),
            effective_user_trigger=effective_user_trigger,
        )
        return (_ContinuityGateResult(kind="progression_terminal"), progression_retry_consumed)
    maybe_record_sim_progression_metric(
        st_module,
        {
            "kind": "accepted_turn",
            "continuity_turn_index": turn_idx,
            "qualifies": bool(qualifies),
            "gate_active": bool(gate),
            "enforcement_effective": bool(gate_effective),
            "round_number": round_number,
            "orchestration_turn_number": turn_number,
            "next_actor": next_actor,
        },
    )
    return (
        _ContinuityGateResult(
            kind="accepted",
            character_audit_v1=character_audit_v1,
            continuity_applied_in_execute=True,
            continuity_transaction_snapshot=pre_process_snapshot,
            audit_v2_continuity_context={
                "continuity_manager": cm_exec,
                "turn_index": turn_idx,
                "turn_meta": turn_meta,
                "issues_before": issues_before,
            },
        ),
        progression_retry_consumed,
    )


def _turn_execution_metadata(
    *,
    attempt_index: int,
    parse_retry_triggered: bool,
    parse_retry_reason: str,
    duplicate_retry_triggered: bool,
    duplicate_retry_reason: str,
    progression_retry_triggered: bool,
    progression_retry_reason: str,
    binding_retry_triggered: bool,
    binding_retry_reason: str,
    investigation_retry_triggered: bool,
    investigation_retry_reason: str,
    proposal_coherence_retry_triggered: bool,
    proposal_coherence_retry_reason: str,
    proposal_coherence_stats_snapshot: dict[str, Any] | None,
    proposal_legality_retry_triggered: bool,
    proposal_legality_retry_reason: str,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "attempt_index": attempt_index,
        "parse_retry_triggered": parse_retry_triggered,
        "parse_retry_reason": parse_retry_reason,
        "parse_retry_outcome": (
            "success_after_retry" if parse_retry_triggered else "no_retry"
        ),
        "duplicate_retry_triggered": duplicate_retry_triggered,
        "duplicate_retry_reason": duplicate_retry_reason,
        "duplicate_retry_outcome": (
            "success_after_retry" if duplicate_retry_triggered else "no_retry"
        ),
        "progression_retry_triggered": progression_retry_triggered,
        "progression_retry_reason": progression_retry_reason,
        "progression_retry_outcome": (
            "success_after_retry" if progression_retry_triggered else "no_retry"
        ),
        "binding_retry_triggered": binding_retry_triggered,
        "binding_retry_reason": binding_retry_reason,
        "binding_retry_outcome": (
            "success_after_retry" if binding_retry_triggered else "no_retry"
        ),
        "investigation_retry_triggered": investigation_retry_triggered,
        "investigation_retry_reason": investigation_retry_reason,
        "investigation_retry_outcome": (
            "success_after_retry" if investigation_retry_triggered else "no_retry"
        ),
        "proposal_coherence_retry_triggered": proposal_coherence_retry_triggered,
        "proposal_coherence_retry_reason": proposal_coherence_retry_reason,
        "proposal_coherence_retry_outcome": (
            "success_after_retry" if proposal_coherence_retry_triggered else "no_retry"
        ),
        "proposal_coherence_stats": dict(proposal_coherence_stats_snapshot or {}),
        "proposal_legality_retry_triggered": proposal_legality_retry_triggered,
        "proposal_legality_retry_reason": proposal_legality_retry_reason,
        "proposal_legality_retry_outcome": (
            "success_after_retry" if proposal_legality_retry_triggered else "no_retry"
        ),
    }
    return meta


async def _validate_character_move(
    *,
    move: dict[str, Any],
    move_text: str,
    next_actor: str,
    user_name: str,
    st_module: Any,
    state_manager: Any,
    continuity_manager: Any,
    scene_state: dict[str, Any],
    attempt_prompt: str,
    turn_number: int,
    effective_user_trigger: str,
    validate_bot_response_fn: Any,
    get_model_client_fn: Any,
    assess_presence_violation_semantics_fn: Any,
    should_override_presence_rejection_fn: Any,
    assess_proposal_beat_contradiction_fn: Any,
    cancellation_token: Any,
) -> tuple[bool, str, Any, Any]:
    proposal_coherence_assessment: dict[str, Any] | None = None

    ok_struct, struct_reason, struct_code = validate_proposal_structural_coherence(
        move, acting_character=next_actor
    )
    if not ok_struct:
        return (
            False,
            struct_reason,
            None,
            {
                "status": "rejected_structural",
                "reason_code": struct_code,
            },
        )

    proposals_raw = move.get("semantic_proposals") if isinstance(move, dict) else None
    if isinstance(proposals_raw, list) and proposals_raw:
        proposal_coherence_assessment = await assess_proposal_beat_contradiction_fn(
            model_client=get_model_client_fn(),
            acting_character=next_actor,
            move=move,
            cancellation_token=cancellation_token,
        )
        record_proposal_coherence_stats(st_module, proposal_coherence_assessment)
        if (
            isinstance(proposal_coherence_assessment, dict)
            and proposal_coherence_assessment.get("status") == "contradicted"
        ):
            code = str(proposal_coherence_assessment.get("reason_code", "") or "").strip()
            expl = str(proposal_coherence_assessment.get("explanation", "") or "").strip()
            detail = expl or "beats clearly contradict typed semantic_proposals"
            return (
                False,
                f"{PROPOSAL_COHERENCE_TAG} {detail}",
                None,
                proposal_coherence_assessment,
            )

    is_valid, rejection_reason = validate_bot_response_fn(
        move_text,
        next_actor,
        user_name,
        st_module.session_state["chat_history"],
        state_manager.get_state(next_actor) if state_manager else None,
        move,
        (
            continuity_manager.get_relevant_canon_anchors(next_actor)
            if continuity_manager is not None
            else None
        ),
        scene_state,
        continuity_manager,
        scene_grounding=st_module.session_state.get("scene_grounding"),
        effective_user_trigger=effective_user_trigger,
        character_system_prompt=attempt_prompt,
        simulation_scenario_id=st_module.session_state.get("simulation_scenario_id"),
        orchestration_turn_number=turn_number,
    )
    semantic_presence_assessment = None
    if not is_valid and rejection_reason.startswith("[SCENE_PRESENCE]"):
        semantic_presence_assessment = await assess_presence_violation_semantics_fn(
            model_client=get_model_client_fn(),
            speaker=next_actor,
            content=move_text,
            move=move,
            scene_state=scene_state,
            rejection_reason=rejection_reason,
            cancellation_token=cancellation_token,
        )
        if should_override_presence_rejection_fn(
            rejection_reason, semantic_presence_assessment
        ):
            is_valid = True
            rejection_reason = ""
            st_module.session_state["selector_decisions"].append(
                f"Semantic validation kept {next_actor}'s turn after presence review."
            )
    return is_valid, rejection_reason, semantic_presence_assessment, proposal_coherence_assessment


async def _maybe_build_audit_v2_metadata(
    *,
    is_audit_enabled_fn: Any,
    move: dict[str, Any],
    next_actor: str,
    orchestration_state: dict[str, Any],
    is_llm_audit_enabled_fn: Any,
    get_model_client_fn: Any,
    cancellation_token: Any,
    audit_v2_continuity_context: dict[str, Any] | None,
    turn_execution_metadata: dict[str, Any],
) -> dict[str, Any] | None:
    if not is_audit_enabled_fn():
        return None
    v2_kw: dict[str, Any] = {
        "move": dict(move),
        "next_actor": next_actor,
        "orchestration_state": orchestration_state,
        "llm_audit_enabled": is_llm_audit_enabled_fn(),
        "model_client": get_model_client_fn(),
        "cancellation_token": cancellation_token,
    }
    if audit_v2_continuity_context is not None:
        v2_kw["continuity_manager"] = audit_v2_continuity_context["continuity_manager"]
        v2_kw["turn_index"] = audit_v2_continuity_context["turn_index"]
        v2_kw["turn_meta"] = audit_v2_continuity_context["turn_meta"]
        v2_kw["issues_before"] = audit_v2_continuity_context["issues_before"]
        v2_kw["turn_execution"] = turn_execution_metadata
    char_v2_bundle = await build_audit_v2_character_bundle(**v2_kw)
    return {"schema_version": 1, **char_v2_bundle}


async def run_character_attempt_phase(
    *,
    st_module: Any,
    agent: Any,
    next_actor: str,
    char_names: list[str],
    decision: dict[str, Any],
    trigger_text: str,
    user_name: str,
    cancellation_token: Any,
    round_number: int,
    turn_number: int,
    orchestration_state: dict[str, Any],
    actors_failed_this_round: list[str],
    state_manager: Any,
    task_prompt: str,
    character_summary_block_audit: dict[str, Any],
    parse_character_move_fn,
    get_continuity_manager_fn,
    is_audit_enabled_fn,
    is_llm_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
    validate_bot_response_fn,
    get_model_client_fn,
    assess_presence_violation_semantics_fn,
    should_override_presence_rejection_fn,
    log_turn_failure_fn,
    sync_orchestration_state_from_continuity_fn,
    effective_user_trigger: str,
    max_character_attempts: int = DEFAULT_MAX_CHARACTER_ATTEMPTS,
    assess_proposal_beat_contradiction_fn: Any = None,
) -> CharacterAttemptOutcome | None:
    if assess_proposal_beat_contradiction_fn is None:
        from semantic_validation import assess_proposal_beat_contradiction

        assess_proposal_beat_contradiction_fn = assess_proposal_beat_contradiction

    move: dict[str, Any] | None = None
    semantic_presence_assessment = None
    proposal_coherence_assessment: dict[str, Any] | None = None
    rejection_reason = ""
    duplicate_retry_triggered = False
    duplicate_retry_reason = ""
    duplicate_retry_consumed = False
    progression_retry_triggered = False
    progression_retry_reason = ""
    progression_retry_consumed = False
    binding_retry_triggered = False
    binding_retry_reason = ""
    binding_retry_consumed = False
    investigation_retry_triggered = False
    investigation_retry_reason = ""
    investigation_retry_consumed = False
    proposal_coherence_retry_triggered = False
    proposal_coherence_retry_reason = ""
    proposal_coherence_retry_reason_code = ""
    proposal_coherence_retry_consumed = False
    proposal_legality_retry_triggered = False
    proposal_legality_retry_reason = ""
    proposal_legality_retry_reason_code = ""
    proposal_legality_retry_consumed = False
    proposal_authority_context: ProposalAuthorityContext | None = None
    parse_retry_triggered = False
    parse_retry_reason = ""
    continuity_applied_in_execute = False
    continuity_transaction_snapshot: dict[str, Any] | None = None

    attempt_cap = max(1, int(max_character_attempts))
    for attempt_index in range(attempt_cap):
        has_more_attempts = attempt_index < attempt_cap - 1
        continuity_manager = get_continuity_manager_fn()
        scene_state = _scene_state_dict_for_attempt(continuity_manager, orchestration_state)
        attempt_prompt = _build_character_attempt_prompt(
            task_prompt=task_prompt,
            attempt_index=attempt_index,
            st_module=st_module,
            continuity_manager=continuity_manager,
            next_actor=next_actor,
            turn_number=turn_number,
            parse_retry_triggered=parse_retry_triggered,
            duplicate_retry_triggered=duplicate_retry_triggered,
            progression_retry_triggered=progression_retry_triggered,
            binding_retry_triggered=binding_retry_triggered,
            investigation_retry_triggered=investigation_retry_triggered,
            proposal_coherence_retry_triggered=proposal_coherence_retry_triggered,
            proposal_coherence_retry_reason=proposal_coherence_retry_reason,
            proposal_coherence_retry_reason_code=proposal_coherence_retry_reason_code,
            proposal_legality_retry_triggered=proposal_legality_retry_triggered,
            proposal_legality_retry_reason=proposal_legality_retry_reason,
            proposal_legality_retry_reason_code=proposal_legality_retry_reason_code,
        )

        task = TextMessage(content=attempt_prompt, source="system")

        try:
            char_result = await agent.on_messages([task], cancellation_token)
            char_raw_response = char_result.chat_message.content
        except Exception as exc:
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="generation",
                reason=str(exc),
                input_messages=[{"role": "system", "content": attempt_prompt}],
                parsed_output=decision,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={"summary_blocks": character_summary_block_audit},
                effective_user_trigger=effective_user_trigger,
            )
            return None

        move, error = parse_character_move_fn(char_raw_response)
        if error or move is None:
            if has_more_attempts:
                parse_retry_triggered = True
                parse_retry_reason = error or "Character move could not be parsed"
                log_turn_failure_fn(
                    round_number=round_number,
                    turn_number=turn_number,
                    bot_name=next_actor,
                    bot_type="character",
                    stage="parse_retry",
                    reason=parse_retry_reason,
                    input_messages=[{"role": "system", "content": attempt_prompt}],
                    raw_response=char_raw_response,
                    parsed_output=decision,
                    context_snapshot={
                        "director_decision": decision,
                        "character_names": char_names,
                        "attempt_index": attempt_index,
                    },
                    metadata={"summary_blocks": character_summary_block_audit},
                    effective_user_trigger=effective_user_trigger,
                )
                st_module.session_state["selector_decisions"].append(
                    f"Retrying {next_actor} after character move parse failure."
                )
                continue
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="parse",
                reason=error or "Character move could not be parsed",
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=decision,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={"summary_blocks": character_summary_block_audit},
                effective_user_trigger=effective_user_trigger,
            )
            return None

        present_for_norm = scene_state.get("present_characters") or char_names
        move = _normalize_parsed_move(
            move, next_actor=next_actor, present_for_norm=list(present_for_norm)
        )

        move_text = legacy_move_text_for_validation(move)
        (
            is_valid,
            rejection_reason,
            semantic_presence_assessment,
            proposal_coherence_assessment,
        ) = await _validate_character_move(
            move=move,
            move_text=move_text,
            next_actor=next_actor,
            user_name=user_name,
            st_module=st_module,
            state_manager=state_manager,
            continuity_manager=continuity_manager,
            scene_state=scene_state,
            attempt_prompt=attempt_prompt,
            turn_number=turn_number,
            effective_user_trigger=effective_user_trigger,
            validate_bot_response_fn=validate_bot_response_fn,
            get_model_client_fn=get_model_client_fn,
            assess_presence_violation_semantics_fn=assess_presence_violation_semantics_fn,
            should_override_presence_rejection_fn=should_override_presence_rejection_fn,
            assess_proposal_beat_contradiction_fn=assess_proposal_beat_contradiction_fn,
            cancellation_token=cancellation_token,
        )

        if is_valid:
            legality_ok, legality_reason, legality_ctx = (
                _evaluate_proposal_authority_for_attempt(
                    move=move,
                    next_actor=next_actor,
                    continuity_manager=continuity_manager,
                    scene_state=scene_state,
                )
            )
            if not legality_ok:
                is_valid = False
                rejection_reason = legality_reason
                proposal_authority_context = legality_ctx
            else:
                proposal_authority_context = legality_ctx

        sr_kind = _route_structured_validation_retries(
            is_valid=is_valid,
            rejection_reason=rejection_reason,
            has_more_attempts=has_more_attempts,
            duplicate_retry_consumed=duplicate_retry_consumed,
            binding_retry_consumed=binding_retry_consumed,
            investigation_retry_consumed=investigation_retry_consumed,
            proposal_coherence_retry_consumed=proposal_coherence_retry_consumed,
            proposal_legality_retry_consumed=proposal_legality_retry_consumed,
        )
        if sr_kind == "duplicate":
            duplicate_retry_triggered = True
            duplicate_retry_consumed = True
            duplicate_retry_reason = rejection_reason
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_duplicate_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after duplicate-output rejection."
            )
            continue
        if sr_kind == "binding":
            binding_retry_triggered = True
            binding_retry_consumed = True
            binding_retry_reason = rejection_reason
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_binding_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after binding sleeping-surface rejection."
            )
            continue
        if sr_kind == "investigation":
            investigation_retry_triggered = True
            investigation_retry_consumed = True
            investigation_retry_reason = rejection_reason
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_investigation_anchor_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after investigation anchor recall rejection."
            )
            continue
        if sr_kind == "proposal_coherence":
            proposal_coherence_retry_triggered = True
            proposal_coherence_retry_consumed = True
            proposal_coherence_retry_reason = rejection_reason
            if isinstance(proposal_coherence_assessment, dict):
                proposal_coherence_retry_reason_code = str(
                    proposal_coherence_assessment.get("reason_code", "") or ""
                )
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_proposal_coherence_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata=_character_audit_metadata_with_proposal_decision(
                    {
                        "summary_blocks": character_summary_block_audit,
                        "semantic_presence_assessment": semantic_presence_assessment or {},
                        "proposal_coherence_assessment": proposal_coherence_assessment
                        or {},
                    },
                    move=move,
                    attempt_index=attempt_index,
                    terminal=False,
                    retry_class="proposal_coherence",
                    proposal_coherence_assessment=proposal_coherence_assessment,
                    proposal_authority_context=None,
                    legality_evaluated=False,
                    lifecycle_phase="pre_commit",
                ),
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after proposal coherence rejection."
            )
            continue
        if sr_kind == "proposal_legality":
            proposal_legality_retry_triggered = True
            proposal_legality_retry_consumed = True
            proposal_legality_retry_reason = rejection_reason
            if proposal_authority_context is not None:
                proposal_legality_retry_reason_code = str(
                    proposal_authority_context.reason_code or ""
                )
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_proposal_legality_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata=_character_audit_metadata_with_proposal_decision(
                    {
                        "summary_blocks": character_summary_block_audit,
                        "semantic_presence_assessment": semantic_presence_assessment or {},
                    },
                    move=move,
                    attempt_index=attempt_index,
                    terminal=False,
                    retry_class="proposal_legality",
                    proposal_coherence_assessment=proposal_coherence_assessment,
                    proposal_authority_context=proposal_authority_context,
                    legality_evaluated=True,
                    lifecycle_phase="pre_commit",
                ),
                effective_user_trigger=effective_user_trigger,
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after proposal legality rejection."
            )
            continue

        if not is_valid:
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata=_character_audit_metadata_with_proposal_decision(
                    {
                        "summary_blocks": character_summary_block_audit,
                        "semantic_presence_assessment": semantic_presence_assessment or {},
                        "proposal_coherence_assessment": proposal_coherence_assessment
                        or {},
                    },
                    move=move,
                    attempt_index=attempt_index,
                    terminal=True,
                    retry_class=(
                        "proposal_legality"
                        if is_proposal_legality_rejection_reason(rejection_reason)
                        else (
                            "proposal_coherence"
                            if is_proposal_rejection_reason(rejection_reason)
                            else None
                        )
                    ),
                    proposal_coherence_assessment=proposal_coherence_assessment,
                    proposal_authority_context=(
                        proposal_authority_context
                        if is_proposal_legality_rejection_reason(rejection_reason)
                        else None
                    ),
                    legality_evaluated=is_proposal_legality_rejection_reason(
                        rejection_reason
                    ),
                    lifecycle_phase="failed_attempt",
                ),
                effective_user_trigger=effective_user_trigger,
            )
            return None

        continuity_applied_in_execute = False
        cm_exec = get_continuity_manager_fn()
        character_audit_v1: dict[str, Any] | None = None
        audit_v2_continuity_context: dict[str, Any] | None = None
        if cm_exec is not None and cm_exec.scene_state is not None:
            cg_res, progression_retry_consumed = _apply_continuity_and_progression_gate(
                st_module=st_module,
                cm_exec=cm_exec,
                move=move,
                decision=decision,
                next_actor=next_actor,
                char_names=char_names,
                trigger_text=trigger_text,
                attempt_index=attempt_index,
                orchestration_state=orchestration_state,
                round_number=round_number,
                turn_number=turn_number,
                attempt_prompt=attempt_prompt,
                char_raw_response=char_raw_response,
                character_summary_block_audit=character_summary_block_audit,
                effective_user_trigger=effective_user_trigger,
                semantic_presence_assessment=semantic_presence_assessment,
                has_more_attempts=has_more_attempts,
                progression_retry_consumed=progression_retry_consumed,
                proposal_authority_context=proposal_authority_context,
                log_turn_failure_fn=log_turn_failure_fn,
                sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity_fn,
                actors_failed_this_round=actors_failed_this_round,
            )
            if cg_res.kind == "progression_retry":
                progression_retry_triggered = True
                progression_retry_reason = (
                    "Progression enforcement: no qualifying structural delta after process_turn."
                )
                continue
            if cg_res.kind == "progression_terminal":
                return None
            continuity_applied_in_execute = cg_res.continuity_applied_in_execute
            continuity_transaction_snapshot = cg_res.continuity_transaction_snapshot
            character_audit_v1 = cg_res.character_audit_v1
            audit_v2_continuity_context = cg_res.audit_v2_continuity_context
        else:
            orch_scene = orchestration_state.get("scene_state")
            if not isinstance(orch_scene, dict):
                orch_scene = {}
            character_audit_v1 = build_character_audit_v1(
                move=dict(move),
                decision=decision,
                next_actor=next_actor,
                char_names=list(char_names),
                trigger_text=trigger_text,
                attempt_index=attempt_index,
                orchestration_state=orchestration_state,
                continuity_scope="orchestration_only",
                scene_state_pre_source_dict=orch_scene,
                issues_before_signatures=None,
                cm_exec=None,
            )

        stats_snap = st_module.session_state.get("proposal_coherence_stats")
        turn_execution_metadata = _turn_execution_metadata(
            attempt_index=attempt_index,
            parse_retry_triggered=parse_retry_triggered,
            parse_retry_reason=parse_retry_reason,
            duplicate_retry_triggered=duplicate_retry_triggered,
            duplicate_retry_reason=duplicate_retry_reason,
            progression_retry_triggered=progression_retry_triggered,
            progression_retry_reason=progression_retry_reason,
            binding_retry_triggered=binding_retry_triggered,
            binding_retry_reason=binding_retry_reason,
            investigation_retry_triggered=investigation_retry_triggered,
            investigation_retry_reason=investigation_retry_reason,
            proposal_coherence_retry_triggered=proposal_coherence_retry_triggered,
            proposal_coherence_retry_reason=proposal_coherence_retry_reason,
            proposal_coherence_stats_snapshot=(
                dict(stats_snap) if isinstance(stats_snap, dict) else None
            ),
            proposal_legality_retry_triggered=proposal_legality_retry_triggered,
            proposal_legality_retry_reason=proposal_legality_retry_reason,
        )

        cm_for_audit = get_continuity_manager_fn()
        turn_idx_for_decision = (
            int(getattr(cm_for_audit, "turn_counter", 0) or 0)
            if cm_for_audit is not None
            else None
        )
        semantic_proposal_decision = build_semantic_proposal_decision(
            move=move,
            proposal_authority_context=proposal_authority_context,
            lifecycle_phase="committed_attempt",
            attempt_index=attempt_index,
            terminal=False,
            retry_class=None,
            proposal_coherence_assessment=proposal_coherence_assessment,
            legality_evaluated=True,
            continuity_turn_index=turn_idx_for_decision,
            include_commit_proof_pointer=bool(
                continuity_applied_in_execute and turn_idx_for_decision
            ),
            process_turn_ran=continuity_applied_in_execute,
        )

        audit_v2_metadata = await _maybe_build_audit_v2_metadata(
            is_audit_enabled_fn=is_audit_enabled_fn,
            move=move,
            next_actor=next_actor,
            orchestration_state=orchestration_state,
            is_llm_audit_enabled_fn=is_llm_audit_enabled_fn,
            get_model_client_fn=get_model_client_fn,
            cancellation_token=cancellation_token,
            audit_v2_continuity_context=audit_v2_continuity_context,
            turn_execution_metadata=turn_execution_metadata,
        )

        log_character_turn_audit(
            next_actor=next_actor,
            move=move,
            task_prompt=attempt_prompt,
            char_raw_response=char_raw_response,
            decision=decision,
            char_names=char_names,
            continuity_manager=get_continuity_manager_fn(),
            round_number=round_number,
            turn_number=turn_number,
            character_summary_block_audit=character_summary_block_audit,
            turn_execution_metadata=turn_execution_metadata,
            progression_advisory=get_cached_progression_advisory(orchestration_state),
            anti_regression_advisory=get_cached_anti_regression_advisory(
                orchestration_state
            ),
            is_audit_enabled_fn=is_audit_enabled_fn,
            get_audit_logger_fn=get_audit_logger_fn,
            get_audit_context_fn=get_audit_context_fn,
            get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
            get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
            character_audit_v1=character_audit_v1,
            audit_v2=audit_v2_metadata,
            scene_grounding_state=st_module.session_state.get("scene_grounding"),
            effective_user_trigger=effective_user_trigger,
            semantic_proposal_decision=semantic_proposal_decision,
        )

        return CharacterAttemptOutcome(
            move=move,
            continuity_applied_in_execute=continuity_applied_in_execute,
            continuity_transaction_snapshot=continuity_transaction_snapshot,
            turn_execution_metadata=turn_execution_metadata,
        )

    return None
