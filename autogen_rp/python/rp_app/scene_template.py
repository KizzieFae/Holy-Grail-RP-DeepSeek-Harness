import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VALID_PRESENCE_CONSTRAINTS = {"must_remain", "flexible"}


@dataclass
class SceneRoleSlot:
    role_name: str
    required: bool
    presence_constraint: str
    authority: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_name": self.role_name,
            "required": self.required,
            "presence_constraint": self.presence_constraint,
            "authority": self.authority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneRoleSlot":
        presence_constraint = str(data.get("presence_constraint", "") or "").strip()
        if presence_constraint not in VALID_PRESENCE_CONSTRAINTS:
            raise ValueError(
                f"Invalid presence_constraint '{presence_constraint}'. Expected one of {sorted(VALID_PRESENCE_CONSTRAINTS)}."
            )
        role_name = str(data.get("role_name", "") or "").strip()
        if not role_name:
            raise ValueError("Scene role slot is missing role_name.")
        return cls(
            role_name=role_name,
            required=bool(data.get("required", False)),
            presence_constraint=presence_constraint,
            authority=str(data.get("authority", "") or "").strip(),
        )


@dataclass
class TemplateInitialMessage:
    file: str
    label: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "label": self.label,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateInitialMessage":
        file = str(data.get("file", "") or "").strip()
        if not file:
            raise ValueError("Template initial message is missing file.")
        return cls(
            file=file,
            label=str(data.get("label", "") or "").strip() or file,
            description=str(data.get("description", "") or "").strip(),
        )


@dataclass
class SceneTemplate:
    template_id: str
    premise: str
    opening_text: str
    role_slots: list[SceneRoleSlot]
    initial_messages: list[TemplateInitialMessage] = field(default_factory=list)
    progression_profile: dict[str, Any] | None = None
    sleeping_surface_slots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "template_id": self.template_id,
            "premise": self.premise,
            "opening_text": self.opening_text,
            "role_slots": [slot.to_dict() for slot in self.role_slots],
            "initial_messages": [msg.to_dict() for msg in self.initial_messages],
            "sleeping_surface_slots": list(self.sleeping_surface_slots),
        }
        if self.progression_profile is not None:
            out["progression_profile"] = dict(self.progression_profile)
        return out

    def get_role_slot(self, role_name: str) -> SceneRoleSlot | None:
        normalized = str(role_name or "").strip().lower()
        for slot in self.role_slots:
            if slot.role_name.lower() == normalized:
                return slot
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneTemplate":
        template_id = str(data.get("template_id", "") or "").strip()
        if not template_id:
            raise ValueError("Scene template is missing template_id.")
        role_slots = [
            SceneRoleSlot.from_dict(item)
            for item in data.get("role_slots", [])
            if isinstance(item, dict)
        ]
        if not role_slots:
            raise ValueError(
                f"Scene template '{template_id}' must define at least one role slot."
            )
        initial_messages = [
            TemplateInitialMessage.from_dict(item)
            for item in data.get("initial_messages", [])
            if isinstance(item, dict)
        ]
        raw_prog = data.get("progression_profile")
        progression_profile = (
            dict(raw_prog) if isinstance(raw_prog, dict) else None
        )
        sleeping_surface_slots = [
            str(item).strip()
            for item in data.get("sleeping_surface_slots", [])
            if str(item or "").strip()
        ]
        return cls(
            template_id=template_id,
            premise=str(data.get("premise", "") or "").strip(),
            opening_text=str(data.get("opening_text", "") or "").strip(),
            role_slots=role_slots,
            initial_messages=initial_messages,
            progression_profile=progression_profile,
            sleeping_surface_slots=sleeping_surface_slots,
        )


@dataclass
class RoleAssignment:
    character_id: str
    role: str

    def to_dict(self) -> dict[str, str]:
        return {
            "character_id": self.character_id,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoleAssignment":
        character_id = str(data.get("character_id", "") or "").strip()
        role = str(data.get("role", "") or "").strip()
        if not character_id:
            raise ValueError("Role assignment is missing character_id.")
        if not role:
            raise ValueError(f"Role assignment for '{character_id}' is missing role.")
        return cls(character_id=character_id, role=role)


class SceneTemplateManager:
    def __init__(self, templates_dir: str | Path | None = None) -> None:
        if templates_dir is None:
            self.templates_dir = (
                Path(__file__).parent.parent / "data" / "scene_templates"
            )
        else:
            self.templates_dir = Path(templates_dir)

    def list_templates(self) -> list[SceneTemplate]:
        if not self.templates_dir.exists():
            return []
        templates: list[SceneTemplate] = []
        for path in sorted(self.templates_dir.glob("*.json")):
            if path.stem.endswith("_initial_message"):
                continue
            try:
                templates.append(self.load_template(path.stem))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return templates

    def load_template(self, template_id: str) -> SceneTemplate:
        path = self.templates_dir / f"{template_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Scene template not found: {template_id}")
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Scene template '{template_id}' must be a JSON object.")
        template = SceneTemplate.from_dict(data)
        if template.template_id != template_id:
            raise ValueError(
                f"Scene template id mismatch: file '{template_id}.json' contains '{template.template_id}'."
            )
        return template


def normalize_role_assignments(
    assignments: dict[str, str] | list[RoleAssignment] | None,
) -> dict[str, str]:
    if assignments is None:
        return {}
    if isinstance(assignments, dict):
        normalized: dict[str, str] = {}
        for character_id, role in assignments.items():
            character_key = str(character_id or "").strip()
            role_name = str(role or "").strip()
            if character_key and role_name:
                normalized[character_key] = role_name
        return normalized
    normalized = {}
    for assignment in assignments:
        normalized[str(assignment.character_id).strip()] = str(assignment.role).strip()
    return normalized


def validate_role_assignments(
    template: SceneTemplate,
    selected_character_ids: list[str],
    assignments: dict[str, str] | list[RoleAssignment] | None,
) -> list[str]:
    normalized_assignments = normalize_role_assignments(assignments)
    issues: list[str] = []
    selected_ids = [
        str(item or "").strip()
        for item in selected_character_ids
        if str(item or "").strip()
    ]
    selected_id_set = set(selected_ids)
    valid_roles = {slot.role_name for slot in template.role_slots}

    for selected_id in selected_ids:
        if selected_id not in normalized_assignments:
            issues.append(
                f"Missing role assignment for selected character: {selected_id}"
            )

    for character_id in normalized_assignments:
        if character_id not in selected_id_set:
            issues.append(
                f"Role assignment references a non-selected character: {character_id}"
            )

    assigned_roles = set()
    for character_id, role_name in normalized_assignments.items():
        if role_name not in valid_roles:
            issues.append(
                f"Character '{character_id}' was assigned unknown role '{role_name}' for template '{template.template_id}'"
            )
            continue
        assigned_roles.add(role_name)

    for slot in template.role_slots:
        if slot.required and slot.role_name not in assigned_roles:
            issues.append(f"Required role is unfilled: {slot.role_name}")

    return issues
