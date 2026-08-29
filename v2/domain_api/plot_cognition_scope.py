"""Plot cognition scope identity helpers (#59)."""

from __future__ import annotations

import uuid


def new_plot_cognition_scope_id() -> str:
    return f"hg-plot-cognition-scope-{uuid.uuid4()}"


def resolve_plot_cognition_scope_id(
    requested: str | None,
    memory_scope_id: str,
) -> str:
    """Resolve overlay persistence scope for a session."""
    scope = str(requested or "").strip()
    if scope:
        return scope
    memory_scope = str(memory_scope_id or "").strip()
    if memory_scope:
        return memory_scope
    return new_plot_cognition_scope_id()
