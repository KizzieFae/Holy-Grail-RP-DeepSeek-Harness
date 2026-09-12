#!/usr/bin/env python3
"""Issue #175 formal validation: baseline vs optimized Plot update transport."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_V2 = _REPO / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_scene_pressure_projection import compute_issue_material_fingerprint  # noqa: E402
from continuity_state import IssueState, IssueStatus, PublicEvent  # noqa: E402
from datetime import datetime as dt, timezone as tz  # noqa: E402

from domain_api.plot_cognition_forensics_capture import bounded_prior_operative_cognition  # noqa: E402
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    plot_goal_from_dict,
    unresolved_narrative_pressure_from_dict,
)
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    AssimilatedAuthority,
    AssimilatedSessionAuthority,
    empty_store,
)
from domain_api.plot_cognition_update_sources import (  # noqa: E402
    build_assimilated_authority_from_snapshot,
    gather_update_source_snapshot,
)
from domain_api.session_state import CharacterTurnRecord, LiveSession, RoundFixture, initialize_live_session  # noqa: E402

from _repo_paths import INVESTIGATION_RUNS_DIR, REPO_ROOT  # noqa: E402


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def _baseline_manifest_payload(snapshot: Any) -> dict[str, Any]:
    """Pre-#175 model-facing payload reconstructed from snapshot fields."""
    body = snapshot.canonical_body
    excerpts = snapshot.semantic_authority_excerpts
    prior = snapshot.prior_operative_cognition
    return {
        "authority_projection": body,
        "semantic_authority_excerpts": excerpts,
        "prior_operative_cognition": prior,
    }


def _optimized_manifest_payload(snapshot: Any) -> dict[str, Any]:
    return {
        "model_facing_transport": snapshot.model_facing_transport,
        "prior_operative_cognition": snapshot.prior_operative_cognition,
    }


def _collect_verbatim_texts(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_digest"):
                continue
            if isinstance(item, str) and item.strip():
                if key in {
                    "summary",
                    "description",
                    "blocked_what",
                    "required_next_step",
                    "statement",
                    "bounded_excerpt",
                    "opening_description",
                    "intended_direction",
                    "pressure_text",
                    "ensemble_context",
                }:
                    out.append(item.strip())
            _collect_verbatim_texts(item, out)
    elif isinstance(value, list):
        for item in value:
            _collect_verbatim_texts(item, out)


def _semantic_text_set(payload: dict[str, Any]) -> set[str]:
    texts: list[str] = []
    _collect_verbatim_texts(payload, texts)
    return {text for text in texts if len(text) >= 8}


def _transport_diff(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    base_texts = _semantic_text_set(baseline)
    opt_texts = _semantic_text_set(optimized)
    removed = sorted(base_texts - opt_texts)
    added = sorted(opt_texts - base_texts)
    return {
        "baseline_semantic_text_count": len(base_texts),
        "optimized_semantic_text_count": len(opt_texts),
        "removed_verbatim_fragments": removed,
        "added_verbatim_fragments": added[:50],
        "digest_only_removed": "summary_digest" in json.dumps(baseline) and "summary_digest" not in json.dumps(optimized),
        "authority_projection_removed": "authority_projection" not in optimized,
    }


def _estimate_tokens(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False)) // 4


def _goal_draft(goal_id: str, direction: str) -> dict[str, Any]:
    from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
        CognitionApplicability,
        CreationProvenance,
        GoalLineage,
        PLOT_GOAL_SCHEMA,
        PlotGoal,
        plot_goal_to_dict,
    )

    return plot_goal_to_dict(
        PlotGoal(
            schema=PLOT_GOAL_SCHEMA,
            goal_id=goal_id,
            intended_direction=direction,
            basis_note="Established in prior assimilation.",
            basis_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="global",
                primary_character_id=None,
                involved_character_ids=(),
            ),
            planning_horizon="MEDIUM",
            creation_provenance=CreationProvenance(source="storyteller"),
            lineage=GoalLineage(),
            activity_state="active",
        )
    )


def _pressure_draft(pressure_id: str, text: str) -> dict[str, Any]:
    from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
        CognitionApplicability,
        CreationProvenance,
        UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
        UnresolvedNarrativePressure,
        unresolved_narrative_pressure_to_dict,
    )

    return unresolved_narrative_pressure_to_dict(
        UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id=pressure_id,
            pressure_text=text,
            dramatic_rationale="Sustained household tension.",
            basis_note=None,
            basis_refs=(),
            continuity_issue_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="global",
                primary_character_id=None,
                involved_character_ids=(),
            ),
            creation_provenance=CreationProvenance(source="storyteller"),
            activity_state="active",
        )
    )


def _commit_round(
    fixture: LiveSession,
    *,
    commit_id: str,
    turn_index: int,
    move_text: str,
    event: PublicEvent | None = None,
) -> None:
    fixture.commit_ids.append(commit_id)
    fixture.rounds.append(
        RoundFixture(
            hg_round_id=f"round-{turn_index}",
            hg_scene_id=fixture.hg_scene_id,
            turn_index=turn_index,
            domain_commit_id=commit_id,
            committed_character_id="Host",
            committed_move={"beats": [{"type": "action", "action": move_text}]},
            continuity_turn_index=turn_index,
            character_turns=[
                CharacterTurnRecord(
                    character_id="Host",
                    committed_move={"beats": [{"type": "action", "action": move_text}]},
                    domain_commit_id=commit_id,
                    continuity_turn_index=turn_index,
                    director_decision={},
                )
            ],
        )
    )
    if event is not None:
        fixture.manager.public_events.append(event)


def _evolving_fixture() -> tuple[LiveSession, Any]:
    fixture = initialize_live_session(
        cast=["Host", "Applicant"],
        plot_cognition_scope_id="scope-issue175-evolving",
    )
    fixture.setup_snapshot = {
        "opening": {"mode": "minimal"},
        "scene_template_id": "ayame_household_entry_evaluation",
        "scene_template": {
            "template_id": "ayame_household_entry_evaluation",
            "premise": "Household entry evaluation in progress.",
        },
        "location": "evaluation_room",
    }
    fixture.manager.scene_state.location = "evaluation_room"
    issue_a = IssueState(
        issue_id="issue-vulnerability",
        description="Applicant's housing instability remains the leverage point.",
        blocked_what="stable housing",
        required_next_step="demonstrate dependence",
        participants=["Applicant"],
        status=IssueStatus.ACTIVE,
        pressure_kind="social",
        created_at=dt.now(tz.utc),
    )
    issue_b = IssueState(
        issue_id="issue-boundaries",
        description="Household boundaries are being tested during the interview.",
        blocked_what="clear expectations",
        required_next_step="establish control",
        participants=["Host", "Applicant"],
        status=IssueStatus.ACTIVE,
        pressure_kind="obstacle",
        created_at=dt.now(tz.utc),
    )
    fixture.manager.issues["issue-vulnerability"] = issue_a
    fixture.manager.issues["issue-boundaries"] = issue_b
    fixture.manager.scene_state.active_issue_ids = ["issue-vulnerability", "issue-boundaries"]

    store = empty_store(fixture.plot_cognition_scope_id)
    store.store_revision = 1
    store.goals["goal-stability"] = plot_goal_from_dict(
        _goal_draft("goal-stability", "Maintain applicant dependence while appearing helpful.")
    )
    store.pressures["pressure-evaluation"] = unresolved_narrative_pressure_from_dict(
        _pressure_draft("pressure-evaluation", "The interview must not expose the engineered vulnerability.")
    )

    _commit_round(
        fixture,
        commit_id="commit-1",
        turn_index=1,
        move_text="Host welcomes the applicant into the evaluation room.",
        event=PublicEvent(
            event_id="evt-arrival",
            timestamp=dt.now(tz.utc),
            event_type="action",
            participants=["Host", "Applicant"],
            summary="The applicant enters the household evaluation room under formal scrutiny.",
            turn_index=1,
            related_issue_ids=["issue-vulnerability"],
        ),
    )
    snapshot1 = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
    store.assimilated_authority = build_assimilated_authority_from_snapshot(snapshot1)
    store.assimilated_through_domain_commit_id = "commit-1"

    _commit_round(
        fixture,
        commit_id="commit-2",
        turn_index=2,
        move_text="Host questions the applicant about prior employment loss.",
        event=PublicEvent(
            event_id="evt-employment",
            timestamp=dt.now(tz.utc),
            event_type="dialogue",
            participants=["Host", "Applicant"],
            summary="The host presses the applicant on the recent job loss and housing crisis.",
            turn_index=2,
            related_issue_ids=["issue-vulnerability", "issue-boundaries"],
        ),
    )
    store.store_revision = 2
    return fixture, store


def _mature_fixture() -> tuple[LiveSession, Any]:
    fixture, store = _evolving_fixture()
    issue_c = IssueState(
        issue_id="issue-loyalty",
        description="A prior household servant's loyalty is being tested against the new applicant.",
        blocked_what="household cohesion",
        required_next_step="observe divided loyalties",
        participants=["Guard", "Applicant"],
        status=IssueStatus.ACTIVE,
        pressure_kind="social",
        created_at=dt.now(tz.utc),
    )
    fixture.manager.issues["issue-loyalty"] = issue_c
    fixture.manager.scene_state.active_issue_ids = [
        "issue-vulnerability",
        "issue-boundaries",
        "issue-loyalty",
    ]
    for idx, (commit_id, summary) in enumerate(
        [
            ("commit-3", "A guard silently observes the applicant's reactions during questioning."),
            ("commit-4", "The host references prior servants who accepted household boundaries."),
            ("commit-5", "The applicant reveals desperation that predates the advertised opportunity."),
        ],
        start=3,
    ):
        _commit_round(
            fixture,
            commit_id=commit_id,
            turn_index=idx,
            move_text=f"Turn {idx} household pressure escalates.",
            event=PublicEvent(
                event_id=f"evt-{idx}",
                timestamp=dt.now(tz.utc),
                event_type="dialogue",
                participants=["Host", "Applicant", "Guard"],
                summary=summary,
                turn_index=idx,
                related_issue_ids=["issue-loyalty" if idx >= 4 else "issue-boundaries"],
            ),
        )
    snapshot_mid = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
    store.assimilated_authority = build_assimilated_authority_from_snapshot(snapshot_mid)
    store.assimilated_through_domain_commit_id = "commit-3"
    store.store_revision = 3
    return fixture, store


def _checkpoint_record(
    *,
    scenario_id: str,
    checkpoint: str,
    fixture: LiveSession,
    store: Any,
) -> dict[str, Any]:
    snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
    baseline = _baseline_manifest_payload(snapshot)
    optimized = _optimized_manifest_payload(snapshot)
    diff = _transport_diff(baseline, optimized)
    transport = snapshot.model_facing_transport
    stable = transport.get("stable_semantic_frame") or {}
    incremental = transport.get("incremental_change_evidence") or {}
    active_issue_ids = {item.get("issue_id") for item in (stable.get("active_issues") or [])}
    rubric = {
        "active_issues_in_stable_frame": active_issue_ids == {
            issue_id
            for issue_id in (fixture.manager.scene_state.active_issue_ids or [])
        },
        "incremental_has_new_events": len(incremental.get("public_events") or []) > 0
        or store.assimilated_through_domain_commit_id is None,
        "no_digest_in_optimized": "summary_digest" not in json.dumps(optimized),
        "prior_operative_present": bool(snapshot.prior_operative_cognition.get("goals")),
        "semantic_text_removed": len(diff["removed_verbatim_fragments"]) == 0,
        "contextual_anchors_present": len(stable.get("contextual_anchor_events") or []) > 0
        or len(incremental.get("public_events") or []) > 0,
        "fail_safe_state": transport.get("fail_safe_expanded"),
    }
    return {
        "scenario_id": scenario_id,
        "checkpoint": checkpoint,
        "through_domain_commit_id": snapshot.through_domain_commit_id,
        "assimilated_through_domain_commit_id": store.assimilated_through_domain_commit_id,
        "authority_source_fingerprint": snapshot.authority_source_fingerprint,
        "store_revision": store.store_revision,
        "baseline_input": baseline,
        "optimized_input": optimized,
        "transport_diff": diff,
        "rubric": rubric,
        "baseline_estimated_input_tokens": _estimate_tokens(baseline),
        "optimized_estimated_input_tokens": _estimate_tokens(optimized),
    }


def _fail_safe_record() -> dict[str, Any]:
    fixture = initialize_live_session(cast=["Alice"], plot_cognition_scope_id="scope-fail-safe")
    fixture.manager.scene_state.location = "Hall"
    store = empty_store(fixture.plot_cognition_scope_id)
    store.assimilated_authority = AssimilatedAuthority(
        schema="hg_plot_cognition_assimilated_authority_v1",
        sessions=(
            AssimilatedSessionAuthority(
                hg_scene_id=fixture.hg_scene_id,
                through_domain_commit_id="commit-old",
                through_continuity_version=1,
                authority_source_fingerprint="stale-fingerprint-not-matching",
            ),
        ),
    )
    store.assimilated_through_domain_commit_id = "commit-old"
    snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
    transport = snapshot.model_facing_transport
    return {
        "fail_safe_expanded": transport.get("fail_safe_expanded"),
        "has_supplemental_verbatim": "supplemental_verbatim_authority"
        in (transport.get("stable_semantic_frame") or {}),
        "fingerprint_changed": snapshot.authority_source_fingerprint != "stale-fingerprint-not-matching",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue #175 Plot transport formal validation")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=INVESTIGATION_RUNS_DIR
        / f"issue175-quality-validation-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
    )
    args = parser.parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    evolving_fixture, evolving_store = _evolving_fixture()
    mature_fixture, mature_store = _mature_fixture()

    checkpoints = [
        _checkpoint_record(
            scenario_id="evolving_ayame_like",
            checkpoint="post_commit_2",
            fixture=evolving_fixture,
            store=evolving_store,
        ),
        _checkpoint_record(
            scenario_id="mature_household_context",
            checkpoint="post_commit_5",
            fixture=mature_fixture,
            store=mature_store,
        ),
    ]
    fail_safe = _fail_safe_record()

    rubric_failures: list[str] = []
    for record in checkpoints:
        for key, value in record["rubric"].items():
            if key == "fail_safe_state" and value is False:
                continue
            if value is False:
                rubric_failures.append(f"{record['scenario_id']}:{record['checkpoint']}:{key}")

    if not fail_safe.get("fail_safe_expanded"):
        rubric_failures.append("fail_safe:not_expanded")

    total_base_tokens = sum(item["baseline_estimated_input_tokens"] for item in checkpoints)
    total_opt_tokens = sum(item["optimized_estimated_input_tokens"] for item in checkpoints)

    summary = {
        "schema_version": "issue175_plot_transport_validation.v1",
        "candidate_sha": _git_sha(),
        "base_sha": "ba5574988c81414a0e54341b6c9681e0ec904de9",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoints": checkpoints,
        "fail_safe": fail_safe,
        "rubric_failures": rubric_failures,
        "semantic_quality_verdict": "PASS" if not rubric_failures else "FAIL",
        "efficiency": {
            "baseline_estimated_input_tokens_total": total_base_tokens,
            "optimized_estimated_input_tokens_total": total_opt_tokens,
            "delta_tokens": total_opt_tokens - total_base_tokens,
            "method": "json_payload_length_div_4_approximation",
            "confidence": "medium_for_input_transport_only",
        },
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for record in checkpoints:
        name = f"{record['scenario_id']}_{record['checkpoint']}.json"
        (out_dir / name).write_text(json.dumps(record, indent=2), encoding="utf-8")

    print(json.dumps({"out_dir": str(out_dir), "semantic_quality_verdict": summary["semantic_quality_verdict"]}, indent=2))
    if rubric_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
