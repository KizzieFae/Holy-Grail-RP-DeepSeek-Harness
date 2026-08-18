"""Dedupe detected consequences (Issue #159)."""

try:
    from continuity_state import DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import DetectedConsequence


def dedupe_detected_consequences(
    items: list[DetectedConsequence],
) -> list[DetectedConsequence]:
    """Keep first occurrence per category; preserve multi-label distinct categories."""
    seen: set[str] = set()
    out: list[DetectedConsequence] = []
    for item in items:
        key = item.category.value
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
