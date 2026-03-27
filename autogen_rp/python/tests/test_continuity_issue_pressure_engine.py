from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from continuity_state import IssueState, IssueStatus
from continuity_summary_helpers import build_summary_block


def test_pressure_engine_creates_plan_execution_issue_from_refusal() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Parlor",
        opening_description="A formal offer hangs in the air.",
        present_characters=["Ayame", "Celina"],
    )

    snapshot = manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "pushes the contract back across the table",
            "dialogue": "No.",
            "motivation": {
                "goal": "refuse the proposed arrangement and hold position",
                "tactic": "reject the offer cleanly",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "The room goes still.",
            "tension_shift": "steady",
            "reason": "Ayame rejects the proposal outright.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
    )

    assert len(snapshot.active_issues) == 1
    issue = snapshot.active_issues[0]

    assert issue.pressure_kind == "plan_execution"
    assert issue.blocked_what == "The current proposed course of action"
    assert issue.required_next_step == (
        "The cast must respond to the refusal or choose a different course."
    )
    assert issue.description.startswith("The current proposed course of action.")
    assert "plan execution" in issue.status_reason
    assert issue.description != "No."


def test_pressure_engine_resolves_information_gap_without_collapsing_broader_risk() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Safehouse",
        opening_description="They listen for pursuit beyond the boarded windows.",
        present_characters=["Celina", "Kizzie"],
    )
    info_issue = IssueState(
        issue_id="info_issue",
        description="Establish whether the checkpoint guards can trace Kizzie here",
        participants=["Celina", "Kizzie"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        resolution_signals=["answer", "clarify", "reveal"],
        pressure_kind="information_gap",
        blocked_what="Whether the checkpoint guards can trace Kizzie here",
        blocked_characters=["Celina", "Kizzie"],
        required_next_step="Someone must clarify whether pursuit is immediate.",
    )
    safety_issue = IssueState(
        issue_id="safety_issue",
        description="Decide how to protect the safehouse if pursuit reaches the block",
        participants=["Celina", "Kizzie"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        resolution_signals=["safe for now", "stable"],
        pressure_kind="safety_risk",
        blocked_what="Immediate safety if pursuit reaches the safehouse",
        blocked_characters=["Celina", "Kizzie"],
        required_next_step="The cast must prepare a fallback exit or defense.",
    )
    manager.issues[info_issue.issue_id] = info_issue
    manager.issues[safety_issue.issue_id] = safety_issue
    manager.scene_state.active_issue_ids.extend([info_issue.issue_id, safety_issue.issue_id])

    manager.process_turn(
        acting_character="Kizzie",
        move={
            "action": "keeps her voice low and steady",
            "dialogue": "Answer me this if you need it plain: no guard followed me here.",
            "motivation": {
                "goal": "clarify whether pursuit is immediate",
                "tactic": "answer the tactical uncertainty directly",
                "emotional_driver": "wary honesty",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "Rain masks the street noise outside.",
            "tension_shift": "steady",
            "reason": "Kizzie answers the immediate tracing question.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
    )

    assert manager.issues[info_issue.issue_id].status == IssueStatus.RESOLVED
    assert manager.issues[safety_issue.issue_id].status != IssueStatus.RESOLVED
    assert info_issue.issue_id not in manager.scene_state.active_issue_ids
    assert safety_issue.issue_id in manager.scene_state.active_issue_ids


def test_summary_blocks_preserve_pressure_metadata_for_access_conflict() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Gatehouse",
        opening_description="A guard bars the inner door.",
        present_characters=["Mira", "Courier"],
    )
    timestamp = datetime.fromisoformat("2026-03-15T12:00:00")

    manager.process_turn(
        acting_character="Mira",
        move={
            "action": "plants her spear across the threshold",
            "dialogue": "You do not enter until I say so.",
            "motivation": {
                "goal": "deny entry until authority is established",
                "tactic": "block access physically and verbally",
                "emotional_driver": "suspicion",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Courier",
            "environment_event": "The inner door remains shut.",
            "tension_shift": "escalate",
            "reason": "Mira blocks access and forces a response.",
        },
        other_characters=["Courier"],
        timestamp=timestamp,
    )

    summary_block = build_summary_block(
        manager=manager,
        events=manager.public_events,
        generated_at=timestamp + timedelta(minutes=1),
    )

    assert len(summary_block.issue_updates) == 1
    issue_update = summary_block.issue_updates[0]
    assert issue_update["pressure_kind"] == "access_conflict"
    assert issue_update["blocked_what"] == "Access to the relevant person, place, or action"
    assert issue_update["required_next_step"]
    assert "access conflict" in issue_update["status_reason"]
