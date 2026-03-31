"""Deterministic audibility and perception filtering (single source of truth).

Structured ``move`` is the ground truth for who may receive dialogue text.
Narrator ``rendered`` prose must not be used to infer boundaries.
"""

from __future__ import annotations

import re
from typing import Any, Callable

AUDIBILITY_PUBLIC = "public"
AUDIBILITY_DIRECTED = "directed"
AUDIBILITY_PRIVATE = "private"
_VALID_AUDIBILITY = frozenset(
    {AUDIBILITY_PUBLIC, AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE}
)


def _clean_audience(raw: Any, acting_character: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        name = str(item or "").strip()
        if not name or name == acting_character or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def infer_audience_from_text(
    action: str, dialogue: str, present_characters: list[str], acting_character: str
) -> list[str]:
    """Heuristic audience for whisper / private speech (structured text only)."""
    text = f"{action} {dialogue}".lower()
    if not any(
        token in text
        for token in (
            "whisper",
            "mutter",
            "under breath",
            "quietly",
            "low voice",
            "aside",
            "private",
            "only ",
            "into ",
            "ear",
        )
    ):
        return []
    found: list[str] = []
    for name in present_characters:
        if name == acting_character:
            continue
        nlow = name.lower()
        if len(nlow) < 2:
            continue
        # "to Marlene", "toward Marlene", "into Marlene's ear"
        if re.search(
            rf"(?:\bto\b|\btoward\b|\bfor\b)\s+{re.escape(nlow)}\b", text
        ) or re.search(rf"{re.escape(nlow)}(?:'s)?\s+ear", text):
            found.append(name)
    return list(dict.fromkeys(found))


def normalize_move_audibility(
    move: dict[str, Any],
    acting_character: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return a copy of ``move`` with ``audibility`` and ``audience`` set deterministically."""
    out = dict(move)
    raw_aud = str(out.get("audibility", "") or "").strip().lower()
    if raw_aud not in _VALID_AUDIBILITY:
        raw_aud = ""

    audience = _clean_audience(out.get("audience"), acting_character)

    if raw_aud == AUDIBILITY_PUBLIC or not raw_aud:
        combined = (
            f"{out.get('action', '')} {out.get('dialogue', '')}".lower()
        )
        if raw_aud == "" and any(
            marker in combined
            for marker in (
                "whisper",
                "mutter",
                "under breath",
                "into ",
                " ear",
                "aside",
                "quietly to ",
            )
        ):
            inferred = infer_audience_from_text(
                str(out.get("action", "") or ""),
                str(out.get("dialogue", "") or ""),
                present_characters,
                acting_character,
            )
            out["audibility"] = (
                AUDIBILITY_DIRECTED if inferred else AUDIBILITY_PRIVATE
            )
            out["audience"] = inferred
        else:
            out["audibility"] = AUDIBILITY_PUBLIC
            out["audience"] = []
    else:
        out["audibility"] = raw_aud
        if raw_aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE) and not audience:
            inferred = infer_audience_from_text(
                str(out.get("action", "") or ""),
                str(out.get("dialogue", "") or ""),
                present_characters,
                acting_character,
            )
            out["audience"] = inferred
        else:
            out["audience"] = audience

    return out


def viewer_may_perceive_dialogue(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str,
) -> bool:
    """Whether ``viewer_character`` may receive structured ``dialogue`` for this move."""
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    if aud == AUDIBILITY_PRIVATE:
        return False
    audience = move.get("audience")
    if not isinstance(audience, list):
        return False
    return viewer_character in [str(a).strip() for a in audience if str(a).strip()]


def use_full_narrator_content_for_recipient(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str | None,
) -> bool:
    """Whether to include full ``rendered`` prose (vs observable-only stub).

    ``viewer_character`` None => orchestration / global transcript: only public beats
    get full prose; directed/private never (no parsing narrator output).
    """
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if viewer_character is None:
        return aud == AUDIBILITY_PUBLIC
    if viewer_character == acting_character:
        return True
    if aud == AUDIBILITY_PUBLIC:
        return True
    if aud == AUDIBILITY_DIRECTED:
        audience = move.get("audience")
        if not isinstance(audience, list):
            return False
        names = [str(a).strip() for a in audience if str(a).strip()]
        return viewer_character in names
    return False


def event_knowledge_recipients(
    move: dict[str, Any],
    *,
    acting_character: str,
    present_characters: list[str],
) -> list[str]:
    """Return canonical names who may know a continuity event tied to this move."""
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    present = [str(p).strip() for p in present_characters if str(p).strip()]
    if aud == AUDIBILITY_PUBLIC:
        return list(dict.fromkeys(present))
    audience = _clean_audience(move.get("audience"), acting_character)
    core = [acting_character] + audience
    return list(dict.fromkeys([n for n in core if n in present or n == acting_character]))


def strip_dialogue_from_summary(summary: str, dialogue: str) -> str:
    """Remove verbatim dialogue from a summary string when dialogue must stay private."""
    d = str(dialogue or "").strip()
    if not d:
        return summary
    s = str(summary or "")
    if d in s:
        return s.replace(d, "").replace('""', "").replace("''", "").strip(" ;:")
    low = d.lower()
    if low and low in s.lower():
        pattern = re.compile(re.escape(d), re.IGNORECASE)
        return pattern.sub("", s).strip(" ;:")
    return s


def public_safe_event_summary(
    *,
    acting_character: str,
    move: dict[str, Any],
    provisional_summary: str,
) -> str:
    """Ensure ``PublicEvent.summary`` never embeds private/directed verbatim dialogue."""
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    dialogue = str(move.get("dialogue", "") or "").strip()
    action = str(move.get("action", "") or "").strip()
    if aud == AUDIBILITY_PUBLIC:
        return provisional_summary
    base = strip_dialogue_from_summary(provisional_summary, dialogue)
    if dialogue and dialogue.lower() in base.lower():
        base = strip_dialogue_from_summary(base, dialogue)
    if base.strip():
        return base.strip()
    audience = _clean_audience(move.get("audience"), acting_character)
    if aud == AUDIBILITY_DIRECTED and audience:
        names = ", ".join(audience)
        return f"{acting_character} addressed {names} in a low or private voice (words not globally knowable)."
    if aud == AUDIBILITY_PRIVATE:
        return f"{acting_character} spoke privately (words not globally knowable)."
    return f"{acting_character} {action}".strip() or f"{acting_character} took action"


def format_observable_beat_text(
    *,
    speaker_label: str,
    move: dict[str, Any],
    acting_character: str,
) -> str:
    """Perception-safe line when full narrator prose must not be shown."""
    action = str(move.get("action", "") or "").strip()
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if not action:
        if aud == AUDIBILITY_PUBLIC:
            return f"{speaker_label}: [nonverbal beat]"
        return f"{speaker_label}: [private or directed speech — audible action only; dialogue omitted]"
    if aud == AUDIBILITY_PUBLIC:
        return f"{speaker_label}: {action}"
    return f"{speaker_label}: {action} (private or directed speech; exact words omitted for this recipient)"


def resolve_message_actor(
    message: dict[str, Any],
    *,
    character_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str | None:
    """Resolve internal character id for an assistant chat message."""
    raw = message.get("actor")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    speaker_label = str(message.get("speaker", "") or "").strip()
    if not speaker_label:
        return None
    for name in character_names:
        if get_character_display_name_fn(name).strip() == speaker_label:
            return name
    return None


def build_recent_dialogue_history_for_viewer(
    *,
    chat_history: list[dict[str, Any]],
    viewer_character_name: str | None,
    character_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
    limit: int,
) -> list[dict[str, str]]:
    """Assemble recent history; filter narrator content using structured ``move`` only.

    ``viewer_character_name`` None => orchestration mode (no character may receive
    private/directed dialogue or full prose carrying it).
    """
    history: list[dict[str, str]] = []
    for message in chat_history[-limit:]:
        if message.get("role") == "system":
            continue
        role = str(message.get("role", "assistant") or "assistant")
        if role == "user":
            history.append(
                {
                    "role": role,
                    "speaker": str(message.get("speaker", "Traveler") or "Traveler"),
                    "content": str(message.get("content", "") or ""),
                }
            )
            continue

        speaker_label = str(message.get("speaker", "Unknown") or "Unknown")
        move = message.get("move")
        if not isinstance(move, dict):
            move = {}
        actor = resolve_message_actor(
            message,
            character_names=character_names,
            get_character_display_name_fn=get_character_display_name_fn,
        )
        content = str(message.get("content", "") or "")

        if actor is None:
            history.append({"role": role, "speaker": speaker_label, "content": content})
            continue

        present = [n for n in character_names if n]
        move = normalize_move_audibility(move, actor, present)
        if use_full_narrator_content_for_recipient(
            move,
            acting_character=actor,
            viewer_character=viewer_character_name,
        ):
            pass
        else:
            content = format_observable_beat_text(
                speaker_label=speaker_label,
                move=move,
                acting_character=actor,
            )

        history.append({"role": role, "speaker": speaker_label, "content": content})

    return history


def redact_structured_move_for_orchestration(
    move_entry: dict[str, Any],
    *,
    present_characters: list[str],
) -> dict[str, Any]:
    """Strip non-public dialogue from structured moves in Director / global prompts."""
    if not isinstance(move_entry, dict):
        return move_entry
    out = dict(move_entry)
    speaker = str(out.get("speaker", "") or "").strip()
    if not speaker:
        return out
    present = [str(p).strip() for p in present_characters if str(p).strip()]
    move_like = {
        "action": out.get("action", ""),
        "dialogue": out.get("dialogue", ""),
        "audibility": out.get("audibility", AUDIBILITY_PUBLIC),
        "audience": out.get("audience", []),
    }
    norm = normalize_move_audibility(move_like, speaker, present)
    out["audibility"] = norm.get("audibility", AUDIBILITY_PUBLIC)
    out["audience"] = norm.get("audience", [])
    if str(norm.get("audibility", "")).lower() != AUDIBILITY_PUBLIC:
        out["dialogue"] = ""
    return out


def filter_structured_move_for_viewer(
    move_entry: dict[str, Any],
    *,
    viewer_character_name: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Redact ``dialogue`` when the viewer must not perceive it."""
    if not isinstance(move_entry, dict):
        return move_entry
    out = dict(move_entry)
    speaker = str(out.get("speaker", "") or "").strip()
    if not speaker or speaker == viewer_character_name:
        return out
    move_like = {
        "action": out.get("action", ""),
        "dialogue": out.get("dialogue", ""),
        "audibility": out.get("audibility", AUDIBILITY_PUBLIC),
        "audience": out.get("audience", []),
    }
    present = [str(p).strip() for p in present_characters if str(p).strip()]
    move_like = normalize_move_audibility(move_like, speaker, present)
    if not viewer_may_perceive_dialogue(
        move_like, acting_character=speaker, viewer_character=viewer_character_name
    ):
        out["dialogue"] = ""
    out["audibility"] = move_like.get("audibility", AUDIBILITY_PUBLIC)
    out["audience"] = move_like.get("audience", [])
    return out


def observer_may_quote_dialogue_in_interpretation(
    move: dict[str, Any],
    *,
    acting_character: str,
    observer_character: str,
) -> bool:
    """Whether interpretations may include quoted dialogue for this observer."""
    return viewer_may_perceive_dialogue(
        move, acting_character=acting_character, viewer_character=observer_character
    )
