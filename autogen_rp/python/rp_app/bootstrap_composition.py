"""Bootstrap interpretation composition (GitHub Issue #94).

Single authoritative scene-start composition: intent-locked opening strategy, canonical
opener refs, location precedence, first-round user line (CLI as composition operand),
and bootstrap-owned ``initial_continuity`` projection. Streamlit and headless share this logic.

Mechanical split (Issue #165): implementations live in sibling modules; this file is a thin façade.
"""

from __future__ import annotations

from bootstrap_compose_headless import compose_headless_bootstrap
from bootstrap_compose_streamlit import compose_streamlit_bootstrap
from bootstrap_context_inputs import compose_first_round_user_line, resolve_location_precedence
from bootstrap_interpretation import (
    BOOTSTRAP_SHIM_SCHEMA_VERSION,
    BootstrapCompositionError,
    BootstrapInterpretation,
    Surface,
    build_initial_continuity_projection,
    interpretation_to_jsonable,
    interpretation_to_seed_scene_setup,
)
from bootstrap_streamlit_opening_modes import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
    VALID_STREAMLIT_OPENING_MODES,
    is_streamlit_template_opener_id_valid_for_openers,
    migrate_legacy_generated_streamlit_opening_state,
    streamlit_opening_mode_options_for_ui,
    validate_streamlit_opening_mode_untrusted,
)
from bootstrap_strategy_shared import OPENING_STRATEGIES, lock_headless_opening_strategy_intent
from bootstrap_strategy_streamlit import _lock_streamlit_opening_strategy_intent
