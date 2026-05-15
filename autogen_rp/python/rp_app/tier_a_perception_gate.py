"""Deterministic Tier A perception smoke gate (GitHub #214).

Inspects character ``*_full.json`` audit artifacts for v2 speech beats with
``directed`` / ``private`` audibility and non-empty ``audience``.  Does **not**
assert continuity-grounded offstage or excursion adoption (#216 / Tier B).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TierAPerceptionGateError(RuntimeError):
    """Raised when a Tier A perception-smoke audit session fails deterministic checks."""


def _speech_beats_v2(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    if parsed.get("move_schema_version") != 2:
        return []
    beats = parsed.get("beats")
    if not isinstance(beats, list):
        return []
    out: list[dict[str, Any]] = []
    for b in beats:
        if isinstance(b, dict) and b.get("type") == "speech":
            out.append(b)
    return out


def _scan_character_full_audits(session_root: Path) -> list[Path]:
    return sorted(session_root.rglob("audit_*_*_full.json"))


def _analyze_tier_a_session(
    session_dir: Path,
    *,
    bounded_token: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    root = session_dir.resolve()
    errors: list[str] = []
    if not root.is_dir():
        return [f"session dir not found: {root}"], {"speech_beats_scanned": 0}

    all_speech: list[tuple[str, dict[str, Any]]] = []

    for path in _scan_character_full_audits(root):
        if "_narrator_" in path.name:
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue
        bot_type = str(raw.get("bot_type") or "")
        if bot_type != "character":
            continue
        po = raw.get("parsed_output")
        if not isinstance(po, dict):
            continue
        label = path.name
        for beat in _speech_beats_v2(po):
            all_speech.append((label, beat))

    has_non_public = False
    for label, beat in all_speech:
        aud = str(beat.get("audibility") or "").strip().lower()
        if aud in ("directed", "private"):
            has_non_public = True
            audience = beat.get("audience")
            if not isinstance(audience, list) or len(audience) == 0:
                dia = str(beat.get("dialogue") or "")[:80]
                errors.append(
                    f"{label}: speech beat audibility={aud!r} requires non-empty audience "
                    f"(dialogue excerpt: {dia!r})"
                )

    if not has_non_public:
        errors.append(
            "no character parsed_output speech beat with audibility "
            "'directed' or 'private' found under session"
        )

    bounded_token_found: bool | None = None
    if bounded_token and str(bounded_token).strip():
        tok = str(bounded_token).strip()
        bounded_token_found = False
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".json", ".txt", ".md"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if tok in text:
                bounded_token_found = True
                break

    meta: dict[str, Any] = {
        "speech_beats_scanned": len(all_speech),
        "bounded_token": bounded_token,
        "bounded_token_found": bounded_token_found,
    }
    return errors, meta


def validate_tier_a_perception_smoke_session(
    session_dir: Path,
    *,
    bounded_token: str | None = None,
) -> dict[str, Any]:
    """Validate audit JSON under ``session_dir`` (e.g. ``.../rp_audits/session_N``).

    Returns a report dict with ``ok``, ``errors``, and scan metadata.

    Raises:
        TierAPerceptionGateError: on any validation failure.
    """
    errors, meta = _analyze_tier_a_session(session_dir, bounded_token=bounded_token)
    report: dict[str, Any] = {"ok": not errors, "errors": errors, **meta}
    if errors:
        raise TierAPerceptionGateError(
            "Tier A perception gate failed:\n- " + "\n- ".join(errors)
        )
    return report


def validate_tier_a_perception_smoke_session_report_only(
    session_dir: Path,
    *,
    bounded_token: str | None = None,
) -> dict[str, Any]:
    """Same analysis as :func:`validate_tier_a_perception_smoke_session` but never raises."""
    errors, meta = _analyze_tier_a_session(session_dir, bounded_token=bounded_token)
    return {"ok": not errors, "errors": errors, **meta}
