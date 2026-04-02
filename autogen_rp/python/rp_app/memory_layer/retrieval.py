"""Memory read path: episodic prompt snapshots and formatting (Phase B).

``character_memory_summary`` holds interpretation-style lines (including content
from ``remember_event``). ``recent_observations`` is a legacy **self-trace**
source (e.g. ``update_from_move``, emotional shifts), not the same conceptual
bucket as interpretation memory. Both are surfaced in character prompts for
**parity** with pre–Phase B behavior; this module owns caps and string shape only.
"""

from __future__ import annotations

from dataclasses import dataclass

from character_state_model import CharacterState

DEFAULT_MAX_INTERPRETATION_LINES = 5
DEFAULT_MAX_SELF_TRACE_LINES = 5


@dataclass(frozen=True)
class EpisodicPromptSnapshot:
    """Tail slices only; no dedup or scrubbing."""

    interpretation_lines: tuple[str, ...]
    self_trace_lines: tuple[str, ...]


def build_episodic_prompt_snapshot(
    *,
    state: CharacterState,
    max_interpretation_lines: int = DEFAULT_MAX_INTERPRETATION_LINES,
    max_self_trace_lines: int = DEFAULT_MAX_SELF_TRACE_LINES,
) -> EpisodicPromptSnapshot:
    summary = getattr(state, "character_memory_summary", None) or []
    obs = getattr(state, "recent_observations", None) or []
    i_lines = tuple(str(x) for x in summary[-max_interpretation_lines:])
    s_lines = tuple(str(x) for x in obs[-max_self_trace_lines:])
    return EpisodicPromptSnapshot(
        interpretation_lines=i_lines,
        self_trace_lines=s_lines,
    )


def format_episodic_prompt_sections(snapshot: EpisodicPromptSnapshot) -> str:
    """Match pre–Phase B episodic prompt blocks (section titles and bullets)."""
    parts: list[str] = []
    if snapshot.interpretation_lines:
        parts.append("\nYour private interpretation summary:")
        for line in snapshot.interpretation_lines:
            parts.append(f"  • {line}")
    if snapshot.self_trace_lines:
        parts.append("\nRecent memories:")
        for line in snapshot.self_trace_lines:
            parts.append(f"  • {line}")
    return "\n".join(parts) if parts else ""


def build_character_state_context_for_prompt(
    *,
    state: CharacterState,
    relationship_focus_names: list[str] | None = None,
    relationship_secondary_names: list[str] | None = None,
    max_interpretation_lines: int = DEFAULT_MAX_INTERPRETATION_LINES,
    max_self_trace_lines: int = DEFAULT_MAX_SELF_TRACE_LINES,
) -> str:
    """Identity + episodic, single string for ``state_context`` (downstream parity)."""
    identity = state.to_prompt_identity_context(
        relationship_focus_names=relationship_focus_names,
        relationship_secondary_names=relationship_secondary_names,
    )
    episodic = format_episodic_prompt_sections(
        build_episodic_prompt_snapshot(
            state=state,
            max_interpretation_lines=max_interpretation_lines,
            max_self_trace_lines=max_self_trace_lines,
        )
    )
    if not episodic:
        return identity
    return "\n".join([identity, episodic])
