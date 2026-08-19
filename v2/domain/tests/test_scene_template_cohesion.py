import json
import sys
from pathlib import Path

import pytest


from domain.paths import scene_templates_data_dir
from scene_template import SceneTemplate, SceneTemplateManager
from scene_template_cohesion import resolve_effective_presence_constraint


def _minimal_anchor_only_template(**overrides: object) -> dict:
    base = {
        "template_id": "t",
        "cohesion_policy": "anchor_only",
        "premise": "p",
        "opening_text": "",
        "anchor_role_name": "anchor",
        "role_slots": [
            {"role_name": "anchor", "required": True, "presence_constraint": "must_remain"},
            {"role_name": "support", "required": True},
        ],
    }
    base.update(overrides)
    return base


def test_missing_cohesion_policy_rejected(tmp_path: Path) -> None:
    data = _minimal_anchor_only_template()
    del data["cohesion_policy"]
    (tmp_path / "t.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required cohesion_policy"):
        SceneTemplateManager(tmp_path).load_template("t")


def test_invalid_cohesion_policy_rejected(tmp_path: Path) -> None:
    (tmp_path / "t.json").write_text(
        json.dumps(_minimal_anchor_only_template(cohesion_policy="explicit")),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid cohesion_policy"):
        SceneTemplateManager(tmp_path).load_template("t")


def test_anchor_flexible_rejected(tmp_path: Path) -> None:
    data = _minimal_anchor_only_template(
        role_slots=[
            {"role_name": "anchor", "required": True, "presence_constraint": "flexible"},
            {"role_name": "support", "required": True},
        ]
    )
    (tmp_path / "t.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="anchor role.*flexible"):
        SceneTemplateManager(tmp_path).load_template("t")


def test_non_anchor_override_requires_rationale(tmp_path: Path) -> None:
    data = _minimal_anchor_only_template(
        role_slots=[
            {"role_name": "anchor", "required": True, "presence_constraint": "must_remain"},
            {
                "role_name": "support",
                "required": True,
                "presence_constraint": "must_remain",
            },
        ]
    )
    (tmp_path / "t.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="cohesion_rationale"):
        SceneTemplateManager(tmp_path).load_template("t")


def test_resolver_anchor_only_defaults() -> None:
    template = SceneTemplate.from_dict(
        _minimal_anchor_only_template(
            role_slots=[
                {"role_name": "anchor", "required": True, "presence_constraint": "must_remain"},
                {
                    "role_name": "support",
                    "required": True,
                    "presence_constraint": "must_remain",
                    "cohesion_rationale": "Support role must remain visible in the shared focal evaluation space.",
                },
                {"role_name": "rover", "required": False},
            ]
        )
    )
    anchor = template.get_role_slot("anchor")
    support = template.get_role_slot("support")
    rover = template.get_role_slot("rover")
    assert anchor is not None and support is not None and rover is not None
    assert resolve_effective_presence_constraint(template, anchor) == "must_remain"
    assert resolve_effective_presence_constraint(template, support) == "must_remain"
    assert resolve_effective_presence_constraint(template, rover) == "flexible"


def test_all_production_templates_load() -> None:
    templates_dir = scene_templates_data_dir()
    manager = SceneTemplateManager(templates_dir)
    templates = manager.list_templates()
    assert len(templates) == 9
    for template in templates:
        assert template.cohesion_policy == "anchor_only"


def test_weak_rationale_rejected(tmp_path: Path) -> None:
    data = _minimal_anchor_only_template(
        role_slots=[
            {"role_name": "anchor", "required": True, "presence_constraint": "must_remain"},
            {
                "role_name": "support",
                "required": True,
                "presence_constraint": "must_remain",
                "cohesion_rationale": "This role has high authority only.",
            },
        ]
    )
    (tmp_path / "t.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="scene-cohesion function"):
        SceneTemplateManager(tmp_path).load_template("t")
