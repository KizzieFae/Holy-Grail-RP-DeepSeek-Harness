"""Live authoritative session state shared by repository and test fixtures."""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_RP_APP = Path(__file__).resolve().parents[2] / "autogen_rp" / "python" / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from character_state_model import CharacterState  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_setup_seam_v77 import finalize_continuity_setup_seam  # noqa: E402

V2_HOST_METADATA_KEY = "v2_host_state"


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

    @property
    def session_id(self) -> str:
        return self.hg_session_id


# Backward-compatible alias used by participation policy and tests.
SceneFixture = LiveSession


def initialize_live_session(
    *,
    hg_session_id: str | None = None,
    location: str = "Workshop",
    cast: list[str] | None = None,
    opening_description: str = "A quiet workshop for boundary prototype tests.",
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
    )
