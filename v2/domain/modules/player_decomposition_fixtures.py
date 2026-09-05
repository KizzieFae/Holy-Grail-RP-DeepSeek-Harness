"""Fixture builders for player perceptual decomposition envelopes (#91 tests)."""

from __future__ import annotations

from typing import Any

from player_source_accounting import (
    SOURCE_ACCOUNTING_NORMALIZATION,
    normalize_source_for_indexing,
    normalized_source_sha256,
)


def build_player_decomposition_for_content(
    content: str,
    *,
    kind: str = "speech",
    scope: str = "public",
    characters: list[str] | None = None,
    unit_id: str = "u1",
    segment_id: str = "s1",
) -> dict[str, Any]:
    """Build a minimal valid player decomposition envelope."""
    normalized = normalize_source_for_indexing(content)
    length = len(normalized)
    if length == 0:
        return {
            "perceptual_visibility": {"units": []},
            "source_accounting": {
                "source_length": 0,
                "source_sha256": normalized_source_sha256(normalized),
                "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
                "segments": [
                    {
                        "segment_id": segment_id,
                        "char_start": 0,
                        "char_end": 0,
                        "disposition": "non_projects",
                        "unit_ids": [],
                    }
                ],
            },
            "generation": {"inference_id": "test-player-decomposition"},
        }

    recipients: dict[str, Any] = {
        "scope": scope,
        "characters": list(characters or []),
        "roles": [],
    }
    return {
        "perceptual_visibility": {
            "units": [
                {
                    "unit_id": unit_id,
                    "kind": kind,
                    "text": normalized,
                    "recipients": recipients,
                    "source_provenance": {
                        "segment_ids": [segment_id],
                        "order_index": 0,
                    },
                    "source": "player_decomposition",
                }
            ]
        },
        "source_accounting": {
            "source_length": length,
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": [
                {
                    "segment_id": segment_id,
                    "char_start": 0,
                    "char_end": length,
                    "disposition": "projects",
                    "unit_ids": [unit_id],
                }
            ],
        },
        "generation": {"inference_id": "test-player-decomposition"},
    }


def build_multi_segment_player_decomposition(
    content: str,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a player decomposition with explicit segments and units."""
    normalized = normalize_source_for_indexing(content)
    units: list[dict[str, Any]] = []
    accounting_segments: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        unit_id = str(segment.get("unit_id", f"u{index + 1}"))
        segment_id = str(segment.get("segment_id", f"s{index + 1}"))
        start = int(segment["char_start"])
        end = int(segment["char_end"])
        disposition = str(segment.get("disposition", "projects"))
        kind = str(segment.get("kind", "speech"))
        scope = str(segment.get("scope", "public"))
        characters = list(segment.get("characters") or [])
        text = normalized[start:end]
        unit_ids: list[str] = []
        if disposition == "projects":
            unit_ids = [unit_id]
            units.append(
                {
                    "unit_id": unit_id,
                    "kind": kind,
                    "text": text,
                    "recipients": {
                        "scope": scope,
                        "characters": characters,
                        "roles": [],
                    },
                    "source_provenance": {
                        "segment_ids": [segment_id],
                        "order_index": index,
                    },
                    "source": "player_decomposition",
                }
            )
        accounting_segments.append(
            {
                "segment_id": segment_id,
                "char_start": start,
                "char_end": end,
                "disposition": disposition,
                "unit_ids": unit_ids,
            }
        )
    return {
        "perceptual_visibility": {"units": units},
        "source_accounting": {
            "source_length": len(normalized),
            "source_sha256": normalized_source_sha256(normalized),
            "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
            "segments": accounting_segments,
        },
        "generation": {"inference_id": "test-player-decomposition"},
    }


# Parent Issue #88 mixed-turn regression fixture (deterministic controlled decomposition).
ISSUE_88_UNIT_DEPARTURE = "u_departure"
ISSUE_88_UNIT_PRIVATE = "u_private"
ISSUE_88_UNIT_RETURN = "u_return"
ISSUE_88_UNIT_COMPLETION = "u_completion"
ISSUE_88_PRIVATE_METHOD_TOKEN = "tension-wrench rake technique"
ISSUE_88_COMPLETION_TOKEN = "Panel secured"
ISSUE_88_DEPARTURE_TOKEN = "walks away from Harley"
ISSUE_88_RETURN_TOKEN = "steps back into Harley's view"


def build_issue_88_mixed_turn_fixture() -> tuple[str, dict[str, Any]]:
    """Controlled #88-shaped mixed player turn with complete source accounting."""
    part_departure = (
        f"The player {ISSUE_88_DEPARTURE_TOKEN} toward the storeroom archway."
    )
    part_private = (
        f" Behind the closed door, the player works a concealed floor-panel latch "
        f"with a {ISSUE_88_PRIVATE_METHOD_TOKEN}."
    )
    part_return = f" The player {ISSUE_88_RETURN_TOKEN}, brushing dust from their hands."
    part_completion = (
        f' "{ISSUE_88_COMPLETION_TOKEN}—the seam is hidden," the player says to the group.'
    )
    content = part_departure + part_private + part_return + part_completion
    normalized = normalize_source_for_indexing(content)
    departure_end = len(normalize_source_for_indexing(part_departure))
    private_end = departure_end + len(normalize_source_for_indexing(part_private))
    return_end = private_end + len(normalize_source_for_indexing(part_return))
    decomposition = build_multi_segment_player_decomposition(
        content,
        [
            {
                "unit_id": ISSUE_88_UNIT_DEPARTURE,
                "segment_id": "s_departure",
                "char_start": 0,
                "char_end": departure_end,
                "kind": "observable_event",
                "scope": "public",
            },
            {
                "unit_id": ISSUE_88_UNIT_PRIVATE,
                "segment_id": "s_private",
                "char_start": departure_end,
                "char_end": private_end,
                "kind": "observable_event",
                "scope": "private",
                "characters": ["Celina"],
            },
            {
                "unit_id": ISSUE_88_UNIT_RETURN,
                "segment_id": "s_return",
                "char_start": private_end,
                "char_end": return_end,
                "kind": "observable_event",
                "scope": "public",
            },
            {
                "unit_id": ISSUE_88_UNIT_COMPLETION,
                "segment_id": "s_completion",
                "char_start": return_end,
                "char_end": len(normalized),
                "kind": "speech",
                "scope": "public",
            },
        ],
    )
    return content, decomposition


# Issue #120 seiza/Japan regression (issue112-seiza-japan-regression).
ISSUE_120_SEIZA_JAPAN_TURN = (
    'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
    "they were not in Japan, but hold habits died hard. "
    '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
    'she hesittated, looking up. '
    '"Have you ever had a time in your life when the entire road has been destroyed and you '
    "realized that there was another path, one you would not have even considered before? "
    'Some people see misfortune, I see an opportunity to reinvent."'
)
ISSUE_120_UNIT_SEIZA = "u_seiza"
ISSUE_120_UNIT_JAPAN = "u_japan"
ISSUE_120_UNIT_SPEECH_1 = "u_speech_1"
ISSUE_120_UNIT_HESITATION = "u_hesitation"
ISSUE_120_UNIT_SPEECH_2 = "u_speech_2"
ISSUE_120_JAPAN_TOKEN = "they were not in Japan, but hold habits died hard."


def build_issue_120_seiza_japan_fixture() -> tuple[str, dict[str, Any]]:
    """Deterministic #120 seiza/Japan decomposition with generalized internal unit."""
    content = ISSUE_120_SEIZA_JAPAN_TURN
    normalized = normalize_source_for_indexing(content)
    japan_start = normalized.index(ISSUE_120_JAPAN_TOKEN)
    japan_end = japan_start + len(ISSUE_120_JAPAN_TOKEN)
    speech_1 = (
        '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..."'
    )
    speech_1_start = normalized.index(speech_1)
    speech_1_end = speech_1_start + len(speech_1)
    hesitation = "she hesittated, looking up."
    hesitation_start = normalized.index(hesitation)
    hesitation_end = hesitation_start + len(hesitation)
    speech_2_start = normalized.index('"Have you ever had a time')
    speech_2_end = len(normalized)
    decomposition = build_multi_segment_player_decomposition(
        content,
        [
            {
                "unit_id": ISSUE_120_UNIT_SEIZA,
                "segment_id": "s_seiza",
                "char_start": 0,
                "char_end": japan_start,
                "kind": "observable_event",
                "scope": "present",
            },
            {
                "unit_id": ISSUE_120_UNIT_JAPAN,
                "segment_id": "s_japan",
                "char_start": japan_start,
                "char_end": speech_1_start,
                "kind": "internal",
                "scope": "private",
                "characters": ["Kizzie"],
            },
            {
                "unit_id": ISSUE_120_UNIT_SPEECH_1,
                "segment_id": "s_speech_1",
                "char_start": speech_1_start,
                "char_end": hesitation_start,
                "kind": "speech",
                "scope": "present",
            },
            {
                "unit_id": ISSUE_120_UNIT_HESITATION,
                "segment_id": "s_hesitation",
                "char_start": hesitation_start,
                "char_end": speech_2_start,
                "kind": "observable_event",
                "scope": "present",
            },
            {
                "unit_id": ISSUE_120_UNIT_SPEECH_2,
                "segment_id": "s_speech_2",
                "char_start": speech_2_start,
                "char_end": speech_2_end,
                "kind": "speech",
                "scope": "present",
            },
        ],
    )
    return content, decomposition
