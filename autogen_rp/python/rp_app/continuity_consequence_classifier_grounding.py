"""Persistent scene-state signals aligned with scene_grounding (Issue #159)."""

from typing import Any

from continuity_consequence_classifier_move_tools import (
    move_with_flat_text_for_deterministic_tools,
)

try:
    from continuity_state import ConsequenceCategory, DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import ConsequenceCategory, DetectedConsequence


def detect_persistent_scene_state(move: dict[str, Any]) -> list[DetectedConsequence]:
    """Lexical scene-state signals; must match ``grounding_state_signals_from_move``."""
    try:
        from scene_grounding import (
            SIGNAL_BANDAGE_APPLIED,
            SIGNAL_PHONE_BROKEN,
            SIGNAL_WEAPON_ON_TABLE,
            grounding_state_signals_from_move,
        )
    except ImportError:
        from python.rp_app.scene_grounding import (
            SIGNAL_BANDAGE_APPLIED,
            SIGNAL_PHONE_BROKEN,
            SIGNAL_WEAPON_ON_TABLE,
            grounding_state_signals_from_move,
        )

    tm = move_with_flat_text_for_deterministic_tools(move)
    signals = grounding_state_signals_from_move(tm)
    results: list[DetectedConsequence] = []
    excerpt_src = f"{tm.get('dialogue', '')} {tm.get('action', '')}".strip()
    excerpt = excerpt_src[:80] if excerpt_src else ""

    if SIGNAL_PHONE_BROKEN in signals or SIGNAL_WEAPON_ON_TABLE in signals:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.PHYSICAL_STATE_SET,
                confidence="strong",
                source_fields=["dialogue", "action"],
                excerpt=excerpt,
            )
        )
    if SIGNAL_BANDAGE_APPLIED in signals:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.MEDICAL_STATE_SET,
                confidence="strong",
                source_fields=["dialogue", "action"],
                excerpt=excerpt,
            )
        )
    return results
