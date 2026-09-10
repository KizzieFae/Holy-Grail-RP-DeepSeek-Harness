"""Live authoritative session state shared by repository and test fixtures."""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from datetime import datetime, timezone

from character_state_model import CharacterState  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_setup_seam_v77 import finalize_continuity_setup_seam  # noqa: E402
from continuity_state import IssueState, IssueStatus  # noqa: E402

from .memory_scope import resolve_memory_scope_id  # noqa: E402
from .plot_cognition_scope import resolve_plot_cognition_scope_id  # noqa: E402

V2_HOST_METADATA_KEY = "v2_host_state"
EXECUTION_EVIDENCE_METADATA_KEY = "execution_evidence"


@dataclass
class CharacterTurnRecord:
    character_id: str
    committed_move: dict[str, Any]
    domain_commit_id: str
    continuity_turn_index: int
    director_decision: dict[str, Any]


@dataclass
class RoundFixture:
    hg_round_id: str
    hg_scene_id: str
    turn_index: int
    director_decision: dict[str, Any] | None = None
    committed_character_id: str | None = None
    committed_move: dict[str, Any] | None = None
    domain_commit_id: str | None = None
    continuity_turn_index: int | None = None
    actors_used_this_round: list[str] = field(default_factory=list)
    character_turns: list[CharacterTurnRecord] = field(default_factory=list)
    spotlight_history: list[str] = field(default_factory=list)
    eligibility_epoch: int = 0
    storyteller_advisory_package: dict[str, Any] | None = None
    storyteller_round_audit: dict[str, Any] | None = None
    storyteller_invalidation_reason: str | None = None


@dataclass
class LiveSession:
    """Authoritative in-memory session; hg_session_id and hg_scene_id are 1:1 in M5.1."""

    hg_session_id: str
    hg_scene_id: str
    manager: ContinuityManager
    cast: list[str]
    character_states: dict[str, CharacterState]
    committed_move_count: int = 0
    commit_ids: list[str] = field(default_factory=list)
    character_private_secrets: dict[str, str] = field(default_factory=dict)
    rounds: list[RoundFixture] = field(default_factory=list)
    continuity_version: int = 0
    commit_dedup_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    rp_history: list[dict[str, Any]] = field(default_factory=list)
    setup_snapshot: dict[str, Any] = field(default_factory=dict)
    character_file_ids: dict[str, str] = field(default_factory=dict)
    memory_scope_id: str = ""
    plot_cognition_scope_id: str = ""
    librarian_proposal_audit_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def session_id(self) -> str:
        return self.hg_session_id


# Backward-compatible alias used by participation policy and tests.
SceneFixture = LiveSession


def seed_test_active_issue(
    manager: ContinuityManager,
    cast: list[str],
    *,
    issue_id: str = "issue-contract-test-1",
) -> IssueState:
    """Seed one ACTIVE issue for integration tests (e.g. #164 eligibility)."""
    issue = IssueState(
        issue_id=issue_id,
        description="Integration test active issue pressure.",
        participants=list(cast),
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="access_conflict",
        blocked_what="Test objective remains unresolved.",
        required_next_step="A character must act.",
        last_change="Scene opened with unresolved pressure.",
    )
    manager.issues[issue.issue_id] = issue
    assert manager.scene_state is not None
    manager.scene_state.active_issue_ids = [issue.issue_id]
    return issue


def initialize_live_session(
    *,
    hg_session_id: str | None = None,
    location: str = "Workshop",
    cast: list[str] | None = None,
    opening_description: str = "A quiet workshop for boundary prototype tests.",
    memory_scope_id: str | None = None,
    plot_cognition_scope_id: str | None = None,
    seed_active_issue: bool = False,
) -> LiveSession:
    cast = cast or ["Alice", "Bob"]
    session_id = hg_session_id or f"hg-session-{uuid.uuid4()}"
    scene_id = session_id
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location=location,
        opening_description=opening_description,
        present_characters=list(cast),
    )
    assert mgr.scene_state is not None
    roles = ["guest", "staff", "witness", "observer"]
    mgr.scene_state.role_assignments = {
        name: roles[index % len(roles)] for index, name in enumerate(cast)
    }
    finalize_continuity_setup_seam(mgr, cast=list(cast))
    if seed_active_issue:
        seed_test_active_issue(mgr, list(cast))
    secrets = {name: f"private-{name}-{uuid.uuid4().hex[:8]}" for name in cast}
    character_states: dict[str, CharacterState] = {}
    for name in cast:
        state = CharacterState(name=name)
        state.private_memories.append(secrets[name])
        character_states[name] = state
    return LiveSession(
        hg_session_id=session_id,
        hg_scene_id=scene_id,
        manager=mgr,
        cast=list(cast),
        character_states=character_states,
        character_private_secrets=secrets,
        memory_scope_id=resolve_memory_scope_id(memory_scope_id),
        plot_cognition_scope_id=resolve_plot_cognition_scope_id(
            plot_cognition_scope_id,
            resolve_memory_scope_id(memory_scope_id),
        ),
        character_file_ids={name: name.strip().lower().replace(" ", "_") for name in cast},
    )
