"""Prompt fragments for NarrativeVisibilityRecord generation (#81)."""

from __future__ import annotations

import json


NARRATIVE_VISIBILITY_UNIT_KINDS = [
    "observable_scene",
    "observable_event",
    "speech",
    "internal",
    "presentation_only",
]

NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION = f"""
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{{
  "presentation_text": "<full human-facing narration in third person past tense>",
  "narrative_visibility": {{
    "units": [
      {{
        "unit_id": "u1",
        "kind": "observable_scene|observable_event|speech|internal|presentation_only",
        "text": "<verbatim prose fragment for this semantic unit>",
        "recipients": {{
          "scope": "public|present|directed|private|role_private|environmental",
          "characters": ["<optional character ids>"],
          "roles": ["<optional role names>"]
        }},
        "beat_index": <required for speech units — 0-based speech beat index>
      }}
    ]
  }}
}}

SEMANTIC UNIT RULES:
- observable_scene: perceptible environment/spatial/object/sensory detail any present character could notice.
- observable_event: perceptible action/event prose not already covered by structured speech beats.
- speech: dialogue tied to a structured speech beat; set beat_index; recipients must not exceed that beat's audibility.
- internal: private viewpoint/cognition; NEVER use scope public; narrow to the experiencing character.
- presentation_only: stylistic flourish for the human reader only; excluded from character cognition.

COVERAGE: Every substantive phrase in presentation_text must appear in exactly one unit (except presentation_only flourishes).
Do not paraphrase structured dialogue in speech units — use the exact quoted dialogue.
Do not place restricted/private dialogue inside observable_scene or observable_event units.
"""

OPENING_VISIBILITY_OUTPUT_INSTRUCTION = f"""
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{{
  "presentation_text": "<full opening narration>",
  "narrative_visibility": {{
    "units": [
      {{
        "unit_id": "u1",
        "kind": {"|".join(NARRATIVE_VISIBILITY_UNIT_KINDS)},
        "text": "<prose fragment>",
        "recipients": {{
          "scope": "public|present|directed|private|role_private|environmental",
          "characters": [],
          "roles": []
        }}
      }}
    ]
  }}
}}

Segment the opening into semantic units with accurate recipient scopes.
internal units must never be public. presentation_only is human-facing only.
Observable mansion/scene detail visible to present characters should be public or present scoped.
Private interior thoughts or knowledge not perceptible to others must be internal/private scoped.
"""


OPENING_SEGMENTATION_OUTPUT_INSTRUCTION = f"""
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{{
  "narrative_visibility": {{
    "units": [
      {{
        "unit_id": "u1",
        "kind": {"|".join(NARRATIVE_VISIBILITY_UNIT_KINDS)},
        "text": "<verbatim prose fragment from the opening>",
        "recipients": {{
          "scope": "public|present|directed|private|role_private|environmental",
          "characters": [],
          "roles": []
        }}
      }}
    ]
  }}
}}

Segment the authoritative opening prose into semantic units with accurate recipient scopes.
Do NOT return presentation_text — the opening prose is already fixed.
internal units must never be public. presentation_only is human-facing only.
Observable scene detail visible to present characters should be public or present scoped.
Private interior thoughts or knowledge not perceptible to others must be internal/private scoped.
Use exact character display names from the cast list in recipients.characters.
"""


def narrator_visibility_schema_hint(structured_move: dict | None = None) -> str:
    speech_indices: list[int] = []
    if isinstance(structured_move, dict):
        beats = structured_move.get("beats")
        if isinstance(beats, list):
            for idx, beat in enumerate(beats):
                if isinstance(beat, dict) and beat.get("type") == "speech":
                    speech_indices.append(idx)
    hint = {
        "speech_beat_indices": speech_indices,
        "unit_kinds": NARRATIVE_VISIBILITY_UNIT_KINDS,
    }
    return json.dumps(hint, ensure_ascii=False, indent=2)
