"""Issue #83 — consolidated scene-start contract checks.

Evidence that headless uses the unified continuity init path, scenario startup modes
behave as declared, and obsolete headless template patching is gone.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import headless_scene_simulation as headless_mod  # noqa: E402
from app_state_continuity import get_continuity_manager  # noqa: E402
from app_state_helpers import (  # noqa: E402
    restore_or_initialize_continuity_manager,
)
from continuity_manager import ContinuityManager  # noqa: E402
from headless_scene_simulation import prepare_headless_session  # noqa: E402
from progression_simulation_scenarios import (  # noqa: E402
    effective_round1_trigger_text_headless,
    load_scenario,
    scenario_prepare_kwargs,
)


def test_headless_has_no_late_template_patch_hook() -> None:
    assert not hasattr(headless_mod, "_apply_headless_scene_template_to_continuity")


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_parity_scenario_headless_startup_matches_contract(_mock_client: MagicMock) -> None:
    raw = load_scenario("parity_opening_trigger_smoke")
    assert raw["startup_trigger_mode"] == "parity"
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, user_name="Traveler", scenario_raw=raw)
    opening_final = str(st.session_state.get("simulation_opening_final") or "").strip()
    assert opening_final == prep["opening_description"].strip()
    chat = st.session_state.get("chat_history") or []
    assert chat and "Scene Opening" in str(chat[0].get("content", ""))
    assert (
        effective_round1_trigger_text_headless(
            scenario_raw=raw,
            simulation_opening_final=opening_final,
            adhoc_fallback_trigger="x",
            cli_trigger_provided=False,
            cli_trigger_value="",
        )
        == opening_final
    )
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.setup_seam_complete is True
    bi = st.session_state.get("bootstrap_interpretation") or {}
    assert bi.get("id") == "parity_opening_trigger_smoke"
    assert bi.get("opening_resolved_text") == opening_final
    assert st.session_state.get("first_round_user_line_composed") == opening_final
    assert "opening_text" not in str(bi.get("initial_continuity") or {})


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_overlay_scenario_headless_uses_manifest_trigger(_mock_client: MagicMock) -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    assert raw["startup_trigger_mode"] == "overlay"
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, user_name="Traveler", scenario_raw=raw)
    opening_final = str(st.session_state.get("simulation_opening_final") or "").strip()
    assert opening_final == prep["opening_description"].strip()
    manifest_trigger = str(raw["trigger_text"]).strip()
    assert manifest_trigger != opening_final
    resolved = effective_round1_trigger_text_headless(
        scenario_raw=raw,
        simulation_opening_final=opening_final,
        adhoc_fallback_trigger="fallback",
        cli_trigger_provided=False,
        cli_trigger_value="",
    )
    assert resolved == manifest_trigger
    bi = st.session_state.get("bootstrap_interpretation") or {}
    assert bi.get("id") == "headless_template_retrieval_smoke"
    assert st.session_state.get("first_round_user_line_composed") == manifest_trigger
    cm_overlay = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm_overlay is not None and cm_overlay.scene_state is not None
    assert cm_overlay.scene_state.location == str(raw["location"])


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
@patch(
    "headless_scene_simulation.state_helpers.restore_or_initialize_continuity_manager",
    wraps=restore_or_initialize_continuity_manager,
)
def test_template_scenario_passes_non_none_scene_setup_on_first_init(
    mock_restore: MagicMock,
    _mock_client: MagicMock,
) -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    prep = scenario_prepare_kwargs(raw)
    prepare_headless_session(**prep, scenario_raw=raw)
    kw = mock_restore.call_args.kwargs
    assert kw.get("scene_setup") is not None
    assert kw["scene_setup"].get("template_id") == "arkham_asylum_cell_intake"


def test_streamlit_start_scene_orders_interim_anchor_before_finalize() -> None:
    """Static guard: UI start calls interim anchor fallback immediately before finalize."""
    import inspect  # noqa: E402

    import scene_lifecycle_start as sls  # noqa: E402

    src = inspect.getsource(sls.start_scene)
    idx_ensure = src.find("ensure_interim_anchor_role_fallback_for_finalize")
    idx_fin = src.find("finalize_continuity_setup_seam", idx_ensure)
    assert idx_ensure != -1 and idx_fin != -1 and idx_ensure < idx_fin
