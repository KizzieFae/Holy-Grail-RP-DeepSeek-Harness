#!/usr/bin/env python3
"""Issue #201 G3-E read-only retrieval forensic probe (investigation tooling)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.retrieval_contract import (  # noqa: E402
    GenerationHints,
    HardAccessConstraints,
    RetrievalAccessDiagnostics,
    RetrievalAccessRequest,
    ResponseBudget,
)
from domain_api.retrieval_service import RetrievalService  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain_api.story_knowledge_contract import StoryKnowledgeRecord  # noqa: E402
from domain_api.story_knowledge_epistemic import story_record_epistemically_eligible  # noqa: E402
from domain_api.story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402
from domain_api.story_knowledge_retrieval import (  # noqa: E402
    _referent_match,
    build_query_text,
    select_story_candidates,
)
from domain_api.story_knowledge_service import StoryKnowledgeService  # noqa: E402
from domain_api.story_semantic_index import SemanticIndexBackend  # noqa: E402


def _load_records(records_path: Path) -> list[StoryKnowledgeRecord]:
    records: list[StoryKnowledgeRecord] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(StoryKnowledgeRecord.from_dict(json.loads(line)))
    return records


def _seed_repo(records: list[StoryKnowledgeRecord], memory_scope_id: str) -> tuple[Path, StoryKnowledgeRepository]:
    tmp = Path(tempfile.mkdtemp(prefix="g3e-probe-"))
    repo = StoryKnowledgeRepository(tmp)
    path = repo.records_path(memory_scope_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = record.to_dict()
            if not payload.get("content_hash"):
                payload["content_hash"] = record.compute_content_hash()
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    service = StoryKnowledgeService(repo)
    recovered = repo.recover_truncated_tail(memory_scope_id)
    if recovered != len(records):
        raise RuntimeError(f"manifest recovery expected {len(records)} records, got {recovered}")
    service.rebuild_semantic_index(memory_scope_id)
    return tmp, repo


def _make_request(
    fixture: object,
    *,
    query_terms: tuple[str, ...],
    viewer: str,
    budget_chars: int = 8000,
    max_candidates: int = 8,
) -> RetrievalAccessRequest:
    return RetrievalAccessRequest(
        request_id="g3e-probe",
        consumer_role="librarian",
        hg_scene_id=fixture.hg_scene_id,
        hg_round_id="g3e-round-1",
        turn_index=1,
        memory_scope_id=fixture.memory_scope_id,
        hard_access=HardAccessConstraints(
            known_by_character_name=viewer,
            allowed_information_classes=frozenset({"story_occurrence", "story_derived"}),
        ),
        generation_hints=GenerationHints(query_terms=query_terms),
        response_budget=ResponseBudget(max_candidates=max_candidates, max_total_chars=budget_chars),
    )


def _pre_entitlement_relevance_probe(
    *,
    fixture: object,
    records: list[StoryKnowledgeRecord],
    request: RetrievalAccessRequest,
    semantic_index: SemanticIndexBackend,
    target_record_id: str | None = None,
) -> dict[str, object]:
    hard = request.hard_access
    referent_pool: list[StoryKnowledgeRecord] = []
    for record in records:
        if not _referent_match(record, hard.entity_eligibility_refs):
            continue
        referent_pool.append(record)
    query_text = build_query_text(request.generation_hints, request)
    ranked_ids: list[str] = []
    if semantic_index.available:
        ranked_ids = semantic_index.rank(
            query_text,
            [record.record_id for record in referent_pool],
            limit=request.response_budget.max_candidates * 4,
        )
    target_in_referent_pool = any(record.record_id == target_record_id for record in referent_pool)
    target_in_ranked = target_record_id in ranked_ids if target_record_id else False
    return {
        "probe_kind": "offline_pre_entitlement_relevance",
        "read_only": True,
        "does_not_alter_production_path": True,
        "query_text": query_text,
        "referent_pool_count": len(referent_pool),
        "ranked_ids_sample": ranked_ids[:16],
        "target_record_id": target_record_id,
        "target_in_referent_pool": target_in_referent_pool,
        "target_in_unconstrained_rank": target_in_ranked,
    }


def _per_record_entitlement(
    fixture: object,
    records: list[StoryKnowledgeRecord],
    viewer: str,
    record_ids: list[str],
) -> dict[str, bool]:
    by_id = {record.record_id: record for record in records}
    return {
        record_id: story_record_epistemically_eligible(
            fixture,
            by_id[record_id],
            viewer_character_id=viewer,
        )
        for record_id in record_ids
        if record_id in by_id
    }


def _eligible_ids_without_ranking(
    fixture: object,
    records: list[StoryKnowledgeRecord],
    request: RetrievalAccessRequest,
) -> list[str]:
    hard = request.hard_access
    viewer = hard.known_by_character_name or hard.viewer_character_id
    eligible: list[str] = []
    for record in records:
        if not _referent_match(record, hard.entity_eligibility_refs):
            continue
        if not story_record_epistemically_eligible(
            fixture,
            record,
            viewer_character_id=viewer,
            viewer_role=hard.viewer_role,
        ):
            continue
        eligible.append(record.record_id)
    return sorted(eligible)


def probe_case(
    *,
    case_id: str,
    policy: dict[str, object],
    records: list[StoryKnowledgeRecord],
    fixture: object,
    retrieval: RetrievalService,
    repo: StoryKnowledgeRepository,
) -> dict[str, object]:
    viewer = str(policy.get("viewer_character_id", "ayame"))
    query_terms = tuple(str(term) for term in policy.get("query_terms", []) if str(term).strip())
    request = _make_request(
        fixture,
        query_terms=query_terms,
        viewer=viewer,
        budget_chars=int(policy.get("max_projected_chars", 8000)),
        max_candidates=int(policy.get("max_projected_items", 8)),
    )
    response = retrieval.retrieve(request, fixture)
    eligible_ids = _eligible_ids_without_ranking(fixture, records, request)
    ranked_ids = [candidate.candidate_id for candidate in response.candidates]
    projected_ids = ranked_ids[:]
    semantic_index = SemanticIndexBackend(index_path=repo.semantic_index_path(fixture.memory_scope_id))

    forbidden_id = policy.get("forbidden_record_id")
    pre_probe = None
    if forbidden_id:
        pre_probe = _pre_entitlement_relevance_probe(
            fixture=fixture,
            records=records,
            request=request,
            semantic_index=semantic_index,
            target_record_id=str(forbidden_id),
        )

    required_ids = list(policy.get("required_record_ids") or [])
    if policy.get("required_record_id"):
        required_ids.append(str(policy["required_record_id"]))
    if policy.get("authoritative_record_id"):
        required_ids.append(str(policy["authoritative_record_id"]))

    entitlement_targets = list({*(required_ids or []), *([str(forbidden_id)] if forbidden_id else [])})
    entitlement_map = _per_record_entitlement(fixture, records, viewer, entitlement_targets)
    entitlement_rejections: list[dict[str, str]] = []
    hard = request.hard_access
    viewer_id = hard.known_by_character_name or hard.viewer_character_id
    for record in records:
        if not _referent_match(record, hard.entity_eligibility_refs):
            continue
        if story_record_epistemically_eligible(
            fixture,
            record,
            viewer_character_id=viewer_id,
            viewer_role=hard.viewer_role,
        ):
            continue
        entitlement_rejections.append({"record_id": record.record_id, "reason": "entitlement"})

    forensic_chain = {
        "knowledge_need": {
            "case_id": case_id,
            "query_terms": list(query_terms),
            "viewer_character_id": viewer,
        },
        "candidate_retrieval": {
            "story_selection_path": response.diagnostics.story_selection_path,
            "semantic_index_failed": response.diagnostics.story_semantic_index_failed,
        },
        "ranking": {"ranked_ids": ranked_ids},
        "entitlement_decision": {
            "hard_access_rejected": response.diagnostics.hard_access_rejected,
            "entitlement_rejection_count": len(entitlement_rejections),
            "entitlement_rejections_sample": entitlement_rejections[:32],
            "eligible_record_ids": eligible_ids,
            "per_record_entitled": entitlement_map,
        },
        "provenance": [
            {
                "record_id": candidate.candidate_id,
                "provenance": dict(candidate.provenance or {}),
            }
            for candidate in response.candidates
        ],
        "projection": {
            "projected_record_ids": projected_ids,
            "projected_char_estimate": sum(len(candidate.payload.content) for candidate in response.candidates),
        },
        "pre_entitlement_relevance_probe": pre_probe,
    }

    return {
        "case_id": case_id,
        "viewer_character_id": viewer,
        "diagnostics": response.diagnostics.to_dict(),
        "eligible_record_ids": eligible_ids,
        "ranked_ids": ranked_ids,
        "forensic_chain": forensic_chain,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="G3-E retrieval forensic probe")
    parser.add_argument("--records", required=True, help="Path to records.jsonl")
    parser.add_argument("--policies-dir", required=True, help="Directory of K*.json policies")
    parser.add_argument("--memory-scope-id", default="g3e_ayame_archive_v1")
    parser.add_argument("--cast", default="ayame,kizzie")
    args = parser.parse_args()

    records_path = Path(args.records)
    policies_dir = Path(args.policies_dir)
    records = _load_records(records_path)
    tmp_dir, repo = _seed_repo(records, args.memory_scope_id)
    try:
        fixture = initialize_live_session(cast=[c.strip() for c in args.cast.split(",") if c.strip()])
        fixture.memory_scope_id = args.memory_scope_id
        retrieval = RetrievalService(story_knowledge_repo=repo)
        cases: list[dict[str, object]] = []
        for policy_path in sorted(policies_dir.glob("K*.json")):
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            case_id = str(policy.get("case_id", policy_path.stem))
            cases.append(
                probe_case(
                    case_id=case_id,
                    policy=policy,
                    records=records,
                    fixture=fixture,
                    retrieval=retrieval,
                    repo=repo,
                )
            )
        payload = {
            "schema": "issue201_g3e_retrieval_probe_v1",
            "record_count": len(records),
            "memory_scope_id": args.memory_scope_id,
            "cases": cases,
        }
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
