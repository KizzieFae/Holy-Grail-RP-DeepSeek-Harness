"""Seed a co-present session with trembling observable for issue #199 supplemental validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "v2"))
from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from domain.tests.perceptual_test_helpers import co_present_zone_context
from domain_api.contract import RoundStartRequest, UserTurnRecordRequest
from domain_api.kernel import DomainKernel
from domain_api.session_repository import SessionRepository
from player_source_accounting import normalize_source_for_indexing, normalized_source_sha256


def build_trembling_decomposition() -> dict:
    content = "Kizzie's hands trembled visibly as she waited."
    norm = normalize_source_for_indexing(content)
    return {
        "perceptual_visibility": {
            "units": [
                {
                    "unit_id": "u_tremble",
                    "kind": "observable_event",
                    "text": norm,
                    "perception_channel": "visual",
                    "recipients": {"scope": "present", "characters": [], "roles": []},
                    "source_provenance": {"segment_ids": ["s1"], "order_index": 0},
                    "source": "player_decomposition",
                }
            ]
        },
        "source_accounting": {
            "source_length": len(norm),
            "source_sha256": normalized_source_sha256(norm),
            "normalization": "nfc_nfkc_ws_collapse",
            "segments": [
                {
                    "segment_id": "s1",
                    "char_start": 0,
                    "char_end": len(norm),
                    "disposition": "projects",
                    "unit_ids": ["u_tremble"],
                }
            ],
        },
        "generation": {"inference_id": "issue199-supplemental-tremble-decomposition"},
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: seed_issue199_copresent_session.py <sessions_dir>")
    sessions_dir = Path(sys.argv[1])
    sessions_dir.mkdir(parents=True, exist_ok=True)
    repository = SessionRepository(sessions_dir)
    kernel = DomainKernel.for_repository(repository)
    scene = kernel.create_scene(cast=["Ayame", "Kizzie"], location="Evaluation room")
    fixture = kernel.store.require(scene.hg_session_id)
    fixture.manager.scene_state.perceptual_scene_context = co_present_zone_context(
        ["Ayame", "Kizzie"]
    ).to_dict()
    fixture.setup_snapshot = {
        "character_file_ids": {"kizzie": "Kizzie"},
        "control_modes": {"Kizzie": "player"},
    }
    rnd = kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    content = "Kizzie's hands trembled visibly as she waited."
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=fixture.hg_session_id,
            content=content,
            speaker="Kizzie",
            player_decomposition=build_trembling_decomposition(),
            hg_round_id=rnd.hg_round_id,
        )
    )
    fixture = kernel.store.require(fixture.hg_session_id)
    repository.persist(fixture)
    print(
        json.dumps(
            {
                "hg_session_id": fixture.hg_session_id,
                "hg_round_id": rnd.hg_round_id,
                "turn_counter": fixture.manager.turn_counter,
            }
        )
    )


if __name__ == "__main__":
    main()
