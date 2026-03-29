import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state import CharacterState
from continuity_manager import ContinuityManager
from continuity_summary_helpers import build_summary_block
from continuity_state import IssueState, IssueStatus, PublicEvent
from scene_grounding import rebuild_scene_grounding_from_continuity


def _build_test_move(idx: int) -> dict:
    return {
        "action": f"takes step {idx}",
        "dialogue": f"Turn {idx} demands an answer.",
        "motivation": {
            "goal": f"press issue {idx}",
            "tactic": "apply pressure",
            "emotional_driver": "determination",
            "risk_level": "medium",
        },
    }


def _build_test_decision(next_actor: str) -> dict:
    return {
        "next_actor": next_actor,
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "Maintain scene pressure.",
    }


def test_process_turn_creates_public_event_and_issue() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="A tense confrontation in the forge.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    snapshot = manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "points at Celina",
            "dialogue": "Why did you sabotage the forge?",
            "motivation": {
                "goal": "expose Celina",
                "tactic": "direct accusation",
                "emotional_driver": "anger",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "The forge fire spits sparks.",
            "tension_shift": "escalate",
            "reason": "Celina was directly accused.",
        },
        other_characters=["Celina", "Mira"],
        timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
    )

    assert len(manager.public_events) == 1
    assert manager.public_events[0].significance == "major"
    assert manager.public_events[0].known_by == ["Ayame", "Celina", "Mira"]
    assert snapshot.scene_state.current_tension_level == "moderate"
    assert snapshot.scene_state.location == "Workshop"
    assert len(snapshot.active_issues) == 1
    assert snapshot.active_issues[0].status == IssueStatus.ESCALATING


def test_process_turn_creates_outcome_focused_decision_event() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Apartment",
        opening_description="Rain beats softly against the windows.",
        present_characters=["Ayame", "Celina"],
    )

    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "folds her arms",
            "dialogue": "I refuse your offer.",
            "motivation": {
                "goal": "refuse the offer and hold position",
                "tactic": "shut down the proposal cleanly",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Ayame rejects the proposed arrangement.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:00:30"),
    )

    event = manager.public_events[0]
    assert event.event_type == "decision"
    assert (
        event.summary
        == "Ayame refused the current demand, request, or proposed course of action."
    )
    assert event.state_changes == [
        "Ayame refused the current demand, request, or proposed course of action."
    ]
    assert event.actionable_implications == [
        "The cast must respond to the refusal or choose a different course."
    ]
    assert manager.scene_state.recent_delta == event.summary


def test_issue_resolution_removes_resolved_issue_from_active_list() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Common room",
        opening_description="A quiet argument over tea.",
        present_characters=["Ayame", "Celina"],
    )
    issue = IssueState(
        issue_id="issue_1",
        description="Trust between Ayame and Celina",
        participants=["Ayame", "Celina"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        escalation_signals=["accus"],
        resolution_signals=["apolog", "accept"],
    )
    manager.issues[issue.issue_id] = issue
    manager.scene_state.active_issue_ids.append(issue.issue_id)

    manager.process_turn(
        acting_character="Celina",
        move={
            "action": "lowers her gaze",
            "dialogue": "I am sorry. I should have told you the truth.",
            "motivation": {
                "goal": "apologize and repair trust",
                "tactic": "admit fault",
                "emotional_driver": "regret",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Ayame",
            "environment_event": "",
            "tension_shift": "soften",
            "reason": "Celina is trying to resolve the conflict.",
        },
        other_characters=["Ayame"],
        timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
    )

    assert manager.issues[issue.issue_id].status == IssueStatus.RESOLVED
    assert manager.scene_state.active_issue_ids == []


def test_issue_can_transition_to_stalled_when_not_reinforced() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="Tension lingers around the anvil.",
        present_characters=["Ayame", "Celina"],
    )
    issue = IssueState(
        issue_id="issue_1",
        description="Expose the saboteur",
        participants=["Ayame", "Celina"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        escalation_signals=["expose", "accus"],
        resolution_signals=["confess", "resolve"],
        last_updated=datetime.fromisoformat("2026-03-15T12:00:00"),
        last_turn_index=1,
    )
    manager.issues[issue.issue_id] = issue
    manager.scene_state.active_issue_ids.append(issue.issue_id)
    manager.turn_counter = 3

    manager.process_turn(
        acting_character="Celina",
        move={
            "action": "watches the forge fire",
            "dialogue": "",
            "motivation": {
                "goal": "wait in silence",
                "tactic": "hold still",
                "emotional_driver": "guarded calm",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Ayame",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "No one forces the issue yet.",
        },
        other_characters=["Ayame"],
        timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
    )

    assert manager.issues[issue.issue_id].status == IssueStatus.STALLED
    assert manager.issues[issue.issue_id].last_turn_index == 4
    assert "did not materially change this pressure" in manager.issues[issue.issue_id].status_reason
    assert manager.scene_state.active_issue_ids == []
    assert manager.get_active_issues() == []


def test_process_turn_updates_scene_presence_on_exit() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Hallway",
        opening_description="An argument spills toward the door.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    manager.process_turn(
        acting_character="Mira",
        move={
            "action": "turned and left the room without another word",
            "dialogue": "",
            "motivation": {
                "goal": "leave before the argument can continue",
                "tactic": "walk out and end participation physically",
                "emotional_driver": "anger",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Ayame",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Mira exits rather than continuing the exchange.",
        },
        other_characters=["Ayame", "Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
    )

    assert "Mira" not in manager.scene_state.present_characters
    assert "Mira" in manager.scene_state.absent_but_relevant
    assert manager.public_events[0].state_changes == ["Mira left the immediate scene."]
    assert manager.scene_state.recent_delta == "Mira left the immediate scene."


def test_process_turn_propagates_told_knowledge_to_addressed_character() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Harbor",
        opening_description="Rain beats against the warehouse roof.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    manager.public_events.append(
        PublicEvent(
            event_id="evt_secret_ledger",
            timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
            event_type="revelation",
            participants=["Ayame"],
            summary="Ayame found the hidden ledger in the harbor office.",
            location="Harbor",
            significance="major",
            known_by=["Ayame"],
            observed_by=["Ayame"],
        )
    )

    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "leans toward Mira",
            "dialogue": "Mira, the hidden ledger is in the harbor office.",
            "motivation": {
                "goal": "tell Mira about the ledger",
                "tactic": "share direct information",
                "emotional_driver": "urgency",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Mira",
            "environment_event": "Rain drums harder on the windows.",
            "tension_shift": "steady",
            "reason": "Ayame passes critical information to Mira.",
        },
        other_characters=["Celina", "Mira"],
        timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
    )

    secret_event = next(
        event
        for event in manager.public_events
        if event.event_id == "evt_secret_ledger"
    )
    assert secret_event.knowledge_level_for("Mira") == "told"
    assert secret_event.knowledge_level_for("Celina") is None


def test_get_character_context_filters_to_known_events() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Docks",
        opening_description="Rain falls over the harbor.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    manager.public_events = [
        PublicEvent(
            event_id="evt_secret",
            timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
            event_type="revelation",
            participants=["Ayame"],
            summary="Ayame discovered the hidden ledger.",
            location="Docks",
            significance="major",
            known_by=["Ayame"],
        ),
        PublicEvent(
            event_id="evt_public",
            timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
            event_type="dialogue",
            participants=["Celina"],
            summary="Celina confronted Mira in the open.",
            location="Docks",
            significance="major",
            known_by=["Ayame", "Celina", "Mira"],
        ),
    ]

    ayame_context = manager.get_character_context("Ayame")
    mira_context = manager.get_character_context("Mira")

    assert [event.event_id for event in ayame_context["recent_events"]] == [
        "evt_secret",
        "evt_public",
    ]
    assert [event.event_id for event in mira_context["recent_events"]] == ["evt_public"]


def test_continuity_manager_roundtrip_serialization() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="The forge glows red.",
        present_characters=["Ayame", "Celina"],
    )
    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "steps toward the anvil",
            "dialogue": "We settle this now.",
            "motivation": {
                "goal": "force a decision",
                "tactic": "escalate",
                "emotional_driver": "resolve",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "The anvil rings sharply.",
            "tension_shift": "escalate",
            "reason": "The confrontation is intensifying.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:03:00"),
    )

    restored = ContinuityManager.from_dict(manager.to_dict())

    assert restored.scene_state is not None
    assert restored.scene_state.location == "Workshop"
    assert restored.scene_state.opening_description == "The forge glows red."
    assert len(restored.public_events) == 1
    assert restored.public_events[0].summary == manager.public_events[0].summary
    assert (
        restored.public_events[0].state_changes
        == manager.public_events[0].state_changes
    )
    assert (
        restored.public_events[0].actionable_implications
        == manager.public_events[0].actionable_implications
    )
    assert restored.event_counter == manager.event_counter
    assert restored.interpretations.keys() == manager.interpretations.keys()


def test_issue_creation_deduplicates_similar_pressure() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="Heat lingers in the forge.",
        present_characters=["Ayame", "Celina"],
    )
    existing_issue = IssueState(
        issue_id="issue_existing",
        description="Expose Celina's sabotage",
        participants=["Ayame", "Celina"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        escalation_signals=["accus", "expose"],
        resolution_signals=["confess"],
    )
    manager.issues[existing_issue.issue_id] = existing_issue
    manager.scene_state.active_issue_ids.append(existing_issue.issue_id)

    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "steps closer",
            "dialogue": "Tell me why you sabotaged the forge.",
            "motivation": {
                "goal": "expose Celina sabotage",
                "tactic": "renew accusation",
                "emotional_driver": "anger",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "escalate",
            "reason": "The confrontation sharpens.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:05:00"),
    )

    assert len(manager.issues) == 1
    assert manager.issues[existing_issue.issue_id].status == IssueStatus.ESCALATING


def test_issue_creation_respects_max_active_issue_limit() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Council chamber",
        opening_description="Three arguments already strain the room.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    for idx in range(3):
        issue = IssueState(
            issue_id=f"issue_{idx}",
            description=f"Active pressure {idx}",
            participants=["Ayame", "Celina", "Mira"],
            status=IssueStatus.ACTIVE,
            created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        )
        manager.issues[issue.issue_id] = issue
        manager.scene_state.active_issue_ids.append(issue.issue_id)

    manager.process_turn(
        acting_character="Mira",
        move={
            "action": "slams a ledger onto the table",
            "dialogue": "Which lie are we dealing with first?",
            "motivation": {
                "goal": "force a fourth confrontation",
                "tactic": "demand clarity",
                "emotional_driver": "frustration",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Ayame",
            "environment_event": "",
            "tension_shift": "escalate",
            "reason": "Mira pushes the room harder.",
        },
        other_characters=["Ayame", "Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:06:00"),
    )

    assert len(manager.issues) == 3
    assert len(manager.scene_state.active_issue_ids) == 3


def test_get_character_context_supports_observed_told_and_inferred_events() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Docks",
        opening_description="Rain falls over the harbor.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    manager.public_events = [
        PublicEvent(
            event_id="evt_observed",
            timestamp=datetime.fromisoformat("2026-03-15T12:00:00"),
            event_type="action",
            participants=["Ayame"],
            summary="Ayame found the ledger herself.",
            location="Docks",
            significance="major",
            observed_by=["Ayame"],
            known_by=["Ayame"],
        ),
        PublicEvent(
            event_id="evt_told",
            timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
            event_type="dialogue",
            participants=["Celina"],
            summary="Celina privately told Mira about the ledger.",
            location="Docks",
            significance="major",
            told_to=["Mira"],
            known_by=["Celina", "Mira"],
        ),
        PublicEvent(
            event_id="evt_inferred",
            timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
            event_type="revelation",
            participants=["Mira"],
            summary="Mira inferred Ayame had seen the hidden record.",
            location="Docks",
            significance="major",
            inferred_by=["Celina"],
            known_by=["Mira", "Celina"],
        ),
    ]

    ayame_context = manager.get_character_context("Ayame")
    mira_context = manager.get_character_context("Mira")
    celina_context = manager.get_character_context("Celina")

    assert [event.event_id for event in ayame_context["recent_events"]] == [
        "evt_observed"
    ]
    assert [event.event_id for event in mira_context["recent_events"]] == [
        "evt_told",
        "evt_inferred",
    ]
    assert [event.event_id for event in celina_context["recent_events"]] == [
        "evt_told",
        "evt_inferred",
    ]
    assert manager.public_events[1].knowledge_level_for("Mira") == "told"
    assert manager.public_events[2].knowledge_level_for("Celina") == "inferred"


def test_seed_character_canon_anchors_creates_relevant_character_anchors() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Workshop",
        opening_description="A quiet forge before the argument.",
        present_characters=["Ayame", "Celina"],
    )
    manager.seed_character_canon_anchors(
        {
            "Ayame": CharacterState(
                name="Ayame",
                core_goals=["protect the forge", "uncover betrayal"],
                voice_profile={"cadence": "measured", "tone": "cool"},
                reaction_profile={"under_pressure": "narrows focus"},
                speech_fingerprint={"signature": "spare, cutting phrasing"},
            )
        }
    )

    relevant = manager.get_relevant_canon_anchors("Ayame")
    anchor_ids = [anchor.anchor_id for anchor in relevant]
    anchor_statements = [anchor.statement for anchor in relevant]

    assert "canon_ayame_goals" in anchor_ids
    assert "canon_ayame_voice" in anchor_ids
    assert "canon_ayame_reaction" in anchor_ids
    assert any("protect the forge" in statement for statement in anchor_statements)


def test_summary_blocks_generate_at_strict_interval_and_compress_older_events() -> None:
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Archive",
        opening_description="Dust hangs over the records room.",
        present_characters=["Ayame", "Celina"],
    )

    for idx in range(1, 5):
        manager.process_turn(
            acting_character="Ayame" if idx % 2 else "Celina",
            move=_build_test_move(idx),
            director_decision=_build_test_decision("Celina" if idx % 2 else "Ayame"),
            other_characters=["Celina"] if idx % 2 else ["Ayame"],
            timestamp=datetime.fromisoformat(f"2026-03-15T12:0{idx}:00"),
        )

    assert manager.turn_counter == 4
    assert len(manager.public_events) == 4
    assert len(manager.summary_blocks) == 1
    assert manager.last_summarized_event_index == 2

    summary_block = manager.summary_blocks[0]
    assert summary_block.turn_range_start == 1
    assert summary_block.turn_range_end == 2
    assert len(summary_block.source_event_ids) == 2
    assert len(summary_block.key_events) == 2
    assert summary_block.impact_score >= 2
    snapshot = manager.get_snapshot()
    assert summary_block.participant_names == ["Ayame", "Celina"]

    snapshot = manager.get_snapshot()
    assert [event.turn_index for event in snapshot.recent_public_events] == [3, 4]


def test_direct_route_risk_issue_can_resolve_while_broader_outside_threat_remains_active() -> (
    None
):
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Apartment",
        opening_description="Rain hammers the windows.",
        present_characters=["Celina", "Kizzie"],
    )
    route_issue = IssueState(
        issue_id="route_issue",
        description="Establish whether Kizzie led immediate danger directly to this refuge",
        participants=["Celina", "Kizzie"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        escalation_signals=["followed", "lead", "building"],
        resolution_signals=["didn't lead anyone here", "wouldn't know this building"],
    )
    outside_threat_issue = IssueState(
        issue_id="outside_issue",
        description="Determine whether outside danger can reach Kizzie here and decide the next protective step",
        participants=["Celina", "Kizzie"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        escalation_signals=["hunter", "danger", "tracked"],
        resolution_signals=["plan", "move tomorrow", "safe for now"],
    )
    manager.issues[route_issue.issue_id] = route_issue
    manager.issues[outside_threat_issue.issue_id] = outside_threat_issue
    manager.scene_state.active_issue_ids.extend(
        [route_issue.issue_id, outside_threat_issue.issue_id]
    )

    manager.process_turn(
        acting_character="Kizzie",
        move={
            "action": "keeps still under the blankets",
            "dialogue": "I didn't lead anyone here. They wouldn't know this building.",
            "motivation": {
                "goal": "reassure Celina that the refuge was not directly compromised",
                "tactic": "answer the tactical question clearly and briefly",
                "emotional_driver": "wary honesty",
                "risk_level": "medium",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Kizzie answers the immediate route question.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
    )

    assert manager.issues[route_issue.issue_id].status == IssueStatus.RESOLVED
    assert manager.issues[outside_threat_issue.issue_id].status != IssueStatus.RESOLVED
    assert route_issue.issue_id not in manager.scene_state.active_issue_ids
    assert outside_threat_issue.issue_id in manager.scene_state.active_issue_ids


def test_build_summary_block_preserves_answered_tactical_threat_facts() -> None:
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Apartment",
        opening_description="Rain hammers the windows.",
        present_characters=["Celina", "Kizzie"],
    )
    events = [
        PublicEvent(
            event_id="evt_1",
            timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
            event_type="dialogue",
            participants=["Kizzie"],
            summary="Kizzie said: \"I didn't lead anyone here. They wouldn't know this building.\"",
            turn_index=1,
        ),
        PublicEvent(
            event_id="evt_2",
            timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
            event_type="dialogue",
            participants=["Kizzie"],
            summary='Kizzie said: "I doubled back through the sewers and lost them in the storm."',
            turn_index=2,
        ),
    ]

    summary_block = build_summary_block(
        manager=manager,
        events=events,
        generated_at=datetime.fromisoformat("2026-03-15T12:03:00"),
    )

    assert (
        "Kizzie denied leading the outside threat directly to the refuge."
        in summary_block.continuity_facts
    )
    assert (
        "Kizzie described evasive movement intended to break pursuit before reaching the refuge."
        in summary_block.continuity_facts
    )


def test_build_summary_block_preserves_extracted_state_changes() -> None:
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Archive",
        opening_description="Dust hangs over the stacks.",
        present_characters=["Ayame", "Celina"],
    )
    events = [
        PublicEvent(
            event_id="evt_1",
            timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
            event_type="decision",
            participants=["Ayame"],
            summary="Ayame denied access or blocked the requested action.",
            turn_index=1,
            state_changes=["Ayame denied access or blocked the requested action."],
            actionable_implications=[
                "Anyone blocked must find leverage, permission, or an alternate route."
            ],
        )
    ]

    summary_block = build_summary_block(
        manager=manager,
        events=events,
        generated_at=datetime.fromisoformat("2026-03-15T12:03:00"),
    )

    assert (
        "Ayame denied access or blocked the requested action."
        in summary_block.continuity_facts
    )


def test_retrieve_public_events_supports_deterministic_filters() -> None:
    manager = ContinuityManager(summary_interval=12, recent_event_window=8)
    manager.initialize_scene(
        location="Workshop",
        opening_description="Steel rings in the forge.",
        present_characters=["Ayame", "Celina", "Mira"],
    )
    issue = IssueState(
        issue_id="issue_1",
        description="Protect the forge",
        participants=["Ayame", "Celina"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
    )
    manager.issues[issue.issue_id] = issue
    manager.scene_state.active_issue_ids.append(issue.issue_id)
    manager.public_events = [
        PublicEvent(
            event_id="evt_1",
            timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
            event_type="dialogue",
            participants=["Ayame"],
            summary="Ayame warned Celina to defend the forge.",
            turn_index=1,
            location="Workshop",
            significance="major",
            known_by=["Ayame", "Celina"],
            related_issue_ids=["issue_1"],
        ),
        PublicEvent(
            event_id="evt_2",
            timestamp=datetime.fromisoformat("2026-03-15T12:02:00"),
            event_type="action",
            participants=["Mira"],
            summary="Mira slipped out to the docks.",
            turn_index=2,
            location="Docks",
            significance="minor",
            known_by=["Mira"],
        ),
    ]

    by_participant = manager.retrieve_public_events(participants=["Ayame"])
    by_issue = manager.retrieve_public_events(issue_ids=["issue_1"])
    by_location = manager.retrieve_public_events(location="Workshop")
    by_significance = manager.retrieve_public_events(significance=["major"])
    by_knowledge = manager.retrieve_public_events(known_by="Celina")

    assert [event.event_id for event in by_participant] == ["evt_1"]
    assert [event.event_id for event in by_issue] == ["evt_1"]
    assert [event.event_id for event in by_location] == ["evt_1"]
    assert [event.event_id for event in by_significance] == ["evt_1"]
    assert [event.event_id for event in by_knowledge] == ["evt_1"]


def test_retrieve_summary_blocks_supports_issue_location_and_turn_filters() -> None:
    manager = ContinuityManager(summary_interval=12, recent_event_window=8)
    manager.initialize_scene(
        location="Workshop",
        opening_description="The forge smolders.",
        present_characters=["Ayame", "Celina"],
    )
    manager.summary_blocks = [
        manager._build_summary_block(
            [
                PublicEvent(
                    event_id="evt_1",
                    timestamp=datetime.fromisoformat("2026-03-15T12:01:00"),
                    event_type="dialogue",
                    participants=["Ayame"],
                    summary="Ayame swore to protect the forge.",
                    turn_index=1,
                    location="Workshop",
                    significance="major",
                    related_issue_ids=["issue_1"],
                )
            ],
            datetime.fromisoformat("2026-03-15T12:05:00"),
        )
    ]
    manager.summary_blocks[0].issue_updates = [
        {
            "issue_id": "issue_1",
            "description": "Protect the forge",
            "status": "active",
            "update_type": "introduced",
        }
    ]

    by_issue = manager.retrieve_summary_blocks(issue_ids=["issue_1"])
    by_location = manager.retrieve_summary_blocks(location="Workshop")
    by_turn = manager.retrieve_summary_blocks(min_turn_index=1)

    assert len(by_issue) == 1
    assert len(by_location) == 1
    assert len(by_turn) == 1


def test_get_orchestration_context_uses_continuity_accessors() -> None:
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Archive",
        opening_description="Dust hangs over old records.",
        present_characters=["Ayame", "Celina"],
    )

    for idx in range(1, 5):
        manager.process_turn(
            acting_character="Ayame" if idx % 2 else "Celina",
            move=_build_test_move(idx),
            director_decision=_build_test_decision("Celina" if idx % 2 else "Ayame"),
            other_characters=["Celina"] if idx % 2 else ["Ayame"],
            timestamp=datetime.fromisoformat(f"2026-03-15T12:3{idx}:00"),
        )

    context = manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=2,
        summary_limit=1,
    )

    assert context["scene_state"] is manager.scene_state
    assert len(context["recent_public_events"]) == 2
    assert len(context["summary_blocks"]) == 1
    assert "resolved_events" in context
    assert "scene_canon_anchors" in context


def test_scene_template_fields_flow_through_snapshot_orchestration_and_character_context() -> (
    None
):
    manager = ContinuityManager(summary_interval=4, recent_event_window=2)
    manager.initialize_scene(
        location="Household foyer",
        opening_description="A guarded evaluation begins.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    assert manager.scene_state is not None
    manager.scene_state.scene_template_id = "household_entry_evaluation"
    manager.scene_state.scene_premise = (
        "A host evaluates a newcomer while a guard remains present."
    )
    manager.scene_state.role_assignments = {
        "Ayame": "host",
        "Celina": "applicant",
        "Mira": "guard",
    }
    manager.scene_state.character_presence_constraints = {
        "Ayame": "must_remain",
        "Celina": "must_remain",
        "Mira": "must_remain",
    }
    manager.scene_state.character_authority_labels = {
        "Ayame": "high",
        "Celina": "low",
        "Mira": "medium",
    }

    for idx in range(1, 5):
        actor = "Ayame" if idx % 2 else "Celina"
        others = ["Celina", "Mira"] if actor == "Ayame" else ["Ayame", "Mira"]
        manager.process_turn(
            acting_character=actor,
            move=_build_test_move(idx),
            director_decision=_build_test_decision("Mira"),
            other_characters=others,
            timestamp=datetime.fromisoformat(f"2026-03-15T12:4{idx}:00"),
        )

    snapshot = manager.get_snapshot()
    orchestration = manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=2,
        summary_limit=1,
    )
    mira_context = manager.get_character_context("Mira")

    for state in [
        snapshot.scene_state,
        orchestration["scene_state"],
        mira_context["scene_state"],
    ]:
        assert state.scene_template_id == "household_entry_evaluation"
        assert (
            state.scene_premise
            == "A host evaluates a newcomer while a guard remains present."
        )
        assert state.role_assignments["Ayame"] == "host"
        assert state.character_presence_constraints["Mira"] == "must_remain"
        assert state.character_authority_labels["Ayame"] == "high"

    assert len(snapshot.summary_blocks) == 1
    assert len(orchestration["summary_blocks"]) == 1
    assert len(mira_context["summary_blocks"]) == 1
    assert [event.turn_index for event in mira_context["recent_events"]] == [3, 4]


def test_twenty_four_turn_continuity_stability_preserves_template_and_prompt_context() -> (
    None
):
    manager = ContinuityManager(summary_interval=6, recent_event_window=3)
    manager.initialize_scene(
        location="Archive annex",
        opening_description="A long, tense evaluation stretches into the night.",
        present_characters=["Ayame", "Celina", "Mira"],
    )

    assert manager.scene_state is not None
    manager.scene_state.scene_template_id = "household_entry_evaluation"
    manager.scene_state.scene_premise = (
        "A host evaluates a newcomer while a guard remains present."
    )
    manager.scene_state.role_assignments = {
        "Ayame": "host",
        "Celina": "applicant",
        "Mira": "guard",
    }
    manager.scene_state.character_presence_constraints = {
        "Ayame": "must_remain",
        "Celina": "must_remain",
        "Mira": "must_remain",
    }
    manager.scene_state.character_authority_labels = {
        "Ayame": "high",
        "Celina": "low",
        "Mira": "medium",
    }
    manager.seed_character_canon_anchors(
        {
            "Ayame": CharacterState(
                name="Ayame",
                core_goals=["control the evaluation"],
                voice_profile={"cadence": "measured"},
                reaction_profile={"under_pressure": "tightens control"},
                speech_fingerprint={"signature": "precise commands"},
            ),
            "Celina": CharacterState(
                name="Celina",
                core_goals=["protect her autonomy"],
                voice_profile={"tone": "guarded"},
                reaction_profile={"under_pressure": "pushes back"},
                speech_fingerprint={"signature": "sharp retorts"},
            ),
        }
    )

    turn_order = ["Ayame", "Celina", "Mira"]
    for idx in range(1, 25):
        actor = turn_order[(idx - 1) % len(turn_order)]
        others = [name for name in turn_order if name != actor]
        manager.process_turn(
            acting_character=actor,
            move=_build_test_move(idx),
            director_decision=_build_test_decision(others[0]),
            other_characters=others,
            timestamp=datetime.fromisoformat(f"2026-03-16T00:{idx:02d}:00"),
        )

    snapshot = manager.get_snapshot()
    orchestration = manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=3,
        summary_limit=3,
    )
    restored = ContinuityManager.from_dict(manager.to_dict())
    restored_snapshot = restored.get_snapshot()
    restored_context = restored.get_character_context("Ayame")

    assert manager.turn_counter == 24
    assert snapshot.scene_state.scene_template_id == "household_entry_evaluation"
    assert snapshot.scene_state.role_assignments["Mira"] == "guard"
    assert snapshot.scene_state.character_presence_constraints["Mira"] == "must_remain"
    assert [event.turn_index for event in snapshot.recent_public_events] == [22, 23, 24]
    assert len(manager.summary_blocks) >= 3
    assert 1 <= len(orchestration["summary_blocks"]) <= 3

    assert restored.turn_counter == 24
    assert (
        restored_snapshot.scene_state.scene_template_id == "household_entry_evaluation"
    )
    assert restored_snapshot.scene_state.character_authority_labels["Ayame"] == "high"
    assert [event.turn_index for event in restored_snapshot.recent_public_events] == [
        22,
        23,
        24,
    ]
    assert restored_context["summary_blocks"]
    assert any(
        anchor.anchor_id == "canon_ayame_goals"
        for anchor in restored_context["canon_anchors"]
    )


def test_reconcile_presence_lists_clears_overlap_and_dedupes() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[
            "Marlene_Fletcher",
            "Marlene_Fletcher",
            "Harley_Quinn",
        ],
    )
    assert manager.scene_state is not None
    manager.scene_state.absent_but_relevant = [
        "Marlene_Fletcher",
        "Willow_Reeves",
        "Willow_Reeves",
    ]
    manager._reconcile_presence_lists()
    assert manager.scene_state.present_characters == [
        "Marlene_Fletcher",
        "Harley_Quinn",
    ]
    overlap = set(manager.scene_state.present_characters) & set(
        manager.scene_state.absent_but_relevant
    )
    assert overlap == set()
    assert manager.scene_state.absent_but_relevant == ["Willow_Reeves"]


def test_soft_exit_does_not_remove_actor_required_by_multi_party_issue() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Marlene_Fletcher", "Harley_Quinn"],
    )
    issue = IssueState(
        issue_id="issue_multi",
        description="Standoff",
        participants=["Marlene_Fletcher", "Harley_Quinn"],
        status=IssueStatus.ESCALATING,
        created_at=datetime.fromisoformat("2026-03-27T12:00:00"),
    )
    manager.issues[issue.issue_id] = issue
    assert manager.scene_state is not None
    manager.scene_state.active_issue_ids.append(issue.issue_id)

    manager._update_scene_state(
        acting_character="Marlene_Fletcher",
        move={
            "action": "tilts her head",
            "dialogue": "Hmm.",
            "motivation": {
                "goal": "wait",
                "tactic": "observe",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={},
        event=None,
        turn_consequences={
            "tags": ["exit"],
            "state_changes": [],
            "actionable_implications": [],
        },
    )

    assert "Marlene_Fletcher" in manager.scene_state.present_characters
    assert "Marlene_Fletcher" not in manager.scene_state.absent_but_relevant


def test_hard_exit_still_removes_despite_multi_party_issue() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Marlene_Fletcher", "Harley_Quinn"],
    )
    issue = IssueState(
        issue_id="issue_multi",
        description="Standoff",
        participants=["Marlene_Fletcher", "Harley_Quinn"],
        status=IssueStatus.ESCALATING,
        created_at=datetime.fromisoformat("2026-03-27T12:00:00"),
    )
    manager.issues[issue.issue_id] = issue
    assert manager.scene_state is not None
    manager.scene_state.active_issue_ids.append(issue.issue_id)

    manager._update_scene_state(
        acting_character="Marlene_Fletcher",
        move={
            "action": "left the room without another word",
            "dialogue": "",
            "motivation": {
                "goal": "leave",
                "tactic": "walk out",
                "emotional_driver": "done",
                "risk_level": "medium",
            },
        },
        director_decision={},
        event=None,
        turn_consequences={
            "tags": ["exit"],
            "state_changes": [],
            "actionable_implications": [],
        },
    )

    assert "Marlene_Fletcher" not in manager.scene_state.present_characters
    assert "Marlene_Fletcher" in manager.scene_state.absent_but_relevant


def test_exit_tag_does_not_remove_must_remain_from_present_even_on_hard_departure() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Willow_Reeves", "Harley_Quinn"],
    )
    assert manager.scene_state is not None
    manager.scene_state.character_presence_constraints = {
        "Willow_Reeves": "must_remain",
        "Harley_Quinn": "must_remain",
    }
    manager._update_scene_state(
        acting_character="Willow_Reeves",
        move={
            "action": "stomped out into the hallway and slammed the door",
            "dialogue": "",
            "motivation": {
                "goal": "leave",
                "tactic": "exit",
                "emotional_driver": "rage",
                "risk_level": "high",
            },
        },
        director_decision={},
        event=None,
        turn_consequences={
            "tags": ["exit"],
            "state_changes": [],
            "actionable_implications": [],
        },
    )
    assert "Willow_Reeves" in manager.scene_state.present_characters
    assert "Willow_Reeves" not in manager.scene_state.absent_but_relevant


def test_soft_exit_removes_when_actor_not_protected() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Only_One"],
    )
    manager._update_scene_state(
        acting_character="Only_One",
        move={
            "action": "blinks",
            "dialogue": "",
            "motivation": {
                "goal": "idle",
                "tactic": "wait",
                "emotional_driver": "flat",
                "risk_level": "low",
            },
        },
        director_decision={},
        event=None,
        turn_consequences={
            "tags": ["exit"],
            "state_changes": [],
            "actionable_implications": [],
        },
    )
    assert manager.scene_state is not None
    assert "Only_One" not in manager.scene_state.present_characters


def test_process_turn_under_strict_presence_invariant_env(
    monkeypatch: object,
) -> None:
    monkeypatch.setenv("RP_CONTINUITY_STRICT_INVARIANTS", "1")
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Ayame", "Celina"],
    )
    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "points at Celina",
            "dialogue": "Explain.",
            "motivation": {
                "goal": "press for truth",
                "tactic": "confront",
                "emotional_driver": "tension",
                "risk_level": "high",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "escalate",
            "reason": "Pressure beat.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-27T12:00:00"),
    )
    assert manager.scene_state is not None
    overlap = set(manager.scene_state.present_characters) & set(
        manager.scene_state.absent_but_relevant
    )
    assert overlap == set()


def test_phone_broken_persists_public_event_and_grounding_fact() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Dorm",
        opening_description="Quiet hallway.",
        present_characters=["Willow", "Kizzie"],
    )
    manager.process_turn(
        acting_character="Willow",
        move={
            "action": "",
            "dialogue": "My phone is broken.",
            "motivation": {
                "goal": "explain",
                "tactic": "state a fact",
                "emotional_driver": "frustration",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Kizzie",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Willow volunteered context.",
        },
        other_characters=["Kizzie"],
        timestamp=datetime.fromisoformat("2026-03-28T10:00:00"),
    )
    assert len(manager.public_events) == 1
    ev = manager.public_events[0]
    assert ev.event_type == "state"
    assert any("object_state:phone" in m for m in ev.grounding_markers)
    grounding = rebuild_scene_grounding_from_continuity(manager)
    assert len(grounding["facts"]) >= 1
    phone_facts = [f for f in grounding["facts"] if f.get("key") == "phone"]
    assert phone_facts
    assert "broken" in phone_facts[0].get("value_summary", "").lower()


def test_marker_only_promotion_when_classifier_empty(monkeypatch: object) -> None:
    """Phase 0: markers must persist even if consequence classifier returns nothing."""
    manager = ContinuityManager()
    monkeypatch.setattr(manager._consequence_classifier, "classify_turn", lambda *a, **k: [])
    manager.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Willow", "Kizzie"],
    )
    manager.process_turn(
        acting_character="Willow",
        move={
            "action": "",
            "dialogue": "My cell phone shattered.",
            "motivation": {
                "goal": "vent",
                "tactic": "complain",
                "emotional_driver": "annoyance",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Kizzie",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Beat.",
        },
        other_characters=["Kizzie"],
        timestamp=datetime.fromisoformat("2026-03-28T10:05:00"),
    )
    assert len(manager.public_events) == 1
    ev = manager.public_events[0]
    assert ev.event_type == "state"
    assert "Phone:" in ev.summary or "phone" in ev.summary.lower()
    grounding = rebuild_scene_grounding_from_continuity(manager)
    assert any(f.get("key") == "phone" for f in grounding["facts"])


def test_bandage_applied_persists_grounding_fact() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Infirmary",
        opening_description="First aid.",
        present_characters=["Ayame", "Celina"],
    )
    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "presses gauze gently",
            "dialogue": "Hold still—the bandage is applied.",
            "motivation": {
                "goal": "stabilize",
                "tactic": "first aid",
                "emotional_driver": "focus",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Care beat.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-28T10:10:00"),
    )
    ev = manager.public_events[-1]
    assert any("wound_dressing" in m for m in ev.grounding_markers)
    grounding = rebuild_scene_grounding_from_continuity(manager)
    dress = [f for f in grounding["facts"] if f.get("key") == "wound_dressing"]
    assert dress


def test_plain_greeting_does_not_create_noisy_public_event() -> None:
    manager = ContinuityManager()
    manager.initialize_scene(
        location="Lobby",
        opening_description="Morning.",
        present_characters=["Ayame", "Celina"],
    )
    manager.process_turn(
        acting_character="Ayame",
        move={
            "action": "",
            "dialogue": "Hello.",
            "motivation": {
                "goal": "greet",
                "tactic": "small talk",
                "emotional_driver": "neutral",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Celina",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "Social open.",
        },
        other_characters=["Celina"],
        timestamp=datetime.fromisoformat("2026-03-28T10:15:00"),
    )
    assert manager.public_events == []

