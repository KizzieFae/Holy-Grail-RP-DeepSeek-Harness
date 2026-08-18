"""Tokens and stubs for audibility / perception (``perception_audibility`` package)."""

AUDIBILITY_PUBLIC = "public"
AUDIBILITY_DIRECTED = "directed"
AUDIBILITY_PRIVATE = "private"
_VALID_AUDIBILITY = frozenset(
    {AUDIBILITY_PUBLIC, AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE}
)

# Deterministic stub for non-perceivable speech in **per-recipient projections** only.
REDACTED_SPEECH_STUB = "[speech inaudible to this recipient]"

REDACTED_PLAYER_TEXT_CONTENT = (
    "[private or directed player input — exact words omitted for this recipient]"
)
