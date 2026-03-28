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

    if _EXPLICIT_DEPARTURE_RE.search(direct_text):
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
    if not direct_text and not combined_authored:
        return False
    # Soft heuristics need an embodied beat; motivation-only intent is not a departure.
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

    if (
        has_movement
        and has_boundary_location
        and has_departure_completion
    ):
        return True

    if (has_boundary_structure and has_departure_completion) or leaves_anchor:
        if has_movement or has_boundary_location:
            return True

    if (
        has_soft_intent
        and has_boundary_location
        and has_departure_completion
    ):
        return True

    return False


def detect_exit_from_scene(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> bool:
    """True if the turn describes actually leaving the immediate scene.

    Hard evidence (explicit wording / system phrase in authored text) wins first; soft
    path requires completion or clear anchor-leave, and ignores structured list echoes.
    """
    if has_hard_scene_departure_evidence(move, scene_state):
        return True
    return _detect_exit_soft_movement_boundary(move, scene_state)
