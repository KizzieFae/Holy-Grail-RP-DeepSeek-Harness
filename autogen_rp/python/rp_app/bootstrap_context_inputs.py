"""Location precedence and first-round user line (Issue #165 split)."""

from __future__ import annotations

from bootstrap_interpretation import BootstrapCompositionError, Surface


def _strip(s: str | None) -> str:
    return str(s or "").strip()


def resolve_location_precedence(
    *,
    authored_bootstrap_location: str | None,
    scenario_manifest_location: str | None,
    opener_location: str | None,
    template_default_location: str | None,
    streamlit_fallback_if_all_empty: str | None = None,
) -> str:
    """First non-empty strip wins (Issue #94 §3.4).

    Streamlit may pass ``streamlit_fallback_if_all_empty`` (e.g. ``\"unspecified\"``)
    when no authored/harness/opener/template default exists yet historical UI allowed
    unset location until continuity finalize.
    """
    for candidate in (
        authored_bootstrap_location,
        scenario_manifest_location,
        opener_location,
        template_default_location,
    ):
        s = _strip(candidate)
        if s:
            return s
    fb = _strip(streamlit_fallback_if_all_empty)
    if fb:
        return fb
    raise BootstrapCompositionError("location resolution failed (all sources empty)")


def compose_first_round_user_line(
    *,
    cli_trigger_operand: str | None,
    authored_bootstrap_first_line: str | None,
    startup_trigger_mode: str | None,
    trigger_text: str | None,
    opening_resolved_text: str,
    surface: Surface,
) -> str:
    """Model A: CLI is a composition operand; result is sole authority for round 1."""
    if _strip(cli_trigger_operand):
        return _strip(cli_trigger_operand)
    if _strip(authored_bootstrap_first_line):
        return _strip(authored_bootstrap_first_line)
    mode = str(startup_trigger_mode or "").strip().lower()
    if mode == "parity":
        return _strip(opening_resolved_text)
    if mode == "overlay" and trigger_text is not None:
        t = _strip(trigger_text)
        if t:
            return t
    if surface == "streamlit":
        return _strip(opening_resolved_text)
    if _strip(trigger_text):
        return _strip(trigger_text)
    return _strip(opening_resolved_text)
