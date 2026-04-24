"""Issue #94 — end-to-end bootstrap interpretation on headless session prep (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from bootstrap_composition import (  # noqa: E402
    BOOTSTRAP_SHIM_SCHEMA_VERSION,
    BootstrapCompositionError,
    compose_headless_bootstrap,
    compose_streamlit_bootstrap,
)
from headless_scene_simulation import prepare_headless_session  # noqa: E402
from progression_simulation_scenarios import load_scenario, scenario_prepare_kwargs  # noqa: E402
from scene_opener import OpenerManager  # noqa: E402


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_cli_trigger_becomes_composed_first_round(_mock: MagicMock) -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(
        **prep,
        user_name="Traveler",
        scenario_raw=raw,
        cli_trigger_for_composition="  cli_first_round  ",
    )
    assert st.session_state.get("first_round_user_line_composed") == "cli_first_round"
    bi = st.session_state.get("bootstrap_interpretation") or {}
    assert bi.get("first_round_user_line") == "cli_first_round"


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_initial_continuity_has_template_binding_for_template_scenario(
    _mock: MagicMock,
) -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, scenario_raw=raw)
    bi = st.session_state.get("bootstrap_interpretation") or {}
    ic = bi.get("initial_continuity") or {}
    assert ic.get("template_binding", {}).get("template_id") == "arkham_asylum_cell_intake"
    rs = ic.get("role_structure") or {}
    ra = rs.get("role_assignments") or {}
    assert set(ra.values()) == {"cell_anchor", "new_arrival"}
    assert len(ra) == 2


def test_headless_authored_bootstrap_generated_strategy_rejected() -> None:
    om = OpenerManager()
    doc = {
        "id": "x",
        "bootstrap_schema_version": BOOTSTRAP_SHIM_SCHEMA_VERSION,
        "opening": {"strategy": "generated"},
    }
    with pytest.raises(BootstrapCompositionError, match="forbidden on headless"):
        compose_headless_bootstrap(
            scene_setup=None,
            character_card_ids=["a"],
            opening_description_operand="",
            scenario_raw={"id": "s", "location": "L"},
            cli_trigger_operand=None,
            harness_location_operand="L",
            opener_manager=om,
            authored_bootstrap_document=doc,
        )


def test_asset_resolution_failure_is_composition_error_not_strategy_flip() -> None:
    om = OpenerManager(
        templates_dir=Path(__file__).resolve().parent / "nonexistent_tpl_dir_94b",
        characters_dir=Path(__file__).resolve().parent / "nonexistent_char_dir_94b",
    )
    doc = {
        "id": "y",
        "bootstrap_schema_version": BOOTSTRAP_SHIM_SCHEMA_VERSION,
        "location": "auth-loc",
        "opening": {"strategy": "template_asset", "ref": "template_opener:fake:no_such"},
    }
    with pytest.raises(BootstrapCompositionError, match="resolution failed"):
        compose_headless_bootstrap(
            scene_setup=None,
            character_card_ids=["a"],
            opening_description_operand="ignored",
            scenario_raw={"id": "s", "location": "manifest-loc"},
            cli_trigger_operand=None,
            harness_location_operand="",
            opener_manager=om,
            authored_bootstrap_document=doc,
        )


@pytest.mark.asyncio
async def test_cross_path_static_opening_aligned_where_inputs_align() -> None:
    """Same manifest opening + parity + location → same resolved opening and first line (Issue #94)."""
    om = OpenerManager()
    raw = load_scenario("parity_opening_trigger_smoke")
    opening = str(raw["opening_description"]).strip()
    loc = str(raw["location"]).strip()
    h = compose_headless_bootstrap(
        scene_setup=None,
        character_card_ids=list(raw["character_card_ids"]),
        opening_description_operand=opening,
        scenario_raw=raw,
        cli_trigger_operand=None,
        harness_location_operand=loc,
        opener_manager=om,
    )

    async def _gen() -> str:
        raise AssertionError("generated opening must not run for this parity")

    s, _o = await compose_streamlit_bootstrap(
        scene_setup=None,
        character_card_ids_or_files=list(raw["character_card_ids"]),
        display_names=["A", "B"],
        opening_mode="custom",
        specific_opener_id=None,
        custom_text=opening,
        opener_manager=om,
        authored_bootstrap_document=None,
        generate_opening_fn=_gen,
        scenario_raw=raw,
        cli_trigger_operand=None,
        scenario_manifest_location=loc,
        template_default_location=None,
        authored_bootstrap_location=None,
    )
    assert h.opening_resolved_text == s.opening_resolved_text == opening
    assert h.first_round_user_line == s.first_round_user_line == opening
    assert h.location == s.location == loc
    assert h.opening_strategy == s.opening_strategy == "template_static_text"
