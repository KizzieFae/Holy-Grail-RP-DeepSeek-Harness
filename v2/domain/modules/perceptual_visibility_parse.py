"""Parse combined narrator/opening JSON envelopes with perceptual_visibility (#90)."""

from __future__ import annotations

import json
import re
from typing import Any


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_perceptual_visibility_envelope(
    raw: str,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """Return (presentation_text, perceptual_visibility_dict, error)."""
    if not raw or not str(raw).strip():
        return None, None, "empty output"

    stripped = _strip_code_fence(str(raw))
    if not stripped.startswith("{"):
        return stripped, None, None

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped, None, None

    if not isinstance(payload, dict):
        return stripped, None, "envelope not an object"

    presentation = payload.get("presentation_text")
    if presentation is None:
        presentation = payload.get("presentation")
    if presentation is None and isinstance(payload.get("text"), str):
        presentation = payload.get("text")

    presentation_text = str(presentation or "").strip() or None
    pvr = payload.get("perceptual_visibility")
    if pvr is not None and not isinstance(pvr, dict):
        return presentation_text, None, "perceptual_visibility not an object"

    units = pvr.get("units") if isinstance(pvr, dict) else None
    if units is not None and not isinstance(units, list):
        return presentation_text, None, "perceptual_visibility.units not a list"

    return presentation_text, (pvr if isinstance(pvr, dict) else None), None
