import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_logger import AuditLogger  # noqa: E402
from audit_progression_analysis import build_progression_analysis  # noqa: E402


def _issue(
    issue_id: str,
    *,
    status: str,
    participants: list[str] | None = None,
    blocked_what: str,
    pressure_kind: str = "plan_execution",
    last_turn_index: int,
) -> dict:
    return {
        "issue_id": issue_id,
        "description": blocked_what,
        "status": status,
        "status_reason": "",
        "participants": participants or ["Ayame", "Harley"],
        "pressure_kind": pressure_kind,
        "blocked_what": blocked_what,
        "required_next_step": "Take the next concrete step.",
        "last_change": blocked_what,
        "last_turn_index": last_turn_index,
    }


def _observed(
    *,
    turn_index: int,
    scene_debt: int,
    scene_tier: str,
    scene_class: str,
    issue_debt: dict[str, int],
    issue_classes: dict[str, str],
    dominant_issue_ids: list[str] | None = None,
) -> dict:
    return {
        "scene_progression_debt": scene_debt,
        "scene_instability_tier": scene_tier,
        "issue_progression_debt": issue_debt,
        "issue_instability_tiers": {
            issue_id: (
                "forcing"
                if debt >= 6
                else "escalating"
                if debt >= 4
                else "unstable"
                if debt >= 2
                else "stable"
            )
            for issue_id, debt in issue_debt.items()
        },
        "dominant_issue_ids": dominant_issue_ids or [],
        "last_turn": {
            "turn_index": turn_index,
            "scene_turn_class": scene_class,
            "issue_turn_classes": {
                issue_id: {"turn_class": turn_class}
                for issue_id, turn_class in issue_classes.items()
            },
            "issue_identity_notes": [],
        },
    }


def _turn(
    *,
    round_number: int,
    turn_number: int,
    character: str,
    issues_after: list[dict],
    progression_observed: dict,
    continuity_tags: list[str] | None = None,
    resolved_outcome_debug: dict | None = None,
    state_changes: list[str] | None = None,
    actionable_implications: list[str] | None = None,
    scene_core_after: dict | None = None,
) -> dict:
    return {
        "round": round_number,
        "turn": turn_number,
        "character": character,
        "issues_after": issues_after,
        "progression_pressure_observed": progression_observed,
        "continuity_tags": continuity_tags or [],
        "continuity_consequences": continuity_tags or [],
        "resolved_outcome_debug": resolved_outcome_debug or {},
        "state_changes": state_changes or [],
        "actionable_implications": actionable_implications or [],
        "scene_core_after": scene_core_after
        or {
            "scene_phase": "rising",
            "location": "Dorm",
            "present_characters": ["Ayame", "Harley"],
            "offstage_characters": [],
        },
    }


def test_progression_analysis_flags_invalid_scene_reset_for_peripheral_material() -> None:
    turns = [
        _turn(
            round_number=1,
            turn_number=1,
            character="Ayame",
            issues_after=[
                _issue(
                    "issue_core",
                    status="active",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=1,
                ),
                _issue(
                    "issue_peripheral",
                    status="active",
                    blocked_what="Who sleeps where tonight",
                    last_turn_index=1,
                ),
            ],
            progression_observed=_observed(
                turn_index=1,
                scene_debt=4,
                scene_tier="escalating",
                scene_class="non_progression",
                issue_debt={"issue_core": 4, "issue_peripheral": 0},
                issue_classes={
                    "issue_core": "non_progression",
                    "issue_peripheral": "non_progression",
                },
                dominant_issue_ids=["issue_core"],
            ),
        ),
        _turn(
            round_number=1,
            turn_number=2,
            character="Harley",
            issues_after=[
                _issue(
                    "issue_core",
                    status="active",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=1,
                ),
                _issue(
                    "issue_peripheral",
                    status="resolved",
                    blocked_what="Who sleeps where tonight",
                    last_turn_index=2,
                ),
            ],
            continuity_tags=["decision_made", "plan_committed"],
            resolved_outcome_debug={
                "sleeping_surface": {
                    "decision": "promoted",
                    "issue_id": "issue_peripheral",
                }
            },
            progression_observed=_observed(
                turn_index=2,
                scene_debt=0,
                scene_tier="stable",
                scene_class="material_progression",
                issue_debt={"issue_core": 4, "issue_peripheral": 0},
                issue_classes={
                    "issue_core": "non_progression",
                    "issue_peripheral": "material_progression",
                },
                dominant_issue_ids=["issue_core"],
            ),
        ),
    ]
    report = build_progression_analysis(turns)
    second = report["turns"][1]
    assert second["scene_classification"]["expected"] == "partial_progression"
    assert second["reset_validation"]["classification"] == "invalid_reset"
    assert "false_progression_credit" in second["notable_flags"]
    assert report["summary"]["reset_errors"] == 1
    assert report["summary"]["false_progression_events"] == 1


def test_progression_analysis_detects_issue_identity_fragmentation() -> None:
    turns = [
        _turn(
            round_number=1,
            turn_number=1,
            character="Ayame",
            issues_after=[
                _issue(
                    "issue_old",
                    status="stalled",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=1,
                )
            ],
            progression_observed=_observed(
                turn_index=1,
                scene_debt=3,
                scene_tier="unstable",
                scene_class="explicit_stagnation",
                issue_debt={"issue_old": 3},
                issue_classes={"issue_old": "explicit_stagnation"},
                dominant_issue_ids=["issue_old"],
            ),
        ),
        _turn(
            round_number=1,
            turn_number=2,
            character="Harley",
            issues_after=[
                _issue(
                    "issue_new",
                    status="active",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=2,
                )
            ],
            progression_observed=_observed(
                turn_index=2,
                scene_debt=4,
                scene_tier="escalating",
                scene_class="partial_progression",
                issue_debt={"issue_new": 0},
                issue_classes={"issue_new": "partial_progression"},
                dominant_issue_ids=["issue_new"],
            ),
        ),
    ]
    report = build_progression_analysis(turns)
    second = report["turns"][1]
    assert second["issue_identity_events"][0]["classification"] == "fragmentation"
    assert report["summary"]["fragmentation_events"] == 1


def test_progression_analysis_marks_plateau_correctly_pressured_when_debt_climbs() -> None:
    turns = [
        _turn(
            round_number=1,
            turn_number=1,
            character="Ayame",
            issues_after=[
                _issue(
                    "issue_core",
                    status="active",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=1,
                )
            ],
            progression_observed=_observed(
                turn_index=1,
                scene_debt=1,
                scene_tier="stable",
                scene_class="non_progression",
                issue_debt={"issue_core": 1},
                issue_classes={"issue_core": "non_progression"},
                dominant_issue_ids=["issue_core"],
            ),
        ),
        _turn(
            round_number=1,
            turn_number=2,
            character="Harley",
            issues_after=[
                _issue(
                    "issue_core",
                    status="active",
                    blocked_what="Get the bleeding under control",
                    pressure_kind="safety_risk",
                    last_turn_index=1,
                )
            ],
            progression_observed=_observed(
                turn_index=2,
                scene_debt=2,
                scene_tier="unstable",
                scene_class="non_progression",
                issue_debt={"issue_core": 2},
                issue_classes={"issue_core": "non_progression"},
                dominant_issue_ids=["issue_core"],
            ),
        ),
    ]
    report = build_progression_analysis(turns)
    assert report["turns"][1]["plateau_assessment"] == "plateau_correctly_pressured"
    assert (
        report["summary"]["plateau_behavior_assessment"]["plateau_correctly_pressured"]
        == 1
    )


def test_audit_summary_report_includes_progression_analysis_section(tmp_path: Path) -> None:
    logger = AuditLogger(str(tmp_path))
    logger.write_session_manifest(
        session_owner="Ayame",
        session_number=1,
        cast=["Ayame", "Harley"],
        opening_description="A dorm room standoff.",
        user_name="Alex",
    )
    logger.write_round_index(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        director_choice_reason="Deterministic test decision.",
    )
    logger.update_narrative_summary(
        session_owner="Ayame",
        session_number=1,
        round_number=1,
        turn_number=1,
        acting_character="Ayame",
        rendered_output="Ayame held her ground.",
        character_move={"action": "held her ground", "dialogue": "", "motivation": {}},
        director_decision={"reason": "Deterministic test decision."},
        issue_updates=[],
        presence_changes=[],
        continuity_tags=[],
        continuity_consequences=[],
        resolved_outcome_debug={},
        issues_after=[
            _issue(
                "issue_core",
                status="active",
                blocked_what="Get the bleeding under control",
                pressure_kind="safety_risk",
                last_turn_index=1,
            )
        ],
        scene_core_after={
            "scene_phase": "rising",
            "location": "Dorm",
            "present_characters": ["Ayame", "Harley"],
            "offstage_characters": [],
        },
        progression_pressure=_observed(
            turn_index=1,
            scene_debt=1,
            scene_tier="stable",
            scene_class="non_progression",
            issue_debt={"issue_core": 1},
            issue_classes={"issue_core": "non_progression"},
            dominant_issue_ids=["issue_core"],
        ),
    )

    report_path = logger.write_summary_report("Ayame", 1)
    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    assert "progression_analysis" in report
    assert report["progression_analysis"]["summary"]["total_turns_analyzed"] == 1
    assert report["progression_analysis"]["turns"][0]["scene_classification"]["expected"] == "non_progression"
