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
# If a long/medium-term anchor names a strong off-site setting absent from current scene
# context, skip binding drift checks to that anchor (cross-session / canon bleed).
_OFFSITE_SETTING_LEXEMES = frozenset(
    {
        "arkham",
        "asylum",
        "gotham",
        "penitentiary",
        "cellblock",
        "straitjacket",
        "jailhouse",
        "blackgate",
    }
)

MIN_DIALOGUE_WORDS_FOR_VOICE_DRIFT = 8

_VOICE_MARKER_FAMILY = ("measured", "cool", "calm", "controlled")
_SPEECH_MARKER_FAMILY = ("spare", "clipped", "blunt", "formal")


def _identity_profile_blob(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict) or not profile:
        return ""
    parts = [str(v).strip() for v in profile.values() if str(v).strip()]
    return " ".join(parts).lower()


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


def _scene_context_blob(scene_state: dict[str, Any] | None) -> str:
    if not isinstance(scene_state, dict):
        return ""
    parts = [
        scene_state.get("location", "") or "",
        scene_state.get("environment_description", "") or "",
        scene_state.get("scene_premise", "") or "",
        scene_state.get("premise", "") or "",
        scene_state.get("opening_situation", "") or "",
        scene_state.get("scene_title", "") or "",
    ]
    return " ".join(parts).lower()


def _offsite_lexemes_in_text(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z]{4,}", str(text or "").lower())
        if token in _OFFSITE_SETTING_LEXEMES
    }


def _anchor_goal_applies_to_scene(
    anchor_goal: str, scene_state: dict[str, Any] | None
) -> bool:
    """False when anchor names an off-site setting not reflected in current scene text."""
    blob = _scene_context_blob(scene_state)
    if not blob.strip():
        return True
    anchor_offsites = _offsite_lexemes_in_text(anchor_goal)
    if not anchor_offsites:
        return True
    scene_offsites = _offsite_lexemes_in_text(blob)
    return bool(anchor_offsites.intersection(scene_offsites))


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
    scene_state: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    wrong_pov, pov_reason = contains_wrong_character_pov(content, speaker)
    if wrong_pov:
        return True, pov_reason

    if state is None:
        return False, ""

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    candidate_goal = str(motivation.get("goal", "") or "")
    anchor_goals = [
        goal
        for goal in state.core_goals
        if goal and _anchor_goal_applies_to_scene(goal, scene_state)
    ]
    if state.long_term_goal and _anchor_goal_applies_to_scene(
        state.long_term_goal, scene_state
    ):
        anchor_goals.append(state.long_term_goal)
    if state.medium_term_goal and _anchor_goal_applies_to_scene(
        state.medium_term_goal, scene_state
    ):
        anchor_goals.append(state.medium_term_goal)

    for anchor_goal in anchor_goals:
        if goal_conflicts_with_identity_anchor(candidate_goal, anchor_goal):
            return True, f"Move goal conflicts with stable goal anchor: '{anchor_goal}'"

    if isinstance(move, dict):
        dialogue = str(move.get("dialogue") or "").strip()
        voice_blob = _identity_profile_blob(
            state.voice_profile if isinstance(state.voice_profile, dict) else None
        )
        speech_blob = _identity_profile_blob(
            state.speech_fingerprint
            if isinstance(state.speech_fingerprint, dict)
            else None
        )
        voice_family_hit = any(m in voice_blob for m in _VOICE_MARKER_FAMILY)
        speech_family_hit = any(m in speech_blob for m in _SPEECH_MARKER_FAMILY)
        if (
            dialogue
            and _dialogue_word_count(dialogue) >= MIN_DIALOGUE_WORDS_FOR_VOICE_DRIFT
            and (voice_family_hit or speech_family_hit)
        ):
            voice_msg = _dialogue_breaks_voice_profile(
                dialogue, voice_blob, speech_blob
            )
            if voice_msg:
                return True, voice_msg

        reaction_blob = _identity_profile_blob(
            state.reaction_profile if isinstance(state.reaction_profile, dict) else None
        )
        if reaction_blob:
            reaction_msg = _move_conflicts_with_reaction_profile(move, reaction_blob)
            if reaction_msg:
                return True, reaction_msg

    return False, ""
