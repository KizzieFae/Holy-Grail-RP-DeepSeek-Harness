"""Memory scope identity helpers."""

from __future__ import annotations

import uuid


def new_memory_scope_id() -> str:
    return f"hg-memory-scope-{uuid.uuid4()}"


def resolve_memory_scope_id(requested: str | None) -> str:
    scope = str(requested or "").strip()
    if scope:
        return scope
    return new_memory_scope_id()
