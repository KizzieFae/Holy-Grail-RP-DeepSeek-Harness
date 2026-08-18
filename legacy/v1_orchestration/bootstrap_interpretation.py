"""Bootstrap interpretation dataclass and continuity projection (Issue #165 split)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

Surface = Literal["streamlit", "headless"]

BOOTSTRAP_SHIM_SCHEMA_VERSION = "94.1"

# Keys consumed by ``apply_scene_setup_to_scene_state`` (bootstrap-owned projection → apply).
_SCENE_SETUP_APPLY_KEYS = frozenset(
    {
        "template_id",
        "premise",
        "anchor_role_name",
        "role_assignments",
        "character_presence_constraints",
        "character_authority_labels",
        "sleeping_surface_slots",
        "location_entry_slots",
    }
)


class BootstrapCompositionError(ValueError):
    """Scene-start composition failed (no silent strategy fallback)."""


@dataclass(frozen=True)
class BootstrapInterpretation:
    """Sole authority for scene-start inputs after successful composition (Issue #94)."""

    bootstrap_schema_version: str
    id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    character_refs: tuple[str, ...] = ()
    template_ref: str | None = None
    location: str = ""
    opening_strategy: str = ""
    opening_ref: str | None = None
    opening_resolved_text: str = ""
    first_round_user_line: str = ""
    initial_continuity: dict[str, Any] = field(default_factory=dict)
    harness_seed_issue: dict[str, Any] | None = None

    def scene_setup_for_continuity_apply(self) -> dict[str, Any] | None:
        """Flatten ``initial_continuity`` projection to ``apply_scene_setup`` shape."""
        flat: dict[str, Any] = {}
        tb = self.initial_continuity.get("template_binding") or {}
        if isinstance(tb, dict) and tb.get("template_id"):
            flat["template_id"] = str(tb["template_id"])
        rs = self.initial_continuity.get("role_structure") or {}
        if isinstance(rs, dict):
            for key in (
                "role_assignments",
                "character_authority_labels",
                "character_presence_constraints",
            ):
                v = rs.get(key)
                if isinstance(v, dict):
                    flat[key] = dict(v)
        sp = self.initial_continuity.get("structural_premise")
        if sp is not None and str(sp).strip():
            flat["premise"] = str(sp)
        slots = self.initial_continuity.get("structural_slots") or {}
        if isinstance(slots, dict):
            arn = slots.get("anchor_role_name")
            if arn is not None and str(arn).strip():
                flat["anchor_role_name"] = str(arn).strip()
            for key in ("sleeping_surface_slots", "location_entry_slots"):
                v = slots.get(key)
                if isinstance(v, list):
                    flat[key] = list(v)
        return flat if flat else None


def build_initial_continuity_projection(
    scene_setup: dict[str, Any] | None,
    *,
    harness_narrative_start: dict[str, Any] | None = None,
    harness_seeded_issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bootstrap-owned nested projection (not a raw ``scene_setup`` pass-through)."""
    proj: dict[str, Any] = {}
    if scene_setup and isinstance(scene_setup, dict):
        tid = scene_setup.get("template_id")
        if tid:
            proj["template_binding"] = {"template_id": str(tid)}
        proj["role_structure"] = {
            "role_assignments": dict(scene_setup.get("role_assignments", {}) or {}),
            "character_authority_labels": dict(
                scene_setup.get("character_authority_labels", {}) or {}
            ),
            "character_presence_constraints": dict(
                scene_setup.get("character_presence_constraints", {}) or {}
            ),
        }
        proj["structural_premise"] = str(scene_setup.get("premise", "") or "")
        proj["structural_slots"] = {
            "anchor_role_name": scene_setup.get("anchor_role_name"),
            "sleeping_surface_slots": list(
                scene_setup.get("sleeping_surface_slots", []) or []
            ),
            "location_entry_slots": list(
                scene_setup.get("location_entry_slots", []) or []
            ),
        }
    if harness_narrative_start:
        proj["narrative_start_state"] = dict(harness_narrative_start)
    if harness_seeded_issues:
        proj["seeded_issues"] = list(harness_seeded_issues)
    return proj


def interpretation_to_seed_scene_setup(
    interp: BootstrapInterpretation,
) -> dict[str, Any] | None:
    """Shape compatible with ``_seed_scene_role_*`` (premise + role maps)."""
    flat = interp.scene_setup_for_continuity_apply()
    premise = interp.initial_continuity.get("structural_premise")
    out: dict[str, Any] = dict(flat) if flat else {}
    if premise is not None and str(premise).strip():
        out["premise"] = str(premise)
    return out if out else None


def interpretation_to_jsonable(interp: BootstrapInterpretation) -> dict[str, Any]:
    """Session / audit friendly dict (tests, debugging)."""
    return {
        "bootstrap_schema_version": interp.bootstrap_schema_version,
        "id": interp.id,
        "metadata": dict(interp.metadata),
        "character_refs": list(interp.character_refs),
        "template_ref": interp.template_ref,
        "location": interp.location,
        "opening_strategy": interp.opening_strategy,
        "opening_ref": interp.opening_ref,
        "opening_resolved_text": interp.opening_resolved_text,
        "first_round_user_line": interp.first_round_user_line,
        "initial_continuity": json.loads(json.dumps(interp.initial_continuity)),
        "harness_seed_issue": interp.harness_seed_issue,
    }
