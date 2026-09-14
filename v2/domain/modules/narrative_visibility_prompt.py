"""Prompt fragments for perceptual visibility generation (#90 / #81 lineage)."""

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
  "perceptual_visibility": {{
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
  "perceptual_visibility": {{
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
  "perceptual_visibility": {{
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
Do NOT include beat_index or other CharacterMove beat provenance — template openings exist
before any CharacterMove beats at session initialization.
Genuine quoted dialogue may use kind=speech with recipient scope only.
internal units must never be public. presentation_only is human-facing only.
Observable scene detail visible to present characters should be public or present scoped.
Private interior thoughts or knowledge not perceptible to others must be internal/private scoped.
Use exact character display names from the cast list in recipients.characters.
"""


PLAYER_SEMANTIC_DECOMPOSITION_OUTPUT_INSTRUCTION = f"""
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{{
  "semantic_decomposition": {{
    "units": [
      {{
        "kind": "observable_scene|observable_event|speech|internal",
        "text": "<verbatim semantic excerpt from the player source>",
        "recipients": {{
          "scope": "public|present|directed|private|role_private|environmental",
          "characters": ["<optional character ids>"],
          "roles": ["<optional role names>"]
        }}
      }}
    ]
  }}
}}

SEMANTIC RULES:
- Kind identifies perceptibility in principle; scope identifies entitlement for perceptible information.
- observable_scene / observable_event: perceptible in principle; scope determines which characters may perceive.
- speech: spoken or communicated content; scope and authority determine recipients.
- internal: intrinsically nonperceptual player information (never public scope). Use for unexpressed
  cognition, private mental state, nonperceptual explanatory narration, background/context, and other
  player-authored narrative facts not directly observable in the scene — not only literal thoughts.
- Hidden/concealed physical actions: observable_event with restrictive recipient scope (NOT internal).
- Examples: "Kizzie settled into seiza." → observable_event; "They weren't in Japan, but old habits
  died hard." → internal; concealed latch work behind a closed door → observable_event + private scope.

COMPLETENESS:
- Every substantive (non-whitespace) character in the player source must appear in exactly one unit excerpt.
- Unit excerpts must be verbatim substrings of the player source.
- Unit excerpts must not overlap.
- Whitespace between semantic units may be omitted from excerpts.
- Array order is not authoritative.

DO NOT include: unit_id, segment_id, char_start, char_end, order_index, source_accounting,
occurrence numbers, disambiguation metadata, or any mechanical indexing/accounting fields.
- Do NOT use kind uniform_projection — that kind is reserved for deterministic checker synthesis only.
"""

# Legacy combined contract retained for reference/tests migrating off pre-#124 envelopes.
PLAYER_DECOMPOSITION_OUTPUT_INSTRUCTION = PLAYER_SEMANTIC_DECOMPOSITION_OUTPUT_INSTRUCTION


PLAYER_VISIBILITY_TRIAGE_OUTPUT_INSTRUCTION = """
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{
  "uniform_projection_safe": true|false,
  "reason": "<short audit-only code, e.g. affirmative_uniform_present|requires_semantic_decomposition|uncertain>"
}

ROLE: Routing checker only. You do NOT classify semantic units, name recipients, or produce source spans.

Set uniform_projection_safe to true ONLY when you can affirmatively assert that EVERY meaningful
portion of the complete player source is safe to represent as ONE uniformly projected unit visible
to ALL Characters present at submit time, with NO semantic decomposition required to prevent
over-disclosure.

Return uniform_projection_safe: false when ANY portion may contain:
- intrinsically nonperceptual or internal information;
- unexpressed cognition or private mental state;
- explanatory/background/contextual narration not directly perceptible in the scene;
- player-authored narrative exposition establishing story truth Characters cannot directly observe
  (e.g. geographic/historical context, off-screen facts, authorial asides like "they were not in Japan");
- concealed or restricted observable actions;
- private, directed, role-private, or subset entitlement;
- mixed entitlement within the same turn;
- any ambiguity about the above.

Implicit descriptions of a Player's unexpressed internal preparation or private mental state
(for example bracing, steeling oneself, silently resolving, or privately deciding before acting)
are private/internal content and are NOT uniformly projectable even when paired with observable actions.

A turn that mixes observable behavior with any unexpressed internal state is NOT uniformly projectable.

CRITICAL EXAMPLES (must return false):
- Action plus authorial aside: sitting in seiza WHILE narrating they are not in Japan / old habits —
  the aside is not uniformly perceptible scene truth.
- Mixed observable action plus implicit internal preparation: checking an address or knocking WHILE
  privately steeling oneself or bracing internally — the internal preparation is not uniformly visible.
- Concealed action: smiling while slipping something unseen, hidden work, actions explicitly not visible
  to others present.
- Lowered voice, whisper, wondering aloud about whether others can hear — potential private/subset speech.
- Directed speech to one character, private thoughts, mixed public+private spans.

SAFE EXAMPLES (may return true only when the ENTIRE source is uniformly present-visible):
- Simple public speech to the room.
- Simple observable action everyone present could see.
- Simple perceptible scene description with no hidden cognition or authorial exposition.

Absence of detected complexity is insufficient. Uncertainty requires false.
The reason field is audit-only and must not be treated as semantic truth.
"""


PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_OUTPUT_INSTRUCTION = """
OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary):
{
  "uniform_eligibility_disposition": "clear|disqualified|uncertain",
  "reason": "<short audit-only code>",
  "audit_note": "<optional brief note; not semantic truth>"
}

ROLE: Adversarial uniform-eligibility challenger only. You do NOT independently prove uniformity.
You do NOT produce PVR units, recipient scopes, or source spans.

Your task: attempt to FALSIFY a proposed uniform projection by finding ANY semantic content in the
complete player source that disqualifies representing the ENTIRE source as ONE uniformly projected
unit visible to ALL Characters present without semantic decomposition.

Return uniform_eligibility_disposition:
- "disqualified" when ANY disqualifying semantic content is present, including:
  - private/internal cognition or unexpressed mental state (explicit or implicit);
  - concealed or restricted observable actions;
  - nonuniform directed or subset speech entitlement;
  - mixed entitlement within the same turn;
  - authorial/off-screen/explanatory narration not uniformly perceptible;
  - any ambiguity that could hide the above.
- "clear" ONLY when you find NO disqualifying semantic content after adversarial review.
- "uncertain" when you cannot confidently determine clear vs disqualified.

Bias toward finding disqualifying content when plausible. Uncertainty is not clearance.
The reason and audit_note fields are audit-only and must not be treated as semantic truth.
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
