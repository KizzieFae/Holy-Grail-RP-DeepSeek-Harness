"""Headless bootstrap composition — Issue #165 split."""

from __future__ import annotations

import uuid
from typing import Any

from scene_opener import OpenerManager

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
from bootstrap_strategy_shared import (
    OPENING_STRATEGIES,
    _resolve_opening_text_after_lock,
    lock_headless_opening_strategy_intent,
)


def compose_headless_bootstrap(
    *,
    scene_setup: dict[str, Any] | None,
    character_card_ids: list[str],
    opening_description_operand: str,
    scenario_raw: dict[str, Any] | None,
    cli_trigger_operand: str | None,
    harness_location_operand: str,
    opener_manager: OpenerManager,
    authored_bootstrap_document: dict[str, Any] | None = None,
    harness_seed_issue: dict[str, Any] | None = None,
    harness_narrative_start: dict[str, Any] | None = None,
) -> BootstrapInterpretation:
    """Compose headless scene-start (no ``generated``)."""
    character_refs = tuple(str(x).strip() for x in character_card_ids if str(x).strip())
    if authored_bootstrap_document and isinstance(authored_bootstrap_document, dict):
        schema = str(
            authored_bootstrap_document.get("bootstrap_schema_version")
            or BOOTSTRAP_SHIM_SCHEMA_VERSION
        )
        bootstrap_id = str(authored_bootstrap_document.get("id") or "")
        if not bootstrap_id:
            raise BootstrapCompositionError("authored bootstrap missing id")
        meta = dict(authored_bootstrap_document.get("metadata") or {})
        op = authored_bootstrap_document.get("opening") or {}
        strategy = str(op.get("strategy") or "").strip()
        ref = op.get("ref")
        opening_ref = str(ref).strip() if ref else None
        if strategy not in OPENING_STRATEGIES:
            raise BootstrapCompositionError("authored bootstrap opening.strategy invalid")
        if strategy == "generated":
            raise BootstrapCompositionError("generated opening is forbidden on headless surface")
        if strategy == "template_static_text":
            raise BootstrapCompositionError(
                "authored bootstrap template_static_text is not supported in this release"
            )
        if strategy in ("template_asset", "character_asset") and not opening_ref:
            raise BootstrapCompositionError("authored bootstrap asset strategy requires ref")
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
            scenario_manifest_location=(
                str(scenario_raw.get("location") or "").strip() if scenario_raw else None
            ),
            opener_location=getattr(res_opener, "location", None),
            template_default_location=None,
        )
        ic = build_initial_continuity_projection(
            scene_setup,
            harness_narrative_start=harness_narrative_start,
        )
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
            surface="headless",
        )
        tpl_ref = str(authored_bootstrap_document.get("template_ref") or "").strip() or None
        return BootstrapInterpretation(
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
            harness_seed_issue=harness_seed_issue,
        )

    strategy, opening_ref = lock_headless_opening_strategy_intent(
        opening_description=opening_description_operand,
        scene_setup=scene_setup,
    )
    static_operand = _strip(opening_description_operand)
    if not static_operand and scene_setup:
        static_operand = _strip(scene_setup.get("opening_text"))
    resolved_text, res_opener = _resolve_opening_text_after_lock(
        strategy=strategy,
        opening_ref=opening_ref,
        opener_manager=opener_manager,
        static_text_operand=static_operand,
    )
    scenario_loc = (
        str(scenario_raw.get("location") or "").strip() if scenario_raw else None
    )
    loc = resolve_location_precedence(
        authored_bootstrap_location=None,
        scenario_manifest_location=scenario_loc or None,
        opener_location=getattr(res_opener, "location", None),
        template_default_location=_strip(harness_location_operand) or None,
    )
    ic = build_initial_continuity_projection(
        scene_setup,
        harness_narrative_start=harness_narrative_start,
    )
    bootstrap_id = str(scenario_raw["id"]).strip() if scenario_raw else f"headless-adhoc:{uuid.uuid4().hex}"
    meta: dict[str, Any] = {}
    if scenario_raw:
        meta["title"] = scenario_raw.get("title")
        meta["intent"] = scenario_raw.get("intent")
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
        surface="headless",
    )
    return BootstrapInterpretation(
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
        harness_seed_issue=harness_seed_issue,
    )
