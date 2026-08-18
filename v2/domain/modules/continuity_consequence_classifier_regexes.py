"""Compiled regex patterns for consequence classification (Issue #159)."""

import re

# Geometry: "turn" only counts as movement when a standalone verb and not negated
# (avoids "did not turn", "didn't turn", "not turning", etc.).
GEOMETRY_NEGATED_TURN_PHRASE = re.compile(
    r"(?:did\s+not|didn't|does\s+not|don't)\s+turn(?:ed|s|ing)?\b|\bnot\s+turn(?:ed|s|ing)?\b",
    re.IGNORECASE,
)
GEOMETRY_TURN_VERB = re.compile(r"\bturn(?:ed|s|ing)?\b", re.IGNORECASE)

# REFUSAL legacy: standalone words only (avoids "nothing", "notice", "know", "snow", etc.).
REFUSAL_LEGACY_NO_OR_NOT_WORD = re.compile(r"\b(?:no|not)\b", re.IGNORECASE)

# ACCESS_GRANTED: "can" must not match inside "can't" (ASCII or Unicode apostrophe).
ACCESS_GRANTED_CAN_WORD = re.compile(
    r"\bcan\b(?!['\u2019]t\b)",
    re.IGNORECASE,
)
# AGREEMENT: whole-word only (avoids yes/yesterday, agree/disagree, fine/refine).
AGREEMENT_BOUNDARY_WORDS = re.compile(
    r"\b(?:yes|agree|fine|alright)\b",
    re.IGNORECASE,
)
# COMMITMENT: "will" must not match inside compounds like "goodwill".
COMMITMENT_WILL_WORD = re.compile(r"\bwill\b", re.IGNORECASE)
