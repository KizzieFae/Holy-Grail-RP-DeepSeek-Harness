from typing import Any

from character_state_model import CharacterState


class CharacterStateManager:
    """Manages state for all characters in a scene."""

    def __init__(self) -> None:
        self._states: dict[str, CharacterState] = {}

    def register_character(self, name: str, state: CharacterState) -> None:
        self._states[name] = state

    def get_state(self, name: str) -> CharacterState | None:
        return self._states.get(name)

    def update_character_move(
        self,
        name: str,
        action: str,
        dialogue: str,
        motivation: dict[str, Any] | str | None,
    ) -> None:
        if state := self._states.get(name):
            state.update_from_move(action, dialogue, motivation)

    def remember_event(
        self, name: str, event_summary: str, interpretation: str = ""
    ) -> None:
        if state := self._states.get(name):
            state.remember_event(event_summary, interpretation)

    def public_state_snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "core_goals": state.core_goals
                or ([state.long_term_goal] if state.long_term_goal else []),
                "long_term_goal": state.long_term_goal,
                "medium_term_goal": state.medium_term_goal,
                "current_objective": state.current_objective,
                "short_term_tactic": state.short_term_tactic,
                "local_task_goal": state.local_task_goal,
                "local_task_tactic": state.local_task_tactic,
                "emotional_state": state.emotional_state,
                "stress_level": state.stress_level,
            }
            for name, state in self._states.items()
        }

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {name: state.to_dict() for name, state in self._states.items()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> "CharacterStateManager":
        manager = cls()
        for name, state_data in data.items():
            manager.register_character(name, CharacterState.from_dict(state_data))
        return manager
