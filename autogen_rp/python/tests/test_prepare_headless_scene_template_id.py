"""Phase 3a: scene_template_id on prepare_headless_session (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_continuity import get_continuity_manager  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from headless_scene_simulation import prepare_headless_session  # noqa: E402
from scene_template import SceneTemplateManager  # noqa: E402

from progression_simulation_scenarios import load_scenario, scenario_prepare_kwargs  # noqa: E402


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_session_sets_scene_template_id(_mock_client: MagicMock) -> None:
    st = prepare_headless_session(
        character_card_ids=["ayame", "celina"],
        opening_description="Test opening.",
        location="test_loc",
        seed_escalating_issue=False,
        scene_template_id="arkham_asylum_cell_intake",
    )
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.scene_state.scene_template_id == "arkham_asylum_cell_intake"
    tpl = SceneTemplateManager().load_template("arkham_asylum_cell_intake")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)
    assert st.session_state.get("sim_retrieval_saw_nonempty_bundle") is False


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
    st = prepare_headless_session(**prep)
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    assert cm.scene_state.scene_template_id == "arkham_asylum_cell_intake"
    tpl = SceneTemplateManager().load_template("arkham_asylum_cell_intake")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)


@patch("headless_scene_simulation.create_deepseek_client", return_value=MagicMock())
def test_prepare_headless_willow_dorm_binding_stress_applies_template_sleeping_slots(
    _mock_client: MagicMock,
) -> None:
    raw = load_scenario("willow_dorm_binding_stress")
    prep = scenario_prepare_kwargs(raw)
    assert prep["scene_template_id"] == "marlene_willow_dorm_omega_misassignment"
    assert prep["scene_template_role_assignments"]["marlene"] == "alpha_roommate_marlene"
    st = prepare_headless_session(**prep)
    cm = get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    assert cm is not None and cm.scene_state is not None
    tpl = SceneTemplateManager().load_template("marlene_willow_dorm_omega_misassignment")
    assert cm.scene_state.sleeping_surface_slots == list(tpl.sleeping_surface_slots)
    assert cm.scene_state.location_entry_slots == list(tpl.location_entry_slots)
    assert cm.scene_state.scene_template_id == "marlene_willow_dorm_omega_misassignment"
    assert cm.scene_state.role_assignments
