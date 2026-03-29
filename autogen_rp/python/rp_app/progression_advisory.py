"""Deterministic progression advisory: stall score, soft prompt guidance, beat-shift hook.

Advisory only — does not write continuity truth or override orchestration decisions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from beat_shift_state import plateau_snapshots_suggest_beat_shift

logger = logging.getLogger("rp_app.progression_advisory")

_HIGH_TENSION = frozenset({"high", "extreme"})
_ISSUE_STABLE = frozenset({"active", "escalating", ""})
_STALL_WEIGHT_PLATEAU = 0.35
_STALL_WEIGHT_HIGH_TENSION = 0.25
_STALL_WEIGHT_ISSUE_STABILITY = 0.25
_STALL_WEIGHT_LOW_CONSEQUENCE = 0.15
STALL_BEAT_SHIFT_THRESHOLD = 0.6
_LOW_CONSEQUENCE_MOVE_WINDOW = 4
_LOW_CONSEQUENCE_UNIQUE_MAX = 2
_MIN_MOVES_FOR_LOW_VARIETY = 3

DEFAULT_ADVANCEMENT_CHANNELS: list[str] = [
    "physical_action",
    "spatial_shift",
    "bureaucratic_followthrough",
    "social_reconfiguration",
    "consequence",
]

DEFAULT_COMMON_STALL_PATTERN = (
    "verbal escalation loop without material state change"
)

_CACHE_KEY = "_progression_advisory_cache"


def default_progression_profile() -> dict[str, Any]:
    return {
        "advancement_channels": list(DEFAULT_ADVANCEMENT_CHANNELS),
        "common_stall_pattern": DEFAULT_COMMON_STALL_PATTERN,
    }


def normalize_progression_profile(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = default_progression_profile()
    if not isinstance(raw, dict):
        return base
    ch = raw.get("advancement_channels")
    if isinstance(ch, list) and all(isinstance(x, str) and x.strip() for x in ch):
        base["advancement_channels"] = [str(x).strip() for x in ch]
    pat = raw.get("common_stall_pattern")
    if isinstance(pat, str) and pat.strip():
        base["common_stall_pattern"] = pat.strip()
    return base


def _humanize_channel(channel_id: str) -> str:
    return str(channel_id or "").replace("_", " ").strip() or channel_id


def compute_stall_score(
    *,
    scene_state: dict[str, Any],
    recent_structured_moves: list[dict[str, Any]],
    active_issues: list[dict[str, Any]],
    beat_shift_snapshots: list[dict[str, Any]],
) -> tuple[float, dict[str, bool]]:
    """Return (stall_score 0..1, stall_components). Deterministic; no LLM."""
    same_phase = bool(plateau_snapshots_suggest_beat_shift(beat_shift_snapshots)[0])
    tension_raw = str(scene_state.get("current_tension_level", "") or "").strip().lower()
    high_tension = tension_raw in _HIGH_TENSION

    issue_stability = False
    if active_issues:
        issue_stability = all(
            str(iss.get("status", "") or "").strip().lower() in _ISSUE_STABLE
            for iss in active_issues
            if isinstance(iss, dict)
        )

    low_consequence_variety = False
    tail = [
        m
        for m in (recent_structured_moves or [])[-_LOW_CONSEQUENCE_MOVE_WINDOW:]
        if isinstance(m, dict)
    ]
    if len(tail) >= _MIN_MOVES_FOR_LOW_VARIETY:
        flattened: list[str] = []
        for m in tail:
            cons = m.get("consequences")
            if isinstance(cons, list):
                for c in cons:
                    if c is not None and str(c).strip():
                        flattened.append(str(c).strip().lower())
        low_consequence_variety = (
            len(flattened) > 0
            and len(set(flattened)) <= _LOW_CONSEQUENCE_UNIQUE_MAX
        )

    stall_score = min(
        1.0,
        (_STALL_WEIGHT_PLATEAU if same_phase else 0.0)
        + (_STALL_WEIGHT_HIGH_TENSION if high_tension else 0.0)
        + (_STALL_WEIGHT_ISSUE_STABILITY if issue_stability else 0.0)
        + (_STALL_WEIGHT_LOW_CONSEQUENCE if low_consequence_variety else 0.0),
    )

    components = {
        "same_phase": same_phase,
        "high_tension": high_tension,
        "issue_stability": issue_stability,
        "low_consequence_variety": low_consequence_variety,
    }
    return stall_score, components


def stall_score_to_pressure(stall_score: float) -> str:
    if stall_score < 0.3:
        return "low"
    if stall_score < 0.6:
        return "medium"
    return "high"


def build_progression_advisory(
    *,
    stall_score: float,
    stall_components: dict[str, bool],
    progression_profile: dict[str, Any],
) -> dict[str, Any]:
    prof = normalize_progression_profile(progression_profile)
    pressure = stall_score_to_pressure(stall_score)
    channels = list(prof["advancement_channels"])
    pattern = str(prof["common_stall_pattern"] or DEFAULT_COMMON_STALL_PATTERN)
    human = ", ".join(_humanize_channel(c) for c in channels[:5])
    note = (
        f"Scene has remained in a high-friction interaction pattern ({pattern}); "
        f"favor advancing through one of: {human}. "
        "Avoid repeating the same type of verbal exchange unless strongly justified."
    )
    if len(note) > 400:
        note = note[:397] + "..."

    return {
        "stall_score": round(stall_score, 4),
        "progression_pressure": pressure,
        "recommended_channels": channels,
        "note": note,
        "stall_components": dict(stall_components),
    }


def build_progression_director_prompt_prefix(advisory: dict[str, Any]) -> str:
    if advisory.get("progression_pressure") != "high":
        return ""
    channels = advisory.get("recommended_channels") or []
    lines = [f"- {_humanize_channel(c)}" for c in channels[:6]]
    body = "\n".join(lines) if lines else "- concrete action or consequence"
    return (
        "PROGRESSION ADVISORY:\n"
        "The scene appears stalled in its current interaction pattern.\n"
        "Prefer advancing the scene through one of:\n"
        f"{body}\n"
        "Avoid repeating the same type of verbal exchange unless strongly justified.\n\n"
    )


PROGRESSION_CHARACTER_SUFFIX = (
    "\n\nPROGRESSION ADVISORY: The scene should advance through a concrete change in "
    "state (action, movement, consequence, or commitment), not only continued verbal "
    "escalation."
)


def should_append_progression_character_suffix(
    *,
    progression_pressure: str,
    beat_shift_active: bool,
) -> bool:
    if progression_pressure == "high":
        return True
    return progression_pressure == "medium" and beat_shift_active


def refresh_progression_advisory_cache(
    *,
    orchestration_state: dict[str, Any],
    active_issues: list[dict[str, Any]],
    progression_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute advisory from current orchestration snapshot; store on orchestration_state."""
    scene_state = orchestration_state.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    moves = orchestration_state.get("recent_structured_moves")
    if not isinstance(moves, list):
        moves = []
    snaps = orchestration_state.get("beat_shift_scene_snapshots")
    if not isinstance(snaps, list):
        snaps = []

    stall_score, stall_components = compute_stall_score(
        scene_state=scene_state,
        recent_structured_moves=moves,
        active_issues=active_issues,
        beat_shift_snapshots=snaps,
    )
    advisory = build_progression_advisory(
        stall_score=stall_score,
        stall_components=stall_components,
        progression_profile=progression_profile,
    )
    orchestration_state[_CACHE_KEY] = advisory
    return advisory


def get_cached_progression_advisory(
    orchestration_state: dict[str, Any],
) -> dict[str, Any] | None:
    raw = orchestration_state.get(_CACHE_KEY)
    return raw if isinstance(raw, dict) else None


def sync_progression_advisory_for_prompts(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any | None,
) -> dict[str, Any]:
    """Refresh advisory cache from continuity + orchestration (read-only on truth)."""
    raw_issues: list[dict[str, Any]] = []
    if continuity_manager is not None:
        ctx = continuity_manager.get_orchestration_context(
            active_issue_limit=4,
            recent_event_limit=4,
            summary_limit=3,
        )
        for iss in ctx.get("active_issues") or []:
            if hasattr(iss, "to_dict"):
                raw_issues.append(iss.to_dict())
    ss = orchestration_state.get("scene_state")
    tid = ""
    if isinstance(ss, dict):
        tid = str(ss.get("scene_template_id", "") or "")
    prof = load_progression_profile_for_template_id(tid)
    return refresh_progression_advisory_cache(
        orchestration_state=orchestration_state,
        active_issues=raw_issues,
        progression_profile=prof,
    )


def load_progression_profile_for_template_id(template_id: str) -> dict[str, Any]:
    """Static template progression_profile, or defaults if missing / load error."""
    tid = str(template_id or "").strip()
    if not tid:
        return default_progression_profile()
    try:
        from scene_template import SceneTemplateManager  # noqa: PLC0415

        template = SceneTemplateManager().load_template(tid)
        return normalize_progression_profile(template.progression_profile)
    except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError):
        return default_progression_profile()
