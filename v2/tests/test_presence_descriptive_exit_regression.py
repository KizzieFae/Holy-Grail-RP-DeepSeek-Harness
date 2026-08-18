"""Known descriptive-exit presence regression (M12.4 preservation).

Documents ContinuityManager contract: descriptive exit moves update
``present_characters`` / ``absent_but_relevant``. Underlying behavior fix
is out of scope for M12.4; this test preserves evidence of the discrepancy.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from continuity_manager import ContinuityManager  # noqa: E402
from continuity_setup_seam_v77 import (  # noqa: E402
    ensure_interim_anchor_role_fallback_for_finalize,
    finalize_continuity_setup_seam,
)


def _complete_setup_seam(manager: ContinuityManager) -> None:
    cast = [
        str(x).strip()
        for x in (manager.scene_state.present_characters or [])
        if str(x or "").strip()
    ]
    ensure_interim_anchor_role_fallback_for_finalize(manager, cast=cast)
    finalize_continuity_setup_seam(manager, cast=cast)


class DescriptiveExitPresenceRegressionTests(unittest.TestCase):
    @pytest.mark.xfail(
        reason="Known domain discrepancy — descriptive exit presence (pre-M12.4 baseline)",
        strict=True,
    )
    def test_descriptive_exit_updates_authoritative_presence_state(self) -> None:
        manager = ContinuityManager()
        manager.initialize_scene(
            location="Dorm 303",
            opening_description="The argument spills across the threshold.",
            present_characters=["Ayame", "Celina", "Mira"],
        )
        _complete_setup_seam(manager)
        manager.process_turn(
            acting_character="Mira",
            move={
                "action": (
                    "let the door swing shut behind her and stalked down the hallway "
                    "toward the stairwell without looking back"
                ),
                "dialogue": "",
                "motivation": {
                    "goal": "remove herself from the confrontation entirely",
                    "tactic": "put the hallway and stairwell between herself and the room",
                    "emotional_driver": "anger",
                    "risk_level": "medium",
                },
            },
            director_decision={
                "next_actor": "Ayame",
                "environment_event": "The door shudders in Mira's wake.",
                "tension_shift": "steady",
                "reason": "Mira leaves the room rather than continuing the exchange.",
            },
            other_characters=["Ayame", "Celina"],
            timestamp=datetime.fromisoformat("2026-03-15T12:02:30"),
        )

        self.assertNotIn("Mira", manager.scene_state.present_characters)
        self.assertIn("Mira", manager.scene_state.absent_but_relevant)
        self.assertEqual(
            manager.public_events[0].state_changes,
            ["Mira left the immediate scene."],
        )


if __name__ == "__main__":
    unittest.main()
