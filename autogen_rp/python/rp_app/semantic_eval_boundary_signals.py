"""Dorm/studio ontology boundary signal plugins (Issue #243-B — profile-scoped only).

These regex helpers are **calibration-guided** from Issue #240 corrected scorer evidence.
They apply **only** when the active evaluation profile is ``dorm_studio_single_space``.
They must **not** be used for profile resolution or runtime continuity.
"""

from __future__ import annotations

import re

# In-room / same-space — NOT excursion semantics (Issue #240 calibration)
IN_ROOM = re.compile(
    r"\b("
    r"couch|bunk|bed|desk|kitchenette|mattress|blanket|pillow|drawer|"
    r"window(?:sill)?|tool\s+bag|sketchbook|mini-fridge|closet|"
    r"crossed\s+to\s+(?:my|her|the)\s+(?:bunk|desk|couch|bed)|"
    r"swung\s+(?:her\s+)?boots?\s+off\s+the\s+edge\s+of\s+(?:the\s+)?bunk|"
    r"swung\s+onto\s+(?:my|her|the)\s+bunk|"
    r"sat\s+(?:on|down\s+on)\s+(?:the\s+)?(?:couch|bunk|bed|edge)|"
    r"dropped\s+to\s+the\s+floor|tool\s+bag|gray\s+blanket"
    r")\b",
    re.I,
)

INFO_BOUNDARY = re.compile(
    r"\b(bathroom(?:'s|\s+is|\s+door|'s\s+yours)|down\s+the\s+hall|third\s+door|"
    r"door\s+locks\s+from\s+the\s+inside)\b",
    re.I,
)

# Executed scene-boundary transition (net durable state may change)
EXEC_DEPART = re.compile(
    r"\b("
    r"(?:walk(?:ed|s|ing)?|step(?:ped|s|ping)?|head(?:ed|s|ing)?|slip(?:ped|s|ping)?|"
    r"move(?:d|s|ing)?|cross(?:ed|es|ing)?|exit(?:ed|s|ing)?|leave(?:s|d|ing)?|"
    r"push(?:ed|es|ing)?)\s+(?:out|past|through|into|toward|down)\s+"
    r"(?:the\s+)?(?:open\s+)?(?:door(?:way)?|hall(?:way)?|corridor|building|outside|bathroom|room)"
    r"|(?:into|to|toward|through)\s+(?:the\s+)?(?:hall(?:way)?|corridor|bathroom|shower|outside)"
    r"|(?:out\s+(?:into|of|the)\s+(?:the\s+)?(?:hall(?:way)?|corridor|door|room|building))"
    r"|walked\s+past\s+her\s+through"
    r")\b",
    re.I,
)

EXEC_RETURN = re.compile(
    r"\b("
    r"(?:return(?:ed|s|ing)?|re-?enter(?:ed|s|ing)?|come(?:s|back)?\s+back|"
    r"step(?:ped|s|ping)?\s+back\s+in)\s+(?:to|into)\s+"
    r"(?:the\s+)?(?:room|dorm|exchange|conversation|focal|doorway)"
    r"|(?:back\s+into\s+the\s+(?:room|dorm|living\s+room))"
    r")\b",
    re.I,
)

ROUND_TRIP = re.compile(
    r"(?:slip(?:ped|s)?\s+out|left\s+(?:the\s+)?room|into\s+the\s+hall).*(?:return(?:ed|s)?|back\s+into|stepped\s+inside)",
    re.I | re.S,
)

# Participation choreography within a single focal space — not durable net-state (calibration)
# Split in #243 supplemental: safe in-focal repositioning vs boundary-adjacent threshold cases.
PARTICIPATION_CHOREOGRAPHY_SAFE = re.compile(
    r"\b("
    r"parallel to the wall|"
    r"one\s+slow,\s+deliberate\s+step\s+forward(?!\s*[\u2014\-]\s*into\s+the\s+(?:hall|corridor|doorway))|"
    r"into the hallway, not out"
    r")\b",
    re.I,
)

PARTICIPATION_CHOREOGRAPHY_BOUNDARY_ADJACENT = re.compile(
    r"\b("
    r"(?:two|three|\d+)\s+steps?\s+(?:down|along|into|forward)\s+(?:the\s+)?(?:corridor|hallway|hall)|"
    r"step(?:ped|s|ping)?\s+(?:sideways|into the corridor|through the doorway|into the room)|"
    r"just past the threshold|"
    r"walked\s+past\s+her\s+through\s+the\s+open\s+doorway|"
    r"three\s+measured\s+steps\s+into\s+the\s+room|"
    r"cleared\s+the\s+doorway\s+with|"
    r"turning\s+to\s+face\s+.*\s+with\s+the\s+doorframe\s+between|"
    r"(?:took|take|walked|walks)\s+(?:one|two|three|\d+)\s+(?:slow|deliberate|measured)\s+steps?\s+"
    r"(?:down|into)\s+(?:the\s+)?(?:corridor|hallway|hall|room|doorway)"
    r")\b",
    re.I | re.S,
)


def dorm_studio_boundary_signals(beats: str) -> dict[str, bool]:
    depart = bool(EXEC_DEPART.search(beats))
    ret = bool(EXEC_RETURN.search(beats))
    info_match = bool(INFO_BOUNDARY.search(beats))
    in_room_match = bool(IN_ROOM.search(beats))
    # Informational bathroom/hall directions may co-occur with direction grammar that
    # EXEC_DEPART over-matches ("out the door, third door down") — preserve Willow in-room lane.
    in_room_only = in_room_match and (not depart or info_match)
    info_only = info_match and (not depart or in_room_match)
    round_trip = bool(ROUND_TRIP.search(beats))
    boundary_adjacent = bool(PARTICIPATION_CHOREOGRAPHY_BOUNDARY_ADJACENT.search(beats)) and not round_trip
    safe = (
        bool(PARTICIPATION_CHOREOGRAPHY_SAFE.search(beats))
        and not round_trip
        and not depart
        and not boundary_adjacent
    )
    return {
        "exec_depart": depart,
        "exec_return": ret,
        "in_room_only": in_room_only,
        "info_boundary_only": info_only,
        "round_trip_same_turn": round_trip and depart and ret,
        "participation_choreography": safe,
        "participation_choreography_safe": safe,
        "participation_choreography_boundary_adjacent": boundary_adjacent,
    }
