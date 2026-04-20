import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from scene_template import SceneTemplateManager, validate_role_assignments


def test_scene_template_requires_anchor_role_name(tmp_path: Path) -> None:
    (tmp_path / "t.json").write_text(
        json.dumps(
            {
                "template_id": "t",
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
                        "presence_constraint": "must_remain",
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
                        "presence_constraint": "must_remain",
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
                        "presence_constraint": "must_remain",
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


def test_arkham_templates_keep_new_arrival_optional() -> None:
    templates_dir = Path(__file__).resolve().parent.parent / "data" / "scene_templates"
    manager = SceneTemplateManager(templates_dir)

    for template_id in [
        "arkham_asylum_cell_intake",
        "arkham_asylum_shower_predation",
        "arkham_asylum_cafeteria_magpie_incident",
        "arkham_asylum_cafeteria_harley_ivy_conflict",
    ]:
        template = manager.load_template(template_id)
        role_slot = template.get_role_slot("new_arrival")
        assert role_slot is not None
        assert role_slot.required is False


def test_harley_ivy_conflict_uses_high_authority_staff_response_slot() -> None:
    templates_dir = Path(__file__).resolve().parent.parent / "data" / "scene_templates"
    manager = SceneTemplateManager(templates_dir)

    template = manager.load_template("arkham_asylum_cafeteria_harley_ivy_conflict")
    witness_role_slot = template.get_role_slot("witness_or_intervenor")
    role_slot = template.get_role_slot("guard_or_staff_response")

    assert witness_role_slot is not None
    assert witness_role_slot.required is False
    assert witness_role_slot.presence_constraint == "flexible"
    assert witness_role_slot.authority == "medium"
    assert role_slot is not None
    assert role_slot.required is False
    assert role_slot.presence_constraint == "flexible"
    assert role_slot.authority == "high"


def test_celina_recovery_template_stays_grounded_and_slow_recovery() -> None:
    templates_dir = Path(__file__).resolve().parent.parent / "data" / "scene_templates"
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
    assert "fragile stabilization under pressure" in template.opening_text
    assert (
        "unusual traits or impossible-seeming developments carrying real emotional weight"
        in template.opening_text
    )
