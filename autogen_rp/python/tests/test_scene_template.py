import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from domain.paths import scene_templates_data_dir
from scene_opener import OpenerManager
from scene_template import (
    SceneRoleSlot,
    SceneTemplate,
    SceneTemplateManager,
    validate_role_assignments,
)


def test_scene_template_requires_anchor_role_name(tmp_path: Path) -> None:
    (tmp_path / "t.json").write_text(
        json.dumps(
            {
                "template_id": "t",
                "cohesion_policy": "anchor_only",
                "premise": "p",
                "opening_text": "o",
                "role_slots": [
                    {
                        "role_name": "only",
                        "required": True,
                        "presence_constraint": "must_remain",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="anchor_role_name"):
        SceneTemplateManager(tmp_path).load_template("t")


def test_scene_template_manager_loads_minimal_template(tmp_path: Path) -> None:
    template_path = tmp_path / "mansion_interview.json"
    template_path.write_text(
        json.dumps(
            {
                "template_id": "mansion_interview",
                "cohesion_policy": "anchor_only",
                "premise": "A newcomer is evaluated inside a controlled household.",
                "opening_text": "The interview begins under careful observation.",
                "anchor_role_name": "host",
                "role_slots": [
                    {
                        "role_name": "host",
                        "required": True,
                        "presence_constraint": "must_remain",
                    },
                    {
                        "role_name": "guard",
                        "required": False,
                        "authority": "medium",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = SceneTemplateManager(tmp_path)
    template = manager.load_template("mansion_interview")

    assert template.template_id == "mansion_interview"
    assert template.premise
    assert template.get_role_slot("host") is not None
    assert template.get_role_slot("guard") is not None
    assert template.anchor_role_name == "host"


def test_validate_role_assignments_requires_explicit_role_for_each_selected_character(
    tmp_path: Path,
) -> None:
    template_path = tmp_path / "parlor_scene.json"
    template_path.write_text(
        json.dumps(
            {
                "template_id": "parlor_scene",
                "cohesion_policy": "anchor_only",
                "premise": "A tense meeting in the parlor.",
                "opening_text": "Everyone gathers in the parlor.",
                "anchor_role_name": "host",
                "role_slots": [
                    {
                        "role_name": "host",
                        "required": True,
                        "presence_constraint": "must_remain",
                    },
                    {
                        "role_name": "guest",
                        "required": True,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = SceneTemplateManager(tmp_path)
    template = manager.load_template("parlor_scene")

    issues = validate_role_assignments(
        template,
        ["ayame", "celina"],
        {"ayame": "host"},
    )

    assert any("Missing role assignment" in issue for issue in issues)
    assert any("Required role is unfilled: guest" in issue for issue in issues)


def test_validate_role_assignments_accepts_valid_explicit_assignments(
    tmp_path: Path,
) -> None:
    template_path = tmp_path / "parlor_scene.json"
    template_path.write_text(
        json.dumps(
            {
                "template_id": "parlor_scene",
                "cohesion_policy": "anchor_only",
                "premise": "A tense meeting in the parlor.",
                "opening_text": "Everyone gathers in the parlor.",
                "anchor_role_name": "host",
                "role_slots": [
                    {
                        "role_name": "host",
                        "required": True,
                        "presence_constraint": "must_remain",
                    },
                    {
                        "role_name": "guest",
                        "required": True,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = SceneTemplateManager(tmp_path)
    template = manager.load_template("parlor_scene")

    issues = validate_role_assignments(
        template,
        ["ayame", "celina"],
        {"ayame": "host", "celina": "guest"},
    )

    assert issues == []


def test_scene_template_manager_ignores_template_owned_initial_message_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "arkham_asylum_cell_intake.json").write_text(
        json.dumps(
            {
                "template_id": "arkham_asylum_cell_intake",
                "cohesion_policy": "anchor_only",
                "premise": "A new arrival is locked into a cell.",
                "opening_text": "The cell door closes.",
                "anchor_role_name": "new_arrival",
                "role_slots": [
                    {
                        "role_name": "new_arrival",
                        "required": True,
                        "presence_constraint": "must_remain",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (tmp_path / "arkham_asylum_cell_intake_initial_message.json").write_text(
        json.dumps(
            {
                "label": "Arkham Cell Intake",
                "text": "A steel door slams shut.",
                "tags": ["arkham"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = SceneTemplateManager(tmp_path)

    templates = manager.list_templates()

    assert [template.template_id for template in templates] == [
        "arkham_asylum_cell_intake"
    ]


def test_scene_template_manager_ignores_template_owned_progression_support_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "arkham_asylum_cell_intake.json").write_text(
        json.dumps(
            {
                "template_id": "arkham_asylum_cell_intake",
                "cohesion_policy": "anchor_only",
                "premise": "A new arrival is locked into a cell.",
                "opening_text": "The cell door closes.",
                "anchor_role_name": "new_arrival",
                "role_slots": [
                    {
                        "role_name": "new_arrival",
                        "required": True,
                        "presence_constraint": "must_remain",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (tmp_path / "arkham_asylum_cell_intake_progression.json").write_text(
        json.dumps(
            {
                "advancement_channels": ["consequence"],
                "common_stall_pattern": "test stall pattern",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = SceneTemplateManager(tmp_path)
    templates = manager.list_templates()

    assert [template.template_id for template in templates] == [
        "arkham_asylum_cell_intake"
    ]


def test_arkham_templates_keep_new_arrival_optional() -> None:
    templates_dir = scene_templates_data_dir()
    manager = SceneTemplateManager(templates_dir)

    for template_id in [
        "arkham_asylum_cell_intake",
        "arkham_asylum_shower_predation",
        "arkham_asylum_mess_hall_arena",
    ]:
        template = manager.load_template(template_id)
        role_slot = template.get_role_slot("new_arrival")
        assert role_slot is not None
        assert role_slot.required is False


def test_mess_hall_arena_uses_high_authority_staff_response_slot() -> None:
    templates_dir = scene_templates_data_dir()
    manager = SceneTemplateManager(templates_dir)

    template = manager.load_template("arkham_asylum_mess_hall_arena")
    witness_role_slot = template.get_role_slot("witness_or_intervenor")
    role_slot = template.get_role_slot("guard_or_staff_response")

    assert witness_role_slot is not None
    assert witness_role_slot.required is False
    assert witness_role_slot.authority == "medium"
    assert role_slot is not None
    assert role_slot.required is False
    assert role_slot.authority == "high"
    from scene_template_cohesion import resolve_effective_presence_constraint

    assert (
        resolve_effective_presence_constraint(template, witness_role_slot) == "flexible"
    )
    assert resolve_effective_presence_constraint(template, role_slot) == "must_remain"
    assert role_slot.cohesion_rationale


def test_celina_recovery_template_stays_grounded_and_slow_recovery() -> None:
    templates_dir = scene_templates_data_dir()
    manager = SceneTemplateManager(templates_dir)

    template = manager.load_template("celina_apartment_recovery_watch")

    assert "mostly grounded" in template.premise
    assert (
        "most people do not treat overt magic as a known public system"
        in template.premise
    )
    assert (
        "Do not assume hidden forms, supernatural recovery, or specialized occult knowledge"
        in template.premise
    )
    opener_mgr = OpenerManager(templates_dir=templates_dir)
    opener = opener_mgr.get_default_template_opener("celina_apartment_recovery_watch")
    assert opener is not None
    # Canonical opener: street rescue → car → apartment; slow physical recovery beats on couch.
    text_lower = opener.text.lower()
    assert "apartment" in text_lower
    assert "couch" in text_lower
    assert "blankets" in text_lower


def test_issue128_validate_role_assignments_accepts_player_file_in_cast() -> None:
    """Template cast may include bot files plus player POV file (Issue #128)."""
    template = SceneTemplate(
        template_id="t",
        premise="p",
        opening_text="",
        role_slots=[
            SceneRoleSlot(
                role_name="host",
                required=True,
                presence_constraint="flexible",
            ),
            SceneRoleSlot(
                role_name="applicant",
                required=True,
                presence_constraint="must_remain",
            ),
        ],
        anchor_role_name="applicant",
    )
    selected = ["bot.json", "player.json"]
    assignments = {"bot.json": "host", "player.json": "applicant"}
    assert validate_role_assignments(template, selected, assignments) == []


def _issue129_two_role_template() -> SceneTemplate:
    return SceneTemplate(
        template_id="t",
        premise="p",
        opening_text="",
        role_slots=[
            SceneRoleSlot(
                role_name="host",
                required=True,
                presence_constraint="flexible",
            ),
            SceneRoleSlot(
                role_name="applicant",
                required=True,
                presence_constraint="must_remain",
            ),
        ],
        anchor_role_name="applicant",
    )


def test_issue129_player_roleless_valid_when_npcs_fill_required_and_anchor() -> None:
    """Roleless player file in validation set; NPCs cover required + anchor (Issue #129)."""
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "npc_b.json", "player.json"]
    assignments = {"npc_a.json": "host", "npc_b.json": "applicant"}
    assert (
        validate_role_assignments(
            template,
            selected,
            assignments,
            player_character_file="player.json",
        )
        == []
    )


def test_issue129_player_invalid_assigned_role_still_invalid() -> None:
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "player.json"]
    issues = validate_role_assignments(
        template,
        selected,
        {"npc_a.json": "host", "player.json": "bogus_role"},
        player_character_file="player.json",
    )
    assert any("unknown role" in msg for msg in issues)


def test_issue129_player_holds_anchor_role_still_valid() -> None:
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "player.json"]
    assignments = {"npc_a.json": "host", "player.json": "applicant"}
    assert (
        validate_role_assignments(
            template,
            selected,
            assignments,
            player_character_file="player.json",
        )
        == []
    )


def test_issue129_non_player_missing_role_still_invalid() -> None:
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "npc_b.json", "player.json"]
    issues = validate_role_assignments(
        template,
        selected,
        {"npc_a.json": "host", "player.json": "applicant"},
        player_character_file="player.json",
    )
    assert any("Missing role assignment" in msg and "npc_b.json" in msg for msg in issues)


def test_issue129_player_roleless_but_required_unfilled_still_invalid() -> None:
    """Player may omit role; required slots must still be covered by assignments."""
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "player.json"]
    issues = validate_role_assignments(
        template,
        selected,
        {"npc_a.json": "host"},
        player_character_file="player.json",
    )
    assert any("Required role is unfilled: applicant" in msg for msg in issues)


def test_issue129_default_no_player_exception_preserves_strict_npc_rules() -> None:
    """Omitting player_character_file keeps mandatory role for every selected id."""
    template = _issue129_two_role_template()
    selected = ["npc_a.json", "npc_b.json"]
    issues = validate_role_assignments(
        template,
        selected,
        {"npc_a.json": "host"},
    )
    assert any("Missing role assignment" in msg for msg in issues)
