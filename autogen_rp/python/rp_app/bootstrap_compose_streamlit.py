"""Streamlit bootstrap composition — Issue #165 split."""

from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

from scene_opener import OpenerManager, SceneOpener

from bootstrap_context_inputs import (
    _strip,
    compose_first_round_user_line,
    resolve_location_precedence,
)
from bootstrap_interpretation import (
    BOOTSTRAP_SHIM_SCHEMA_VERSION,
    BootstrapCompositionError,
    BootstrapInterpretation,
    build_initial_continuity_projection,
)
from bootstrap_streamlit_opening_modes import (
    STREAMLIT_OPENING_MODE_CUSTOM,
    validate_streamlit_opening_mode_untrusted,
)
from bootstrap_strategy_shared import OPENING_STRATEGIES, _resolve_opening_text_after_lock
from bootstrap_strategy_streamlit import _lock_streamlit_opening_strategy_intent


async def compose_streamlit_bootstrap(
    *,
    scene_setup: dict[str, Any] | None,
    character_card_ids_or_files: list[str],
    display_names: list[str],
    opening_mode: object,
    specific_opener_id: str | None,
    custom_text: str | None,
    opener_manager: OpenerManager,
    authored_bootstrap_document: dict[str, Any] | None,
    generate_opening_fn: Callable[[], Awaitable[str]],
    scenario_raw: dict[str, Any] | None,
    cli_trigger_operand: str | None,
    authored_bootstrap_location: str | None = None,
    scenario_manifest_location: str | None = None,
    template_default_location: str | None = None,
) -> tuple[BootstrapInterpretation, SceneOpener | None]:
    """Compose Streamlit scene-start (Issue #94).

    Opening resolution is strategy-locked from ``opening_mode`` and template/custom inputs;
    it does not use ``session_state["scene_owner"]`` (Issue #107: that key is a normalized
    session/run owner label elsewhere—audits, narrator hook, packets—not opener scope).
    """
    character_refs = tuple(str(x).strip() for x in character_card_ids_or_files if str(x).strip())
    meta: dict[str, Any] = {}
    bootstrap_id = f"streamlit-adhoc:{uuid.uuid4().hex}"
    schema = BOOTSTRAP_SHIM_SCHEMA_VERSION

    if authored_bootstrap_document and isinstance(authored_bootstrap_document, dict):
        schema = str(
            authored_bootstrap_document.get("bootstrap_schema_version")
            or BOOTSTRAP_SHIM_SCHEMA_VERSION
        )
        bootstrap_id = str(authored_bootstrap_document.get("id") or bootstrap_id)
        meta = dict(authored_bootstrap_document.get("metadata") or {})
        op = authored_bootstrap_document.get("opening") or {}
        strategy = str(op.get("strategy") or "").strip()
        ref = op.get("ref")
        if strategy not in OPENING_STRATEGIES:
            raise BootstrapCompositionError("authored bootstrap opening.strategy invalid")
        opening_ref = str(ref).strip() if ref else None
        if strategy in ("template_asset", "character_asset") and not opening_ref:
            raise BootstrapCompositionError("authored bootstrap asset strategy requires ref")
        if strategy == "template_static_text":
            raise BootstrapCompositionError(
                "authored bootstrap template_static_text is not supported in this release"
            )
        res_opener: SceneOpener | None
        if strategy == "generated":
            resolved_text = _strip(await generate_opening_fn())
            if not resolved_text:
                raise BootstrapCompositionError("generated opening produced empty text")
            res_opener = None
        else:
            resolved_text, res_opener = _resolve_opening_text_after_lock(
                strategy=strategy,
                opening_ref=opening_ref,
                opener_manager=opener_manager,
                static_text_operand="",
            )
        loc = resolve_location_precedence(
            authored_bootstrap_location=str(
                authored_bootstrap_document.get("location") or ""
            ).strip()
            or None,
            scenario_manifest_location=scenario_manifest_location,
            opener_location=getattr(res_opener, "location", None),
            template_default_location=template_default_location,
            streamlit_fallback_if_all_empty="unspecified",
        )
        ic = build_initial_continuity_projection(scene_setup)
        fr = compose_first_round_user_line(
            cli_trigger_operand=cli_trigger_operand,
            authored_bootstrap_first_line=str(
                authored_bootstrap_document.get("first_round_user_line") or ""
            ).strip()
            or None,
            startup_trigger_mode=(
                str(scenario_raw.get("startup_trigger_mode")).strip()
                if scenario_raw
                else None
            ),
            trigger_text=str(scenario_raw.get("trigger_text") or "") if scenario_raw else None,
            opening_resolved_text=resolved_text,
            surface="streamlit",
        )
        tpl_ref = str(authored_bootstrap_document.get("template_ref") or "").strip() or None
        return (
            BootstrapInterpretation(
                bootstrap_schema_version=schema,
                id=bootstrap_id,
                metadata=meta,
                character_refs=character_refs,
                template_ref=tpl_ref,
                location=loc,
                opening_strategy=strategy,
                opening_ref=opening_ref,
                opening_resolved_text=resolved_text,
                first_round_user_line=fr,
                initial_continuity=ic,
            ),
            res_opener,
        )

    strategy, opening_ref = _lock_streamlit_opening_strategy_intent(
        opening_mode=opening_mode,
        scene_setup=scene_setup,
        opener_manager=opener_manager,
        specific_opener_id=specific_opener_id,
        custom_text=custom_text,
    )

    om = validate_streamlit_opening_mode_untrusted(opening_mode)
    static_operand = ""
    if strategy == "template_static_text":
        if (
            om == STREAMLIT_OPENING_MODE_CUSTOM
            and _strip(custom_text)
        ):
            static_operand = _strip(custom_text)
        else:
            raise BootstrapCompositionError(
                "invariant: Streamlit ad-hoc template_static_text may only use non-empty "
                "Custom text; scene_setup['opening_text'] is not a composition source (Issue #100)"
            )

    resolved_text: str
    res_opener: SceneOpener | None
    if strategy == "generated":
        resolved_text = _strip(await generate_opening_fn())
        if not resolved_text:
            raise BootstrapCompositionError("generated opening produced empty text")
        res_opener = None
    else:
        resolved_text, res_opener = _resolve_opening_text_after_lock(
            strategy=strategy,
            opening_ref=opening_ref,
            opener_manager=opener_manager,
            static_text_operand=static_operand,
        )

    loc = resolve_location_precedence(
        authored_bootstrap_location=authored_bootstrap_location,
        scenario_manifest_location=scenario_manifest_location,
        opener_location=getattr(res_opener, "location", None),
        template_default_location=template_default_location,
        streamlit_fallback_if_all_empty="unspecified",
    )
    ic = build_initial_continuity_projection(scene_setup)
    tpl_ref = _strip(scene_setup.get("template_id")) if scene_setup else None
    if not tpl_ref:
        tpl_ref = None
    fr = compose_first_round_user_line(
        cli_trigger_operand=cli_trigger_operand,
        authored_bootstrap_first_line=None,
        startup_trigger_mode=(
            str(scenario_raw.get("startup_trigger_mode")).strip() if scenario_raw else None
        ),
        trigger_text=str(scenario_raw.get("trigger_text") or "") if scenario_raw else None,
        opening_resolved_text=resolved_text,
        surface="streamlit",
    )
    return (
        BootstrapInterpretation(
            bootstrap_schema_version=BOOTSTRAP_SHIM_SCHEMA_VERSION,
            id=bootstrap_id,
            metadata=meta,
            character_refs=character_refs,
            template_ref=tpl_ref,
            location=loc,
            opening_strategy=strategy,
            opening_ref=opening_ref,
            opening_resolved_text=resolved_text,
            first_round_user_line=fr,
            initial_continuity=ic,
        ),
        res_opener,
    )
