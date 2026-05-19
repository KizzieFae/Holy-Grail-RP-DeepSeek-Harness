"""GitHub #233 — semantic_proposal_decision audit contract."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_semantic_proposal_decision import (
    ACCEPTED_PROPOSAL_BATCH_NOTE,
    build_semantic_proposal_decision,
    should_emit_semantic_proposal_decision,
)
from app_turn_audit import log_turn_failure
from continuity_semantic_proposals import (
    ProposalAuthorityContext,
    ProposalAuthorityOutcome,
)
from turn_runner_audit import log_character_turn_audit


def _accept_ctx() -> ProposalAuthorityContext:
    proposal = {"kind": "off_focal", "character": "A"}
    return ProposalAuthorityContext(
        outcome=ProposalAuthorityOutcome.ACCEPT,
        accepted_proposals=(proposal,),
    )


def _reject_ctx() -> ProposalAuthorityContext:
    return ProposalAuthorityContext(
        outcome=ProposalAuthorityOutcome.REJECT,
        reason_code="illegal_already_off_focal",
        reason_detail="off_focal illegal: A is not on-stage.",
    )


def test_should_emit_on_success_character_row() -> None:
    assert should_emit_semantic_proposal_decision(
        {},
        force_success_character_row=True,
    )


def test_accept_includes_batch_and_commit_pointer() -> None:
    move = {"semantic_proposals": [{"kind": "off_focal", "character": "A"}]}
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=_accept_ctx(),
        lifecycle_phase="committed_attempt",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        continuity_turn_index=3,
        include_commit_proof_pointer=True,
        process_turn_ran=True,
    )
    assert record["batch"]["authority_outcome"] == "accept"
    assert record["batch"]["covered_compile_authorized"] is True
    assert record["batch"]["process_turn_authorized"] is True
    assert record["accepted_proposal_batch"] == [{"kind": "off_focal", "character": "A"}]
    assert record["accepted_proposal_batch_note"] == ACCEPTED_PROPOSAL_BATCH_NOTE
    assert record["commit_proof_pointer"]["continuity_turn_index"] == 3
    assert "scene_state_after" in record["commit_proof_pointer"]["scene_state_field"]


def test_no_proposal_omits_accepted_batch() -> None:
    record = build_semantic_proposal_decision(
        move={"beats": []},
        proposal_authority_context=ProposalAuthorityContext(
            outcome=ProposalAuthorityOutcome.NO_PROPOSAL
        ),
        lifecycle_phase="committed_attempt",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        process_turn_ran=True,
    )
    assert record["batch"]["authority_outcome"] == "no_proposal"
    assert "accepted_proposal_batch" not in record
    assert "accepted_proposal_batch_note" not in record


def test_reject_omits_accepted_batch() -> None:
    move = {"semantic_proposals": [{"kind": "off_focal", "character": "A"}]}
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=_reject_ctx(),
        lifecycle_phase="failed_attempt",
        attempt_index=1,
        terminal=True,
        retry_class="proposal_legality",
        legality_evaluated=True,
        process_turn_ran=False,
    )
    assert record["batch"]["authority_outcome"] == "reject"
    assert record["batch"]["covered_compile_authorized"] is False
    assert "accepted_proposal_batch" not in record
    assert "commit_proof_pointer" not in record


def test_rollback_phase_omits_commit_proof_pointer() -> None:
    move = {"semantic_proposals": [{"kind": "off_focal", "character": "A"}]}
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=_accept_ctx(),
        lifecycle_phase="committed_attempt_rolled_back",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        process_turn_ran=True,
    )
    assert record["batch"]["covered_compile_authorized"] is True
    assert "commit_proof_pointer" not in record


def test_coherence_failure_without_legality_omits_authority_outcome() -> None:
    move = {"semantic_proposals": [{"kind": "off_focal", "character": "A"}]}
    record = build_semantic_proposal_decision(
        move=move,
        proposal_authority_context=None,
        lifecycle_phase="pre_commit",
        attempt_index=0,
        terminal=False,
        retry_class="proposal_coherence",
        proposal_coherence_assessment={"status": "contradicted"},
        legality_evaluated=False,
    )
    assert "authority_outcome" not in record["batch"]
    assert record["pre_commit"]["coherence_status"] == "contradicted"
    assert record["pre_commit"]["legality_evaluated"] is False


def test_log_character_turn_audit_includes_semantic_proposal_decision() -> None:
    captured: dict[str, Any] = {}

    class _Logger:
        def create_entry(self, **kwargs: Any) -> object:
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry: object) -> None:
            pass

    decision = build_semantic_proposal_decision(
        move={},
        proposal_authority_context=ProposalAuthorityContext(
            outcome=ProposalAuthorityOutcome.NO_PROPOSAL
        ),
        lifecycle_phase="committed_attempt",
        attempt_index=0,
        terminal=False,
        retry_class=None,
        legality_evaluated=True,
        process_turn_ran=False,
    )

    log_character_turn_audit(
        next_actor="A",
        move={"beats": []},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"next_actor": "A"},
        char_names=["A"],
        continuity_manager=None,
        round_number=1,
        turn_number=1,
        character_summary_block_audit={
            "summary_generation_eligible": False,
            "summary_blocks_generated_total": 0,
            "generated_summary_block_ids": [],
            "summary_blocks_available_count": 0,
            "available_summary_block_ids": [],
            "summary_blocks_selected_count": 0,
            "selected_summary_block_ids": [],
            "excluded_summary_block_ids": [],
            "selection_reason": "",
            "skipped_reason": "",
            "fallback_used": False,
            "summary_limit": None,
            "has_binding_constraints": False,
            "scene_binding_constraints_section": "",
        },
        semantic_proposal_decision=decision,
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
        effective_user_trigger="",
    )

    meta = captured["metadata"]
    assert "semantic_proposal_decision" in meta
    assert meta["semantic_proposal_decision"]["batch"]["authority_outcome"] == "no_proposal"
    assert "proposal_authority_outcome" not in meta.get("turn_execution", {})


def test_log_turn_failure_includes_semantic_proposal_decision_in_metadata() -> None:
    captured: dict[str, Any] = {}

    class _Logger:
        def create_entry(self, **kwargs: Any) -> object:
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry: object) -> None:
            pass

    class _St:
        session_state = {"rejected_messages": [], "selector_decisions": []}

    decision = build_semantic_proposal_decision(
        move={"semantic_proposals": [{"kind": "off_focal", "character": "A"}]},
        proposal_authority_context=_reject_ctx(),
        lifecycle_phase="pre_commit",
        attempt_index=1,
        terminal=False,
        retry_class="proposal_legality",
        legality_evaluated=True,
    )

    log_turn_failure(
        st_module=_St(),
        round_number=1,
        turn_number=1,
        bot_name="A",
        bot_type="character",
        stage="validation_proposal_legality_retry",
        reason="[PROPOSAL_LEGALITY] illegal",
        input_messages=[],
        raw_response="{}",
        parsed_output={"semantic_proposals": [{"kind": "off_focal", "character": "A"}]},
        context_snapshot={},
        metadata={"semantic_proposal_decision": decision},
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        build_attempted_post_details_fn=lambda *_a, **_k: None,
        get_continuity_manager_fn=lambda: None,
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
    )

    meta = captured["metadata"]
    assert meta["semantic_proposal_decision"]["lifecycle_phase"] == "pre_commit"
    assert meta["semantic_proposal_decision"]["batch"]["authority_outcome"] == "reject"
