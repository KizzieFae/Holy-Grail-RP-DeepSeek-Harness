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

See ``autogen_rp/python/rp_app/ARCHITECTURE.md`` (perception / audibility).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from character_move_adapters import (
    copy_move_shallow_with_deep_beats,
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)

AUDIBILITY_PUBLIC = "public"
AUDIBILITY_DIRECTED = "directed"
AUDIBILITY_PRIVATE = "private"
_VALID_AUDIBILITY = frozenset(
    {AUDIBILITY_PUBLIC, AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE}
)

# Deterministic stub for non-perceivable speech in **per-recipient projections** only.
REDACTED_SPEECH_STUB = "[speech inaudible to this recipient]"


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


def normalize_speech_beat_audibility(
    beat: dict[str, Any],
    acting_character: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return a copy of a ``type: speech`` beat with ``audibility`` / ``audience`` set.

    Omitted or invalid audibility → **public** with empty audience.
    """
    out = dict(beat)
    raw_aud = str(out.get("audibility", "") or "").strip().lower()
    if raw_aud not in _VALID_AUDIBILITY:
        raw_aud = ""

    audience = _clean_audience(out.get("audience"), acting_character)
    dialogue = str(out.get("dialogue", "") or "")

    if raw_aud == AUDIBILITY_PUBLIC or not raw_aud:
        out["audibility"] = AUDIBILITY_PUBLIC
        out["audience"] = []
    else:
        out["audibility"] = raw_aud
        if raw_aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE) and not audience:
            inferred = infer_audience_from_text(
                "",
                dialogue,
                present_characters,
                acting_character,
            )
            out["audience"] = inferred
        else:
            out["audience"] = audience
    return out


def normalize_move_audibility(
    move: dict[str, Any],
    acting_character: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return a copy of ``move`` with audibility normalized (v1 root or v2 per speech beat)."""
    if is_canonical_v2_move(move):
        out = dict(move)
        beats = out.get("beats")
        if not isinstance(beats, list):
            return out
        new_beats: list[Any] = []
        for b in beats:
            if not isinstance(b, dict):
                new_beats.append(b)
                continue
            if b.get("type") == "speech":
                new_beats.append(
                    normalize_speech_beat_audibility(
                        dict(b), acting_character, present_characters
                    )
                )
            else:
                new_beats.append(dict(b))
        out["beats"] = new_beats
        return out

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


def speech_beat_viewer_may_perceive(
    beat: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str,
) -> bool:
    """Whether ``viewer_character`` may receive verbatim ``dialogue`` for this speech beat."""
    aud = str(beat.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    # Directed / private: visibility-equivalent for #138.
    audience = beat.get("audience")
    if not isinstance(audience, list):
        return False
    return viewer_character in [str(a).strip() for a in audience if str(a).strip()]


def viewer_may_perceive_dialogue(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str,
) -> bool:
    """Whether ``viewer_character`` may receive structured dialogue for this move (any beat)."""
    if is_canonical_v2_move(move):
        beats = move.get("beats")
        if not isinstance(beats, list):
            return True
        speech_any = False
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            speech_any = True
            if speech_beat_viewer_may_perceive(
                b, acting_character=acting_character, viewer_character=viewer_character
            ):
                return True
        return not speech_any

    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    if aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        audience = move.get("audience")
        if not isinstance(audience, list):
            return False
        return viewer_character in [str(a).strip() for a in audience if str(a).strip()]
    return False


REDACTED_PLAYER_TEXT_CONTENT = (
    "[private or directed player input — exact words omitted for this recipient]"
)


def _canonical_viewer_for_present(
    viewer_character_name: str,
    present_characters: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str:
    """Align viewer id with the ``present_characters`` labels used in audiences."""
    v = str(viewer_character_name or "").strip()
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]
    if v in present:
        return v
    vd = get_character_display_name_fn(v).strip()
    for p in present:
        if get_character_display_name_fn(p).strip() == vd:
            return p
    return v


def player_text_for_character_viewer(
    *,
    raw_text: str,
    viewer_character_name: str,
    present_characters: list[str],
    user_display_name: str,
    get_character_display_name_fn: Callable[[str], str] | None = None,
) -> str:
    """Return player/user ``raw_text`` or a redacted placeholder for this viewer.

    Models the line as structured ``dialogue`` on a synthetic move from
    ``user_display_name``, then applies :func:`normalize_move_audibility` and
    :func:`viewer_may_perceive_dialogue` — same rules as character moves.

    **MVP:** If audibility is ambiguous (no whisper / directed markers), the line
    is treated as **public** so all present characters receive the full string.
    This preserves pre-fix default exposure and avoids over-redaction; it is not
    declared final policy.

    Director / orchestration transcript paths pass ``viewer_character_name=None``
    to :func:`build_recent_dialogue_history_for_viewer` and receive unfiltered
    user lines.
    """
    text = str(raw_text or "")
    if not str(text).strip():
        return text

    display_fn = get_character_display_name_fn or (lambda x: str(x))
    acting = str(user_display_name or "").strip() or "Traveler"
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]

    synthetic: dict[str, Any] = {
        "action": "",
        "dialogue": text,
        "audibility": "",
        "audience": [],
    }
    norm = normalize_move_audibility(synthetic, acting, present)
    viewer = _canonical_viewer_for_present(
        viewer_character_name, present, display_fn
    )
    if viewer_may_perceive_dialogue(
        norm, acting_character=acting, viewer_character=viewer
    ):
        return text
    return REDACTED_PLAYER_TEXT_CONTENT


def use_full_narrator_content_for_recipient(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str | None,
    present_characters: list[str] | None = None,
) -> bool:
    """Whether to include full ``rendered`` prose (vs observable-only stub).

    ``viewer_character`` ``None`` => Director / orchestration transcript: **always**
    full prose (canonical visibility for orchestration; Issue #138).

    For v2 moves, all speech beats must be perceivable by the viewer; optional
    ``present_characters`` is used when normalizing beats (defaults to
    ``[acting_character, viewer_character]`` when the viewer is a character).
    """
    if viewer_character is None:
        return True
    present = present_characters
    if present is None:
        present = list(dict.fromkeys([acting_character, viewer_character]))
    move_norm = normalize_move_audibility(dict(move), acting_character, present)
    if is_canonical_v2_move(move_norm):
        beats = move_norm.get("beats")
        if not isinstance(beats, list):
            return True
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            if not speech_beat_viewer_may_perceive(
                b,
                acting_character=acting_character,
                viewer_character=viewer_character,
            ):
                return False
        return True

    aud = str(move_norm.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    if aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        audience = move_norm.get("audience")
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
    present = [str(p).strip() for p in present_characters if str(p).strip()]
    if is_canonical_v2_move(move):
        move_norm = normalize_move_audibility(dict(move), acting_character, present)
        recipients: set[str] = set()
        beats = move_norm.get("beats")
        if not isinstance(beats, list):
            return list(dict.fromkeys(present))
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            aud = str(b.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
            if aud == AUDIBILITY_PUBLIC:
                recipients.update(present)
            else:
                recipients.add(acting_character)
                recipients.update(
                    _clean_audience(b.get("audience"), acting_character)
                )
        if not recipients:
            return list(dict.fromkeys(present))
        out = [n for n in recipients if n in present or n == acting_character]
        return list(dict.fromkeys(out))

    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
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
    if is_canonical_v2_move(move):
        # Callers (e.g. continuity) normalize moves with full ``present_characters``
        # before summary; do not re-normalize here with an incomplete roster.
        base = str(provisional_summary or "")
        beats = move.get("beats")
        if isinstance(beats, list):
            for b in beats:
                if not isinstance(b, dict) or b.get("type") != "speech":
                    continue
                aud = str(
                    b.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC
                ).lower()
                if aud == AUDIBILITY_PUBLIC:
                    continue
                dialogue = str(b.get("dialogue", "") or "").strip()
                base = strip_dialogue_from_summary(base, dialogue)
        if base.strip():
            return base.strip()
        return f"{acting_character} took action"

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
    """Perception-safe line when full narrator prose must not be shown (v1-shaped move)."""
    action = str(move.get("action", "") or "").strip()
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if not action:
        if aud == AUDIBILITY_PUBLIC:
            return f"{speaker_label}: [nonverbal beat]"
        return f"{speaker_label}: [private or directed speech — audible action only; dialogue omitted]"
    if aud == AUDIBILITY_PUBLIC:
        return f"{speaker_label}: {action}"
    return f"{speaker_label}: {action} (private or directed speech; exact words omitted for this recipient)"


def format_observable_v2_turn_for_viewer(
    *,
    speaker_label: str,
    move_norm: dict[str, Any],
    acting_character: str,
    viewer_character_name: str,
    present_characters: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str:
    """Structured-transcript stub line for a v2 move when ``rendered`` must not leak."""
    vc = _canonical_viewer_for_present(
        viewer_character_name, present_characters, get_character_display_name_fn
    )
    parts: list[str] = []
    beats = move_norm.get("beats")
    if not isinstance(beats, list):
        return f"{speaker_label}: [beat]"
    for b in beats:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "action":
            a = str(b.get("action", "") or "").strip()
            if a:
                parts.append(a)
        elif b.get("type") == "speech":
            if speech_beat_viewer_may_perceive(
                b, acting_character=acting_character, viewer_character=vc
            ):
                d = str(b.get("dialogue", "") or "").strip()
                if d:
                    parts.append(d)
            else:
                parts.append(REDACTED_SPEECH_STUB)
    if not parts:
        return f"{speaker_label}: [beat]"
    return f"{speaker_label}: " + " ".join(parts)


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

    ``viewer_character_name`` ``None`` => Director / orchestration: full **rendered**
    lines and unredacted structured semantics for transcript assembly (Issue #138).
    """
    history: list[dict[str, str]] = []
    present = [str(n).strip() for n in character_names if str(n or "").strip()]
    for message in chat_history[-limit:]:
        if message.get("role") == "system":
            continue
        role = str(message.get("role", "assistant") or "assistant")
        if role == "user":
            speaker = str(message.get("speaker", "Traveler") or "Traveler")
            content = str(message.get("content", "") or "")
            if viewer_character_name is None:
                safe_content = content
            else:
                safe_content = player_text_for_character_viewer(
                    raw_text=content,
                    viewer_character_name=viewer_character_name,
                    present_characters=present,
                    user_display_name=speaker,
                    get_character_display_name_fn=get_character_display_name_fn,
                )
            history.append(
                {
                    "role": role,
                    "speaker": speaker,
                    "content": safe_content,
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

        move_norm = normalize_move_audibility(dict(move), actor, present)
        if use_full_narrator_content_for_recipient(
            move_norm,
            acting_character=actor,
            viewer_character=viewer_character_name,
            present_characters=present,
        ):
            pass
        elif is_canonical_v2_move(move_norm) and viewer_character_name is not None:
            content = format_observable_v2_turn_for_viewer(
                speaker_label=speaker_label,
                move_norm=move_norm,
                acting_character=actor,
                viewer_character_name=viewer_character_name,
                present_characters=present,
                get_character_display_name_fn=get_character_display_name_fn,
            )
        else:
            content = format_observable_beat_text(
                speaker_label=speaker_label,
                move=move_norm,
                acting_character=actor,
            )

        history.append({"role": role, "speaker": speaker_label, "content": content})

    return history


def redact_structured_move_for_orchestration(
    move_entry: dict[str, Any],
    *,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return an unredacted copy for Director structured history (Issue #138).

    ``present_characters`` is retained for call-site compatibility only.
    """
    _ = present_characters  # Director consumes canonical truth; arg unused
    if not isinstance(move_entry, dict):
        return move_entry
    return copy_move_shallow_with_deep_beats(move_entry)


def filter_structured_move_for_viewer(
    move_entry: dict[str, Any],
    *,
    viewer_character_name: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Derive per-recipient structured move entry (redacted speech stubs when needed)."""
    if not isinstance(move_entry, dict):
        return move_entry
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]
    speaker = str(move_entry.get("speaker", "") or "").strip()
    if not speaker or speaker == viewer_character_name:
        out = copy_move_shallow_with_deep_beats(move_entry)
        if is_canonical_v2_move(out):
            beats = out.get("beats")
            if isinstance(beats, list):
                new_beats = [
                    normalize_speech_beat_audibility(dict(b), speaker, present)
                    if isinstance(b, dict) and b.get("type") == "speech"
                    else (dict(b) if isinstance(b, dict) else b)
                    for b in beats
                ]
                out["beats"] = new_beats
                flat: dict[str, Any] = {"move_schema_version": 2, "beats": new_beats}
                out["action"] = legacy_flat_action_text(flat)
                out["dialogue"] = legacy_flat_dialogue_text(flat)
        return out

    if is_canonical_v2_move(move_entry):
        out = copy_move_shallow_with_deep_beats(move_entry)
        beats = out.get("beats")
        if not isinstance(beats, list):
            return out
        new_beats: list[Any] = []
        for b in beats:
            if not isinstance(b, dict):
                new_beats.append(b)
                continue
            if b.get("type") == "speech":
                nb = normalize_speech_beat_audibility(dict(b), speaker, present)
                if not speech_beat_viewer_may_perceive(
                    nb,
                    acting_character=speaker,
                    viewer_character=viewer_character_name,
                ):
                    nb = dict(nb)
                    nb["dialogue"] = REDACTED_SPEECH_STUB
                new_beats.append(nb)
            else:
                new_beats.append(dict(b))
        out["beats"] = new_beats
        flat = {"move_schema_version": 2, "beats": new_beats}
        out["action"] = legacy_flat_action_text(flat)
        out["dialogue"] = legacy_flat_dialogue_text(flat)
        out["audibility"] = AUDIBILITY_PUBLIC
        out["audience"] = []
        return out

    out = dict(move_entry)
    move_like = {
        "action": out.get("action", ""),
        "dialogue": out.get("dialogue", ""),
        "audibility": out.get("audibility", AUDIBILITY_PUBLIC),
        "audience": out.get("audience", []),
    }
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
    if is_canonical_v2_move(move):
        beats = move.get("beats")
        if not isinstance(beats, list):
            return True
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            if speech_beat_viewer_may_perceive(
                b,
                acting_character=acting_character,
                viewer_character=observer_character,
            ):
                return True
        return False
    return viewer_may_perceive_dialogue(
        move, acting_character=acting_character, viewer_character=observer_character
    )
