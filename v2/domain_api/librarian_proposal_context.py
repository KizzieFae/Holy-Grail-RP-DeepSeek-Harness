"""Post-commit evidence catalog for Librarian proposal inference (#34 S4a)."""

from __future__ import annotations

import json
from typing import Any

from continuity_issue_retrieval import get_active_issues
from continuity_state import IssueStatus

from .contract import PromptContribution
from .librarian_proposal_contract import (
    LibrarianProposalContextRequest,
    ProposalEvidenceCatalogItem,
)
from .session_history import history_entries
from .session_state import LiveSession


def _find_committed_turn(
    fixture: LiveSession,
    *,
    domain_commit_id: str,
) -> dict[str, Any] | None:
    for entry in reversed(history_entries(fixture.rp_history)):
        if entry.kind != "committed_turn":
            continue
        if str(entry.domain_commit_id or "") != domain_commit_id:
            continue
        metadata = dict(entry.metadata or {})
        move = dict(metadata.get("structured_move") or {})
        return {
            "domain_commit_id": entry.domain_commit_id,
            "character_id": entry.actor_id,
            "turn_index": metadata.get("continuity_turn_index"),
            "committed_move": move,
            "hg_round_id": entry.hg_round_id,
        }
    return None


def build_post_commit_evidence_catalog(
    request: LibrarianProposalContextRequest,
    fixture: LiveSession,
) -> tuple[tuple[ProposalEvidenceCatalogItem, ...], dict[str, Any] | None]:
    commit_record = _find_committed_turn(fixture, domain_commit_id=request.domain_commit_id)
    if commit_record is None:
        return (), None

    move = dict(commit_record.get("committed_move") or {})
    catalog: list[ProposalEvidenceCatalogItem] = [
        ProposalEvidenceCatalogItem(
            anchor_id=f"committed_move:{request.domain_commit_id}",
            evidence_kind="committed_move",
            stable_ref=f"commit:{request.domain_commit_id}",
            authority_class="authoritative",
            visibility_scope="public",
            content=json.dumps(move, ensure_ascii=False, sort_keys=True)[:4000],
            anchor_commit_id=request.domain_commit_id,
            anchor_path="/",
            provenance={
                "character_id": commit_record.get("character_id"),
                "turn_index": commit_record.get("turn_index"),
            },
        )
    ]

    scene_state_obj = getattr(fixture.manager, "scene_state", None)
    scene_state = scene_state_obj.to_dict() if scene_state_obj is not None else {}
    turn_index = request.turn_index
    if turn_index is None and commit_record.get("turn_index") is not None:
        turn_index = int(commit_record.get("turn_index"))

    for event in getattr(fixture.manager, "public_events", []) or []:
        event_turn = getattr(event, "turn_index", None)
        if turn_index is not None and event_turn not in (None, turn_index):
            continue
        event_id = str(getattr(event, "event_id", "") or "").strip()
        if not event_id:
            continue
        event_payload = {
            "event_id": event_id,
            "event_type": getattr(event, "event_type", "action"),
            "summary": getattr(event, "summary", ""),
            "significance": getattr(event, "significance", "minor"),
            "known_by": list(getattr(event, "known_by", []) or []),
            "observed_by": list(getattr(event, "observed_by", []) or []),
            "turn_index": event_turn,
            "revelation_significance_by_character": getattr(
                event, "revelation_significance_by_character", None
            ),
        }
        catalog.append(
            ProposalEvidenceCatalogItem(
                anchor_id=f"public_event:{event_id}",
                evidence_kind="public_event",
                stable_ref=f"event:{event_id}",
                authority_class="authoritative",
                visibility_scope="public",
                content=json.dumps(event_payload, ensure_ascii=False, sort_keys=True),
                anchor_commit_id=request.domain_commit_id,
                anchor_path=f"/public_events/{event_id}",
                provenance={
                    "event_id": event_id,
                    "turn_index": event_turn,
                },
            )
        )

    if isinstance(scene_state, dict) and scene_state:
        catalog.append(
            ProposalEvidenceCatalogItem(
                anchor_id=f"scene_state:{request.domain_commit_id}",
                evidence_kind="scene_state",
                stable_ref=f"scene_state:{request.domain_commit_id}",
                authority_class="authoritative",
                visibility_scope="scene_orchestration",
                content=json.dumps(
                    {
                        "present_characters": scene_state.get("present_characters"),
                        "location_id": scene_state.get("location_id"),
                        "phase": scene_state.get("phase"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                anchor_commit_id=request.domain_commit_id,
                provenance={"snapshot": "post_commit"},
            )
        )
        catalog.append(
            ProposalEvidenceCatalogItem(
                anchor_id=f"continuity_state:{request.domain_commit_id}",
                evidence_kind="continuity_state",
                stable_ref=f"continuity_state:{request.domain_commit_id}",
                authority_class="authoritative",
                visibility_scope="orchestration_only",
                content=json.dumps(
                    {
                        "active_issues": list((scene_state.get("active_issues") or {}).keys())[:8],
                        "turn_index": request.turn_index,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                anchor_commit_id=request.domain_commit_id,
                provenance={"snapshot": "post_commit"},
            )
        )

    active_issues = get_active_issues(
        manager=fixture.manager,
        limit=8,
        statuses=[IssueStatus.ACTIVE, IssueStatus.ESCALATING],
    )
    for issue in active_issues:
        issue_id = str(issue.issue_id)
        issue_payload = {
            "issue_id": issue_id,
            "status": issue.status.value,
            "participants": list(issue.participants),
            "pressure_kind": issue.pressure_kind,
            "blocked_what": issue.blocked_what,
            "required_next_step": issue.required_next_step,
            "last_change": issue.last_change,
            "description": issue.description,
        }
        catalog.append(
            ProposalEvidenceCatalogItem(
                anchor_id=f"continuity_issue:{issue_id}",
                evidence_kind="continuity_issue",
                stable_ref=f"issue:{issue_id}",
                authority_class="authoritative",
                visibility_scope="scene_orchestration",
                content=json.dumps(issue_payload, ensure_ascii=False, sort_keys=True),
                anchor_commit_id=request.domain_commit_id,
                anchor_path=f"/issues/{issue_id}",
                provenance={
                    "issue_id": issue_id,
                    "status": issue.status.value,
                    "turn_index": request.turn_index,
                },
            )
        )

    return tuple(catalog), commit_record


def build_proposal_manifest_contributions(
    request: LibrarianProposalContextRequest,
    *,
    manifest_id: str,
    catalog: tuple[ProposalEvidenceCatalogItem, ...],
    authoritative_snapshot_id_value: str,
) -> list[PromptContribution]:
    envelope = request.visibility_envelope
    request_block = {
        "request_id": request.request_id,
        "domain_commit_id": request.domain_commit_id,
        "hg_round_id": request.hg_round_id,
        "turn_index": request.turn_index,
        "pipeline_stage": "post_commit",
        "audit_reason": request.audit_reason,
    }
    envelope_block = {
        "viewer_role": envelope.viewer_role,
        "authority_ceiling_enforced": envelope.authority_ceiling_enforced,
        "viewer_character_id": envelope.viewer_character_id,
        "subject_character_id": envelope.subject_character_id,
        "session_template_id": envelope.session_template_id,
    }
    catalog_block = [
        {
            "anchor_id": item.anchor_id,
            "evidence_kind": item.evidence_kind,
            "stable_ref": item.stable_ref,
            "authority_class": item.authority_class,
            "visibility_scope": item.visibility_scope,
            "anchor_commit_id": item.anchor_commit_id,
            "anchor_path": item.anchor_path,
            "content": item.content,
            "provenance": item.provenance,
        }
        for item in catalog
    ]
    return [
        PromptContribution(
            contribution_id=f"{manifest_id}-request",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"librarian_proposal_request:{request.request_id}",),
            priority=10,
            content=(
                "Post-commit Librarian proposal request (information interpretation only):\n"
                f"{json.dumps(request_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={
                "inference_id": request.librarian_inference_id,
                "request_id": request.request_id,
                "domain_commit_id": request.domain_commit_id,
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-envelope",
            source_kind="active_constraints",
            authority_class="authoritative",
            knowledge_ids=(f"librarian_proposal_envelope:{request.request_id}",),
            priority=11,
            content=(
                "Host visibility/authority envelope (must not be widened):\n"
                f"{json.dumps(envelope_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={
                "inference_id": request.librarian_inference_id,
                "authoritative_snapshot_id": authoritative_snapshot_id_value,
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-catalog",
            source_kind="librarian_knowledge",
            authority_class="derived",
            knowledge_ids=tuple(item.anchor_id for item in catalog),
            priority=12,
            content=(
                "Bounded post-commit evidence catalog. Proposals MUST cite anchor_id values "
                "from this catalog only. Do NOT invent facts or use Storyteller PreservationSignal "
                "attention refs as evidence.\n"
                f"{json.dumps(catalog_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={
                "inference_id": request.librarian_inference_id,
                "domain_commit_id": request.domain_commit_id,
            },
        ),
    ]
