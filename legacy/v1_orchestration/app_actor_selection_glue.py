"""Director fallback actor selection with orchestration spotlight history (Issue #174)."""

from typing import Any

import app_turn_helpers as turn_helpers
from orchestration_helpers import choose_fallback_actor as choose_fallback_actor_impl


def choose_fallback_actor_from_orchestration(
    available_actors: list[str],
    forced_speaker: str | None,
    *,
    orchestration_state: dict[str, Any],
    prefer_continuing_spotlight: bool = False,
) -> str | None:
    return turn_helpers.choose_fallback_actor(
        available_actors=available_actors,
        forced_speaker=forced_speaker,
        spotlight_history=orchestration_state.get("spotlight_history", []),
        choose_fallback_actor_impl_fn=choose_fallback_actor_impl,
        prefer_continuing_spotlight=prefer_continuing_spotlight,
    )
