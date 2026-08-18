"""Streamlit-only opening strategy lock — Issue #165 split."""

from __future__ import annotations

from typing import Any

from scene_opener import OpenerManager, build_template_opener_ref, template_intent_has_opener_assets

from bootstrap_context_inputs import _strip
from bootstrap_interpretation import BootstrapCompositionError
from bootstrap_streamlit_opening_modes import (
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
    validate_streamlit_opening_mode_untrusted,
)
from bootstrap_strategy_shared import _normalize_template_opener_selection_to_asset_id


def _lock_streamlit_opening_strategy_intent(
    *,
    opening_mode: object,
    scene_setup: dict[str, Any] | None,
    opener_manager: OpenerManager,
    specific_opener_id: str | None,
    custom_text: str | None,
) -> tuple[str, str | None]:
    """Return (strategy, opening_ref) from intent only (Issue #94 §3.2.2 Rule B).

    **Issue #100:** ``opening_mode`` is always treated as **untrusted**; canonical
    modes and validation live in
    :data:`VALID_STREAMLIT_OPENING_MODES` / :func:`validate_streamlit_opening_mode_untrusted`.
    **Do not** use ``scene_setup["opening_text"]`` for Streamlit ad-hoc strategy
    selection; generated openings are explicit via ``generated`` only (no implicit
    template-text fallback).

    **Issue #108:** Streamlit ad-hoc composition uses only template assets, custom
    static text, or generated — not character-scoped openers.
    """
    mode = validate_streamlit_opening_mode_untrusted(opening_mode)
    tpl_id = _strip(scene_setup.get("template_id") if scene_setup else None)

    if mode == STREAMLIT_OPENING_MODE_TEMPLATE and tpl_id:
        if not template_intent_has_opener_assets(tpl_id, opener_manager):
            raise BootstrapCompositionError(
                f"opening_mode template but no opener assets for template {tpl_id!r}"
            )
        asset_id = _normalize_template_opener_selection_to_asset_id(
            opener_manager=opener_manager,
            template_id=tpl_id,
            specific_opener_id=specific_opener_id,
        )
        return "template_asset", build_template_opener_ref(tpl_id, asset_id)

    if mode == STREAMLIT_OPENING_MODE_CUSTOM and _strip(custom_text):
        return "template_static_text", None

    if mode == STREAMLIT_OPENING_MODE_GENERATED:
        return "generated", None

    if mode == STREAMLIT_OPENING_MODE_CUSTOM:
        raise BootstrapCompositionError(
            "opening_mode custom requires non-empty custom opener text; enter text in the "
            "Custom opening field, or pick another opening type (Issue #100)"
        )
    if mode == STREAMLIT_OPENING_MODE_TEMPLATE and not tpl_id:
        raise BootstrapCompositionError(
            "opening_mode template requires a selected scene template (Issue #100)"
        )
    raise BootstrapCompositionError(
        f"opening mode {mode!r} could not be resolved to a start strategy; "
        "select template + opener, custom text, or generated (Issue #100)"
    )
