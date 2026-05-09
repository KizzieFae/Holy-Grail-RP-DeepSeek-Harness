"""Phase 0.5 packet seam: read-only projections for character prompt inputs (shadow mode).

RuntimeScenePacket holds authored / scene-start-stable scene fields only.
RuntimeCharacterPacket pairs the speaking character with dynamic scene slice + prompt
projections (transcript-derived lists, cross-session slices, etc.).

Packets are not a second continuity store; continuity + character state remain authoritative.

Mechanical split (Issue #166): implementations live in sibling modules; this file is a thin façade.
"""

from __future__ import annotations

from runtime_packet_formatting import format_retrieved_context_for_prompt
from runtime_packet_parity import (
    compare_character_prompt_bundles,
    debug_bundle_mismatch_strings,
)
from runtime_packet_prompt_bundle import (
    build_live_character_prompt_input_bundle,
    live_bundle_from_character_prompt_assembly,
    runtime_packets_from_character_prompt_assembly,
)
from runtime_packet_reconstruct import reconstruct_character_prompt_input_bundle
from runtime_packet_scene_split import merge_scene_state_from_packets, split_scene_state
from runtime_packet_build import (
    build_runtime_character_packet,
    build_runtime_scene_packet,
)
from runtime_packet_types import (
    STABLE_SCENE_STATE_KEYS,
    CharacterPromptInputAssembly,
    CharacterRuntimePromptProjection,
    RetrievedContextBundle,
    RetrievedItem,
    RuntimeCharacterPacket,
    RuntimeScenePacket,
)
