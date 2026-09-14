"""Generate valid PVR decompositions for issue #199 supplemental validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "v2"))
from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()
from player_source_accounting import normalize_source_for_indexing, normalized_source_sha256


def mixed_f06_opening() -> dict:
    opening = (
        "Kizzie glanced up, double-checking the house number and then steeled herself before knocking."
    )
    norm = normalize_source_for_indexing(opening)
    u1 = normalize_source_for_indexing("Kizzie glanced up, double-checking the house number")
    u2 = normalize_source_for_indexing("and then steeled herself before knocking.")
    return {
        "perceptual_visibility": {
            "units": [
                {
                    "unit_id": "u_visual_glance",
                    "kind": "observable_event",
                    "text": u1,
                    "perception_channel": "visual",
                    "recipients": {"scope": "present", "characters": [], "roles": []},
                    "source_provenance": {"segment_ids": ["s1"], "order_index": 0},
                    "source": "player_decomposition",
                },
                {
                    "unit_id": "u_internal_steel",
                    "kind": "internal",
                    "text": u2,
                    "perception_channel": "non_perceptual",
                    "recipients": {"scope": "private", "characters": ["Kizzie"], "roles": []},
                    "source_provenance": {"segment_ids": ["s2"], "order_index": 1},
                    "source": "player_decomposition",
                },
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
                    "char_end": len(u1),
                    "disposition": "projects",
                    "unit_ids": ["u_visual_glance"],
                },
                {
                    "segment_id": "s2",
                    "char_start": len(u1),
                    "char_end": len(norm),
                    "disposition": "projects",
                    "unit_ids": ["u_internal_steel"],
                },
            ],
        },
        "generation": {"inference_id": "issue199-supplemental-f06-decomposition"},
    }


def trembling_observable() -> dict:
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
    out = ROOT / "governance" / "records" / "issue-199-supplemental-decompositions.json"
    out.write_text(
        json.dumps(
            {"f06_opening": mixed_f06_opening(), "trembling": trembling_observable()},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
