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
_BOUNDARY_STRUCTURE_TERMS = {
    "door",
    "doorway",
    "threshold",
    "gate",
    "exit",
    "entrance",
    "stairwell door",
    "front door",
    "back door",
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


def _collect_text_parts(move: dict[str, Any] | None) -> tuple[str, str]:
    if not isinstance(move, dict):
        return "", ""
    motivation = (
        move.get("motivation", {})
        if isinstance(move.get("motivation", {}), dict)
        else {}
    )
    direct_parts: list[str] = [
        str(move.get("action", "") or ""),
        str(move.get("dialogue", "") or ""),
    ]
    evidence_parts = direct_parts + [
        str(motivation.get("goal", "") or ""),
        str(motivation.get("tactic", "") or ""),
    ]
    for item in (
        move.get("state_changes", [])
        if isinstance(move.get("state_changes", []), list)
        else []
    ):
        evidence_parts.append(str(item or ""))
    for item in (
        move.get("presence_changes", [])
        if isinstance(move.get("presence_changes", []), list)
        else []
    ):
        if isinstance(item, dict):
            evidence_parts.append(str(item.get("summary", "") or ""))
            evidence_parts.append(str(item.get("change", "") or ""))
        else:
            evidence_parts.append(str(item or ""))
    direct_text = " ".join(
        part.strip() for part in direct_parts if str(part or "").strip()
    ).lower()
    evidence_text = " ".join(
        part.strip() for part in evidence_parts if str(part or "").strip()
    ).lower()
    return direct_text, evidence_text


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


def detect_exit_from_scene(
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
) -> bool:
    direct_text, evidence_text = _collect_text_parts(move)
    if not evidence_text:
        return False

    if (
        "left the immediate scene" in evidence_text
        or '"change": "exit"' in evidence_text
    ):
        return True

    explicit_exit = re.search(
        r"\b(?:walk(?:ed|ing)?\s+out|storm(?:ed|ing)?\s+out|head(?:ed|ing)?\s+out|left\s+(?:the\s+)?(?:room|scene|dorm|building|apartment|house|hallway|hall|doorway|door|threshold|outside|outdoors)|(?:leave|leaving|exit|exited|exiting|depart(?:ed|ing)?)\s+(?:the\s+)?(?:room|scene|dorm|building|apartment|house|hallway|hall|doorway|door|threshold|outside|outdoors|here)|(?:i|i'm|im|we|we're|were|she|he|they)\s+(?:am\s+|are\s+|is\s+)?(?:leaving|exiting|departing))\b",
        direct_text,
    )

    if _contains_any(direct_text, _INTERNAL_REPOSITION_TERMS) and explicit_exit is None:
        return False

    if explicit_exit is not None and not _contains_any(
        direct_text, _INTERNAL_REPOSITION_TERMS
    ):
        return True

    has_movement = _contains_any(direct_text, _MOVEMENT_TERMS)
    has_boundary_location = _contains_any(direct_text, _BOUNDARY_LOCATION_TERMS)
    has_boundary_structure = _contains_any(direct_text, _BOUNDARY_STRUCTURE_TERMS)
    has_departure_completion = _contains_any(direct_text, _DEPARTURE_COMPLETION_TERMS)
    has_supporting_departure_intent = _contains_any(
        evidence_text, {"leave", "exit", "depart", "withdraw", "walk out", "head out"}
    )

    scene_anchor_terms = _extract_scene_anchor_terms(scene_state)
    leaves_scene_anchor = any(
        re.search(
            rf"\b(?:outside|out of|away from|beyond)\s+the\s+{re.escape(term)}\b",
            evidence_text,
        )
        for term in scene_anchor_terms
    )

    if (
        has_movement
        and has_boundary_location
        and not _contains_any(direct_text, _INTERNAL_REPOSITION_TERMS)
    ):
        return True

    if (has_boundary_structure and has_departure_completion) or leaves_scene_anchor:
        if has_movement or has_boundary_location:
            return True

    if (
        has_supporting_departure_intent
        and has_boundary_location
        and has_departure_completion
    ):
        return True

    return False
