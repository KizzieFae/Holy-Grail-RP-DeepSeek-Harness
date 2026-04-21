"""Headless template startup: ``scene_template_id``, continuity init, and contract checks (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_continuity import get_continuity_manager  # noqa: E402
from app_state_helpers import restore_or_initialize_continuity_manager  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from headless_scene_simulation import prepare_headless_session  # noqa: E402
from scene_template import SceneTemplateManager  # noqa: E402

from progression_simulation_scenarios import load_scenario, scenario_prepare_kwargs  # noqa: E402


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
@patch(
    "headless_scene_simulation.state_helpers.restore_or_initialize_continuity_manager",
    wraps=restore_or_initialize_continuity_manager,
)
def test_prepare_headless_template_passes_scene_setup_to_restore(
    mock_restore: MagicMock,
    _mock_client: MagicMock,
) -> None:
    prepare_headless_session(
        character_card_ids=["harley_quinn", "magpie"],
        opening_description="Test opening.",
        location="test_loc",
        seed_escalating_issue=False,
        scene_template_id="arkham_asylum_cell_intake",
        scene_template_role_assignments={
            "harley_quinn": "cell_anchor",
            "magpie": "new_arrival",
        },
    )
    kw = mock_restore.call_args.kwargs
    assert kw.get("scene_setup") is not None
    assert kw["scene_setup"].get("template_id") == "arkham_asylum_cell_intake"
    assert kw.get("opening_description") == "Test opening."


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_session_sets_scene_template_id(_mock_client: MagicMock) -> None:
    st = prepare_headless_session(
        character_card_ids=["harley_quinn", "magpie"],
        opening_description="Test opening.",
        location="test_loc",
        seed_escalating_issue=False,
        scene_template_id="arkham_asylum_cell_intake",
        scene_template_role_assignments={
            "harley_quinn": "cell_anchor",
            "magpie": "new_arrival",
        },
    )
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.scene_state.scene_template_id == "arkham_asylum_cell_intake"
    tpl = SceneTemplateManager().load_template("arkham_asylum_cell_intake")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)
    assert st.session_state.get("sim_retrieval_saw_nonempty_bundle") is False
    assert st.session_state.get("simulation_opening_final") == "Test opening."
    chat = st.session_state.get("chat_history") or []
    assert chat and "Scene Opening" in str(chat[0].get("content", ""))


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_session_omitted_scene_template_id_unchanged(_mock_client: MagicMock) -> None:
    st = prepare_headless_session(
        character_card_ids=["ayame", "celina"],
        opening_description="Test opening.",
        location="test_loc",
        seed_escalating_issue=False,
    )
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.scene_state.scene_template_id is None


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_headless_template_retrieval_smoke_scenario_passes_prepare_kwargs(
    _mock_client: MagicMock,
) -> None:
    raw = load_scenario("headless_template_retrieval_smoke")
    prep = scenario_prepare_kwargs(raw)
    assert prep["scene_template_id"] == "arkham_asylum_cell_intake"
    st = prepare_headless_session(**prep, scenario_raw=raw)
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.scene_state.scene_template_id == "arkham_asylum_cell_intake"
    tpl = SceneTemplateManager().load_template("arkham_asylum_cell_intake")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)
    assert st.session_state.get("simulation_opening_final") == prep["opening_description"]
    chat = st.session_state.get("chat_history") or []
    assert chat and "Scene Opening" in str(chat[0].get("content", ""))
    ra = cm.scene_state.role_assignments or {}
    assert set(ra.values()) == {"cell_anchor", "new_arrival"}


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_willow_dorm_binding_stress_applies_template_sleeping_slots(
    _mock_client: MagicMock,
) -> None:
    raw = load_scenario("willow_dorm_binding_stress")
    prep = scenario_prepare_kwargs(raw)
    assert prep["scene_template_id"] == "marlene_willow_dorm_omega_misassignment"
    assert prep["scene_template_role_assignments"]["marlene"] == "alpha_roommate_marlene"
    st = prepare_headless_session(**prep, scenario_raw=raw)
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    tpl = SceneTemplateManager().load_template("marlene_willow_dorm_omega_misassignment")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)
    assert cm.scene_state.location_entry_slots == list(tpl.location_entry_slots)
    assert cm.scene_state.scene_template_id == "marlene_willow_dorm_omega_misassignment"
    assert cm.scene_state.role_assignments
    assert cm.issues
    assert any(
        "sleeping_surface" in str(iid) for iid in cm.issues
    ), "template with sleeping slots should seed sleeping-surface issue at init"
