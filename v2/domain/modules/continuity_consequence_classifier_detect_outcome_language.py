"""Agreement, sleeping assignment, access, information detectors (Issue #159)."""

from typing import Any

try:
    from continuity_resolved_outcomes import extract_sleeping_surface_candidates
except ImportError:
    from python.rp_app.continuity_resolved_outcomes import (
        extract_sleeping_surface_candidates,
    )

try:
    from continuity_state import ConsequenceCategory, DetectedConsequence
except ImportError:
    from python.rp_app.continuity_state import ConsequenceCategory, DetectedConsequence

from continuity_consequence_classifier_regexes import (
    ACCESS_GRANTED_CAN_WORD,
    AGREEMENT_BOUNDARY_WORDS,
    COMMITMENT_WILL_WORD,
    REFUSAL_LEGACY_NO_OR_NOT_WORD,
)


def detect_agreement(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    goal: str,
    tactic: str,
) -> list[DetectedConsequence]:
    """Detect agreement, refusal, and commitment patterns."""
    results = []

    # REFUSAL: (resist OR challenge) intent from goal/tactic AND (dialogue OR strong intent)
    intent_refusal = intent["resist"] or intent["challenge"]
    combined_gt = f"{goal} {tactic}"
    if intent_refusal:
        legacy_short = bool(REFUSAL_LEGACY_NO_OR_NOT_WORD.search(dialogue))
        legacy_other = any(
            ref in dialogue
            for ref in classifier.REFUSAL_LEGACY_DIALOGUE_MARKERS
            if ref not in ("no", "not")
        )
        legacy_hit = legacy_short or legacy_other
        curated_hit = any(tok in dialogue for tok in classifier.REFUSAL_DIALOGUE_MARKERS)
        strong_intent_hit = any(
            tok in combined_gt for tok in classifier.REFUSAL_STRONG_INTENT_MARKERS
        )
        if legacy_hit or curated_hit or strong_intent_hit:
            results.append(
                DetectedConsequence(
                    category=ConsequenceCategory.REFUSAL,
                    confidence="strong",
                    source_fields=["motivation.goal", "motivation.tactic", "dialogue"],
                    excerpt=dialogue[:80] or action[:80],
                )
            )

    # AGREEMENT: comply intent + explicit acceptance language
    if intent["comply"] and (
        AGREEMENT_BOUNDARY_WORDS.search(dialogue) or "accept" in dialogue
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.AGREEMENT,
                confidence="strong",
                source_fields=["motivation.goal", "dialogue"],
                excerpt=dialogue[:80],
            )
        )

    # COMMITMENT: control intent + future-oriented language
    if intent["control"] and (
        COMMITMENT_WILL_WORD.search(dialogue)
        or any(com in dialogue for com in ["promise", "commit", "shall"])
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.COMMITMENT,
                confidence="moderate",
                source_fields=["motivation.goal", "dialogue"],
                excerpt=dialogue[:80],
            )
        )

    return results


def detect_structured_sleeping_assignment(
    classifier: Any,
    *,
    move: dict[str, Any],
    scene_state: dict[str, Any] | None,
    goal: str,
    tactic: str,
    action: str,
    dialogue: str,
) -> list[DetectedConsequence]:
    candidates, _ = extract_sleeping_surface_candidates(move, scene_state)
    if len(candidates) != 1:
        return []

    combined = f"{goal} {tactic} {action} {dialogue}".lower()
    if any(
        token in combined
        for token in ("maybe", "might", "guess", "suggest", "option", "?")
    ):
        return []

    results: list[DetectedConsequence] = []
    if any(
        token in combined
        for token in (
            "settle",
            "assign",
            "decide",
            "plan",
            "commit",
            "take the",
            "sleep tonight",
            "sleeps tonight",
            "that's the plan",
            "actual plan",
        )
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.DECISION_MADE,
                confidence="strong",
                source_fields=[
                    "scene_state_updates.sleeping_surface_assignment",
                    "motivation.goal",
                    "motivation.tactic",
                ],
                excerpt=dialogue[:80] or action[:80],
            )
        )
    if any(token in combined for token in ("tonight", "will", "plan", "commit")):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.PLAN_COMMITTED,
                confidence="moderate",
                source_fields=[
                    "scene_state_updates.sleeping_surface_assignment",
                    "motivation.goal",
                    "motivation.tactic",
                ],
                excerpt=dialogue[:80] or action[:80],
            )
        )
    return results


def detect_access(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
) -> list[DetectedConsequence]:
    """Detect access granted/denied patterns."""
    results = []

    # Same phrases for denied and for suppressing false "enter" grant evidence.
    access_denial_markers = (
        "can't",
        "can\u2019t",
        "cannot",
        "not allowed",
        "stay out",
        "no access",
    )
    denial_in_dialogue = any(m in dialogue for m in access_denial_markers)

    # ACCESS_DENIED: control/resist intent + blocking language
    if (intent["control"] or intent["resist"]) and denial_in_dialogue:
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.ACCESS_DENIED,
                confidence="strong",
                source_fields=["motivation.goal", "dialogue"],
                excerpt=dialogue[:80],
            )
        )

    # ACCESS_GRANTED: control/comply intent + permission language
    enter_grant_evidence = "enter" in dialogue and not denial_in_dialogue
    if (intent["control"] or intent["comply"]) and (
        ACCESS_GRANTED_CAN_WORD.search(dialogue)
        or any(allow in dialogue for allow in ["allowed", "permission", "go ahead"])
        or enter_grant_evidence
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.ACCESS_GRANTED,
                confidence="moderate",
                source_fields=["motivation.goal", "dialogue"],
                excerpt=dialogue[:80],
            )
        )

    return results


def detect_information(
    classifier: Any,
    character: str,
    intent: dict[str, bool],
    behavior: dict[str, bool],
    action: str,
    dialogue: str,
    goal: str,
    tactic: str,
) -> list[DetectedConsequence]:
    """Detect revelation and concealment patterns."""
    results = []

    # REVELATION: goal/tactic mentions revealing truth
    if any(
        rev in f"{goal} {tactic}"
        for rev in ["reveal", "truth", "admit", "confess", "disclose"]
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.REVELATION,
                confidence="moderate",
                source_fields=["motivation.goal", "motivation.tactic"],
                excerpt=f"{goal[:60]}...",
            )
        )

    # CONCEALMENT: goal/tactic mentions hiding or deception
    if any(
        con in f"{goal} {tactic}"
        for con in ["conceal", "hide", "keep secret", "not reveal"]
    ):
        results.append(
            DetectedConsequence(
                category=ConsequenceCategory.CONCEALMENT,
                confidence="moderate",
                source_fields=["motivation.goal", "motivation.tactic"],
                excerpt=f"{goal[:60]}...",
            )
        )

    return results
