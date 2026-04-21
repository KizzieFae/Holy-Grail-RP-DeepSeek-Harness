"""Bootstrap interpretation composition (GitHub Issue #94).

Single authoritative scene-start composition: intent-locked opening strategy, canonical
opener refs, location precedence, first-round user line (CLI as composition operand),
and bootstrap-owned ``initial_continuity`` projection. Streamlit and headless share this logic.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal

from scene_opener import (
    OpenerManager,
    SceneOpener,
    build_character_opener_ref,
    build_template_opener_ref,
    resolve_scene_opener_from_canonical_ref,
    template_intent_has_opener_assets,
)

Surface = Literal["streamlit", "headless"]

BOOTSTRAP_SHIM_SCHEMA_VERSION = "94.1"

OPENING_STRATEGIES = frozenset(
    {"template_asset", "character_asset", "template_static_text", "generated"}
)

# Keys consumed by ``apply_scene_setup_to_scene_state`` (bootstrap-owned projection → apply).
_SCENE_SETUP_APPLY_KEYS = frozenset(
    {
        "template_id",
        "premise",
        "anchor_role_name",
        "role_assignments",
        "character_presence_constraints",
        "character_authority_labels",
        "sleeping_surface_slots",
        "location_entry_slots",
    }
)


class BootstrapCompositionError(ValueError):
    """Scene-start composition failed (no silent strategy fallback)."""


@dataclass(frozen=True)
class BootstrapInterpretation:
    """Sole authority for scene-start inputs after successful composition (Issue #94)."""

    bootstrap_schema_version: str
    id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    character_refs: tuple[str, ...] = ()
    template_ref: str | None = None
    location: str = ""
    opening_strategy: str = ""
    opening_ref: str | None = None
    opening_resolved_text: str = ""
    first_round_user_line: str = ""
    initial_continuity: dict[str, Any] = field(default_factory=dict)
    harness_seed_issue: dict[str, Any] | None = None

    def scene_setup_for_continuity_apply(self) -> dict[str, Any] | None:
        """Flatten ``initial_continuity`` projection to ``apply_scene_setup`` shape."""
        flat: dict[str, Any] = {}
        tb = self.initial_continuity.get("template_binding") or {}
        if isinstance(tb, dict) and tb.get("template_id"):
            flat["template_id"] = str(tb["template_id"])
        rs = self.initial_continuity.get("role_structure") or {}
        if isinstance(rs, dict):
            for key in (
                "role_assignments",
                "character_authority_labels",
                "character_presence_constraints",
            ):
                v = rs.get(key)
                if isinstance(v, dict):
                    flat[key] = dict(v)
        sp = self.initial_continuity.get("structural_premise")
        if sp is not None and str(sp).strip():
            flat["premise"] = str(sp)
        slots = self.initial_continuity.get("structural_slots") or {}
        if isinstance(slots, dict):
            arn = slots.get("anchor_role_name")
            if arn is not None and str(arn).strip():
                flat["anchor_role_name"] = str(arn).strip()
            for key in ("sleeping_surface_slots", "location_entry_slots"):
                v = slots.get(key)
                if isinstance(v, list):
                    flat[key] = list(v)
        return flat if flat else None


def _strip(s: str | None) -> str:
    return str(s or "").strip()


def build_initial_continuity_projection(
    scene_setup: dict[str, Any] | None,
    *,
    harness_narrative_start: dict[str, Any] | None = None,
    harness_seeded_issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bootstrap-owned nested projection (not a raw ``scene_setup`` pass-through)."""
    proj: dict[str, Any] = {}
    if scene_setup and isinstance(scene_setup, dict):
        tid = scene_setup.get("template_id")
        if tid:
            proj["template_binding"] = {"template_id": str(tid)}
        proj["role_structure"] = {
            "role_assignments": dict(scene_setup.get("role_assignments", {}) or {}),
            "character_authority_labels": dict(
                scene_setup.get("character_authority_labels", {}) or {}
            ),
            "character_presence_constraints": dict(
                scene_setup.get("character_presence_constraints", {}) or {}
            ),
        }
        proj["structural_premise"] = str(scene_setup.get("premise", "") or "")
        proj["structural_slots"] = {
            "anchor_role_name": scene_setup.get("anchor_role_name"),
            "sleeping_surface_slots": list(
                scene_setup.get("sleeping_surface_slots", []) or []
            ),
            "location_entry_slots": list(
                scene_setup.get("location_entry_slots", []) or []
            ),
        }
    if harness_narrative_start:
        proj["narrative_start_state"] = dict(harness_narrative_start)
    if harness_seeded_issues:
        proj["seeded_issues"] = list(harness_seeded_issues)
    return proj


def _normalize_template_opener_selection_to_asset_id(
    *,
    opener_manager: OpenerManager,
    template_id: str,
    specific_opener_id: str | None,
) -> str:
    """Map UI/harness selection to opener JSON ``id`` (id-only refs)."""
    openers = opener_manager.get_template_openers(template_id)
    if not openers:
        raise BootstrapCompositionError(
            f"no template openers available for template {template_id!r}"
        )
    sel = _strip(specific_opener_id)
    if not sel:
        if len(openers) != 1:
            raise BootstrapCompositionError(
                "template opener selection required when multiple template openers exist"
            )
        return str(openers[0].id)
    by_id = [o for o in openers if o.id == sel]
    if len(by_id) == 1:
        return str(by_id[0].id)
    by_label = [o for o in openers if o.label == sel]
    if len(by_label) == 1:
        return str(by_label[0].id)
    raise BootstrapCompositionError(
        f"ambiguous or unknown template opener selection {sel!r} for {template_id!r}"
    )


def _normalize_character_opener_selection_to_asset_id(
    *,
    opener_manager: OpenerManager,
    owner_file: str,
    specific_opener_id: str | None,
) -> str:
    openers = opener_manager.get_character_openers(owner_file)
    if not openers:
        raise BootstrapCompositionError(
            f"no character openers for {owner_file!r}"
        )
    sel = _strip(specific_opener_id)
    if not sel:
        if len(openers) != 1:
            raise BootstrapCompositionError(
                "character opener selection required when multiple character openers exist"
            )
        return str(openers[0].id)
    by_id = [o for o in openers if o.id == sel]
    if len(by_id) == 1:
        return str(by_id[0].id)
    by_label = [o for o in openers if o.label == sel]
    if len(by_label) == 1:
        return str(by_label[0].id)
    raise BootstrapCompositionError(
        f"ambiguous or unknown character opener selection {sel!r}"
    )


def _character_stem(character_file: str) -> str:
    return str(character_file or "").replace(".json", "").strip()


def _lock_streamlit_opening_strategy_intent(
    *,
    opening_mode: str,
    scene_setup: dict[str, Any] | None,
    opener_manager: OpenerManager,
    selected_chars: list[str],
    scene_owner: str,
    specific_opener_id: str | None,
    custom_text: str | None,
) -> tuple[str, str | None]:
    """Return (strategy, opening_ref) from intent only (Issue #94 §3.2.2 Rule B)."""
    from scene_opener import _normalize_owner_identifier  # noqa: PLC0415

    mode = str(opening_mode or "").strip().lower()
    tpl_id = _strip(scene_setup.get("template_id") if scene_setup else None)

    if mode == "template" and tpl_id:
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

    if mode == "character":
        owner_file = None
        norm_owner = _normalize_owner_identifier(scene_owner)
        for char_file in selected_chars:
            ncf = _normalize_owner_identifier(char_file)
            if ncf == norm_owner or norm_owner in ncf:
                owner_file = char_file
                break
        if not owner_file:
            raise BootstrapCompositionError(
                "opening_mode character but scene owner does not match selected cast file"
            )
        if not opener_manager.get_character_openers(owner_file):
            raise BootstrapCompositionError(
                f"opening_mode character but no openers for {owner_file!r}"
            )
        asset_id = _normalize_character_opener_selection_to_asset_id(
            opener_manager=opener_manager,
            owner_file=owner_file,
            specific_opener_id=specific_opener_id,
        )
        stem = _character_stem(owner_file)
        return "character_asset", build_character_opener_ref(stem, asset_id)

    if mode == "custom" and _strip(custom_text):
        return "template_static_text", None

    opening_text = _strip(scene_setup.get("opening_text") if scene_setup else None)
    if opening_text:
        return "template_static_text", None

    return "generated", None


def lock_headless_opening_strategy_intent(
    *,
    opening_description: str,
    scene_setup: dict[str, Any] | None,
) -> tuple[str, str | None]:
    if _strip(opening_description):
        return "template_static_text", None
    opening_text = _strip(scene_setup.get("opening_text") if scene_setup else None)
    if opening_text:
        return "template_static_text", None
    raise BootstrapCompositionError(
        "headless scene-start requires non-empty opening_description or template opening_text"
    )


def _resolve_opening_text_after_lock(
    *,
    strategy: str,
    opening_ref: str | None,
    opener_manager: OpenerManager,
    static_text_operand: str,
) -> tuple[str, SceneOpener | None]:
    if strategy in ("template_asset", "character_asset"):
        if not opening_ref:
            raise BootstrapCompositionError("asset strategy requires opening_ref")
        opener = resolve_scene_opener_from_canonical_ref(opener_manager, opening_ref)
        if opener is None:
            raise BootstrapCompositionError(
                f"opener asset resolution failed for ref {opening_ref!r}"
            )
        text = _strip(opener.text)
        if not text:
            raise BootstrapCompositionError(
                f"opener asset has empty text for ref {opening_ref!r}"
            )
        return text, opener
    if strategy == "template_static_text":
        t = _strip(static_text_operand)
        if not t:
            raise BootstrapCompositionError("template_static_text requires non-empty text")
        return t, None
    raise BootstrapCompositionError(f"unexpected strategy for asset resolve: {strategy!r}")


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


async def compose_streamlit_bootstrap(
    *,
    scene_setup: dict[str, Any] | None,
    character_card_ids_or_files: list[str],
    display_names: list[str],
    opening_mode: str,
    specific_opener_id: str | None,
    custom_text: str | None,
    scene_owner: str,
    opener_manager: OpenerManager,
    authored_bootstrap_document: dict[str, Any] | None,
    generate_opening_fn: Callable[[], Awaitable[str]],
    scenario_raw: dict[str, Any] | None,
    cli_trigger_operand: str | None,
    authored_bootstrap_location: str | None = None,
    scenario_manifest_location: str | None = None,
    template_default_location: str | None = None,
) -> tuple[BootstrapInterpretation, SceneOpener | None]:
    """Compose Streamlit scene-start (Issue #94)."""
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
        selected_chars=character_card_ids_or_files,
        scene_owner=scene_owner,
        specific_opener_id=specific_opener_id,
        custom_text=custom_text,
    )

    static_operand = ""
    if strategy == "template_static_text":
        if _strip(custom_text) and str(opening_mode).strip().lower() == "custom":
            static_operand = _strip(custom_text)
        elif scene_setup:
            static_operand = _strip(scene_setup.get("opening_text"))

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


def interpretation_to_seed_scene_setup(
    interp: BootstrapInterpretation,
) -> dict[str, Any] | None:
    """Shape compatible with ``_seed_scene_role_*`` (premise + role maps)."""
    flat = interp.scene_setup_for_continuity_apply()
    premise = interp.initial_continuity.get("structural_premise")
    out: dict[str, Any] = dict(flat) if flat else {}
    if premise is not None and str(premise).strip():
        out["premise"] = str(premise)
    return out if out else None


def interpretation_to_jsonable(interp: BootstrapInterpretation) -> dict[str, Any]:
    """Session / audit friendly dict (tests, debugging)."""
    return {
        "bootstrap_schema_version": interp.bootstrap_schema_version,
        "id": interp.id,
        "metadata": dict(interp.metadata),
        "character_refs": list(interp.character_refs),
        "template_ref": interp.template_ref,
        "location": interp.location,
        "opening_strategy": interp.opening_strategy,
        "opening_ref": interp.opening_ref,
        "opening_resolved_text": interp.opening_resolved_text,
        "first_round_user_line": interp.first_round_user_line,
        "initial_continuity": json.loads(json.dumps(interp.initial_continuity)),
        "harness_seed_issue": interp.harness_seed_issue,
    }
