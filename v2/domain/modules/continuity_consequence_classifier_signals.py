"""Intent/behavior signals and interaction-geometry helpers (Issue #159)."""

from typing import Any

from continuity_consequence_classifier_regexes import (
    GEOMETRY_NEGATED_TURN_PHRASE,
    GEOMETRY_TURN_VERB,
)


def extract_intent_signals(classifier: Any, goal: str, tactic: str) -> dict[str, bool]:
    """Extract intent categories from goal and tactic fields."""
    combined = f"{goal} {tactic}"
    return {
        "control": any(marker in combined for marker in classifier.INTENT_CONTROL),
        "resist": any(marker in combined for marker in classifier.INTENT_RESIST),
        "mediate": any(marker in combined for marker in classifier.INTENT_MEDIATE),
        "challenge": any(marker in combined for marker in classifier.INTENT_CHALLENGE),
        "comply": any(marker in combined for marker in classifier.INTENT_COMPLY),
        "escalate": any(marker in combined for marker in classifier.INTENT_ESCALATE),
    }


def extract_behavior_signals(
    classifier: Any, action: str, dialogue: str
) -> dict[str, bool]:
    """Extract behavior categories from action and dialogue."""
    combined = f"{action} {dialogue}"
    return {
        "directive": any(marker in combined for marker in classifier.BEHAVIOR_DIRECTIVE),
        "positional": any(
            marker in combined for marker in classifier.BEHAVIOR_POSITIONAL
        ),
        "dismissive": any(
            marker in combined for marker in classifier.BEHAVIOR_DISMISSIVE
        ),
        "counter": any(marker in combined for marker in classifier.BEHAVIOR_COUNTER),
        "entry": any(marker in combined for marker in classifier.BEHAVIOR_ENTRY),
        "exit": False,
    }


def geometry_movement_present(classifier: Any, action: str) -> bool:
    """True if action has a geometry-relevant movement cue (substring markers or non-negated *turn* verb)."""
    lowered = action.lower()
    for m in classifier.GEOMETRY_MOVEMENT_MARKERS:
        if m in lowered:
            return True
    scrubbed = GEOMETRY_NEGATED_TURN_PHRASE.sub(" ", lowered)
    return bool(GEOMETRY_TURN_VERB.search(scrubbed))


def is_geometry_stasis_or_cosmetic_dominant(classifier: Any, action: str) -> bool:
    """True when action reads as in-place posture/micro-motion without locomotion."""
    if any(leader in action for leader in classifier.GEOMETRY_STASIS_LEADERS):
        if not geometry_movement_present(classifier, action):
            return True
    # Cosmetic-only markers without locomotion cues
    if any(c in action for c in classifier.GEOMETRY_COSMETIC_ONLY_MARKERS):
        if not geometry_movement_present(classifier, action):
            return True
    return False


def action_indicates_geometry_repositioning(
    classifier: Any, action: str, dialogue: str
) -> bool:
    """Meaningful interaction-geometry change: locomotion + transition/locus."""
    if is_geometry_stasis_or_cosmetic_dominant(classifier, action):
        return False
    if not geometry_movement_present(classifier, action):
        return False
    has_transition = any(t in action for t in classifier.INTERACTION_TRANSITION_MARKERS)
    has_locus_action = any(
        locus in action for locus in classifier.INTERACTION_LOCUS_MARKERS
    )
    has_locus_dialogue = any(
        locus in dialogue for locus in classifier.INTERACTION_LOCUS_MARKERS
    )
    dialogue_path_transition = any(
        t in dialogue for t in (" to the ", " into the ", " toward", " towards")
    )

    if has_transition and (has_locus_action or has_locus_dialogue):
        return True
    # Movement + locus in action + spatial relation (e.g. around/behind/toward chair)
    if has_locus_action and (
        " around " in action
        or " behind " in action
        or " toward" in action
        or " towards" in action
        or " off the " in action
        or " off of " in action
    ):
        return True
    # Optional: dialogue names locus + path language; action still shows locomotion
    if has_locus_dialogue and dialogue_path_transition:
        return True
    return False
