"""Authority, territory, mediation, tension detectors (Issue #159)."""

from typing import Any

try:
    from continuity_state import ConsequenceCategory, DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import ConsequenceCategory, DetectedConsequence

try:
    from scene_exit_detection import dialogue_has_territorial_removal_language
except ImportError:
    from python.rp_app.scene_exit_detection import (
        dialogue_has_territorial_removal_language,
    )

from continuity_consequence_classifier_signals import action_indicates_geometry_repositioning


def detect_authority(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    goal: str,
) -> list[DetectedConsequence]:
    """Detect authority assertion and challenge patterns."""
    results = []

    # AUTHORITY_ASSERTED: control intent + directive or positional behavior
    if intent["control"] and (behavior["directive"] or behavior["positional"]):
        confidence = "strong" if behavior["directive"] else "moderate"
        source = ["motivation.goal"]
        if behavior["directive"]:
            source.append("dialogue")
        if behavior["positional"]:
            source.append("action")

        excerpt = dialogue[:80] if behavior["directive"] else action[:80]
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.AUTHORITY_ASSERTED,
                confidence=confidence,
                source_fields=source,
                excerpt=excerpt,
            )
        )

    # AUTHORITY_CHALLENGED: challenge/resist intent + dismissive/counter behavior
    if (intent["challenge"] or intent["resist"]) and (
        behavior["dismissive"] or behavior["counter"]
    ):
        confidence = "strong" if behavior["dismissive"] else "moderate"
        source = ["motivation.goal"]
        if behavior["dismissive"]:
            source.append("dialogue")
        if behavior["counter"]:
            source.append("action")

        excerpt = dialogue[:80] if behavior["dismissive"] else action[:80]
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.AUTHORITY_CHALLENGED,
                confidence=confidence,
                source_fields=source,
                excerpt=excerpt,
            )
        )

    return results


def detect_territory(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    tension_shift: str,
) -> list[DetectedConsequence]:
    """Detect territorial claim, denial, and repositioning patterns."""
    results = []

    # TERRITORIAL_CLAIM: entry with tension escalation
    if behavior["entry"] and tension_shift == "escalate":
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.TERRITORIAL_CLAIM,
                confidence="strong",
                source_fields=["action", "director_decision.tension_shift"],
                excerpt=action[:80],
            )
        )

    # TERRITORIAL_DENIAL: control intent + deterministic removal phrasing only
    if intent["control"] and dialogue_has_territorial_removal_language(dialogue):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.TERRITORIAL_DENIAL,
                confidence="strong",
                source_fields=["motivation.goal", "dialogue"],
                excerpt=dialogue[:100],
            )
        )

    # REPOSITIONING: blocking/interposition OR meaningful geometry change; not exit/mediation
    repositioning = False
    if not intent["mediate"] and not behavior["exit"]:
        if behavior["positional"]:
            repositioning = True
        elif action_indicates_geometry_repositioning(classifier, action, dialogue):
            repositioning = True
    if repositioning:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.REPOSITIONING,
                confidence="moderate",
                source_fields=["action"],
                excerpt=action[:80],
            )
        )

    # ARRIVAL/EXIT: pure presence changes
    if behavior["entry"] and tension_shift != "escalate":
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.ARRIVAL,
                confidence="moderate",
                source_fields=["action"],
                excerpt=action[:80],
            )
        )

    if behavior["exit"]:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.EXIT,
                confidence="strong",
                source_fields=["action"],
                excerpt=action[:80],
            )
        )

    return results


def detect_mediation(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    goal: str,
) -> list[DetectedConsequence]:
    """Detect mediation and interception patterns."""
    results = []

    # MEDIATION_ATTEMPTED: mediate intent + positional behavior
    if intent["mediate"] and behavior["positional"]:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.MEDIATION_ATTEMPTED,
                confidence="strong",
                source_fields=["motivation.goal", "action"],
                excerpt=action[:80],
            )
        )

    # INTERCEPTION: resist/control intent + counter-mediator behavior
    if (intent["resist"] or intent["control"]) and behavior["counter"]:
        if "mediat" in goal or any(med in action for med in ["shoved", "pushed", "jerked"]):
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.INTERCEPTION,
                    confidence="strong",
                    source_fields=["motivation.goal", "action"],
                    excerpt=action[:80],
                )
            )

    return results


def detect_tension(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    tension_shift: str,
) -> list[DetectedConsequence]:
    """Detect escalation and de-escalation patterns."""
    results = []

    # ESCALATION: tension shift + challenge/escalate intent
    if tension_shift == "escalate" and (
        intent["challenge"] or intent["escalate"] or behavior["directive"]
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.ESCALATION,
                confidence="strong" if intent["escalate"] else "moderate",
                source_fields=[
                    "director_decision.tension_shift",
                    "motivation.goal",
                ],
                excerpt=f"tension_shift=escalate, goal excerpt: {action[:40]}",
            )
        )

    # DEESCALATION: soften tension + mediate/comply intent
    if tension_shift == "soften" and (intent["mediate"] or intent["comply"]):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.DEESCALATION,
                confidence="moderate",
                source_fields=[
                    "director_decision.tension_shift",
                    "motivation.goal",
                ],
                excerpt=f"tension_shift=soften",
            )
        )

    return results
