"""Phase 3.2: per-character selection from shared episodic candidate pool.

Filters by visibility only; applies episodic-only item/char caps. Read-only.
Does not merge with authored retrieval or prompt assembly (later steps).
"""

from __future__ import annotations

from collections.abc import Sequence

from episodic_memory_compile import EpisodicCompiledItem

# Subcaps for episodic lane only (global merge caps come in a later step).
DEFAULT_MAX_EPISODIC_ITEMS = 6
DEFAULT_MAX_EPISODIC_CHARS = 2400


def select_episodic_items_for_character(
    pool: Sequence[EpisodicCompiledItem],
    char_name: str,
    *,
    max_items: int = DEFAULT_MAX_EPISODIC_ITEMS,
    max_chars: int = DEFAULT_MAX_EPISODIC_CHARS,
) -> tuple[EpisodicCompiledItem, ...]:
    """Return episodic items this character may see, in pool order, within caps.

    Pool is assumed already sorted by global episodic priority (see compile).

    Visibility: include an item iff ``viewer`` is in ``item.visible_to`` (exact
    string match after stripping the viewer name). Names in ``visible_to`` are
    whatever continuity supplied at compile time.

    Caps: walk the filtered list in order; append while both ``max_items`` and
    ``max_chars`` (sum of ``len(summary_text)``) allow. An item longer than
    ``max_chars`` alone is skipped (does not break the walk), so later smaller
    items may still appear.
    """
    viewer = str(char_name or "").strip()
    if not viewer:
        return ()

    filtered: list[EpisodicCompiledItem] = [
        it for it in pool if viewer in it.visible_to
    ]

    if max_items <= 0 or max_chars <= 0:
        return ()

    out: list[EpisodicCompiledItem] = []
    used_chars = 0
    for it in filtered:
        if len(out) >= max_items:
            break
        tlen = len(it.summary_text)
        if tlen > max_chars:
            continue
        if used_chars + tlen > max_chars:
            break
        out.append(it)
        used_chars += tlen

    return tuple(out)
