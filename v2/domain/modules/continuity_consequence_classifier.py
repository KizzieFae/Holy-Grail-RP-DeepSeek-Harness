"""Pattern-based consequence classifier for continuity system.

Uses structured move data (goal, tactic, action, dialogue) to detect
semantic consequence categories via intent + behavior pattern matching.
"""

from typing import Any

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)

try:
    from scene_exit_detection import detect_exit_from_scene
except ImportError:
    from python.rp_app.scene_exit_detection import detect_exit_from_scene

try:
    from continuity_state import DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import DetectedConsequence

import continuity_consequence_classifier_constants as _constants
from continuity_consequence_classifier_dedupe import dedupe_detected_consequences
from continuity_consequence_classifier_detect_outcome_language import (
    detect_access,
    detect_agreement,
    detect_information,
    detect_structured_sleeping_assignment,
)
from continuity_consequence_classifier_detect_scene_dynamics import (
    detect_authority,
    detect_mediation,
    detect_territory,
    detect_tension,
)
from continuity_consequence_classifier_grounding import detect_persistent_scene_state
from continuity_consequence_classifier_move_tools import (
    move_with_flat_text_for_deterministic_tools,
)
from continuity_consequence_classifier_signals import (
    extract_behavior_signals,
    extract_intent_signals,
)


class ConsequenceClassifier:
    """Deterministic classifier using intent (goal/tactic) + behavior (action/dialogue) patterns.

    Multi-label by default: accumulates all supported categories per turn
    rather than stopping at first match.
    """

    INTENT_CONTROL = _constants.INTENT_CONTROL
    INTENT_RESIST = _constants.INTENT_RESIST
    INTENT_MEDIATE = _constants.INTENT_MEDIATE
    INTENT_CHALLENGE = _constants.INTENT_CHALLENGE
    INTENT_COMPLY = _constants.INTENT_COMPLY
    INTENT_ESCALATE = _constants.INTENT_ESCALATE
    BEHAVIOR_DIRECTIVE = _constants.BEHAVIOR_DIRECTIVE
    BEHAVIOR_POSITIONAL = _constants.BEHAVIOR_POSITIONAL
    BEHAVIOR_DISMISSIVE = _constants.BEHAVIOR_DISMISSIVE
    BEHAVIOR_COUNTER = _constants.BEHAVIOR_COUNTER
    BEHAVIOR_ENTRY = _constants.BEHAVIOR_ENTRY
    INTERACTION_LOCUS_MARKERS = _constants.INTERACTION_LOCUS_MARKERS
    INTERACTION_TRANSITION_MARKERS = _constants.INTERACTION_TRANSITION_MARKERS
    GEOMETRY_MOVEMENT_MARKERS = _constants.GEOMETRY_MOVEMENT_MARKERS
    GEOMETRY_STASIS_LEADERS = _constants.GEOMETRY_STASIS_LEADERS
    GEOMETRY_COSMETIC_ONLY_MARKERS = _constants.GEOMETRY_COSMETIC_ONLY_MARKERS
    REFUSAL_DIALOGUE_MARKERS = _constants.REFUSAL_DIALOGUE_MARKERS
    REFUSAL_STRONG_INTENT_MARKERS = _constants.REFUSAL_STRONG_INTENT_MARKERS
    REFUSAL_LEGACY_DIALOGUE_MARKERS = _constants.REFUSAL_LEGACY_DIALOGUE_MARKERS

    def classify_turn(
        self,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        scene_state: dict[str, Any] | None = None,
    ) -> list[DetectedConsequence]:
        """Classify a turn into consequence categories.

        Multi-label: returns all applicable categories, not just first match.
        """
        # Extract structured fields (v2: canonical text from ``beats[]``, not projected views; Issue #140).
        goal = str(move.get("motivation", {}).get("goal", "")).lower()
        tactic = str(move.get("motivation", {}).get("tactic", "")).lower()
        if is_canonical_v2_move(move):
            action = legacy_flat_action_text(move).lower()
            dialogue = legacy_flat_dialogue_text(move).lower()
        else:
            action = str(move.get("action", "")).lower()
            dialogue = str(move.get("dialogue", "")).lower()
        tension_shift = str(director_decision.get("tension_shift", "")).lower()
        environment_event = str(director_decision.get("environment_event", "")).lower()

        tm = move_with_flat_text_for_deterministic_tools(move)

        # Build signal profiles
        intent = extract_intent_signals(self, goal, tactic)
        behavior = extract_behavior_signals(self, action, dialogue)
        if detect_exit_from_scene(tm, scene_state, acting_character):
            behavior["exit"] = True

        # Accumulate all detected consequences
        consequences: list[DetectedConsequence] = []

        # Authority patterns
        consequences.extend(
            detect_authority(
                self, acting_character, intent, behavior, action, dialogue, goal
            )
        )

        # Territory patterns
        consequences.extend(
            detect_territory(
                self, acting_character, intent, behavior, action, dialogue, tension_shift
            )
        )

        # Mediation patterns
        consequences.extend(
            detect_mediation(
                self, acting_character, intent, behavior, action, dialogue, goal
            )
        )

        # Tension trajectory
        consequences.extend(
            detect_tension(
                self, acting_character, intent, behavior, action, dialogue, tension_shift
            )
        )

        # Agreement/refusal
        consequences.extend(
            detect_agreement(
                self, acting_character, intent, behavior, action, dialogue, goal, tactic
            )
        )

        consequences.extend(
            detect_structured_sleeping_assignment(
                self,
                move=move,
                scene_state=scene_state,
                goal=goal,
                tactic=tactic,
                action=action,
                dialogue=dialogue,
            )
        )

        # Access patterns
        consequences.extend(
            detect_access(self, acting_character, intent, behavior, action, dialogue)
        )

        # Information state
        consequences.extend(
            detect_information(
                self, acting_character, intent, behavior, action, dialogue, goal, tactic
            )
        )

        # Deterministic persistent scene-state signals (shared with scene_grounding)
        consequences.extend(detect_persistent_scene_state(move))

        return dedupe_detected_consequences(consequences)
