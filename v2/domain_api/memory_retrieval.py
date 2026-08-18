"""Session-local memory retrieval for ContextAssembly."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from character_state_model import CharacterState  # noqa: E402
from memory_layer.retrieval import (  # noqa: E402
    build_episodic_prompt_snapshot,
    format_episodic_prompt_sections,
)


def build_session_memory_projection(
    state: CharacterState | None,
) -> tuple[str, dict[str, Any]] | None:
    """Return deterministic episodic projection (summary + self-trace tails only)."""
    if state is None:
        return None
    snapshot = build_episodic_prompt_snapshot(state=state)
    content = format_episodic_prompt_sections(snapshot).strip()
    if not content:
        return None
    provenance = {
        "memory_lane": "session_local_episodic",
        "interpretation_line_count": len(snapshot.interpretation_lines),
        "self_trace_line_count": len(snapshot.self_trace_lines),
        "private_memories_injected": False,
    }
    return content, provenance
