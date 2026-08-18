"""Template cohesion policy resolution and validation (#245)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scene_template import SceneRoleSlot, SceneTemplate

VALID_PRESENCE_CONSTRAINTS = frozenset({"must_remain", "flexible"})

COHESION_POLICY_ANCHOR_ONLY = "anchor_only"
VALID_COHESION_POLICIES = frozenset({COHESION_POLICY_ANCHOR_ONLY})

MIN_COHESION_RATIONALE_LEN = 20
MAX_COHESION_RATIONALE_LEN = 200

_WEAK_RATIONALE_PATTERNS = (
    re.compile(r"^\s*high authority\s*$", re.I),
    re.compile(r"^\s*required role\s*$", re.I),
    re.compile(r"^\s*important character\s*$", re.I),
    re.compile(r"^\s*required:\s*true\s*$", re.I),
    re.compile(r"^\s*authority:\s*(high|medium|low)\s*$", re.I),
)

_COHESION_FUNCTION_SIGNALS = (
    "focal",
    "scene",
    "space",
    "shared",
    "visible",
    "margin",
    "room",
    "cohesion",
    "remain",
    "presence",
    "interaction",
    "confrontation",
    "evaluation",
    "visit",
    "shower",
    "cell",
    "lock-in",
    "lock in",
    "mess hall",
    "study",
    "apartment",
    "shrine",
    "dorm",
    "predation",
    "cohabitation",
    "response beat",
)


def normalize_cohesion_policy(raw: str, *, template_id: str) -> str:
    policy = str(raw or "").strip()
    if not policy:
        raise ValueError(
            f"Scene template '{template_id}' is missing required cohesion_policy."
        )
    if policy not in VALID_COHESION_POLICIES:
        raise ValueError(
            f"Scene template '{template_id}': invalid cohesion_policy {policy!r}. "
            f"Expected one of {sorted(VALID_COHESION_POLICIES)}."
        )
    return policy


def _is_anchor_slot(template: SceneTemplate, slot: SceneRoleSlot) -> bool:
    return slot.role_name.lower() == template.anchor_role_name.lower()


def _authored_presence(slot: SceneRoleSlot) -> str:
    return str(slot.presence_constraint or "").strip()


def validate_cohesion_rationale(
    rationale: str,
    *,
    template_id: str,
    role_name: str,
) -> None:
    text = str(rationale or "").strip()
    if len(text) < MIN_COHESION_RATIONALE_LEN:
        raise ValueError(
            f"Scene template '{template_id}': role {role_name!r} requires "
            f"cohesion_rationale of at least {MIN_COHESION_RATIONALE_LEN} characters."
        )
    if len(text) > MAX_COHESION_RATIONALE_LEN:
        raise ValueError(
            f"Scene template '{template_id}': role {role_name!r} "
            f"cohesion_rationale exceeds {MAX_COHESION_RATIONALE_LEN} characters."
        )
    for pattern in _WEAK_RATIONALE_PATTERNS:
        if pattern.match(text):
            raise ValueError(
                f"Scene template '{template_id}': role {role_name!r} "
                "cohesion_rationale must describe scene-cohesion function, "
                "not merely importance, authority, or requiredness."
            )
    lowered = text.lower()
    if lowered in {"high authority", "required role", "important character"}:
        raise ValueError(
            f"Scene template '{template_id}': role {role_name!r} "
            "cohesion_rationale must describe scene-cohesion function."
        )
    if not any(signal in lowered for signal in _COHESION_FUNCTION_SIGNALS):
        raise ValueError(
            f"Scene template '{template_id}': role {role_name!r} "
            "cohesion_rationale must describe scene-cohesion function, "
            "not merely importance, authority, or requiredness."
        )


def resolve_effective_presence_constraint(
    template: SceneTemplate,
    slot: SceneRoleSlot,
) -> str:
    """Return effective presence constraint under anchor_only policy."""
    if template.cohesion_policy != COHESION_POLICY_ANCHOR_ONLY:
        raise ValueError(
            f"Scene template '{template.template_id}': unsupported cohesion_policy "
            f"{template.cohesion_policy!r}."
        )
    authored = _authored_presence(slot)
    if _is_anchor_slot(template, slot):
        if authored == "flexible":
            raise ValueError(
                f"Scene template '{template.template_id}': anchor role "
                f"{slot.role_name!r} cannot use presence_constraint 'flexible'."
            )
        return "must_remain"
    if not authored or authored == "flexible":
        return "flexible"
    if authored == "must_remain":
        return "must_remain"
    raise ValueError(
        f"Scene template '{template.template_id}': role {slot.role_name!r} has invalid "
        f"presence_constraint {authored!r}."
    )


def validate_template_cohesion(template: SceneTemplate) -> None:
    """Validate cohesion_policy and slot constraints for a parsed template."""
    normalize_cohesion_policy(template.cohesion_policy, template_id=template.template_id)
    if template.cohesion_policy != COHESION_POLICY_ANCHOR_ONLY:
        return

    for slot in template.role_slots:
        authored = _authored_presence(slot)
        if authored and authored not in VALID_PRESENCE_CONSTRAINTS:
            raise ValueError(
                f"Scene template '{template.template_id}': role {slot.role_name!r} has "
                f"invalid presence_constraint {authored!r}."
            )
        if _is_anchor_slot(template, slot):
            if authored == "flexible":
                raise ValueError(
                    f"Scene template '{template.template_id}': anchor role "
                    f"{slot.role_name!r} cannot use presence_constraint 'flexible'."
                )
            continue
        if authored == "must_remain":
            validate_cohesion_rationale(
                slot.cohesion_rationale,
                template_id=template.template_id,
                role_name=slot.role_name,
            )
