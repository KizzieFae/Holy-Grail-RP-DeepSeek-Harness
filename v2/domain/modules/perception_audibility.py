"""Deterministic audibility and perception filtering (single source of truth).

Structured ``move`` is the ground truth for who may receive dialogue text.
Narrator ``rendered`` prose must not be used to infer boundaries.

**v2 character moves (GitHub #134 / #138):** ``audibility`` / ``audience`` exist only on
``type: speech`` beats. Omitted audibility on a speech beat means **public**. **Directed**
and **private** are **visibility-equivalent** on this path only (who may receive verbatim
``dialogue``), not a claim of semantic equivalence elsewhere.

**Canonical vs derived:** Orchestration stores **canonical** structured move entries
(unredacted). **Per-recipient** views (character prompts) apply **derived** projections:
speech ``dialogue`` may be replaced by a deterministic stub; ``beats[]`` order is stable;
``action`` beats are never audibility-gated. The **Director** consumes **unredacted**
canonical structured history; transcript assembly for ``viewer_character_name is None``
uses **full** stored lines (no redaction) so orchestration sees verbatim content.

**#169:** Mechanical split across ``perception_audibility_*`` modules; this file is the
stable public façade — import from here only unless an explicit exemption is recorded.

See governance archive for historical perception/audibility architecture notes.
"""

from __future__ import annotations

from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
    REDACTED_PLAYER_TEXT_CONTENT,
    REDACTED_SPEECH_STUB,
)
from perception_audibility_events import (
    event_knowledge_recipients,
    public_event_extraction,
    public_safe_event_summary,
)
from perception_audibility_formatting import (
    format_observable_beat_text,
    format_observable_v2_turn_for_viewer,
)
from perception_audibility_history import (
    build_recent_dialogue_history_for_viewer,
    resolve_message_actor,
)
from perception_audibility_normalize import (
    infer_audience_from_text,
    normalize_move_audibility,
    normalize_speech_beat_audibility,
)
from perception_audibility_quote_policy import observer_may_quote_dialogue_in_interpretation
from perception_audibility_structured import (
    filter_structured_move_for_viewer,
    redact_structured_move_for_orchestration,
)
from perception_audibility_visibility import (
    speech_beat_viewer_may_perceive,
    use_full_narrator_content_for_recipient,
    viewer_may_perceive_dialogue,
)

__all__ = [
    "AUDIBILITY_DIRECTED",
    "AUDIBILITY_PRIVATE",
    "AUDIBILITY_PUBLIC",
    "REDACTED_PLAYER_TEXT_CONTENT",
    "REDACTED_SPEECH_STUB",
    "build_recent_dialogue_history_for_viewer",
    "event_knowledge_recipients",
    "filter_structured_move_for_viewer",
    "format_observable_beat_text",
    "format_observable_v2_turn_for_viewer",
    "infer_audience_from_text",
    "normalize_move_audibility",
    "normalize_speech_beat_audibility",
    "observer_may_quote_dialogue_in_interpretation",
    "public_event_extraction",
    "public_safe_event_summary",
    "redact_structured_move_for_orchestration",
    "resolve_message_actor",
    "speech_beat_viewer_may_perceive",
    "use_full_narrator_content_for_recipient",
    "viewer_may_perceive_dialogue",
]
