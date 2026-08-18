"""Constants for ``continuity_consequence_classifier`` (Issue #159)."""

# Intent signal seeds - broad categories, not exhaustive phrase lists
INTENT_CONTROL = [
    "control",
    "dominate",
    "assert",
    "claim",
    "establish",
    "maintain control",
    "keep control",
    "hold ground",
    "protect",
    "keep",
    "safe",
    "press",
    "pressure",
]
INTENT_RESIST = [
    "resist",
    "reject",
    "defy",
    "push back",
    "refuse",
    "not submit",
    "not comply",
    "stand ground",
    "disengage",
    "ultimatum",
    "stalemate",
    "walk away",
    "walking away",
    "withhold",
    "noncompliant",
    "non-compliant",
    "break the stalemate",
    "break stalemate",
    "forcing a",
    "force a",
]
INTENT_MEDIATE = [
    "mediate",
    "manage",
    "de-escalate",
    "keep peace",
    "control situation",
    "calm",
    "settle",
]
INTENT_CHALLENGE = [
    "challenge",
    "test",
    "provoke",
    "push limits",
    "assert self",
    "establish presence",
    "call the bluff",
]
INTENT_COMPLY = [
    "comply",
    "accept",
    "agree",
    "go along",
    "follow",
    "cooperate",
    "yield",
]
INTENT_ESCALATE = ["escalate", "intensify", "ramp up", "push harder"]

# Behavior signal seeds
BEHAVIOR_DIRECTIVE = [
    "command",
    "order",
    "demand",
    "tell",
    "instruct",
    "warn",
    "threaten",
    "insist",
    "require",
]
BEHAVIOR_POSITIONAL = [
    "stepped between",
    "blocked",
    "moved in front",
    "positioned",
    "interposed",
    "stood before",
    "holds",
    "hold",
]
BEHAVIOR_DISMISSIVE = [
    "dismiss",
    "mock",
    "belittle",
    "ignore",
    "blow off",
    "laugh at",
    "ridicule",
    "taunt",
]
BEHAVIOR_COUNTER = [
    "shove",
    "push away",
    "jerk away",
    "step forward",
    "move into space",
    "close distance",
]
BEHAVIOR_ENTRY = [
    "stepped inside",
    "entered",
    "came in",
    "arrived",
    "stepped in",
    "walked in",
]

# Discrete loci for interaction-geometry repositioning (action/dialogue substrings).
INTERACTION_LOCUS_MARKERS = frozenset(
    {
        "table",
        "chair",
        "door",
        "doorway",
        "counter",
        "kitchen",
        "sink",
        "window",
        "hall",
        "hallway",
        "couch",
        "sofa",
        "bed",
        "desk",
        "wall",
        "corner",
        "backrest",
        "apartment",
        "room",
    }
)

# Path / transition cues: movement between or around loci (primarily action).
INTERACTION_TRANSITION_MARKERS = [
    " to the ",
    " to ",
    " from the ",
    " off the ",
    " off of ",
    " around ",
    " behind ",
    " toward",
    " towards",
    " into the ",
    " into ",
    " across ",
    " back to",
    " away from",
    " out of",
    " over to",
    " up to",
    " onto ",
    " around the",
    " behind the",
]

# Strong movement lemmas (substring match on action). "turn" handled via
# ``geometry_movement_present`` (word-boundary + negation scrub).
GEOMETRY_MOVEMENT_MARKERS = [
    "walk",
    "step",
    "mov",
    "push",
    "pull",
    "cross",
    "circl",
    "retreat",
    "advanc",
    "withdraw",
    "pace",
    "rush",
    "dart",
    "stalk",
    "stomp",
    "lung",
    "round the",
    "straighten",
    "rose ",
    "rise ",
]

# Stasis / cosmetic posture: no geometry path unless paired with movement markers above.
GEOMETRY_STASIS_LEADERS = (
    "remained ",
    "stayed ",
    "still leaning",
    "still seated",
    "still sitting",
)
GEOMETRY_COSMETIC_ONLY_MARKERS = [
    "exhaled",
    "exhale",
    "narrowed her",
    "narrowed his",
    "narrowed their",
    "tilted her head",
    "tilted his head",
    "tapped the",
    "smiled",
    "nodded",
    "shrugged",
]

# REFUSAL: curated dialogue substrings (no bare "no"/"not" alone — those stay in legacy).
REFUSAL_DIALOGUE_MARKERS = [
    "bullshit",
    "ultimatum",
    "no deal",
    "won't",
    "wont",
    "done pretending",
    "screw you",
    "hell no",
    "fat chance",
    "not happening",
    "not buying",
    "over my dead",
    "never going to",
    "ain't going",
    "aren't going",
    "won't work",
    "not your terms",
    "not interested",
]

# Strong refusal stance in goal/tactic only (second factor without dialogue markers).
REFUSAL_STRONG_INTENT_MARKERS = [
    "ultimatum",
    "disengage",
    "withhold compliance",
    "withhold agreement",
    "reject terms",
    "reject the terms",
    "deny the demand",
    "break off",
    "walk away",
    "walking away",
    "noncompliant",
    "non-compliant",
]

# Legacy dialogue gate (still requires resist/challenge intent via merged logic).
# "no"/"not" use word-boundary matching in detect_agreement; other tokens stay substring.
REFUSAL_LEGACY_DIALOGUE_MARKERS = ["no", "not", "won't", "refuse", "deny"]
