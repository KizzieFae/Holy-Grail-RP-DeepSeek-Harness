"""Project a persisted player user history entry for a Character viewer (#91, #120 harness)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[3]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from perceptual_scene_context import PerceptualSceneContextV1  # noqa: E402
from player_perceptual_projection import assemble_player_user_entry_for_viewer  # noqa: E402


def _serialize_result(result: Any) -> dict[str, Any]:
    return {
        "content": result.content,
        "included_unit_ids": list(result.included_unit_ids),
        "excluded_unit_ids": list(result.excluded_unit_ids),
        "exclusion_reasons": dict(result.exclusion_reasons),
        "authority_narrowed_unit_ids": list(result.authority_narrowed_unit_ids),
        "degraded_path": result.degraded_path,
        "source_entry_id": result.source_entry_id,
        "viewer_character": result.viewer_character,
        "record_validation_status": result.record_validation_status,
        "source_kind": result.source_kind,
        "validation_profile": result.validation_profile,
        "historical_normalization": result.historical_normalization,
        "legacy_metadata_key": result.legacy_metadata_key,
        "projector_id": result.projector_id,
        "projector_version": result.projector_version,
        "unit_entitlement_decisions": list(result.unit_entitlement_decisions),
    }


def _parse_scene_context(raw: Any) -> PerceptualSceneContextV1 | None:
    if not isinstance(raw, dict) or not raw:
        return None
    return PerceptualSceneContextV1.from_dict(raw)


def main() -> None:
    payload = json.load(sys.stdin)
    entry = payload["entry"]
    viewer_character = str(payload["viewer_character"])
    present_characters = [str(name) for name in payload.get("present_characters") or []]
    scene_context = _parse_scene_context(payload.get("perceptual_scene_context"))
    player_character = payload.get("player_character")
    player_character_name = (
        str(player_character).strip() if player_character is not None else None
    )
    result = assemble_player_user_entry_for_viewer(
        entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        perceptual_scene_context=scene_context,
        player_character=player_character_name,
    )
    json.dump(_serialize_result(result), sys.stdout)


if __name__ == "__main__":
    main()
