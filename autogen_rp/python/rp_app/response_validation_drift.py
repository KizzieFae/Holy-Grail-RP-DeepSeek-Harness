import re
from typing import Any

from character_state import CharacterState

GOAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "of",
    "for",
    "with",
    "my",
    "our",
    "your",
    "their",
    "his",
    "her",
    "this",
    "that",
    "now",
}
PROTECTIVE_GOAL_TERMS = {"protect", "save", "defend", "keep", "preserve", "guard"}
DESTRUCTIVE_GOAL_TERMS = {"destroy", "burn", "abandon", "betray", "sabotage", "ruin"}
REVEALING_GOAL_TERMS = {"expose", "reveal", "uncover", "confess", "admit"}
CONCEALING_GOAL_TERMS = {"hide", "conceal", "cover", "deny", "bury"}
MEDICAL_STABILIZATION_CONTEXT_TERMS = {
    "antiseptic",
    "bandage",
    "bleeding",
    "blood",
    "cut",
    "doctor",
    "heal",
    "healing",
    "hurt",
    "hurting",
    "pain",
    "painful",
    "raw",
    "sting",
    "stinging",
    "wound",
}
TACTICAL_STABILIZATION_GOAL_TERMS = {
    "assist",
    "breathe",
    "breathing",
    "care",
    "cooperate",
    "cooperation",
    "comply",
    "compliance",
    "endure",
    "enduring",
    "heal",
    "healing",
    "maintain",
    "manage",
    "reassure",
    "recover",
    "recovery",
    "respond",
    "responsive",
    "rest",
    "stabilize",
    "stability",
    "steady",
    "steadying",
    "survive",
    "survival",
    "treat",
    "treatment",
}


def contains_wrong_character_pov(content: str, speaker: str) -> tuple[bool, str]:
    content_lower = content.strip().lower()
    speaker_lower = speaker.lower()

    if len(content_lower) < 20:
        return False, ""

    self_reference_patterns = [
        rf"{re.escape(speaker_lower)}['\"]?s\s+(?:eyes|gaze|hand|fingers|posture|expression|voice|tone)",
        rf"{re.escape(speaker_lower)}\s+(?:took|looked|glanced|turned|walked|stepped|sat|stood|moved)",
    ]

    for pattern in self_reference_patterns:
        match = re.search(pattern, content_lower)
        if match:
            return (
                True,
                f"Character refers to self in third person: '{match.group(0)}' - should use first person for self-reference (I/me/my) or just describe the action",
            )

    return False, ""


def _extract_goal_terms(text: str) -> tuple[set[str], set[str]]:
    normalized = str(text or "").lower()
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z']+", normalized)
        if len(token) > 2 and token not in GOAL_STOPWORDS
    }
    return tokens, {
        token
        for token in tokens
        if token in PROTECTIVE_GOAL_TERMS
        or token in DESTRUCTIVE_GOAL_TERMS
        or token in REVEALING_GOAL_TERMS
        or token in CONCEALING_GOAL_TERMS
    }


def _has_medical_burn_context(candidate_tokens: set[str]) -> bool:
    return "burn" in candidate_tokens and bool(
        candidate_tokens.intersection(MEDICAL_STABILIZATION_CONTEXT_TERMS)
    )


def _is_temporary_tactical_goal(
    candidate_tokens: set[str], candidate_polarity: set[str]
) -> bool:
    if not candidate_tokens:
        return False
    destructive_polarity = set(candidate_polarity).intersection(DESTRUCTIVE_GOAL_TERMS)
    if "burn" in destructive_polarity and _has_medical_burn_context(candidate_tokens):
        destructive_polarity.discard("burn")
    if destructive_polarity:
        return False
    if candidate_polarity.intersection(CONCEALING_GOAL_TERMS):
        return False
    return bool(candidate_tokens.intersection(TACTICAL_STABILIZATION_GOAL_TERMS))


def goal_conflicts_with_identity_anchor(candidate_goal: str, anchor_goal: str) -> bool:
    candidate_tokens, candidate_polarity = _extract_goal_terms(candidate_goal)
    anchor_tokens, anchor_polarity = _extract_goal_terms(anchor_goal)
    if _is_temporary_tactical_goal(candidate_tokens, candidate_polarity):
        return False
    shared_subject_terms = {
        token
        for token in candidate_tokens.intersection(anchor_tokens)
        if token not in PROTECTIVE_GOAL_TERMS
        and token not in DESTRUCTIVE_GOAL_TERMS
        and token not in REVEALING_GOAL_TERMS
        and token not in CONCEALING_GOAL_TERMS
    }
    if not shared_subject_terms:
        return False
    if candidate_polarity.intersection(
        DESTRUCTIVE_GOAL_TERMS
    ) and anchor_polarity.intersection(PROTECTIVE_GOAL_TERMS):
        return True
    if candidate_polarity.intersection(
        CONCEALING_GOAL_TERMS
    ) and anchor_polarity.intersection(REVEALING_GOAL_TERMS):
        return True
    return False


def _dialogue_word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", str(text or "")))


def _dialogue_breaks_voice_profile(
    dialogue: str,
    voice_markers: str,
    speech_markers: str,
) -> str:
    word_count = _dialogue_word_count(dialogue)
    if any(
        marker in voice_markers for marker in ["measured", "cool", "calm", "controlled"]
    ):
        if dialogue.count("!") >= 3 or re.search(r"\b[A-Z]{4,}\b", dialogue):
            return "Dialogue intensity conflicts with stable voice profile"
    if any(marker in speech_markers for marker in ["spare", "clipped", "blunt"]):
        if word_count > 45:
            return "Dialogue length conflicts with stable speech fingerprint"
    if "formal" in speech_markers:
        if re.search(r"\b(?:gonna|ain't|yeah|nah|wanna)\b", dialogue.lower()):
            return "Dialogue diction conflicts with stable speech fingerprint"
    return ""


def _move_conflicts_with_reaction_profile(
    move: dict[str, Any] | None,
    reaction_markers: str,
) -> str:
    if not isinstance(move, dict):
        return ""
    motivation = (
        move.get("motivation", {}) if isinstance(move.get("motivation"), dict) else {}
    )
    tactic = str(motivation.get("tactic", "") or "").lower()
    emotional_driver = str(motivation.get("emotional_driver", "") or "").lower()
    if any(
        marker in reaction_markers
        for marker in ["guarded", "controlled", "narrows focus", "withdraw"]
    ):
        if any(token in tactic for token in ["rant", "explode", "blurt", "babble"]):
            return "Move tactic conflicts with stable reaction profile"
        if emotional_driver in ["panic", "hysteria"]:
            return "Emotional driver conflicts with stable reaction profile"
    return ""


def detect_character_drift(
    content: str,
    speaker: str,
    state: CharacterState | None = None,
    move: dict[str, Any] | None = None,
    canon_anchors: list[Any] | None = None,
) -> tuple[bool, str]:
    wrong_pov, pov_reason = contains_wrong_character_pov(content, speaker)
    if wrong_pov:
        return True, pov_reason

    if state is None:
        return False, ""

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    candidate_goal = str(motivation.get("goal", "") or "")
    anchor_goals = [goal for goal in state.core_goals if goal]
    if state.long_term_goal:
        anchor_goals.append(state.long_term_goal)
    if state.medium_term_goal:
        anchor_goals.append(state.medium_term_goal)

    for anchor_goal in anchor_goals:
        if goal_conflicts_with_identity_anchor(candidate_goal, anchor_goal):
            return True, f"Move goal conflicts with stable goal anchor: '{anchor_goal}'"

    return False, ""
