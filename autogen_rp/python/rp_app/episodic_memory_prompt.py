"""Feature flag for episodic retrieval (Phase 3.2).

Episodic lines are merged into ``RetrievedContextBundle`` via
``merge_retrieved_context_with_episodic`` and ``format_retrieved_context_for_prompt``.
"""

from __future__ import annotations

import os


def is_episodic_memory_enabled() -> bool:
    """True when ``RP_EPISODIC_MEMORY`` is 1/true/yes (case-insensitive)."""
    v = os.environ.get("RP_EPISODIC_MEMORY", "")
    return str(v).strip().lower() in ("1", "true", "yes")
