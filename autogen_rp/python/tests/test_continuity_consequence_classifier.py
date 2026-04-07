"""Tests for ConsequenceClassifier: repositioning, refusal/stance, multi-tag dedupe."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_consequence_classifier import ConsequenceClassifier
from continuity_state import ConsequenceCategory


def _decision() -> dict:
    return {
        "next_actor": "Celina",
        "environment_event": "",
        "tension_shift": "steady",
        "reason": "test",
    }


def _cats(classifier: ConsequenceClassifier, move: dict) -> list[str]:
    raw = classifier.classify_turn("Celina", move, _decision(), None)
    return [d.category.value for d in raw]


class TestRepositioningGeometry:
    def test_boundary_crossing_table_chair_triggers(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": (
                "pushed off the table, straightened her back, and walked around "
                "the chair to stand behind it, resting her hands on its backrest"
            ),
            "dialogue": "My legs are fine. Your terms are bullshit.",
            "motivation": {
                "goal": "break the stalemate",
                "tactic": "physically disengage from the table",
                "emotional_driver": "defiance",
                "risk_level": "high",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value in cats

    def test_walk_to_counter_triggers(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "walked to the kitchen counter and set down her glass.",
            "dialogue": "We need to talk.",
            "motivation": {
                "goal": "gather thoughts",
                "tactic": "create distance",
                "emotional_driver": "tense",
                "risk_level": "medium",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value in cats

    def test_cosmetic_stasis_does_not_trigger_geometry(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": (
                "remained leaning over the table, her palms still pressed flat "
                "against the wood, and let out a low exhale through her nose"
            ),
            "dialogue": "I'm listening.",
            "motivation": {
                "goal": "wait without yielding",
                "tactic": "hold position",
                "emotional_driver": "cool",
                "risk_level": "medium",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value not in cats

    def test_cosmetic_tap_only_does_not_trigger_geometry(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "tapped the table once and narrowed her eyes.",
            "dialogue": "Go on.",
            "motivation": {
                "goal": "signal patience",
                "tactic": "minimal motion",
                "emotional_driver": "watchful",
                "risk_level": "low",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value not in cats

    def test_did_not_turn_does_not_trigger_repositioning(self) -> None:
        """Negated 'turn' must not satisfy geometry movement (session_384-style false positive)."""
        clf = ConsequenceClassifier()
        move = {
            "action": (
                "did not turn, took another slow drag from her cigarette, "
                "and let the smoke drift out the cracked window into the dark."
            ),
            "dialogue": "Ask your real question.",
            "motivation": {
                "goal": "hold position at the window",
                "tactic": "refuse to engage physically",
                "emotional_driver": "cold",
                "risk_level": "high",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value not in cats

    def test_turned_toward_door_triggers_repositioning(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "she turned toward the door and stopped.",
            "dialogue": "This conversation is over.",
            "motivation": {
                "goal": "end the confrontation",
                "tactic": "orient toward exit",
                "emotional_driver": "tense",
                "risk_level": "medium",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REPOSITIONING.value in cats


class TestRefusalStance:
    def test_refusal_without_no_not_when_intent_present(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "held eye contact, jaw tight.",
            "dialogue": "Your terms are bullshit. Give me something real.",
            "motivation": {
                "goal": "break the stalemate by forcing a substantive proposal",
                "tactic": "issue an ultimatum without backing down",
                "emotional_driver": "defiance",
                "risk_level": "high",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REFUSAL.value in cats

    def test_dialogue_only_does_not_trigger_refusal(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "sipped tea calmly.",
            "dialogue": "That's bullshit and you know it.",
            "motivation": {
                "goal": "enjoy the evening",
                "tactic": "stay pleasant",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REFUSAL.value not in cats

    def test_strong_intent_without_curated_dialogue(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "stood still.",
            "dialogue": "We'll see.",
            "motivation": {
                "goal": "reject the terms outright and prepare to walk away",
                "tactic": "hold the line",
                "emotional_driver": "cold",
                "risk_level": "high",
            },
        }
        cats = _cats(clf, move)
        assert ConsequenceCategory.REFUSAL.value in cats


class TestMultiTagAndDedupe:
    def test_session383_like_multiple_categories(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": (
                "pushed off the table, straightened her back, and walked around "
                "the chair to stand behind it, resting her hands on its backrest"
            ),
            "dialogue": (
                "My legs are fine. Your terms are bullshit. "
                "Give me something real to work with."
            ),
            "motivation": {
                "goal": "break the stalemate by forcing a substantive proposal",
                "tactic": "physically disengage while issuing an ultimatum",
                "emotional_driver": "defiance",
                "risk_level": "high",
            },
        }
        raw = clf.classify_turn("Celina", move, _decision(), None)
        values = [d.category.value for d in raw]
        assert len(values) == len(set(values)), "duplicate category in output"
        assert ConsequenceCategory.REPOSITIONING.value in values
        assert ConsequenceCategory.REFUSAL.value in values

    def test_dedupe_drops_duplicate_same_category(self) -> None:
        clf = ConsequenceClassifier()
        # If two code paths ever emit the same category, output is once only.
        move = {
            "action": "stepped between them, blocking the path to the door.",
            "dialogue": "No. Nobody leaves until this is settled.",
            "motivation": {
                "goal": "resist escalation and hold the room",
                "tactic": "physically interpose",
                "emotional_driver": "firm",
                "risk_level": "high",
            },
        }
        raw = clf.classify_turn("Celina", move, _decision(), None)
        refusal_count = sum(
            1 for d in raw if d.category == ConsequenceCategory.REFUSAL
        )
        assert refusal_count <= 1


class TestRegressionCalm:
    def test_low_motion_observation_minimal_tags(self) -> None:
        clf = ConsequenceClassifier()
        move = {
            "action": "watches the rain on the window.",
            "dialogue": "",
            "motivation": {
                "goal": "observe quietly",
                "tactic": "stay still",
                "emotional_driver": "pensive",
                "risk_level": "low",
            },
        }
        cats = set(_cats(clf, move))
        assert ConsequenceCategory.REPOSITIONING.value not in cats
        assert ConsequenceCategory.REFUSAL.value not in cats
