#!/usr/bin/env python3
"""List Holy Grail V2 execution evidence for a session."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from _repo_paths import EXECUTION_EVIDENCE_DIR, REPO_ROOT  # noqa: E402


def session_evidence_dir(hg_session_id: str) -> Path:
    return EXECUTION_EVIDENCE_DIR / hg_session_id


def load_index(hg_session_id: str) -> dict | None:
    index_path = session_evidence_dir(hg_session_id) / "index.json"
    if not index_path.is_file():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def load_attempt(hg_session_id: str, evidence_id: str) -> dict | None:
    attempt_path = session_evidence_dir(hg_session_id) / "attempts" / f"{evidence_id}.json"
    if not attempt_path.is_file():
        return None
    return json.loads(attempt_path.read_text(encoding="utf-8"))


def round_attempt_ids(index: dict, round_id: str | None) -> list[str]:
    if round_id:
        return list((index.get("rounds") or {}).get(round_id) or [])
    return list(index.get("attempt_ids") or [])


def filter_attempts(
    hg_session_id: str,
    attempt_ids: list[str],
    *,
    role: str | None = None,
    qa_target_role: str | None = None,
) -> list[dict]:
    attempts = []
    for evidence_id in attempt_ids:
        attempt = load_attempt(hg_session_id, evidence_id)
        if not attempt:
            continue
        correlation = attempt.get("correlation") or {}
        if role and correlation.get("role") != role:
            continue
        semantic_qa = (attempt.get("decision") or {}).get("semantic_qa")
        if qa_target_role:
            if not semantic_qa or semantic_qa.get("evaluation_target_role") != qa_target_role:
                continue
        attempts.append(attempt)
    return attempts


def summarize_attempt(attempt: dict) -> str:
    correlation = attempt.get("correlation") or {}
    decision = attempt.get("decision") or {}
    semantic_qa = decision.get("semantic_qa") or {}
    semantic_eval = decision.get("semantic_evaluation") or {}
    lines = [
        f"evidence_id: {attempt.get('evidence_id')}",
        f"role: {correlation.get('role')}",
        f"inference_id: {correlation.get('inference_id')}",
        f"prior_attempt_id: {correlation.get('prior_attempt_id')}",
        f"outcome: {decision.get('outcome')}",
        f"terminal_disposition: {decision.get('terminal_disposition')}",
    ]
    policy = semantic_qa.get("policy_action")
    if policy:
        lines.append(f"policy_action: {policy}")
    elif semantic_eval.get("result"):
        lines.append(f"semantic_overall: {semantic_eval.get('result', {}).get('overall_result')}")
    if semantic_qa.get("evaluator_evidence_id"):
        lines.append(f"evaluator_evidence_id: {semantic_qa.get('evaluator_evidence_id')}")
    findings = (semantic_qa.get("result") or semantic_eval.get("result") or {}).get("findings") or []
    for idx, finding in enumerate(findings[:3]):
        lines.append(
            f"finding[{idx}]: {finding.get('dimension')} "
            f"{finding.get('severity')} "
            f"ref={((finding.get('authoritative_citation') or {}).get('ref_id'))}"
        )
    director = decision.get("director") or {}
    eligibility = director.get("eligibility") or {}
    if eligibility.get("eligible_actors") is not None:
        lines.append(f"eligible_actors: {eligibility.get('eligible_actors')}")
    participation = decision.get("participation") or {}
    if participation.get("selected_actor"):
        lines.append(f"selected_actor: {participation.get('selected_actor')}")
        lines.append(f"selection_mode: {participation.get('selection_mode')}")
    return "\n".join(lines)


def resolve_authority_refs(attempt: dict) -> dict[str, dict]:
    refs: dict[str, dict] = {}
    for contribution in (attempt.get("request") or {}).get("contributions") or []:
        content = str(contribution.get("content") or "")
        if "Authority references supplied" not in content and "ref_id" not in content:
            continue
        match = re.search(r"\[[\s\S]*\]", content)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            for ref in parsed:
                ref_id = ref.get("ref_id")
                if ref_id:
                    refs[str(ref_id)] = ref
    return refs


def cite_trace(hg_session_id: str, evidence_id: str) -> str:
    attempt = load_attempt(hg_session_id, evidence_id)
    if not attempt:
        return f"Attempt not found: {evidence_id}"
    decision = attempt.get("decision") or {}
    semantic_qa = decision.get("semantic_qa") or {}
    semantic_eval = decision.get("semantic_evaluation") or {}
    findings = (semantic_qa.get("result") or semantic_eval.get("result") or {}).get("findings") or []
    lines = [summarize_attempt(attempt), ""]
    evaluator_id = semantic_qa.get("evaluator_evidence_id")
    eval_attempt = load_attempt(hg_session_id, evaluator_id) if evaluator_id else attempt
    refs = resolve_authority_refs(eval_attempt or {})
    for finding in findings:
        ref_id = (finding.get("authoritative_citation") or {}).get("ref_id")
        lines.append(f"finding: {finding.get('dimension')} — {finding.get('finding')}")
        lines.append(f"rationale: {finding.get('rationale')}")
        if ref_id and ref_id in refs:
            ref = refs[ref_id]
            lines.append(
                f"cite[{ref_id}] class={ref.get('authority_class')} "
                f"text={str(ref.get('text') or '')[:240]}"
            )
        elif ref_id:
            lines.append(f"cite[{ref_id}]: ref not found in evaluator request")
        lines.append("")
    return "\n".join(lines).rstrip()


def chain_for_inference(hg_session_id: str, index: dict, inference_id: str) -> list[dict]:
    semantic = index.get("semantic") or {}
    qa_chain = (semantic.get("qa_pass_chains") or {}).get(inference_id) or []
    if qa_chain:
        return qa_chain
    evidence_ids = (semantic.get("evaluation_chains") or {}).get(inference_id) or []
    chain = []
    for candidate_id in evidence_ids:
        attempt = load_attempt(hg_session_id, candidate_id)
        if not attempt:
            continue
        semantic_qa = (attempt.get("decision") or {}).get("semantic_qa") or {}
        chain.append(
            {
                "candidate_evidence_id": candidate_id,
                "evaluator_evidence_id": semantic_qa.get("evaluator_evidence_id"),
                "evaluation_pass_id": semantic_qa.get("evaluation_pass_id"),
                "policy_action": semantic_qa.get("policy_action"),
            }
        )
    return chain


def print_chain(
    hg_session_id: str,
    index: dict,
    *,
    chain_kind: str,
    round_id: str | None,
    inference_id: str | None,
) -> None:
    attempt_ids = round_attempt_ids(index, round_id)
    if chain_kind == "participation":
        participation_ids = []
        if round_id:
            participation_ids = list((index.get("participation_by_round") or {}).get(round_id) or [])
        else:
            for attempt in filter_attempts(hg_session_id, attempt_ids, role="participation"):
                participation_ids.append(attempt.get("evidence_id"))
        for pid in participation_ids:
            attempt = load_attempt(hg_session_id, pid)
            if not attempt:
                continue
            print(summarize_attempt(attempt))
            char_id = (attempt.get("associations") or {}).get("character_evidence_id")
            if char_id:
                char_attempt = load_attempt(hg_session_id, char_id)
                if char_attempt:
                    print("\n→ character execution")
                    print(summarize_attempt(char_attempt))
            print("")
        return

    if chain_kind == "character":
        for attempt in filter_attempts(hg_session_id, attempt_ids, role="character"):
            print(summarize_attempt(attempt))
            print("")
        return

    role = "director" if chain_kind == "director" else "narrator"
    if inference_id:
        print(f"inference_id: {inference_id}")
        for entry in chain_for_inference(hg_session_id, index, inference_id):
            print(json.dumps(entry, ensure_ascii=False))
            candidate = load_attempt(hg_session_id, entry.get("candidate_evidence_id"))
            if candidate:
                print(summarize_attempt(candidate))
            evaluator_id = entry.get("evaluator_evidence_id")
            if evaluator_id:
                evaluator = load_attempt(hg_session_id, evaluator_id)
                if evaluator:
                    print("→ evaluator")
                    print(summarize_attempt(evaluator))
            print("")
        return

    for attempt in filter_attempts(hg_session_id, attempt_ids, role=role):
        inf = (attempt.get("correlation") or {}).get("inference_id")
        if not inf:
            continue
        print(f"inference_id: {inf}")
        for entry in chain_for_inference(hg_session_id, index, inf):
            print(json.dumps(entry, ensure_ascii=False))
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hg_session_id", help="Holy Grail session id")
    parser.add_argument("--round", help="Filter to one hg_round_id")
    parser.add_argument("--attempt", help="Print one attempt record by evidence_id")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human summary")
    parser.add_argument("--role", help="Filter attempts by correlation.role")
    parser.add_argument(
        "--qa-target-role",
        choices=["director", "narrator"],
        help="Filter candidate attempts with semantic QA for target role",
    )
    parser.add_argument(
        "--inference-id",
        help="Print QA/candidate chain for one inference id",
    )
    parser.add_argument(
        "--chain",
        choices=["director", "narrator", "character", "participation"],
        help="Reconstruct a role-specific causal chain for the round",
    )
    parser.add_argument(
        "--participation",
        action="store_true",
        help="List participation evidence ids for the selected round",
    )
    parser.add_argument("--summary", action="store_true", help="Human-readable attempt summaries")
    parser.add_argument("--cite", help="Resolve finding citations for an evidence id")
    parser.add_argument("--semantic-hard", action="store_true")
    parser.add_argument("--semantic-soft", action="store_true")
    parser.add_argument("--dimension", help="Filter semantic index by dimension")
    parser.add_argument("--multi-candidate", action="store_true")
    parser.add_argument("--evaluator-failure", action="store_true")
    parser.add_argument("--residual-soft", action="store_true")
    parser.add_argument("--exhausted-hard", action="store_true")
    args = parser.parse_args()

    root = session_evidence_dir(args.hg_session_id)
    if not root.is_dir():
        print(f"No execution evidence directory: {root}", file=sys.stderr)
        return 1

    if args.cite:
        print(cite_trace(args.hg_session_id, args.cite))
        return 0

    if args.attempt:
        attempt = load_attempt(args.hg_session_id, args.attempt)
        if attempt is None:
            print(f"Attempt not found: {args.attempt}", file=sys.stderr)
            return 1
        if args.summary:
            print(summarize_attempt(attempt))
        else:
            print(json.dumps(attempt, indent=2, ensure_ascii=False))
        return 0

    index = load_index(args.hg_session_id)
    if index is None:
        print(f"Missing index.json under {root}", file=sys.stderr)
        return 1

    semantic = index.get("semantic") or {}
    if args.semantic_hard:
        for evidence_id in semantic.get("hard_findings") or []:
            print(evidence_id)
        return 0
    if args.semantic_soft:
        for evidence_id in semantic.get("soft_findings") or []:
            print(evidence_id)
        return 0
    if args.dimension:
        for evidence_id in (semantic.get("by_dimension") or {}).get(args.dimension) or []:
            print(evidence_id)
        return 0
    if args.multi_candidate:
        for inference_id in semantic.get("multi_candidate_inferences") or []:
            print(inference_id)
        return 0
    if args.evaluator_failure:
        for evidence_id in semantic.get("evaluator_failures") or []:
            print(evidence_id)
        return 0
    if args.residual_soft:
        for evidence_id in semantic.get("residual_soft") or []:
            print(evidence_id)
        return 0
    if args.exhausted_hard:
        for inference_id in semantic.get("exhausted_hard_loops") or []:
            print(inference_id)
        return 0

    if args.participation:
        ids = list((index.get("participation_by_round") or {}).get(args.round) or []) if args.round else [
            attempt.get("evidence_id")
            for attempt in filter_attempts(
                args.hg_session_id,
                round_attempt_ids(index, args.round),
                role="participation",
            )
        ]
        for evidence_id in ids:
            print(evidence_id)
        return 0

    if args.inference_id:
        for entry in chain_for_inference(args.hg_session_id, index, args.inference_id):
            if args.summary:
                candidate = load_attempt(args.hg_session_id, entry.get("candidate_evidence_id"))
                print(summarize_attempt(candidate) if candidate else json.dumps(entry))
            else:
                print(json.dumps(entry, ensure_ascii=False))
        return 0

    if args.chain:
        print_chain(
            args.hg_session_id,
            index,
            chain_kind=args.chain,
            round_id=args.round,
            inference_id=args.inference_id,
        )
        return 0

    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
        return 0

    print(f"repo: {REPO_ROOT}")
    print(f"session: {args.hg_session_id}")
    print(f"root: {root}")
    print(f"attempt_count: {len(index.get('attempt_ids') or [])}")
    attempt_ids = round_attempt_ids(index, args.round)
    if args.round:
        print(f"round: {args.round}")
    attempts = filter_attempts(
        args.hg_session_id,
        attempt_ids,
        role=args.role,
        qa_target_role=args.qa_target_role,
    )
    for attempt in attempts:
        if args.summary:
            print(summarize_attempt(attempt))
            print("")
            continue
        correlation = attempt.get("correlation") or {}
        decision = attempt.get("decision") or {}
        semantic_qa = decision.get("semantic_qa") or {}
        print(
            "- "
            f"{attempt.get('evidence_id')} "
            f"role={correlation.get('role')} "
            f"attempt={correlation.get('attempt_index')} "
            f"inference={correlation.get('inference_id')} "
            f"outcome={decision.get('outcome')} "
            f"policy={semantic_qa.get('policy_action')} "
            f"eval={semantic_qa.get('evaluator_evidence_id')} "
            f"terminal={decision.get('terminal_disposition')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
