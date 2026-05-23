"""Issue #240 experimental one-pass prompt topology (investigation-only).

Gates:
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1`` (also ``1``, ``true``, ``yes``, ``on``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next`` (also ``v1-next``, ``v1next``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next2`` (also ``v1-next2``, ``v1next2``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next3`` (also ``v1-next3``, ``v1next3``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next4`` (also ``v1-next4``, ``v1next4``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next5`` (also ``v1-next5``, ``v1next5``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next6`` (also ``v1-next6``, ``v1next6``)
- ``RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7`` (also ``v1-next7``, ``v1next7``)
Default / unset: production ``prompt_builders.build_character_turn_prompt``.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

from prompt_builders import build_character_turn_prompt as _production_build_character_turn_prompt

_ISSUE240_ENV = "RP_ISSUE240_PROMPT_TOPOLOGY"
_V1_TRUTHY = frozenset({"1", "v1", "true", "yes", "on"})
_V1_NEXT_TRUTHY = frozenset({"v1_next", "v1-next", "v1next"})
_V1_NEXT2_TRUTHY = frozenset({"v1_next2", "v1-next2", "v1next2"})
_V1_NEXT3_TRUTHY = frozenset({"v1_next3", "v1-next3", "v1next3"})
_V1_NEXT4_TRUTHY = frozenset({"v1_next4", "v1-next4", "v1next4"})
_V1_NEXT5_TRUTHY = frozenset({"v1_next5", "v1-next5", "v1next5"})
_V1_NEXT6_TRUTHY = frozenset({"v1_next6", "v1-next6", "v1next6"})
_V1_NEXT7_TRUTHY = frozenset({"v1_next7", "v1-next7", "v1next7"})
_ISSUE240_LONG_PROMPT_COMPRESS_CHARS = 35_000

ISSUE240_V1_OPENING_MARKER = "Act primarily as this character"
ISSUE240_SEMANTIC_BLOCK_HEADER = "FOR THIS BEAT — SEMANTIC SELF-REPORT"
ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER = "BEAT-LOCAL SOCIAL FOCUS"
ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER = "ACTIVE SCENE FOCUS"
ISSUE240_V1_NEXT3_PARTICIPATION_FRAME_MARKER = "Ask one question while authoring this beat"
ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER = "RECENT PARTICIPATION ARC"
ISSUE240_V1_NEXT5_SEMANTIC_EVAL_MARKER = "Required root field every beat"
ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER = "COVERED-CHANGE THRESHOLD"
ISSUE240_V1_NEXT7_THRESHOLD_CALIBRATION_MARKER = "Covered-change threshold (calibration"
ISSUE240_DOCTRINE_PHRASE = "not compliance theater"
_ISSUE240_COMPRESS_NOTE = (
    "[Beat-focus window: older entries deprioritized here; continuity authority unchanged.]"
)

_WITHDRAW_CUES = re.compile(
    r"\b(withdraw|disengag|step(?:s|ped)?\s+(?:back|away|off|out)|turn(?:s|ed)?\s+away|"
    r"off.?focal|quiet|minimal|avoid|retreat|distant|guarded|shut\s+down|"
    r"look(?:s|ed)?\s+away|edge\s+of\s+the\s+(?:room|exchange))\b",
    re.I,
)
_REENTRY_CUES = re.compile(
    r"\b(re-?enter|return(?:s|ed|ing)?\s+to|come\s+back|join(?:s|ed|ing)?\s+the\s+"
    r"(?:conversation|exchange)|look(?:s|ed)?\s+up|meet(?:s|ing)?\s+\w+(?:'s)?\s+eyes)\b",
    re.I,
)

_COMPRESSED_PRIORITIES_5_7 = """5. SOCIAL REALISM
- Stay occupied with your own business unless directly addressed, affected, obligated, or strategically choosing to engage. Hierarchy and public tension often suppress speech.

6. KNOWLEDGE AND EVIDENCE DISCIPLINE
- Match reactions to evidence strength; do not upgrade rumor or inference into certainty.

7. CANON AND WORLD CONSISTENCY
- Do not contradict canon anchors or broaden scene ontology beyond established facts."""

_SLIM_OUTPUT_RULES = """OUTPUT RULES:
- Only output a single JSON object: canonical character move v2 (integer ``move_schema_version`` 2, non-empty ``beats[]``, ``motivation``, optional ``scene_state_updates``, optional ``semantic_proposals``).
- Do not emit root-level ``action``, ``dialogue``, ``audibility``, or ``audience``. Put visible action and speech only inside ``beats[]`` as ``type: action`` or ``type: speech`` objects, in true beat order.
- Root ``semantic_proposals`` (when present): self-only semantic commit intent — kinds ``off_focal`` | ``reentry`` | ``excursion_lifecycle``; ``operation`` required only for ``excursion_lifecycle``. Not a commit. Do not emit root ``presence_changes``, ``excursion_lifecycle``, or ``spatial_transition``.
- Each ``type: action`` beat has non-empty ``action`` (visible self-only, third person). Each ``type: speech`` beat has non-empty ``dialogue``. On speech beats, optional ``audibility`` is one of ``public``, ``directed``, ``private``; for ``directed`` or ``private``, include non-empty ``audience``.
- Keep action beats concrete and observable; let speech sound natural and in-character.
- Registry settlements (``scene_state_updates.*``): follow system OUTPUT FORMAT; emit only when this beat explicitly settles a bounded scene fact supported by the beat."""

_V1_NEXT5_SLIM_OUTPUT_RULES = """OUTPUT RULES:
- Only output a single JSON object: canonical character move v2 (integer ``move_schema_version`` 2, non-empty ``beats[]``, ``motivation``, optional ``scene_state_updates``, required ``semantic_evaluation``).
- Do not emit root-level ``action``, ``dialogue``, ``audibility``, or ``audience``. Put visible action and speech only inside ``beats[]`` as ``type: action`` or ``type: speech`` objects, in true beat order.
- Root ``semantic_evaluation`` (required every beat): ``decision`` is ``covered_change`` or ``no_covered_change``; include non-empty ``proposals`` only when ``decision`` is ``covered_change`` (self-only proposal items: kinds ``off_focal`` | ``reentry`` | ``excursion_lifecycle``; ``operation`` required only for ``excursion_lifecycle``). When ``decision`` is ``no_covered_change``, omit ``proposals``. Do not emit root ``semantic_proposals`` or ``semantic_proposals: []``.
- Each ``type: action`` beat has non-empty ``action`` (visible self-only, third person). Each ``type: speech`` beat has non-empty ``dialogue``. On speech beats, optional ``audibility`` is one of ``public``, ``directed``, ``private``; for ``directed`` or ``private``, include non-empty ``audience``.
- Keep action beats concrete and observable; let speech sound natural and in-character.
- Registry settlements (``scene_state_updates.*``): follow system OUTPUT FORMAT; emit only when this beat explicitly settles a bounded scene fact supported by the beat."""


def issue240_prompt_topology_mode() -> str | None:
    raw = os.environ.get(_ISSUE240_ENV, "").strip().lower()
    if raw in _V1_NEXT7_TRUTHY:
        return "v1_next7"
    if raw in _V1_NEXT6_TRUTHY:
        return "v1_next6"
    if raw in _V1_NEXT5_TRUTHY:
        return "v1_next5"
    if raw in _V1_NEXT4_TRUTHY:
        return "v1_next4"
    if raw in _V1_NEXT3_TRUTHY:
        return "v1_next3"
    if raw in _V1_NEXT2_TRUTHY:
        return "v1_next2"
    if raw in _V1_NEXT_TRUTHY:
        return "v1_next"
    if raw in _V1_TRUTHY:
        return "v1"
    return None


def _norm_name(name: str) -> str:
    return str(name or "").replace("_", " ").casefold().strip()


def _speaker_matches(speaker: str, char_norm: str) -> bool:
    sn = _norm_name(speaker)
    if not sn or not char_norm:
        return False
    return sn == char_norm or char_norm in sn or sn in char_norm


def _move_text_blob(move: dict[str, Any]) -> str:
    parts = [str(move.get("action") or ""), str(move.get("dialogue") or "")]
    for beat in move.get("beats") or []:
        if isinstance(beat, dict):
            parts.append(str(beat.get("action") or ""))
            parts.append(str(beat.get("dialogue") or ""))
    return " ".join(parts)


def _dialogue_text(entry: dict[str, Any]) -> str:
    return str(entry.get("content") or entry.get("dialogue") or "")


def _truncate_line(text: str, limit: int = 120) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _extract_json_section(prompt: str, header: str, next_header: str) -> Any | None:
    pattern = rf"{re.escape(header)}\n(.*?)\n\n{re.escape(next_header)}"
    match = re.search(pattern, prompt, flags=re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _replace_json_section(prompt: str, header: str, next_header: str, replacement: str) -> str:
    pattern = rf"({re.escape(header)}\n)(.*?)(\n\n{re.escape(next_header)})"
    return re.sub(pattern, rf"\1{replacement}\3", prompt, count=1, flags=re.DOTALL)


def _extract_emotional_bearing(state_context: str) -> str | None:
    for line in str(state_context or "").splitlines():
        stripped = line.strip().lstrip("-").strip()
        if stripped.lower().startswith("emotional state:"):
            bearing = stripped.split(":", 1)[-1].strip()
            return bearing if bearing else None
    return None


def should_emit_social_focus_capsule(**kwargs: Any) -> bool:
    """Adaptive: multi-character or offstage-aware scenes only (skip simple 2-char lanes)."""
    scene_state = kwargs.get("scene_state") or {}
    if not isinstance(scene_state, dict):
        scene_state = {}
    present = [
        str(x).strip()
        for x in (scene_state.get("present_characters") or kwargs.get("cast") or [])
        if str(x).strip()
    ]
    if len(present) >= 3:
        return True
    offstage = [
        str(x).strip()
        for x in (scene_state.get("offstage_characters") or [])
        if str(x).strip()
    ]
    char_norm = _norm_name(str(kwargs.get("char_name") or ""))
    if char_norm and any(_norm_name(x) == char_norm for x in offstage):
        return True
    if offstage and len(present) >= 2:
        return True
    return False


def build_issue240_v1_next_social_focus_capsule(**kwargs: Any) -> str:
    char = str(kwargs.get("char_name") or "character")
    char_norm = _norm_name(char)
    scene_state = kwargs.get("scene_state") or {}
    if not isinstance(scene_state, dict):
        scene_state = {}
    present = [
        str(x).strip()
        for x in (scene_state.get("present_characters") or [])
        if str(x).strip()
    ]
    others = [n for n in present if _norm_name(n) != char_norm and char_norm not in _norm_name(n)]
    offstage = [
        str(x).strip()
        for x in (scene_state.get("offstage_characters") or [])
        if str(x).strip()
    ]
    lines = [
        f"{ISSUE240_V1_NEXT_SOCIAL_FOCUS_HEADER} (this beat only — do not recite in dialogue):",
    ]
    bearing = _extract_emotional_bearing(str(kwargs.get("state_context") or ""))
    if bearing:
        lines.append(f"- Your bearing now: {bearing}")
    if others:
        lines.append(f"- Others in the live exchange: {', '.join(others)}")
    if char_norm in {_norm_name(x) for x in offstage}:
        lines.append("- You are currently offstage relative to the focal exchange.")
    elif offstage:
        lines.append(f"- Offstage now: {', '.join(offstage)}")
    issues = kwargs.get("active_issues") or []
    if isinstance(issues, list) and issues and isinstance(issues[0], dict):
        desc = str(issues[0].get("description") or "").strip()
        if desc:
            short = desc if len(desc) <= 100 else desc[:97] + "..."
            lines.append(f"- Scene pressure: {short}")
    trigger = str(kwargs.get("trigger_text") or "").lower()
    if "reentry" in trigger and ("off_focal" in trigger or "offstage" in trigger):
        lines.append(
            "- Stepping away from the live exchange → off_focal; returning into it → reentry."
        )
    if len(lines) == 1:
        lines.append(f"- Present: {', '.join(present) if present else 'others'}")
    return "\n".join(lines) + "\n"


def _infer_emotional_focus_line(
    char_norm: str,
    others: list[str],
    recent_dialogue: list[Any],
    recent_moves: list[Any],
) -> str | None:
    for entry in reversed(recent_dialogue[-4:] if isinstance(recent_dialogue, list) else []):
        if not isinstance(entry, dict):
            continue
        speaker = str(entry.get("speaker") or entry.get("role") or "").strip()
        text = _dialogue_text(entry)
        if not text:
            continue
        sn = _norm_name(speaker)
        if sn and not _speaker_matches(speaker, char_norm):
            first = char_norm.split()[0] if char_norm else ""
            if first and first in _norm_name(text):
                who = speaker.replace("_", " ")
                if "?" in text:
                    return f"{who} is pressing you in the live exchange."
                return f"{who}'s recent move centers on you."
            if "?" in text and others and _norm_name(speaker) in {_norm_name(o) for o in others}:
                who = speaker.replace("_", " ")
                return f"{who} is pressing the conversation right now."
    for move in reversed(recent_moves[-4:] if isinstance(recent_moves, list) else []):
        if not isinstance(move, dict):
            continue
        speaker = str(move.get("speaker") or "")
        text = _move_text_blob(move)
        if _speaker_matches(speaker, char_norm):
            continue
        if char_norm.split()[0] in _norm_name(text) and "?" in text:
            return f"{speaker.replace('_', ' ')} recently addressed you directly."
    if others:
        lead = others[0].replace("_", " ")
        return f"The live exchange centers on {lead} and the room's current tension."
    return None


def _infer_engagement_state_line(
    char_norm: str,
    offstage: list[str],
    recent_moves: list[Any],
    trigger: str,
) -> str | None:
    if char_norm in {_norm_name(x) for x in offstage}:
        return "You are currently offstage — outside the focal exchange."
    trig = trigger.lower()
    recent_self: list[str] = []
    for move in reversed(recent_moves[-6:] if isinstance(recent_moves, list) else []):
        if not isinstance(move, dict):
            continue
        if _speaker_matches(str(move.get("speaker") or ""), char_norm):
            recent_self.append(_move_text_blob(move))
    joined = " ".join(recent_self)
    if joined and _WITHDRAW_CUES.search(joined) and not _REENTRY_CUES.search(joined):
        return "You have been partially withdrawn — not fully re-engaged in the exchange."
    if "reentry" in trig:
        return "You may be reconnecting to the exchange, or still holding at its edge."
    if "off_focal" in trig or "offstage" in trig:
        return "You may be stepping back from the exchange, or still present at its margin."
    if recent_self:
        return "You are in the room with the live exchange."
    return None


def _infer_recent_movement_line(
    char_norm: str,
    recent_moves: list[Any],
    my_interpretations: list[Any],
) -> str | None:
    for move in reversed(recent_moves[-6:] if isinstance(recent_moves, list) else []):
        if not isinstance(move, dict):
            continue
        text = _move_text_blob(move)
        if not text:
            continue
        is_self = _speaker_matches(str(move.get("speaker") or ""), char_norm)
        mentions_self = char_norm.split()[0] in _norm_name(text) if char_norm else False
        if not is_self and not mentions_self:
            continue
        if _WITHDRAW_CUES.search(text):
            speaker = str(move.get("speaker") or "You").replace("_", " ")
            subj = "You" if is_self else speaker
            return f"Most recent relevant movement: {subj} pulled back from the focal exchange."
        if _REENTRY_CUES.search(text):
            speaker = str(move.get("speaker") or "You").replace("_", " ")
            subj = "You" if is_self else speaker
            return f"Most recent relevant movement: {subj} moved back toward the exchange."
    for item in reversed(my_interpretations[-3:] if isinstance(my_interpretations, list) else []):
        if not isinstance(item, dict):
            continue
        if not _speaker_matches(str(item.get("character_name") or ""), char_norm):
            continue
        reaction = str(item.get("emotional_reaction") or "").strip()
        if reaction:
            return f"Your recent read of the room: {_truncate_line(reaction, 90)}."
    return None


def _infer_semantic_ambiguity_line(trigger: str) -> str | None:
    trig = trigger.lower()
    wants_reentry = "reentry" in trig or "re-enter" in trig
    wants_off = "off_focal" in trig or "offstage" in trig or "off-focal" in trig
    if wants_reentry and wants_off:
        return (
            "Beat ambiguity: continued off_focal distance vs reentry — "
            "report only what your beats actually do."
        )
    if wants_reentry:
        return (
            "Beat ambiguity: quiet presence vs reentry — "
            "report reentry only if you actually return to the exchange."
        )
    if wants_off:
        return (
            "Beat ambiguity: staying at the margin vs off_focal — "
            "report off_focal only if you actually step out."
        )
    if "semantic_proposals" in trig:
        return "Report semantic intent only when your authored beats substantiate it."
    return None


def _display_name(name: str) -> str:
    return str(name or "").replace("_", " ").strip() or "someone"


def _char_mentioned_in_text(char_norm: str, text: str) -> bool:
    first = char_norm.split()[0] if char_norm else ""
    return bool(first and first in _norm_name(text))


def _infer_self_participation_trajectory(
    char_norm: str,
    recent_moves: list[Any],
) -> str | None:
    tags: list[str] = []
    for move in recent_moves[-5:] if isinstance(recent_moves, list) else []:
        if not isinstance(move, dict):
            continue
        if not _speaker_matches(str(move.get("speaker") or ""), char_norm):
            continue
        text = _move_text_blob(move)
        if _WITHDRAW_CUES.search(text):
            tags.append("withdrawn")
        elif _REENTRY_CUES.search(text):
            tags.append("returning")
        elif str(move.get("dialogue") or "").strip():
            tags.append("speaking")
        else:
            tags.append("present")
    if not tags:
        return None
    if tags.count("withdrawn") >= 2:
        return "You have been partially withdrawn from the focal exchange over recent beats."
    if tags[-1] == "withdrawn":
        return "You pulled back from the live exchange in the last beat or two."
    if tags[-1] == "returning" and "withdrawn" in tags[:-1]:
        return "You have been edging back toward the exchange after earlier withdrawal."
    if tags[-1] == "speaking" and "withdrawn" in tags[:-1]:
        return "You re-entered the back-and-forth after a quieter stretch."
    if tags.count("speaking") >= 2:
        return "You have stayed inside the live exchange across recent beats."
    return "You have been present at the margin of the exchange recently."


def _infer_others_pull_trajectory(
    char_norm: str,
    recent_moves: list[Any],
    recent_dialogue: list[Any],
) -> str | None:
    pull_counts: dict[str, int] = {}
    for entry in recent_dialogue[-4:] if isinstance(recent_dialogue, list) else []:
        if not isinstance(entry, dict):
            continue
        speaker = str(entry.get("speaker") or entry.get("role") or "").strip()
        if not speaker or _speaker_matches(speaker, char_norm):
            continue
        text = _dialogue_text(entry)
        if _char_mentioned_in_text(char_norm, text) or "?" in text:
            key = _norm_name(speaker)
            pull_counts[key] = pull_counts.get(key, 0) + 1
    for move in recent_moves[-4:] if isinstance(recent_moves, list) else []:
        if not isinstance(move, dict):
            continue
        speaker = str(move.get("speaker") or "").strip()
        if not speaker or _speaker_matches(speaker, char_norm):
            continue
        text = _move_text_blob(move)
        if _char_mentioned_in_text(char_norm, text):
            key = _norm_name(speaker)
            pull_counts[key] = pull_counts.get(key, 0) + 1
    if not pull_counts:
        return None
    lead_key = max(pull_counts, key=pull_counts.get)
    lead_name = _display_name(lead_key)
    count = pull_counts[lead_key]
    if count >= 2:
        return f"{lead_name} has repeatedly tried to pull you back into the conversation."
    return f"{lead_name} recently pressed you in the live exchange."


def _infer_beat_participation_projection(
    trigger: str,
    self_trajectory: str | None,
) -> str | None:
    trig = trigger.lower()
    withdrawn = bool(self_trajectory and "withdraw" in self_trajectory.lower())
    if "reentry" in trig or (withdrawn and "re-entered" not in (self_trajectory or "").lower()):
        return "This beat may continue that distance or begin re-engagement."
    if "off_focal" in trig or "offstage" in trig:
        return "This beat may hold at the margin or step further out of the exchange."
    if withdrawn:
        return "This beat may extend recent distance or shift you back into the exchange."
    return None


def build_issue240_v1_next4_participation_arc(**kwargs: Any) -> str:
    char_norm = _norm_name(str(kwargs.get("char_name") or ""))
    scene_state = kwargs.get("scene_state") or {}
    if not isinstance(scene_state, dict):
        scene_state = {}
    offstage = [
        str(x).strip()
        for x in (scene_state.get("offstage_characters") or [])
        if str(x).strip()
    ]
    recent_moves = kwargs.get("recent_moves") or []
    recent_dialogue = kwargs.get("recent_dialogue") or []
    trigger = str(kwargs.get("trigger_text") or "")

    lines = [
        f"{ISSUE240_V1_NEXT4_PARTICIPATION_ARC_HEADER} (recent beats — do not recite in dialogue):",
    ]
    if char_norm in {_norm_name(x) for x in offstage}:
        lines.append("- You have been outside the focal exchange recently.")
    self_arc = _infer_self_participation_trajectory(char_norm, recent_moves)
    if self_arc:
        lines.append(f"- {self_arc}")
    others_arc = _infer_others_pull_trajectory(char_norm, recent_moves, recent_dialogue)
    if others_arc:
        lines.append(f"- {others_arc}")
    projection = _infer_beat_participation_projection(trigger, self_arc)
    if projection:
        lines.append(f"- {projection}")
    if len(lines) == 1:
        lines.append("- The recent exchange has stayed in motion without a sharp participation shift.")
    return "\n".join(lines[:5]) + "\n"


def build_issue240_v1_next2_active_focus_capsule(**kwargs: Any) -> str:
    char = str(kwargs.get("char_name") or "character")
    char_norm = _norm_name(char)
    scene_state = kwargs.get("scene_state") or {}
    if not isinstance(scene_state, dict):
        scene_state = {}
    present = [
        str(x).strip()
        for x in (scene_state.get("present_characters") or [])
        if str(x).strip()
    ]
    others = [n for n in present if _norm_name(n) != char_norm and char_norm not in _norm_name(n)]
    offstage = [
        str(x).strip()
        for x in (scene_state.get("offstage_characters") or [])
        if str(x).strip()
    ]
    recent_moves = kwargs.get("recent_moves") or []
    recent_dialogue = kwargs.get("recent_dialogue") or []
    my_interpretations = kwargs.get("my_interpretations") or []
    trigger = str(kwargs.get("trigger_text") or "")

    lines = [
        f"{ISSUE240_V1_NEXT2_ACTIVE_FOCUS_HEADER} (this beat only — do not recite in dialogue):",
    ]
    focus = _infer_emotional_focus_line(char_norm, others, recent_dialogue, recent_moves)
    if focus:
        lines.append(f"- Emotional focus: {focus}")
    bearing = _extract_emotional_bearing(str(kwargs.get("state_context") or ""))
    if bearing:
        lines.append(f"- Your bearing: {_truncate_line(bearing, 100)}")
    engagement = _infer_engagement_state_line(char_norm, offstage, recent_moves, trigger)
    if engagement:
        lines.append(f"- Your position: {engagement}")
    movement = _infer_recent_movement_line(char_norm, recent_moves, my_interpretations)
    if movement:
        lines.append(f"- {movement}")
    if others:
        lines.append(f"- In the live exchange now: {', '.join(n.replace('_', ' ') for n in others)}")
    issues = kwargs.get("active_issues") or []
    if isinstance(issues, list) and issues and isinstance(issues[0], dict):
        desc = str(issues[0].get("description") or "").strip()
        if desc:
            lines.append(f"- Active pressure: {_truncate_line(desc, 100)}")
    ambiguity = _infer_semantic_ambiguity_line(trigger)
    if ambiguity:
        lines.append(f"- {ambiguity}")
    elif "reentry" in trigger.lower() or "off_focal" in trigger.lower():
        lines.append(
            "- Stepping away from the live exchange → off_focal; returning into it → reentry."
        )
    if len(lines) == 1:
        lines.append(f"- Present: {', '.join(present) if present else 'others'}")
    return "\n".join(lines) + "\n"


def should_compress_long_prompt(prompt: str, **kwargs: Any) -> bool:
    return len(prompt) >= _ISSUE240_LONG_PROMPT_COMPRESS_CHARS and should_emit_social_focus_capsule(
        **kwargs
    )


def apply_issue240_v1_next2_long_prompt_compression(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """Deprioritize inactive history slices on long multi-character prompts only."""
    if not should_compress_long_prompt(production_prompt, **kwargs):
        return production_prompt
    prompt = production_prompt

    moves = _extract_json_section(
        prompt,
        "RECENT STRUCTURED ACTIONS (PERCEPTION-FILTERED FOR THIS CHARACTER):",
        "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):",
    )
    if isinstance(moves, list) and len(moves) > 3:
        trimmed = moves[-3:]
        note = f"{_ISSUE240_COMPRESS_NOTE}\n"
        prompt = _replace_json_section(
            prompt,
            "RECENT STRUCTURED ACTIONS (PERCEPTION-FILTERED FOR THIS CHARACTER):",
            "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):",
            note + json.dumps(trimmed, ensure_ascii=False, indent=2),
        )

    dialogue = _extract_json_section(
        prompt,
        "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):",
        "ACTIVE ISSUES / PRESSURES (ACTIONABLE NOW):",
    )
    if isinstance(dialogue, list) and len(dialogue) > 4:
        trimmed = dialogue[-4:]
        note = f"{_ISSUE240_COMPRESS_NOTE}\n"
        prompt = _replace_json_section(
            prompt,
            "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):",
            "ACTIVE ISSUES / PRESSURES (ACTIONABLE NOW):",
            note + json.dumps(trimmed, ensure_ascii=False, indent=2),
        )

    summaries = _extract_json_section(
        prompt,
        "SUMMARY BLOCKS (OLDER CONTINUITY HISTORY):",
        "RECENT PUBLIC EVENTS YOU KNOW:",
    )
    if isinstance(summaries, list) and summaries:
        prompt = _replace_json_section(
            prompt,
            "SUMMARY BLOCKS (OLDER CONTINUITY HISTORY):",
            "RECENT PUBLIC EVENTS YOU KNOW:",
            f"{_ISSUE240_COMPRESS_NOTE}\n"
            f"- {len(summaries)} older continuity summaries on file; "
            "recent window and active focus below carry this beat.",
        )

    interpretations = _extract_json_section(
        prompt,
        "YOUR RECENT INTERPRETATIONS:",
        "CANON ANCHORS:",
    )
    if isinstance(interpretations, list) and len(interpretations) > 2:
        trimmed = interpretations[-2:]
        note = f"{_ISSUE240_COMPRESS_NOTE}\n"
        prompt = _replace_json_section(
            prompt,
            "YOUR RECENT INTERPRETATIONS:",
            "CANON ANCHORS:",
            note + json.dumps(trimmed, ensure_ascii=False, indent=2),
        )

    cross_mem = _extract_json_section(
        prompt,
        "CROSS-SESSION USER MEMORY:",
        "PERSISTENT WORLD FACTS:",
    )
    if isinstance(cross_mem, list) and len(cross_mem) > 3:
        trimmed = cross_mem[:3]
        note = f"{_ISSUE240_COMPRESS_NOTE}\n"
        prompt = _replace_json_section(
            prompt,
            "CROSS-SESSION USER MEMORY:",
            "PERSISTENT WORLD FACTS:",
            note + json.dumps(trimmed, ensure_ascii=False, indent=2),
        )

    return prompt


def build_character_turn_prompt_issue240_v1_opening(char_name: str) -> str:
    return f"""You are {char_name}, taking your next turn in an ongoing roleplay scene.

Act primarily as this character: voice, pressure, subtext, and in-character judgment come first. While authoring your move, you are also responsible for accurately reporting certain continuity-relevant intent from what you actually write in this beat — when that intent exists.

Your JSON may include root semantic_proposals only as an honest report of covered intent in your authored beats (off_focal, reentry, excursion_lifecycle). semantic_proposals report authored continuity intent — {ISSUE240_DOCTRINE_PHRASE}. They declare what your move means for continuity to evaluate; emission is not proof of commit and must not be cosplayed.

If this beat has no covered intent, omit semantic_proposals entirely. Do not emit semantic_proposals: [] or proposal keys that your beats do not substantiate. Prose implication alone does not substitute for an explicit report."""


def build_issue240_v1_next3_participation_decision_frame() -> str:
    return """Ask one question while authoring this beat: did my move change focal participation?

Report semantic_proposals only when it did — stepping out of the active exchange, returning into it, or materially updating an existing off_focal/excursion state.

Emotional color alone is not enough unless participation actually shifted."""


def build_character_turn_prompt_issue240_v1_semantic_block(
    *,
    include_participation_frame: bool = False,
) -> str:
    block = f"""{ISSUE240_SEMANTIC_BLOCK_HEADER} (same move you are authoring):

When authoring this beat, determine whether your move actually includes:
- off_focal intent (you step out of the immediate focal exchange / go offstage)
- reentry intent (you return to the focal exchange from off-focal)
- excursion lifecycle intent (open, update, or close an excursion — include operation when applicable)

If it does, report that intent honestly in root semantic_proposals aligned with your beats (self-only; kinds off_focal | reentry | excursion_lifecycle).

If it does not, omit semantic_proposals entirely."""
    if include_participation_frame:
        block += f"\n\n{build_issue240_v1_next3_participation_decision_frame()}"
    return block + "\n\nDo not explain this analysis in dialogue or action beats."


def _insert_issue240_active_focus_capsule(prompt: str, capsule: str) -> str:
    return _insert_issue240_post_semantic_capsules(prompt, active_focus=capsule)


def _insert_issue240_post_semantic_capsules(
    prompt: str,
    *,
    participation_arc: str = "",
    threshold_bridge: str = "",
    active_focus: str = "",
) -> str:
    inserts = [
        part.strip()
        for part in (participation_arc, threshold_bridge, active_focus)
        if part.strip()
    ]
    if not inserts:
        return prompt
    block = "\n".join(inserts) + "\n"
    return re.sub(
        r"(Do not explain this analysis in dialogue or action beats\.\n)\n(YOUR PRIVATE STATE:)",
        rf"\1\n{block}\n\2",
        prompt,
        count=1,
        flags=re.DOTALL,
    )


def apply_issue240_v1_topology_transform(
    production_prompt: str,
    *,
    char_name: str,
    include_participation_frame: bool = False,
) -> str:
    """Apply #240 V1 framing to a production-shaped character turn prompt."""
    opening = build_character_turn_prompt_issue240_v1_opening(char_name)
    prompt = production_prompt.replace(
        "You are taking your next turn in an ongoing roleplay scene.",
        opening,
        1,
    )

    semantic_block = build_character_turn_prompt_issue240_v1_semantic_block(
        include_participation_frame=include_participation_frame,
    )
    prompt = re.sub(
        r"(TRIGGER FOR THIS BEAT:\n.*?\n)\n(YOUR PRIVATE STATE:)",
        rf"\1\n{semantic_block}\n\n\2",
        prompt,
        count=1,
        flags=re.DOTALL,
    )

    prompt = re.sub(
        r"5\. SOCIAL REALISM\n.*?7\. CANON AND WORLD CONSISTENCY\n.*?\n\n",
        _COMPRESSED_PRIORITIES_5_7 + "\n\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )

    prompt = re.sub(
        r"OUTPUT RULES:.*\Z",
        _SLIM_OUTPUT_RULES + "\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    return prompt


def apply_issue240_v1_next_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """V1 plus adaptive beat-local social/emotional focus capsule."""
    char_name = str(kwargs.get("char_name") or "")
    prompt = apply_issue240_v1_topology_transform(production_prompt, char_name=char_name)
    if not should_emit_social_focus_capsule(**kwargs):
        return prompt
    capsule = build_issue240_v1_next_social_focus_capsule(**kwargs)
    return _insert_issue240_active_focus_capsule(prompt, capsule)


def build_character_turn_prompt_issue240_v1_next(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next_topology_transform(base, **kwargs)


def apply_issue240_v1_next2_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """V1 plus long-prompt compression and stronger active-focus capsule."""
    char_name = str(kwargs.get("char_name") or "")
    base = apply_issue240_v1_next2_long_prompt_compression(production_prompt, **kwargs)
    prompt = apply_issue240_v1_topology_transform(base, char_name=char_name)
    if not should_emit_social_focus_capsule(**kwargs):
        return prompt
    capsule = build_issue240_v1_next2_active_focus_capsule(**kwargs)
    return _insert_issue240_active_focus_capsule(prompt, capsule)


def build_character_turn_prompt_issue240_v1_next2(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next2_topology_transform(base, **kwargs)


def apply_issue240_v1_next3_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """v1_next2 stack plus abstract participation-state decision frame."""
    char_name = str(kwargs.get("char_name") or "")
    base = apply_issue240_v1_next2_long_prompt_compression(production_prompt, **kwargs)
    prompt = apply_issue240_v1_topology_transform(
        base,
        char_name=char_name,
        include_participation_frame=True,
    )
    if not should_emit_social_focus_capsule(**kwargs):
        return prompt
    capsule = build_issue240_v1_next2_active_focus_capsule(**kwargs)
    return _insert_issue240_active_focus_capsule(prompt, capsule)


def build_character_turn_prompt_issue240_v1_next3(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next3_topology_transform(base, **kwargs)


def apply_issue240_v1_next4_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """v1_next3 stack plus beat-local recent participation arc."""
    char_name = str(kwargs.get("char_name") or "")
    base = apply_issue240_v1_next2_long_prompt_compression(production_prompt, **kwargs)
    prompt = apply_issue240_v1_topology_transform(
        base,
        char_name=char_name,
        include_participation_frame=True,
    )
    if not should_emit_social_focus_capsule(**kwargs):
        return prompt
    arc = build_issue240_v1_next4_participation_arc(**kwargs)
    focus = build_issue240_v1_next2_active_focus_capsule(**kwargs)
    return _insert_issue240_post_semantic_capsules(
        prompt,
        participation_arc=arc,
        active_focus=focus,
    )


def build_character_turn_prompt_issue240_v1_next4(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next4_topology_transform(base, **kwargs)


def build_issue240_v1_next5_opening(char_name: str) -> str:
    return f"""You are {char_name}, taking your next turn in an ongoing roleplay scene.

Act primarily as this character: voice, pressure, subtext, and in-character judgment come first. Every beat also requires an explicit root ``semantic_evaluation`` judgment (see trigger-adjacent self-report below and OUTPUT RULES).

Honest ``no_covered_change`` is valid when your authored beats contain no covered participation shift.

Do not emit root ``semantic_proposals`` or empty proposal arrays."""


def build_issue240_v1_next5_semantic_block() -> str:
    return f"""{ISSUE240_SEMANTIC_BLOCK_HEADER} (same move you are authoring):

After authoring your beats, make an explicit semantic judgment for this beat.

Required root field every beat: ``semantic_evaluation`` with:
- ``decision``: ``covered_change`` or ``no_covered_change``
- ``proposals``: non-empty array only when ``decision`` is ``covered_change`` (self-only; kinds off_focal | reentry | excursion_lifecycle)

``covered_change`` = your beats include off_focal, reentry, or excursion lifecycle intent.
``no_covered_change`` = you considered covered semantics and nothing materially changed — omit proposals.

Do not emit root ``semantic_proposals``. Do not emit ``semantic_proposals: []``.

{build_issue240_v1_next3_participation_decision_frame()}

Do not explain this analysis in dialogue or action beats."""


def _apply_issue240_v1_next5_prompt_overrides(prompt: str, char_name: str) -> str:
    prompt = prompt.replace(
        build_character_turn_prompt_issue240_v1_opening(char_name),
        build_issue240_v1_next5_opening(char_name),
        1,
    )
    prompt = re.sub(
        rf"{re.escape(ISSUE240_SEMANTIC_BLOCK_HEADER)}.*?Do not explain this analysis in dialogue or action beats\.",
        build_issue240_v1_next5_semantic_block().rstrip(),
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    prompt = re.sub(
        r"OUTPUT RULES:.*\Z",
        _V1_NEXT5_SLIM_OUTPUT_RULES + "\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    return prompt


def apply_issue240_v1_next5_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """v1_next4 stack plus mandatory semantic_evaluation judgment."""
    prompt = apply_issue240_v1_next4_topology_transform(production_prompt, **kwargs)
    return _apply_issue240_v1_next5_prompt_overrides(
        prompt,
        str(kwargs.get("char_name") or ""),
    )


def build_character_turn_prompt_issue240_v1_next5(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next5_topology_transform(base, **kwargs)


def build_issue240_v1_next6_covered_change_threshold_bridge() -> str:
    return f"""{ISSUE240_V1_NEXT6_THRESHOLD_BRIDGE_HEADER} (recent arc — do not recite in dialogue):
If the recent participation arc places you withdrawn, at the margin, or partly outside the active exchange, a beat that continues, deepens, or reverses that distance may be ``covered_change`` when it materially changes focal participation.
Use ``covered_change`` only when this beat maintains or shifts that participation state; mere emotional color without a participation change is ``no_covered_change``.
"""


def apply_issue240_v1_next6_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """v1_next5 stack plus arc-linked covered-change threshold bridge."""
    char_name = str(kwargs.get("char_name") or "")
    base = apply_issue240_v1_next2_long_prompt_compression(production_prompt, **kwargs)
    prompt = apply_issue240_v1_topology_transform(
        base,
        char_name=char_name,
        include_participation_frame=True,
    )
    if should_emit_social_focus_capsule(**kwargs):
        arc = build_issue240_v1_next4_participation_arc(**kwargs)
        bridge = build_issue240_v1_next6_covered_change_threshold_bridge()
        focus = build_issue240_v1_next2_active_focus_capsule(**kwargs)
        prompt = _insert_issue240_post_semantic_capsules(
            prompt,
            participation_arc=arc,
            threshold_bridge=bridge,
            active_focus=focus,
        )
    prompt = _apply_issue240_v1_next5_prompt_overrides(prompt, char_name)
    return prompt


def build_character_turn_prompt_issue240_v1_next6(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next6_topology_transform(base, **kwargs)


def build_issue240_v1_next7_threshold_calibration() -> str:
    return """Covered-change threshold (calibration — do not recite in dialogue):
``covered_change`` does not require a dramatic or physical exit.

If the recent participation arc shows you at the edge of the exchange, this beat can be ``covered_change`` when it materially continues that withdrawal, deepens that distance, or reverses it by rejoining the active exchange.

Use ``no_covered_change`` only when the beat expresses emotion without changing that participation state."""


def build_issue240_v1_next7_semantic_block() -> str:
    return f"""{ISSUE240_SEMANTIC_BLOCK_HEADER} (same move you are authoring):

After authoring your beats, make an explicit semantic judgment for this beat.

Required root field every beat: ``semantic_evaluation`` with:
- ``decision``: ``covered_change`` or ``no_covered_change``
- ``proposals``: non-empty array only when ``decision`` is ``covered_change`` (self-only; kinds off_focal | reentry | excursion_lifecycle)

``covered_change`` = your beats materially shift focal participation — including gradual continue/deepen/reverse at the margin when supported by recent arc and your beats.
``no_covered_change`` = you considered covered semantics and participation state did not materially change — omit proposals.

Do not emit root ``semantic_proposals``. Do not emit ``semantic_proposals: []``.

{build_issue240_v1_next3_participation_decision_frame()}

{build_issue240_v1_next7_threshold_calibration()}

Do not explain this analysis in dialogue or action beats."""


def _apply_issue240_v1_next7_prompt_overrides(prompt: str, char_name: str) -> str:
    prompt = prompt.replace(
        build_character_turn_prompt_issue240_v1_opening(char_name),
        build_issue240_v1_next5_opening(char_name),
        1,
    )
    prompt = re.sub(
        rf"{re.escape(ISSUE240_SEMANTIC_BLOCK_HEADER)}.*?Do not explain this analysis in dialogue or action beats\.",
        build_issue240_v1_next7_semantic_block().rstrip(),
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    prompt = re.sub(
        r"OUTPUT RULES:.*\Z",
        _V1_NEXT5_SLIM_OUTPUT_RULES + "\n",
        prompt,
        count=1,
        flags=re.DOTALL,
    )
    return prompt


def apply_issue240_v1_next7_topology_transform(
    production_prompt: str,
    **kwargs: Any,
) -> str:
    """v1_next6 stack plus semantic-cluster covered-change threshold calibration."""
    char_name = str(kwargs.get("char_name") or "")
    base = apply_issue240_v1_next2_long_prompt_compression(production_prompt, **kwargs)
    prompt = apply_issue240_v1_topology_transform(
        base,
        char_name=char_name,
        include_participation_frame=True,
    )
    if should_emit_social_focus_capsule(**kwargs):
        arc = build_issue240_v1_next4_participation_arc(**kwargs)
        bridge = build_issue240_v1_next6_covered_change_threshold_bridge()
        focus = build_issue240_v1_next2_active_focus_capsule(**kwargs)
        prompt = _insert_issue240_post_semantic_capsules(
            prompt,
            participation_arc=arc,
            threshold_bridge=bridge,
            active_focus=focus,
        )
    prompt = _apply_issue240_v1_next7_prompt_overrides(prompt, char_name)
    return prompt


def build_character_turn_prompt_issue240_v1_next7(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_next7_topology_transform(base, **kwargs)


def build_character_turn_prompt_issue240_v1(**kwargs: Any) -> str:
    base = _production_build_character_turn_prompt(**kwargs)
    return apply_issue240_v1_topology_transform(
        base,
        char_name=str(kwargs.get("char_name") or ""),
    )


def resolve_character_turn_prompt_builder() -> Callable[..., str]:
    mode = issue240_prompt_topology_mode()
    if mode == "v1_next7":
        return build_character_turn_prompt_issue240_v1_next7
    if mode == "v1_next6":
        return build_character_turn_prompt_issue240_v1_next6
    if mode == "v1_next5":
        return build_character_turn_prompt_issue240_v1_next5
    if mode == "v1_next4":
        return build_character_turn_prompt_issue240_v1_next4
    if mode == "v1_next3":
        return build_character_turn_prompt_issue240_v1_next3
    if mode == "v1_next2":
        return build_character_turn_prompt_issue240_v1_next2
    if mode == "v1_next":
        return build_character_turn_prompt_issue240_v1_next
    if mode == "v1":
        return build_character_turn_prompt_issue240_v1
    return _production_build_character_turn_prompt


def build_character_turn_prompt_for_runtime(**kwargs: Any) -> str:
    """Runtime entry: production baseline unless ``RP_ISSUE240_PROMPT_TOPOLOGY`` is set."""
    return resolve_character_turn_prompt_builder()(**kwargs)
