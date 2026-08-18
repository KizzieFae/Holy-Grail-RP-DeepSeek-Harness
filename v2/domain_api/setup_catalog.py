"""UI-safe catalogs for authored character cards and scene templates."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.character_cards import CharacterCardLoader  # noqa: E402
from scene_opener import OpenerManager  # noqa: E402
from scene_template import SceneTemplateManager  # noqa: E402


def _public_character_summary(card: dict[str, Any], file_id: str) -> dict[str, Any]:
    return {
        "character_id": file_id,
        "display_name": str(card.get("name", file_id)),
        "description": str(card.get("description", ""))[:280],
    }


def list_characters_catalog() -> list[dict[str, Any]]:
    loader = CharacterCardLoader()
    catalog: list[dict[str, Any]] = []
    for file_id in loader.list_available_characters():
        card = loader.load_character_card(file_id)
        catalog.append(_public_character_summary(card, file_id))
    catalog.sort(key=lambda item: item["display_name"].lower())
    return catalog


def list_scene_templates_catalog() -> list[dict[str, Any]]:
    manager = SceneTemplateManager()
    catalog: list[dict[str, Any]] = []
    for template in manager.list_templates():
        catalog.append(
            {
                "template_id": template.template_id,
                "premise": str(template.premise)[:320],
                "anchor_role_name": template.anchor_role_name,
                "role_slots": [slot.to_dict() for slot in template.role_slots],
            }
        )
    catalog.sort(key=lambda item: item["template_id"])
    return catalog


def list_template_openers_catalog(template_id: str) -> list[dict[str, Any]]:
    manager = OpenerManager()
    openers = manager.get_template_openers(template_id)
    return [
        {
            "opener_id": opener.id,
            "label": opener.label,
            "description": opener.description,
            "location": opener.location,
            "time": opener.time,
        }
        for opener in openers
    ]
