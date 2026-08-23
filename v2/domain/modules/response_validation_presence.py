from typing import Any


# must_remain: keep the character in the Director's selection pool for the scene.
# They may be offstage (hallway, another room, etc.) until the narrative brings them back;
# that is not a validation failure and does not drop them from cast obligations.


def get_must_remain_characters(scene_state: dict[str, Any] | None) -> list[str]:
    if not isinstance(scene_state, dict):
        return []
    presence_constraints = scene_state.get("character_presence_constraints", {})
    if not isinstance(presence_constraints, dict):
        return []
    return [
        str(character_name)
        for character_name, constraint in presence_constraints.items()
        if str(constraint or "") == "must_remain"
    ]
