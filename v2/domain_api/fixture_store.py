"""Test-only in-memory session store. Not production authority."""

from __future__ import annotations

from typing import Any

from .session_state import LiveSession, initialize_live_session


class FixtureStore:
    """In-memory session store for deterministic unit tests only."""

    def __init__(self) -> None:
        self._scenes: dict[str, LiveSession] = {}

    def create_scene(self, **kwargs: Any) -> LiveSession:
        fixture = initialize_live_session(
            hg_session_id=kwargs.get("hg_scene_id") or kwargs.get("hg_session_id"),
            location=kwargs.get("location", "Workshop"),
            cast=kwargs.get("cast"),
        )
        self._scenes[fixture.hg_scene_id] = fixture
        return fixture

    def create_session(self, **kwargs: Any) -> LiveSession:
        return self.create_scene(**kwargs)

    def get(self, hg_scene_id: str) -> LiveSession | None:
        return self._scenes.get(hg_scene_id)

    def require(self, hg_scene_id: str) -> LiveSession:
        fixture = self.get(hg_scene_id)
        if fixture is None:
            raise KeyError(f"unknown hg_scene_id: {hg_scene_id}")
        return fixture

    def persist(self, session: LiveSession) -> None:
        """No-op for in-memory test fixtures."""

    def open_session(self, hg_session_id: str) -> LiveSession:
        return self.require(hg_session_id)

    def health_ok(self) -> bool:
        return True


def create_prototype_scene(**kwargs: Any) -> LiveSession:
    """Backward-compatible helper for tests."""
    return initialize_live_session(**kwargs)
