"""Append-only episodic storage: sole callers of CharacterStateManager.remember_event."""

from __future__ import annotations

from typing import Protocol


class _EpisodicStore(Protocol):
    def remember_event(
        self, name: str, event_summary: str, interpretation: str = ""
    ) -> None: ...


def append_actor_episodic(
    state_manager: _EpisodicStore | None,
    character: str,
    *,
    event_summary: str,
    interpretation: str,
) -> None:
    if not state_manager or not character:
        return
    state_manager.remember_event(character, event_summary, interpretation)


def append_observer_episodic(
    state_manager: _EpisodicStore | None,
    observer: str,
    *,
    observed_line: str,
) -> None:
    if not state_manager or not observer:
        return
    state_manager.remember_event(observer, observed_line, "")
