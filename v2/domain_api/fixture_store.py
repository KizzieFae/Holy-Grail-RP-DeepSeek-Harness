"""In-memory scene fixtures for the V2 boundary prototype."""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_RP_APP = Path(__file__).resolve().parents[2] / "autogen_rp" / "python" / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from continuity_manager import ContinuityManager  # noqa: E402
from continuity_setup_seam_v77 import finalize_continuity_setup_seam  # noqa: E402


@dataclass
class RoundFixture:
    hg_round_id: str
    hg_scene_id: str
    turn_index: int
    director_decision: dict[str, Any] | None = None


@dataclass
class SceneFixture:
    hg_scene_id: str
    manager: ContinuityManager
    cast: list[str]
    committed_move_count: int = 0
    commit_ids: list[str] = field(default_factory=list)
    character_private_secrets: dict[str, str] = field(default_factory=dict)
    rounds: list[RoundFixture] = field(default_factory=list)


def create_prototype_scene(
    *,
    hg_scene_id: str | None = None,
    location: str = "Workshop",
    cast: list[str] | None = None,
) -> SceneFixture:
    cast = cast or ["Alice", "Bob"]
    scene_id = hg_scene_id or f"hg-scene-{uuid.uuid4()}"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location=location,
        opening_description="A quiet workshop for boundary prototype tests.",
        present_characters=list(cast),
    )
    assert mgr.scene_state is not None
    mgr.scene_state.role_assignments = {cast[0]: "guest", cast[1]: "staff"}
    finalize_continuity_setup_seam(mgr, cast=list(cast))
    secrets = {name: f"private-{name}-{uuid.uuid4().hex[:8]}" for name in cast}
    return SceneFixture(
        hg_scene_id=scene_id,
        manager=mgr,
        cast=list(cast),
        character_private_secrets=secrets,
    )


class FixtureStore:
    def __init__(self) -> None:
        self._scenes: dict[str, SceneFixture] = {}

    def create_scene(self, **kwargs: Any) -> SceneFixture:
        fixture = create_prototype_scene(**kwargs)
        self._scenes[fixture.hg_scene_id] = fixture
        return fixture

    def get(self, hg_scene_id: str) -> SceneFixture | None:
        return self._scenes.get(hg_scene_id)

    def require(self, hg_scene_id: str) -> SceneFixture:
        fixture = self.get(hg_scene_id)
        if fixture is None:
            raise KeyError(f"unknown hg_scene_id: {hg_scene_id}")
        return fixture
