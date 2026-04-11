import re
from typing import Any

_BOUNDARY_LOCATION_TERMS = {
    "hall",
    "hallway",
    "corridor",
    "stairwell",
    "stairs",
    "staircase",
    "landing",
    "elevator",
    "lobby",
    "outside",
    "outdoors",
    "street",
    "sidewalk",
    "parking lot",
    "parking garage",
    "driveway",
    "yard",
    "porch",
    "balcony",
    "roof",
}
# Single token "exit" removed: it matches doorway vocabulary and verb "exit" in soft
# heuristics, producing false positives next to movement/boundary terms.
_BOUNDARY_STRUCTURE_TERMS = {
    "door",
    "doorway",
    "threshold",
    "gate",
    "entrance",
    "stairwell door",
    "front door",
    "back door",
    "fire exit",
    "emergency exit",
}
_MOVEMENT_TERMS = {
    "leave",
    "left",
    "leaving",
    "exit",
    "exited",
    "exiting",
    "depart",
    "departed",
    "departing",
    "walk",
    "walked",
    "walking",
    "step",
    "stepped",
    "stepping",
    "storm",
    "stormed",
    "storms",
    "stalk",
    "stalked",
    "headed",
    "go",
    "going",
    "went",
    "move",
    "moved",
    "moving",
    "retreat",
    "retreated",
    "descend",
    "descended",
    "descends",
    "spin",
    "spun",
    "spins",
    "rush",
    "rushed",
    "run",
    "ran",
    "race",
    "raced",
}
_DEPARTURE_COMPLETION_TERMS = {
    "behind her",
    "behind him",
    "behind them",
    "without looking back",
    "out of sight",
    "shut behind",
    "swing shut",
    "closed behind",
    "down the hallway",
    "down the hall",
    "downstairs",
    "descended",
    "outside the room",
    "outside the dorm",
    "outside the building",
    "out of the room",
    "out of the dorm",
    "out of the building",
}
# In-room / adjacent sub-areas: movement here must not trigger soft exit alone.
_INTERIOR_SUBSCENE_TERMS = {
    "kitchenette",
    "kitchen",
    "bathroom",
    "restroom",
    "shower",
    "sink",
    "counter",
    "refrigerator",
    "fridge",
    "pantry",
    "microwave",
    "stove",
    "cupboard",
    "closet",
    "wardrobe",
}
_INTERNAL_REPOSITION_TERMS = {
    "across the room",
    "within the room",
    "inside the room",
    "moved closer",
    "step closer",
    "stepped closer",
    "turned away",
    "turns away",
    "spun away",
    "spin away",
    "pacing",
    "paced",
    "repositioned",
    "stepped back",
    "moves between",
    "stood between",
    "moved in front",
    "backed toward the door",
    "to the doorway",
    "toward the door",
    "toward the hallway",
    "toward the hall",
    "into the hallway",
    "into the hall",
    "skipped toward",
    "bouncing toward",
    "toward the kitchenette",
    "toward the kitchen",
    "to the kitchenette",
    "to the kitchen",
    "toward the bathroom",
    "to the bathroom",
    "toward the counter",
    "to the counter",
    "pushed off the wall",
    "leaned against the wall",
    "leaning against the wall",
}
_LOCATION_STOPWORDS = {
    "the",
    "and",
    "room",
    "suite",
    "building",
    "house",
    "apartment",
    "college",
    "university",
    "hall",
}

# Door closed behind another person / object — not the actor leaving.
_DOOR_SHUT_BEHIND_OTHER_RE = re.compile(
    r"(?:slammed|slam|slamming|shut|shuts|shutting|closed|closes|closing)\s+(?:the\s+)?(?:door|doors)\s+"
    r"(?:shut\s+)?behind\s+(?:the\s+)?(?:omega|them|him|her|they|guest|visitor|newcomer|newcomers|student)\b",
    re.IGNORECASE,
)

# Time / bathroom / release idioms — not scene departure.
_OUT_NON_DEPARTURE_IDIOM_RE = re.compile(
    r"(?:"
    r"\bout\s+in\s+\d+"
    r"|"
    r"\bnot\s+out\s+yet\b"
    r"|"
    r"\bout\s+of\s+the\s+bathroom\b"
    r"|"
    r"\bcoming\s+out\s+of\s+the\s+bathroom\b"
    r"|"
    r"\bif\s+you\s*'?(?:re|are)\s+not\s+out\b"
    r")",
    re.IGNORECASE,
)

_STRONG_REMOVAL_PHRASE_RES = (
    re.compile(r"\bget\s+out\s+of\s+(?:here|this\s+room|my\s+room|my\s+space|the\s+room)\b", re.I),
    re.compile(r"\bout\s+of\s+here\b", re.I),
    re.compile(r"\bout\s+of\s+this\s+room\b", re.I),
    re.compile(r"\bout\s+of\s+my\s+(?:room|space|face)\b", re.I),
    re.compile(r"\bkick\s+(?:him|her|them)\s+out\b", re.I),
    re.compile(r"\bthrow\s+(?:him|her|them)\s+out\b", re.I),
)


def _authored_text_parts(
    move: dict[str, Any] | None,
) -> tuple[str, str, str]:
    """Action+dialogue (direct), goal+tactic (motivation), and combined — all lowercased.

    Omits ``state_changes`` and ``presence_changes``: those may echo templated issue
    text (e.g. 'must exit') and are not reliable departure signals.
    """
    if not isinstance(move, dict):
        return "", "", ""
    motivation = (
        move.get("motivation", {})
        if isinstance(move.get("motivation", {}), dict)
        else {}
    )
    action = str(move.get("action", "") or "").strip()
    dialogue = str(move.get("dialogue", "") or "").strip()
    goal = str(motivation.get("goal", "") or "").strip()
    tactic = str(motivation.get("tactic", "") or "").strip()
    direct_raw = " ".join(part for part in (action, dialogue) if part)
    motivation_raw = " ".join(part for part in (goal, tactic) if part)
    combined_raw = " ".join(part for part in (direct_raw, motivation_raw) if part)
    return direct_raw.lower(), motivation_raw.lower(), combined_raw.lower()


def _extract_scene_anchor_terms(scene_state: dict[str, Any] | None) -> set[str]:
    if not isinstance(scene_state, dict):
        return set()
    raw_location = str(scene_state.get("location", "") or "").lower()
    raw_environment = str(scene_state.get("environment_description", "") or "").lower()
    tokens = set(re.findall(r"[a-z]{4,}", f"{raw_location} {raw_environment}"))
    return {token for token in tokens if token not in _LOCATION_STOPWORDS}


def _contains_any(text: str, terms: set[str]) -> bool:
    for term in terms:
        if " " in term:
            if term in text:
                return True
            continue

        if re.search(rf"\b{re.escape(term)}\b", text):
            return True

    return False


# Explicit departure in *embodied* prose: action and/or dialogue only (not motivation alone).
_EXPLICIT_DEPARTURE_RE = re.compile(
    r"\b(?:walk(?:ed|ing)?\s+out|storms?\s+out|stormed\s+out|storming\s+out|head(?:ed|ing)?\s+out|left\s+(?:the\s+)?(?:room|scene|dorm|building|apartment|house|hallway|hall|doorway|door|threshold|outside|outdoors)|(?:leave|leaving|exit|exited|exiting|depart(?:ed|ing)?)\s+(?:the\s+)?(?:room|scene|dorm|building|apartment|house|hallway|hall|doorway|door|threshold|outside|outdoors|here)|(?:i|i'm|im|we|we're|were|she|he|they)\s+(?:am\s+|are\s+|is\s+)?(?:leaving|exiting|departing))\b",
)

# Directed command / ultimatum / hypothetical: speaker is not describing *their own* embodied exit.
_DEPARTURE_DIRECTED_OR_ULTIMATUM_RE = re.compile(
    r"(?:"
    r"\b(?:walk|walked|walking|head|headed|heading)\s+out\b\s*(?:,\s*)?\s*or\b"
    r"|"
    r"\b(?:walk|walked|walking|head|headed|heading)\s+out\b\s+or\s+(?:i|i['\u2019]?m|i['\u2019]?ll|we|we['\u2019]?re|we['\u2019]?ll|else)\b"
    r"|"
    r"\byou(?:'d|['\u2019]d)?\s+(?:better\s+)?(?:walk|head|storm)\s+out\b"
    r"|"
    r"\b(?:walk|head|storm)\s+out\s*,\s*you\b"
    r"|"
    r"\bif\s+you\s+(?:walk|head|get)\s+out\b"
    r"|"
    r"\b(?:unless|until)\s+you\s+(?:leave|walk|go)\b"
    r")",
    re.IGNORECASE,
)

_FIRST_PERSON_DEPARTURE_COMMITMENT_RE = re.compile(
    r"(?:"
    r"\b(?:i|i'm|im|we|we're|we)\s+(?:am\s+|are\s+)?(?:leaving|exiting|departing|walking\s+out|heading\s+out)\b"
    r"|"
    r"\b(?:i|i've|i)\s+(?:left|walked\s+out|headed\s+out)\b"
    r"|"
    r"\bleft\s+(?:the\s+)?(?:room|scene|dorm|building|apartment|house|hallway|hall|doorway|door|threshold|outside|outdoors)\b"
    r")",
    re.IGNORECASE,
)


# Rhetorical / conditional / coercive toward another party — not embodied self-departure (Issue #18).
# Uses action+dialogue only (see ``_authored_text_parts``); motivation alone cannot suppress.
_RHETORICAL_OR_CONDITIONAL_PHYSICAL_DEPARTURE_SUPPRESSION_RE = re.compile(
    r"(?:"
    r"\byou\s+think\b.{0,240}?\bwalk(?:ed|ing)?\s+out\b"
    r"|"
    r"\bfine\.\s+walk\."
    r"|"
    r"\bso\s+if\s+you\s+want\s+to\s+withdraw,\s*withdraw\b"
    r"|"
    r"\bif\s+you\s+want\s+to\s+withdraw,\s*withdraw\b"
    r"|"
    r"\bif\s+you\s+want\s+to\s+withdraw\b"
    r")",
    re.IGNORECASE,
)


def authored_prose_suppresses_physical_departure(move: dict[str, Any] | None) -> bool:
    """True when authored action/dialogue uses exit wording rhetorically or toward others.

    Deterministic guard: does **not** inspect ``presence_changes`` / ``state_changes`` on the move.
    """
    direct_text, _, _ = _authored_text_parts(move)
    if not str(direct_text).strip():
        return False
    return bool(_RHETORICAL_OR_CONDITIONAL_PHYSICAL_DEPARTURE_SUPPRESSION_RE.search(direct_text))


def _authored_departure_reads_as_directed_or_hypothetical(direct_text: str) -> bool:
    """True when exit-like wording commands another, threatens, or is conditional — not self-exit."""
    if not direct_text or not direct_text.strip():
        return False
    return bool(_DEPARTURE_DIRECTED_OR_ULTIMATUM_RE.search(direct_text))


def _authored_has_first_person_departure_commitment(direct_text: str) -> bool:
    """True when the speaker clearly commits to leaving (first person or completed exit)."""
    if not direct_text or not direct_text.strip():
        return False
    return bool(_FIRST_PERSON_DEPARTURE_COMMITMENT_RE.search(direct_text))


# Prohibition: "no walking out" is not an embodied self-exit for the speaker.
_NEGATED_WALKING_OUT_PROHIBITION_RE = re.compile(
    r"\b(?:no|not|never|without)\s+walk(?:ing|ed)?\s+out\b",
    re.IGNORECASE,
)


def _negated_walking_out_spans(direct_text: str) -> list[tuple[int, int]]:
    return [
        (m.start(), m.end())
        for m in _NEGATED_WALKING_OUT_PROHIBITION_RE.finditer(direct_text)
    ]


def _explicit_departure_matches_after_negation_skip(direct_text: str) -> list[re.Match]:
    """``_EXPLICIT_DEPARTURE_RE`` hits that are not inside a negated *walking out* prohibition."""
    spans = _negated_walking_out_spans(direct_text)
    out: list[re.Match[str]] = []
    for m in _EXPLICIT_DEPARTURE_RE.finditer(direct_text):
        if any(m.start() < end and m.end() > start for start, end in spans):
            continue
        out.append(m)
    return out


def has_hard_scene_departure_evidence(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> bool:
    """True only for clear, authored departure (action/dialogue), not heuristics.

    Does **not** treat ``presence_changes`` or ``state_changes`` as hard evidence: those
    can be model- or template-injected and are not more trustworthy than generic tags.

    Explicit wording in action/dialogue always wins over in-room reposition cues in the
    same line.

    ``scene_state`` is reserved for future use (e.g. anchor phrases).
    """
    _ = scene_state
    direct_text, _, combined_authored = _authored_text_parts(move)
    if not direct_text and not combined_authored:
        return False

    if "left the immediate scene" in combined_authored:
        return True

    explicit_after_skip = _explicit_departure_matches_after_negation_skip(direct_text)
    if explicit_after_skip:
        blocked = _authored_departure_reads_as_directed_or_hypothetical(
            direct_text
        ) or authored_prose_suppresses_physical_departure(move)
        if blocked and not _authored_has_first_person_departure_commitment(direct_text):
            pass
        else:
            return True

    if _contains_any(direct_text, _INTERNAL_REPOSITION_TERMS):
        return False

    return False


def _soft_departure_intent_in_authored(move: dict[str, Any] | None) -> bool:
    """Intent phrases using only action, dialogue, goal, tactic — not structured lists."""
    _, _, combined = _authored_text_parts(move)
    if not combined:
        return False
    return _contains_any(
        combined,
        {
            "leave",
            "leaving",
            "left ",
            "exit",
            "exiting",
            "exited",
            "depart",
            "departing",
            "departed",
            "withdraw",
            "walk out",
            "head out",
            "walked out",
            "headed out",
            "stormed out",
            "storms out",
            "storm out",
        },
    )


def _direct_has_embodied_departure_cue(direct_text: str) -> bool:
    """Primary embodied signals must appear in action/dialogue (not motivation alone)."""
    if not direct_text.strip():
        return False
    embodied_terms = (
        _MOVEMENT_TERMS
        | _BOUNDARY_STRUCTURE_TERMS
        | _BOUNDARY_LOCATION_TERMS
        | _DEPARTURE_COMPLETION_TERMS
    )
    return _contains_any(direct_text, embodied_terms)


def _soft_exit_blocked_door_shut_behind_other(direct_text: str) -> bool:
    if not direct_text.strip():
        return False
    if not _DOOR_SHUT_BEHIND_OTHER_RE.search(direct_text):
        return False
    if _FIRST_PERSON_DEPARTURE_COMMITMENT_RE.search(direct_text):
        return False
    if _EXPLICIT_DEPARTURE_RE.search(direct_text) and not _authored_departure_reads_as_directed_or_hypothetical(
        direct_text
    ):
        return False
    return True


def _soft_exit_blocked_interior_local_move(direct_text: str, combined_authored: str) -> bool:
    """Interior subscene movement without leaving the shared space."""
    if not direct_text.strip():
        return False
    if not _contains_any(direct_text, _INTERIOR_SUBSCENE_TERMS) and not _contains_any(
        direct_text, _INTERNAL_REPOSITION_TERMS
    ):
        return False
    # Explicit leave of room/building in direct text overrides.
    leave_markers = (
        "out of the room",
        "out of the dorm",
        "out of the building",
        "outside the room",
        "left the room",
        "left the dorm",
        "walked out",
        "headed out",
        "storms out",
        "stormed out",
    )
    if any(m in direct_text for m in leave_markers):
        return False
    if _EXPLICIT_DEPARTURE_RE.search(direct_text):
        return False
    # Motivation may support but not independently trigger: need embodied boundary in direct.
    if _contains_any(combined_authored, _BOUNDARY_LOCATION_TERMS) and _contains_any(
        combined_authored, _DEPARTURE_COMPLETION_TERMS
    ):
        return False
    return True


def _soft_exit_blocked_out_idioms(combined_authored: str, direct_text: str) -> bool:
    if _OUT_NON_DEPARTURE_IDIOM_RE.search(combined_authored):
        for rx in _STRONG_REMOVAL_PHRASE_RES:
            if rx.search(combined_authored):
                return False
        if _EXPLICIT_DEPARTURE_RE.search(direct_text):
            return False
        if _FIRST_PERSON_DEPARTURE_COMMITMENT_RE.search(direct_text):
            return False
        return True
    return False


def _soft_exit_false_positive(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> bool:
    """In-room or idiomatic prose that must not count as soft scene exit."""
    if not isinstance(move, dict):
        return True
    direct_text, _, combined = _authored_text_parts(move)
    if _soft_exit_blocked_door_shut_behind_other(direct_text):
        return True
    if _soft_exit_blocked_interior_local_move(direct_text, combined):
        return True
    if _soft_exit_blocked_out_idioms(combined, direct_text):
        return True
    leaves_anchor = _leaves_scene_anchor_authored(
        combined_authored=combined, scene_state=scene_state
    )
    if not _direct_has_embodied_departure_cue(direct_text) and not leaves_anchor:
        return True
    return False


def _leaves_scene_anchor_authored(
    *,
    combined_authored: str,
    scene_state: dict[str, Any] | None,
) -> bool:
    if not combined_authored:
        return False
    scene_anchor_terms = _extract_scene_anchor_terms(scene_state)
    return any(
        re.search(
            rf"\b(?:outside|out of|away from|beyond)\s+the\s+{re.escape(term)}\b",
            combined_authored,
        )
        for term in scene_anchor_terms
    )


def _detect_exit_soft_movement_boundary(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> bool:
    """Tightened soft path: movement/setting cues require completion or anchor leave."""
    direct_text, _, combined_authored = _authored_text_parts(move)
    if not direct_text.strip():
        return False

    has_movement = _contains_any(combined_authored, _MOVEMENT_TERMS)
    has_boundary_location = _contains_any(combined_authored, _BOUNDARY_LOCATION_TERMS)
    has_boundary_structure = _contains_any(combined_authored, _BOUNDARY_STRUCTURE_TERMS)
    has_departure_completion = _contains_any(
        combined_authored, _DEPARTURE_COMPLETION_TERMS
    )
    has_soft_intent = _soft_departure_intent_in_authored(move)

    if _contains_any(direct_text, _INTERNAL_REPOSITION_TERMS):
        return False

    leaves_anchor = _leaves_scene_anchor_authored(
        combined_authored=combined_authored, scene_state=scene_state
    )

    soft_positive = False
    if (
        has_movement
        and has_boundary_location
        and has_departure_completion
    ):
        soft_positive = True

    if (has_boundary_structure and has_departure_completion) or leaves_anchor:
        if has_movement or has_boundary_location:
            soft_positive = True

    if (
        has_soft_intent
        and has_boundary_location
        and has_departure_completion
    ):
        soft_positive = True

    if not soft_positive:
        return False

    if _soft_exit_false_positive(move, scene_state):
        return False

    return True


# Narrow re-entry: spatial return into the immediate scene (no vague "came back").
_REENTRY_DIRECT_RE = re.compile(
    r"\b(?:"
    r"walked\s+back\s+into\s+(?:the\s+)?(?:room|dorm|suite|apartment|building)"
    r"|stepped\s+back\s+into\s+(?:the\s+)?(?:room|dorm|suite|apartment)"
    r"|re-?entered\s+(?:the\s+)?(?:room|dorm|suite|apartment|building)"
    r"|returned\s+to\s+the\s+(?:room|dorm|suite|apartment)"
    r"|back\s+through\s+the\s+door(?:way)?\s+(?:into|to)\s+the\s+(?:room|dorm|suite)"
    r"|entered\s+(?:the\s+)?(?:room|dorm|suite)\s+again"
    r")\b",
    re.IGNORECASE,
)

_STRUCTURED_REENTRY_CHANGES = frozenset({"entry", "return", "reenter", "re-entry"})


def structured_presence_exit_for_character(move: dict[str, Any] | None, character_id: str) -> bool:
    """True when move includes a validated structured exit for this character."""
    if not isinstance(move, dict) or not str(character_id or "").strip():
        return False
    for item in move.get("presence_changes") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("change", "") or "").lower() != "exit":
            continue
        if str(item.get("character", "") or "").strip() == character_id:
            return True
    return False


def structured_presence_reentry_for_character(move: dict[str, Any] | None, character_id: str) -> bool:
    """True when move includes structured re-entry for this character (any speaker)."""
    if not isinstance(move, dict) or not str(character_id or "").strip():
        return False
    for item in move.get("presence_changes") or []:
        if not isinstance(item, dict):
            continue
        chg = str(item.get("change", "") or "").lower().replace("_", "-")
        if chg not in _STRUCTURED_REENTRY_CHANGES:
            continue
        if str(item.get("character", "") or "").strip() == character_id:
            return True
    return False


def has_scene_reentry_evidence(move: dict[str, Any] | None) -> bool:
    """True when authored action/dialogue describes re-entering the immediate scene."""
    direct_text, _, _ = _authored_text_parts(move)
    if not direct_text.strip():
        return False
    return bool(_REENTRY_DIRECT_RE.search(direct_text))


def detect_exit_from_scene(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
    acting_character: str | None = None,
) -> bool:
    """True if the turn describes actually leaving the immediate scene.

    Hard evidence (explicit wording / system phrase in authored text) wins first; soft
    path requires completion or clear anchor-leave, actor-relative false-positive filters,
    and embodied cues in action/dialogue (motivation may support but not trigger alone).

    ``acting_character`` is used for future narrowing; soft false positives are filtered
    regardless when prose matches in-room / door-control patterns.
    """
    _ = acting_character
    if has_hard_scene_departure_evidence(move, scene_state):
        return True
    return _detect_exit_soft_movement_boundary(move, scene_state)


def dialogue_has_territorial_removal_language(dialogue_lower: str) -> bool:
    """True only for deterministic removal phrases (not bare 'out' or 'my')."""
    if not dialogue_lower.strip():
        return False
    for rx in _STRONG_REMOVAL_PHRASE_RES:
        if rx.search(dialogue_lower):
            return True
    if re.search(r"\bget\s+out\b", dialogue_lower) and re.search(
        r"\b(?:here|room|face)\b", dialogue_lower
    ):
        return True
    return False
