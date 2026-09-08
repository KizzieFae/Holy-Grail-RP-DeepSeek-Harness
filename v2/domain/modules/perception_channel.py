"""Perception channel classification for PVR units (#155)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

PerceptionChannel = Literal["visual", "auditory", "non_perceptual"]
ChannelAuthority = Literal["explicit", "inferred", "uncertain"]

VALID_PERCEPTION_CHANNELS = frozenset({"visual", "auditory", "non_perceptual"})

_KNOCK_RE = re.compile(
    r"\b(knock(s|ed|ing)?|rap(s|ped|ping)?|bang(s|ed|ing)?)\b",
    re.IGNORECASE,
)
_SPEECH_DELIVERY_RE = re.compile(
    r"\b(call(s|ed|ing)?\s+through|shout(s|ed|ing)?|yell(s|ed|ing)?|"
    r"say(s|ing)?\s+through|speak(s|ing)?\s+through)\b",
    re.IGNORECASE,
)
_QUOTED_SPEECH_RE = re.compile(r'"[^"]+"|\'[^\']+\'')
_VISUAL_RE = re.compile(
    r"\b(look(s|ed|ing)?|glanc(e|es|ed|ing)|smooth(s|ed|ing)?|hesitat(e|es|ed|ing)|"
    r"peer(s|ed|ing)?|gaz(e|es|ed|ing)|watch(es|ed|ing)?|see(s|ing)?|stare(s|d|ing)?|"
    r"check(s|ed|ing)?\s+the\s+(address|house\s+number|number))\b",
    re.IGNORECASE,
)
_NERVOUS_INTERNAL_RE = re.compile(
    r"\b(nervous(ly)?|anxious(ly)?|worried|afraid)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PerceptionChannelResolution:
    channel: PerceptionChannel
    authority: ChannelAuthority

    @property
    def uncertain(self) -> bool:
        return self.authority == "uncertain"


def normalize_perception_channel(value: Any) -> PerceptionChannel | None:
    raw = str(value or "").strip().lower()
    if raw in VALID_PERCEPTION_CHANNELS:
        return raw  # type: ignore[return-value]
    return None


def infer_channel_from_text(text: str) -> PerceptionChannelResolution:
    """Deterministic channel inference; uncertain when cues are insufficient."""
    snippet = str(text or "").strip()
    if not snippet:
        return PerceptionChannelResolution("non_perceptual", "explicit")

    has_knock = bool(_KNOCK_RE.search(snippet))
    has_speech_delivery = bool(_SPEECH_DELIVERY_RE.search(snippet))
    has_quoted_speech = bool(_QUOTED_SPEECH_RE.search(snippet))
    has_visual = bool(_VISUAL_RE.search(snippet))
    has_internal = bool(_NERVOUS_INTERNAL_RE.search(snippet))

    if has_knock or has_speech_delivery:
        return PerceptionChannelResolution("auditory", "inferred")
    if has_quoted_speech and not has_visual:
        return PerceptionChannelResolution("auditory", "inferred")
    if has_internal and not has_visual and not has_quoted_speech:
        return PerceptionChannelResolution("non_perceptual", "inferred")
    if has_visual and not has_knock and not has_quoted_speech and not has_speech_delivery:
        return PerceptionChannelResolution("visual", "inferred")
    if has_visual and (has_knock or has_quoted_speech or has_speech_delivery):
        return PerceptionChannelResolution("visual", "uncertain")
    if has_quoted_speech:
        return PerceptionChannelResolution("auditory", "uncertain")
    return PerceptionChannelResolution("non_perceptual", "uncertain")


def resolve_unit_perception_channel(unit: Any) -> PerceptionChannel:
    return resolve_unit_perception_channel_with_authority(unit).channel


def resolve_unit_perception_channel_with_authority(unit: Any) -> PerceptionChannelResolution:
    """Resolve perception channel for a PVR unit with authority metadata."""
    kind = str(getattr(unit, "kind", "") or "").strip()
    channel_raw = None
    if hasattr(unit, "perception_channel"):
        channel_raw = getattr(unit, "perception_channel", None)
    elif isinstance(unit, dict):
        channel_raw = unit.get("perception_channel")
    else:
        recipients = getattr(unit, "recipients", None)
        if isinstance(recipients, dict):
            channel_raw = recipients.get("perception_channel")
    normalized = normalize_perception_channel(channel_raw)
    if normalized:
        return PerceptionChannelResolution(normalized, "explicit")
    if kind == "internal":
        return PerceptionChannelResolution("non_perceptual", "explicit")
    if kind in ("observable_event", "observable_scene"):
        return PerceptionChannelResolution("visual", "explicit")
    if kind == "speech":
        return PerceptionChannelResolution("auditory", "explicit")
    if kind == "presentation_only":
        return PerceptionChannelResolution("non_perceptual", "explicit")
    text = str(getattr(unit, "text", "") or "")
    if isinstance(unit, dict):
        text = str(unit.get("text", "") or "")
    return infer_channel_from_text(text)


def text_has_mixed_perception_modalities(text: str) -> bool:
    snippet = str(text or "").strip()
    if not snippet:
        return False
    has_auditory = bool(
        _KNOCK_RE.search(snippet)
        or _SPEECH_DELIVERY_RE.search(snippet)
        or _QUOTED_SPEECH_RE.search(snippet)
    )
    has_visual = bool(_VISUAL_RE.search(snippet))
    return has_auditory and has_visual


def uniform_bundle_requires_decomposition(unit: Any) -> bool:
    kind = str(getattr(unit, "kind", "") or "").strip()
    text = str(getattr(unit, "text", "") or "")
    if isinstance(unit, dict):
        text = str(unit.get("text", "") or "")
    return kind == "uniform_projection" and text_has_mixed_perception_modalities(text)
