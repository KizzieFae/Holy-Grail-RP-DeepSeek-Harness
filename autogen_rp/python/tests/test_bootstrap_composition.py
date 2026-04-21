"""Issue #94: bootstrap composition (intent-locked strategy, projection, CLI operand)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from bootstrap_composition import (  # noqa: E402
    BOOTSTRAP_SHIM_SCHEMA_VERSION,
    BootstrapCompositionError,
    BootstrapInterpretation,
    build_initial_continuity_projection,
    compose_first_round_user_line,
    compose_headless_bootstrap,
    interpretation_to_jsonable,
    lock_headless_opening_strategy_intent,
    resolve_location_precedence,
)
from scene_opener import (  # noqa: E402
    OpenerManager,
    build_template_opener_ref,
    resolve_scene_opener_from_canonical_ref,
    template_intent_has_opener_assets,
)


def test_lock_headless_strategy_intent_static_from_manifest_operand() -> None:
    s, ref = lock_headless_opening_strategy_intent(
        opening_description="Hello scene",
        scene_setup={"opening_text": "ignored when desc set"},
    )
    assert s == "template_static_text"
    assert ref is None


def test_lock_headless_strategy_from_template_opening_text_only() -> None:
    s, ref = lock_headless_opening_strategy_intent(
        opening_description="",
        scene_setup={"opening_text": "  tpl only  "},
    )
    assert s == "template_static_text"
    assert ref is None


def test_lock_headless_strategy_fails_when_no_static() -> None:
    with pytest.raises(BootstrapCompositionError):
        lock_headless_opening_strategy_intent(opening_description="", scene_setup=None)


def test_resolve_opener_ref_returns_none_for_bad_asset() -> None:
    om = OpenerManager(
        templates_dir=Path(__file__).resolve().parent / "nonexistent_tpl_dir_94",
        characters_dir=Path(__file__).resolve().parent / "nonexistent_char_dir_94",
    )
    ref = build_template_opener_ref("fake_template_xyz", "no_such_opener")
    assert resolve_scene_opener_from_canonical_ref(om, ref) is None


def test_initial_continuity_projection_excludes_opening_text() -> None:
    raw = {
        "template_id": "t1",
        "opening_text": "SECRET",
        "premise": "p",
        "role_assignments": {"A": "r1"},
        "character_authority_labels": {},
        "character_presence_constraints": {},
        "anchor_role_name": "r1",
        "sleeping_surface_slots": [],
        "location_entry_slots": [],
    }
    proj = build_initial_continuity_projection(raw)
    dumped = json.dumps(proj)
    assert "SECRET" not in dumped
    assert proj["template_binding"]["template_id"] == "t1"


def test_compose_first_round_cli_operand_wins() -> None:
    fr = compose_first_round_user_line(
        cli_trigger_operand="  cli wins  ",
        authored_bootstrap_first_line="authored",
        startup_trigger_mode="overlay",
        trigger_text="overlay text",
        opening_resolved_text="opening",
        surface="headless",
    )
    assert fr == "cli wins"


def test_compose_first_round_parity_before_overlay_semantics() -> None:
    fr = compose_first_round_user_line(
        cli_trigger_operand=None,
        authored_bootstrap_first_line=None,
        startup_trigger_mode="parity",
        trigger_text="different",
        opening_resolved_text="same opening",
        surface="headless",
    )
    assert fr == "same opening"


def test_compose_first_round_overlay_uses_trigger() -> None:
    fr = compose_first_round_user_line(
        cli_trigger_operand=None,
        authored_bootstrap_first_line=None,
        startup_trigger_mode="overlay",
        trigger_text="  overlay line  ",
        opening_resolved_text="opening",
        surface="headless",
    )
    assert fr == "overlay line"


def test_location_precedence_first_non_empty() -> None:
    loc = resolve_location_precedence(
        authored_bootstrap_location="auth",
        scenario_manifest_location="scen",
        opener_location="op",
        template_default_location="tpl",
    )
    assert loc == "auth"
    loc2 = resolve_location_precedence(
        authored_bootstrap_location=None,
        scenario_manifest_location="",
        opener_location="  x  ",
        template_default_location="tpl",
    )
    assert loc2 == "x"


def test_location_precedence_empty_raises() -> None:
    with pytest.raises(BootstrapCompositionError):
        resolve_location_precedence(
            authored_bootstrap_location=None,
            scenario_manifest_location=None,
            opener_location=None,
            template_default_location=None,
        )


def test_compose_headless_matches_scenario_id() -> None:
    om = OpenerManager()
    raw = {
        "id": "parity_smoke_94",
        "location": "loc_a",
        "opening_description": "od",
        "trigger_text": "od",
        "startup_trigger_mode": "parity",
    }
    interp = compose_headless_bootstrap(
        scene_setup=None,
        character_card_ids=["c1"],
        opening_description_operand="od",
        scenario_raw=raw,
        cli_trigger_operand=None,
        harness_location_operand="fallback_loc",
        opener_manager=om,
    )
    assert interp.id == "parity_smoke_94"
    assert interp.opening_strategy == "template_static_text"
    assert interp.opening_resolved_text == "od"
    assert interp.first_round_user_line == "od"
    assert interp.location == "loc_a"
    assert interp.bootstrap_schema_version == BOOTSTRAP_SHIM_SCHEMA_VERSION


def test_compose_headless_cli_in_composition_not_post_override() -> None:
    om = OpenerManager()
    raw = {
        "id": "cli_94",
        "location": "L",
        "opening_description": "open body",
        "trigger_text": "overlay should lose to cli",
        "startup_trigger_mode": "overlay",
    }
    interp = compose_headless_bootstrap(
        scene_setup=None,
        character_card_ids=["c1"],
        opening_description_operand="open body",
        scenario_raw=raw,
        cli_trigger_operand="from_cli",
        harness_location_operand="L",
        opener_manager=om,
    )
    assert interp.first_round_user_line == "from_cli"


def test_interpretation_jsonable_roundtrip_keys() -> None:
    bi = BootstrapInterpretation(
        bootstrap_schema_version="94.1",
        id="x",
        opening_strategy="template_static_text",
        opening_resolved_text="t",
        first_round_user_line="t",
        location="L",
        initial_continuity={"template_binding": {"template_id": "tid"}},
    )
    d = interpretation_to_jsonable(bi)
    assert d["id"] == "x"
    assert "opening_text" not in json.dumps(d["initial_continuity"])


@pytest.mark.asyncio
async def test_compose_streamlit_generated_only_when_locked() -> None:
    from bootstrap_composition import compose_streamlit_bootstrap  # noqa: E402

    om = OpenerManager()

    async def gen() -> str:
        return "llm body"

    interp, opener = await compose_streamlit_bootstrap(
        scene_setup=None,
        character_card_ids_or_files=["a.json"],
        display_names=["A"],
        opening_mode="general",
        specific_opener_id=None,
        custom_text=None,
        scene_owner="A",
        opener_manager=om,
        authored_bootstrap_document=None,
        generate_opening_fn=gen,
        scenario_raw=None,
        cli_trigger_operand=None,
    )
    assert interp.opening_strategy == "generated"
    assert interp.opening_resolved_text == "llm body"
    assert opener is None


def test_template_intent_has_opener_smoke() -> None:
    tpl_dir = Path(__file__).resolve().parents[1] / "data" / "scene_templates"
    om = OpenerManager(templates_dir=tpl_dir)
    assert template_intent_has_opener_assets("arkham_asylum_cell_intake", om) is True
