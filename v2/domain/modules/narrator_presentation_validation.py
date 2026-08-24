"""Deterministic Narrator presentation fidelity checks (Issue #24)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from character_move_adapters import (
    is_canonical_v2_move,
    iter_speech_beats,
    root_or_flat_dialogue_text,
)


@dataclass(frozen=True)
class NarratorPresentationValidationResult:
    accepted: bool
    validation_class: str
    reason: str
    retryable: bool


def _required_speech_dialogues(structured_move: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(structured_move, Mapping):
        return []
    if is_canonical_v2_move(structured_move):
        dialogues: list[str] = []
        for _, beat in iter_speech_beats(structured_move):
            dialogue = str(beat.get("dialogue", "") or "")
            if dialogue:
                dialogues.append(dialogue)
        return dialogues
    legacy = root_or_flat_dialogue_text(structured_move)
    return [legacy] if legacy else []


def validate_narrator_presentation(
    *,
    structured_move: Mapping[str, Any] | None,
    presentation_text: str,
) -> NarratorPresentationValidationResult:
    prose = str(presentation_text or "").strip()
    if not prose:
        return NarratorPresentationValidationResult(
            accepted=False,
            validation_class="structural",
            reason="presentation text is empty",
            retryable=True,
        )

    required_speech = _required_speech_dialogues(structured_move)
    if not required_speech:
        return NarratorPresentationValidationResult(
            accepted=True,
            validation_class="accepted",
            reason="",
            retryable=False,
        )

    last_index = -1
    for index, dialogue in enumerate(required_speech, start=1):
        position = prose.find(dialogue)
        if position < 0:
            return NarratorPresentationValidationResult(
                accepted=False,
                validation_class="speech_verbatim",
                reason=f"required speech beat {index} missing verbatim dialogue",
                retryable=True,
            )
        if position <= last_index:
            return NarratorPresentationValidationResult(
                accepted=False,
                validation_class="speech_order",
                reason=f"required speech beat {index} out of committed order",
                retryable=True,
            )
        last_index = position

    return NarratorPresentationValidationResult(
        accepted=True,
        validation_class="accepted",
        reason="",
        retryable=False,
    )
