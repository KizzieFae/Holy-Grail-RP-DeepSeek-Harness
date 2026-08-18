"""Streamlit ad-hoc ``opening_mode`` contract (Issues #100/#108/#113) — Issue #165 split."""

from __future__ import annotations

from typing import Any

from bootstrap_interpretation import BootstrapCompositionError

# ---------------------------------------------------------------------------
# Streamlit ad-hoc ``opening_mode`` (GitHub #100) — single source of truth.
# UI must import these symbols; do not duplicate mode string literals.
# ---------------------------------------------------------------------------
STREAMLIT_OPENING_MODE_TEMPLATE = "template"
STREAMLIT_OPENING_MODE_CHARACTER = "character"
STREAMLIT_OPENING_MODE_CUSTOM = "custom"
STREAMLIT_OPENING_MODE_GENERATED = "generated"

# Streamlit persisted modes (Issue #100 / #108 / #113): template, custom, and legacy
# ``generated`` (migrated on load / before UI). ``STREAMLIT_OPENING_MODE_CHARACTER`` is
# migration-only. Operator radio lists template + custom only (Issue #113).
# ``STREAMLIT_OPENING_MODE_GENERATED`` remains in :data:`VALID_STREAMLIT_OPENING_MODES` for
# composition and tests.
VALID_STREAMLIT_OPENING_MODES: frozenset[str] = frozenset(
    {
        STREAMLIT_OPENING_MODE_TEMPLATE,
        STREAMLIT_OPENING_MODE_CUSTOM,
        STREAMLIT_OPENING_MODE_GENERATED,
    }
)


def streamlit_opening_mode_options_for_ui(*, with_template: bool) -> list[str]:
    """Radio option values for scene setup, in order of presentation (operator-facing only).

    Legacy ``generated`` mode is migrated out of session state before the radio is built;
    it is not listed here (Issue #113).
    """
    if with_template:
        return [
            STREAMLIT_OPENING_MODE_TEMPLATE,
            STREAMLIT_OPENING_MODE_CUSTOM,
        ]
    return [STREAMLIT_OPENING_MODE_CUSTOM]


def is_streamlit_template_opener_id_valid_for_openers(
    template_openers: list[Any],
    selected_opener_id: object,
) -> bool:
    """Return whether ``selected_opener_id`` resolves to an opener in ``template_openers``.

    Empty / whitespace ``selected_opener_id`` is treated as valid (UI may auto-bind).
    """
    s = (str(selected_opener_id).strip() if selected_opener_id is not None else "") or ""
    if not template_openers:
        return not s
    if len(template_openers) == 1:
        only = template_openers[0]
        if not s:
            return True
        return s == only.id or s == only.label
    if not s:
        return False
    by_id = [o for o in template_openers if o.id == s]
    if len(by_id) == 1:
        return True
    by_label = [o for o in template_openers if o.label == s]
    return len(by_label) == 1


def migrate_legacy_generated_streamlit_opening_state(
    *,
    opening_mode: str,
    selected_template_id: str | None,
    selected_opener_id: str | None,
    template_openers: list[Any],
) -> tuple[str, str | None]:
    """Migrate persisted or in-memory ``generated`` opening mode (Issue #113).

    When moving to **template** mode, preserves ``selected_opener_id`` only if it is still
    valid for ``template_openers``; otherwise returns ``None`` for the opener slot.
    When moving to **custom**, clears the opener id.
    """
    low = (opening_mode or "").strip().lower()
    if low != STREAMLIT_OPENING_MODE_GENERATED:
        return opening_mode, selected_opener_id
    tid = (selected_template_id or "").strip()
    if tid:
        new_mode = STREAMLIT_OPENING_MODE_TEMPLATE
        if is_streamlit_template_opener_id_valid_for_openers(
            template_openers, selected_opener_id
        ):
            resolved = (
                str(selected_opener_id).strip() if selected_opener_id is not None else ""
            )
            return new_mode, resolved or None
        return new_mode, None
    return STREAMLIT_OPENING_MODE_CUSTOM, None


def validate_streamlit_opening_mode_untrusted(value: object) -> str:
    """Validate ``opening_mode`` for Streamlit ad-hoc composition (Issue #100).

    Input is always treated as **untrusted** (session, future callers). Rejects
    ``None``, empty, whitespace-only, and non-canonical values.

    This is the primary gate for ad-hoc mode; :func:`_lock_streamlit_opening_strategy_intent`
    calls this first, and :func:`start_scene` may call it before :func:`compose_streamlit_bootstrap`
    to surface a friendly error. ``compose_streamlit_bootstrap`` re-validates
    (defense in depth) where needed for the ``template_static_text`` invariant.
    """
    if value is None:
        raise BootstrapCompositionError(
            "opening_mode is required; choose a scene opening type before starting"
        )
    s = str(value).strip()
    if not s:
        raise BootstrapCompositionError(
            "opening_mode is required; choose a scene opening type before starting (empty value)"
        )
    low = s.lower()
    if low not in VALID_STREAMLIT_OPENING_MODES:
        raise BootstrapCompositionError(
            f"invalid opening_mode: {value!r}; expected one of: {sorted(VALID_STREAMLIT_OPENING_MODES)}"
        )
    return low
