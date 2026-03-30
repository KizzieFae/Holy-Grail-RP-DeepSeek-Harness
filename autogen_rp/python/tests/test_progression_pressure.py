from dataclasses import dataclass, field
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from orchestration_helpers import (  # noqa: E402
    build_default_orchestration_state,
    resolve_progression_override_actor,
)
from progression_pressure import (  # noqa: E402
    build_director_progression_pressure_prefix,
    capture_progression_truth_snapshot,
    get_cached_progression_pressure,
    update_progression_pressure_state,
)
from prompt_builders import build_director_selection_prompt  # noqa: E402


@dataclass
class DummyStatus:
    value: str


@dataclass
class DummyIssue:
    issue_id: str
    status: DummyStatus
    participants: list[str]
    pressure_kind: str = "plan_execution"
    blocked_what: str = "The current proposed course of action"
    required_next_step: str = "Someone must force a concrete next move."
    last_change: str = ""
    description: str = "Resolve the blocked plan."
    last_turn_index: int = 0


@dataclass
class DummyOutcome:
    outcome_id: str
    category: str
    key: str
    subject_id: str
    value: dict[str, str]
    status: str = "active"
    source_issue_id: str | None = None
    supersedes_outcome_id: str | None = None
    created_turn_index: int = 0
    revoked_turn_index: int = 0


@dataclass
class DummySceneState:
    phase: str = "rising"
    location: str = "Dorm"
    present_characters: list[str] = field(default_factory=lambda: ["Ayame", "Harley"])
    offstage_characters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "location": self.location,
            "present_characters": list(self.present_characters),
            "offstage_characters": list(self.offstage_characters),
        }


@dataclass
class DummyManager:
    turn_counter: int
    scene_state: DummySceneState
    issues: dict[str, DummyIssue]
    resolved_outcomes: list[DummyOutcome] = field(default_factory=list)
    turn_metadata_by_index: dict[int, dict] = field(default_factory=dict)


def _make_issue(
    issue_id: str,
    *,
    status: str = "active",
    participants: list[str] | None = None,
    last_turn_index: int = 0,
    blocked_what: str = "The current proposed course of action",
) -> DummyIssue:
    return DummyIssue(
        issue_id=issue_id,
        status=DummyStatus(status),
        participants=participants or ["Ayame", "Harley"],
        blocked_what=blocked_what,
        last_turn_index=last_turn_index,
    )


def test_scene_level_stagnation_accumulates_without_primary_delta() -> None:
    orch = build_default_orchestration_state()
    before_1 = DummyManager(
        turn_counter=0,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="active", last_turn_index=0)},
    )
    after_1 = DummyManager(
        turn_counter=1,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="active", last_turn_index=0)},
        turn_metadata_by_index={1: {}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after_1,
        before_snapshot=capture_progression_truth_snapshot(before_1),
    )

    after_state = get_cached_progression_pressure(orch) or {}
    assert after_state["scene_progression_debt"] == 1
    assert after_state["scene_instability_tier"] == "stable"
    assert after_state["last_turn"]["scene_turn_class"] == "non_progression"

    after_2 = DummyManager(
        turn_counter=2,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="active", last_turn_index=0)},
        turn_metadata_by_index={2: {}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after_2,
        before_snapshot=capture_progression_truth_snapshot(after_1),
    )
    after_state = get_cached_progression_pressure(orch) or {}
    assert after_state["scene_progression_debt"] == 2
    assert after_state["scene_instability_tier"] == "unstable"


def test_issue_level_stagnation_uses_explicit_stall_class_and_plus_two() -> None:
    orch = build_default_orchestration_state()
    before = DummyManager(
        turn_counter=2,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="active", last_turn_index=1)},
    )
    after = DummyManager(
        turn_counter=3,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="stalled", last_turn_index=3)},
        turn_metadata_by_index={3: {}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after,
        before_snapshot=capture_progression_truth_snapshot(before),
    )

    state = get_cached_progression_pressure(orch) or {}
    assert state["issue_progression_debt"]["issue_core"] == 2
    assert state["issue_instability_tiers"]["issue_core"] == "unstable"
    assert (
        state["last_turn"]["issue_turn_classes"]["issue_core"]["turn_class"]
        == "explicit_stagnation"
    )
    assert state["last_turn"]["scene_turn_class"] == "explicit_stagnation"


def test_repeated_partial_progression_loop_holds_debt_steady() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["scene_progression_debt"] = 3
    orch["progression_pressure"]["scene_instability_tier"] = "unstable"
    orch["progression_pressure"]["issue_progression_debt"] = {"issue_core": 2}
    orch["progression_pressure"]["issue_instability_tiers"] = {"issue_core": "unstable"}

    before_1 = DummyManager(
        turn_counter=4,
        scene_state=DummySceneState(),
        issues={
            "issue_core": _make_issue(
                "issue_core",
                status="active",
                last_turn_index=4,
                blocked_what="Get the bleeding under control",
            )
        },
    )
    after_1 = DummyManager(
        turn_counter=5,
        scene_state=DummySceneState(),
        issues={
            "issue_core": DummyIssue(
                issue_id="issue_core",
                status=DummyStatus("active"),
                participants=["Ayame", "Harley"],
                blocked_what="Get the bleeding under control",
                required_next_step="Someone must keep pressure on the wound and choose transport.",
                last_change="Ayame tightened the improvised bandage but transport is still unresolved.",
                last_turn_index=5,
            )
        },
        turn_metadata_by_index={5: {"tags": ["agreement"]}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after_1,
        before_snapshot=capture_progression_truth_snapshot(before_1),
    )
    mid = get_cached_progression_pressure(orch) or {}
    assert mid["scene_progression_debt"] == 3
    assert mid["issue_progression_debt"]["issue_core"] == 2
    assert mid["last_turn"]["scene_turn_class"] == "partial_progression"
    assert (
        mid["last_turn"]["issue_turn_classes"]["issue_core"]["turn_class"]
        == "partial_progression"
    )

    after_2 = DummyManager(
        turn_counter=6,
        scene_state=DummySceneState(),
        issues={
            "issue_core": DummyIssue(
                issue_id="issue_core",
                status=DummyStatus("active"),
                participants=["Ayame", "Harley"],
                blocked_what="Get the bleeding under control",
                required_next_step="Someone must commit to transport right now.",
                last_change="Harley stabilized the position, but the evacuation decision is still pending.",
                last_turn_index=6,
            )
        },
        turn_metadata_by_index={6: {"tags": ["agreement"]}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after_2,
        before_snapshot=capture_progression_truth_snapshot(after_1),
    )
    final = get_cached_progression_pressure(orch) or {}
    assert final["scene_progression_debt"] == 3
    assert final["issue_progression_debt"]["issue_core"] == 2
    assert final["scene_instability_tier"] == "unstable"
    assert final["issue_instability_tiers"]["issue_core"] == "unstable"


def test_material_progression_resets_scene_and_resolved_issue_only() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["scene_progression_debt"] = 6
    orch["progression_pressure"]["scene_instability_tier"] = "escalating"
    orch["progression_pressure"]["issue_progression_debt"] = {
        "issue_core": 5,
        "issue_other": 2,
    }
    orch["progression_pressure"]["issue_instability_tiers"] = {
        "issue_core": "escalating",
        "issue_other": "unstable",
    }
    orch["progression_pressure"]["dominant_issue_ids"] = ["issue_core"]

    before = DummyManager(
        turn_counter=7,
        scene_state=DummySceneState(),
        issues={
            "issue_core": _make_issue(
                "issue_core",
                status="active",
                last_turn_index=7,
                blocked_what="Get the bleeding under control",
            ),
            "issue_other": _make_issue(
                "issue_other",
                status="active",
                last_turn_index=7,
                blocked_what="Who sleeps where tonight",
            ),
        },
    )
    after = DummyManager(
        turn_counter=8,
        scene_state=DummySceneState(),
        issues={
            "issue_core": _make_issue(
                "issue_core",
                status="resolved",
                last_turn_index=8,
                blocked_what="Get the bleeding under control",
            ),
            "issue_other": _make_issue(
                "issue_other",
                status="active",
                last_turn_index=7,
                blocked_what="Who sleeps where tonight",
            ),
        },
        resolved_outcomes=[
            DummyOutcome(
                outcome_id="resolved_medical_transport_1",
                category="medical",
                key="suppressant_formulation",
                subject_id="Harley",
                value={"subject_id": "Harley", "status": "compatible"},
                source_issue_id="issue_core",
                created_turn_index=8,
            )
        ],
        turn_metadata_by_index={8: {"tags": ["decision_made", "medical_state_set"]}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after,
        before_snapshot=capture_progression_truth_snapshot(before),
    )

    state = get_cached_progression_pressure(orch) or {}
    assert state["scene_progression_debt"] == 0
    assert state["scene_instability_tier"] == "stable"
    assert state["issue_progression_debt"]["issue_core"] == 0
    assert state["issue_progression_debt"]["issue_other"] == 3
    assert state["last_turn"]["scene_turn_class"] == "material_progression"


def test_mixed_turn_keeps_scene_debt_when_only_peripheral_issue_resolves() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["scene_progression_debt"] = 5
    orch["progression_pressure"]["scene_instability_tier"] = "escalating"
    orch["progression_pressure"]["issue_progression_debt"] = {
        "issue_core": 4,
        "issue_peripheral": 0,
    }
    orch["progression_pressure"]["issue_instability_tiers"] = {
        "issue_core": "escalating",
        "issue_peripheral": "stable",
    }

    before = DummyManager(
        turn_counter=1,
        scene_state=DummySceneState(),
        issues={
            "issue_core": _make_issue(
                "issue_core",
                status="active",
                last_turn_index=1,
                blocked_what="Get the bleeding under control",
            ),
            "issue_peripheral": _make_issue(
                "issue_peripheral",
                status="active",
                last_turn_index=1,
                blocked_what="Who sleeps where tonight",
            ),
        },
    )
    after = DummyManager(
        turn_counter=2,
        scene_state=DummySceneState(),
        issues={
            "issue_core": _make_issue(
                "issue_core",
                status="active",
                last_turn_index=1,
                blocked_what="Get the bleeding under control",
            ),
            "issue_peripheral": _make_issue(
                "issue_peripheral",
                status="resolved",
                last_turn_index=2,
                blocked_what="Who sleeps where tonight",
            ),
        },
        resolved_outcomes=[
            DummyOutcome(
                outcome_id="resolved_assignment_sleeping_surface_1",
                category="assignment",
                key="sleeping_surface",
                subject_id="Harley",
                value={"assignee_id": "Harley", "surface_id": "couch"},
                source_issue_id="issue_peripheral",
                created_turn_index=2,
            )
        ],
        turn_metadata_by_index={2: {"tags": ["decision_made", "plan_committed"]}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after,
        before_snapshot=capture_progression_truth_snapshot(before),
    )

    state = get_cached_progression_pressure(orch) or {}
    assert state["scene_progression_debt"] == 5
    assert state["last_turn"]["scene_turn_class"] == "partial_progression"
    assert state["last_turn"]["scene_debug"]["scene_reset"] is False


def test_same_value_resolved_outcome_no_op_does_not_create_progression_credit() -> None:
    orch = build_default_orchestration_state()
    existing = DummyOutcome(
        outcome_id="resolved_assignment_sleeping_surface_existing",
        category="assignment",
        key="sleeping_surface",
        subject_id="Harley",
        value={"assignee_id": "Harley", "surface_id": "couch"},
        created_turn_index=1,
    )
    before = DummyManager(
        turn_counter=1,
        scene_state=DummySceneState(),
        issues={},
        resolved_outcomes=[existing],
    )
    after = DummyManager(
        turn_counter=2,
        scene_state=DummySceneState(),
        issues={},
        resolved_outcomes=[existing],
        turn_metadata_by_index={2: {}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after,
        before_snapshot=capture_progression_truth_snapshot(before),
    )

    state = get_cached_progression_pressure(orch) or {}
    assert state["scene_progression_debt"] == 1
    assert state["last_turn"]["resolved_outcome_deltas"] == []
    assert state["last_turn"]["scene_turn_class"] == "non_progression"


def test_stalled_issue_identity_continuity_transfers_debt_on_exact_match() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["issue_progression_debt"] = {"issue_old": 3}
    orch["progression_pressure"]["issue_instability_tiers"] = {"issue_old": "unstable"}
    before = DummyManager(
        turn_counter=4,
        scene_state=DummySceneState(),
        issues={
            "issue_old": _make_issue(
                "issue_old",
                status="stalled",
                last_turn_index=4,
                blocked_what="Get the bleeding under control",
            )
        },
    )
    after = DummyManager(
        turn_counter=5,
        scene_state=DummySceneState(),
        issues={
            "issue_new": _make_issue(
                "issue_new",
                status="active",
                last_turn_index=5,
                blocked_what="Get the bleeding under control",
            )
        },
        turn_metadata_by_index={5: {}},
    )
    update_progression_pressure_state(
        orchestration_state=orch,
        continuity_manager=after,
        before_snapshot=capture_progression_truth_snapshot(before),
    )

    state = get_cached_progression_pressure(orch) or {}
    assert state["issue_progression_debt"]["issue_new"] == 3
    assert state["issue_identity_aliases"]["issue_new"] == "issue_old"
    assert state["last_turn"]["issue_identity_notes"]


def test_tier_climb_behavior_matches_locked_thresholds() -> None:
    orch = build_default_orchestration_state()
    previous = DummyManager(
        turn_counter=0,
        scene_state=DummySceneState(),
        issues={"issue_core": _make_issue("issue_core", status="active", last_turn_index=0)},
    )
    checkpoints: dict[int, tuple[int, str, int, str]] = {
        1: (1, "stable", 1, "stable"),
        2: (2, "unstable", 2, "unstable"),
        4: (4, "escalating", 4, "escalating"),
        6: (6, "escalating", 6, "forcing"),
        7: (7, "forcing", 7, "forcing"),
    }
    for turn_index in range(1, 8):
        current = DummyManager(
            turn_counter=turn_index,
            scene_state=DummySceneState(),
            issues={
                "issue_core": _make_issue(
                    "issue_core", status="active", last_turn_index=0
                )
            },
            turn_metadata_by_index={turn_index: {}},
        )
        update_progression_pressure_state(
            orchestration_state=orch,
            continuity_manager=current,
            before_snapshot=capture_progression_truth_snapshot(previous),
        )
        state = get_cached_progression_pressure(orch) or {}
        if turn_index in checkpoints:
            (
                expected_scene_debt,
                expected_scene_tier,
                expected_issue_debt,
                expected_issue_tier,
            ) = checkpoints[turn_index]
            assert state["scene_progression_debt"] == expected_scene_debt
            assert state["scene_instability_tier"] == expected_scene_tier
            assert state["issue_progression_debt"]["issue_core"] == expected_issue_debt
            assert state["issue_instability_tiers"]["issue_core"] == expected_issue_tier
        previous = current


def test_orchestration_override_prefers_actor_on_forcing_issue() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["scene_progression_debt"] = 7
    orch["progression_pressure"]["scene_instability_tier"] = "forcing"
    orch["progression_pressure"]["issue_progression_debt"] = {
        "issue_core": 6,
        "issue_other": 1,
    }
    orch["progression_pressure"]["issue_instability_tiers"] = {
        "issue_core": "forcing",
        "issue_other": "stable",
    }
    orch["progression_pressure"]["dominant_issue_ids"] = ["issue_core"]
    active_issues = [
        {
            "issue_id": "issue_core",
            "status": "active",
            "participants": ["Ayame", "Harley"],
            "description": "Stop the bleeding before the scene collapses.",
        },
        {
            "issue_id": "issue_other",
            "status": "active",
            "participants": ["Kizzie"],
            "description": "Sort out the bedding.",
        },
    ]
    actor = resolve_progression_override_actor(
        director_selected_actor="Kizzie",
        available_actors=["Kizzie", "Ayame", "Harley"],
        active_issues=active_issues,
        orchestration_state=orch,
    )
    assert actor in {"Ayame", "Harley"}


def test_director_prompt_strips_progression_pressure_hint_from_json() -> None:
    orch = build_default_orchestration_state()
    orch["progression_pressure"]["scene_progression_debt"] = 7
    orch["progression_pressure"]["scene_instability_tier"] = "forcing"
    orch["progression_pressure"]["dominant_issue_ids"] = ["issue_core"]
    prefix = build_director_progression_pressure_prefix(orch)
    prompt = build_director_selection_prompt(
        {
            "participants": ["Ayame", "Harley"],
            "available_next_actors": ["Ayame", "Harley"],
            "progression_pressure_director_hints": {
                "active": True,
                "prompt_prefix": prefix,
            },
        }
    )
    assert "PROGRESSION PRESSURE (STRUCTURED)" in prompt
    assert "progression_pressure_director_hints" not in prompt
