"""Mandatory checker validation corpus for Issue #121."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from player_decomposition_fixtures import (
    ISSUE_120_SEIZA_JAPAN_TURN,
    build_issue_88_mixed_turn_fixture,
)

RouteExpectation = Literal["uniform_projection", "full_pvr"]


@dataclass(frozen=True)
class CheckerCorpusCase:
    case_id: str
    content: str
    expected_route: RouteExpectation
    category: str
    safety_critical: bool = False


def build_issue_121_checker_corpus() -> list[CheckerCorpusCase]:
    issue_88_content, _ = build_issue_88_mixed_turn_fixture()
    return [
        CheckerCorpusCase(
            case_id="pos_simple_speech",
            content='"Hello everyone," the player says with a smile.',
            expected_route="uniform_projection",
            category="uniform_safe_positive",
        ),
        CheckerCorpusCase(
            case_id="pos_simple_action",
            content="The player sets the lantern on the table and steps back.",
            expected_route="uniform_projection",
            category="uniform_safe_positive",
        ),
        CheckerCorpusCase(
            case_id="pos_scene_description",
            content="Rain drums against the window while candlelight flickers across the worn floorboards.",
            expected_route="uniform_projection",
            category="uniform_safe_positive",
        ),
        CheckerCorpusCase(
            case_id="pos_mixed_action_speech",
            content=(
                'The player lifts the crate onto the shelf. "There—that should hold," they say to the room.'
            ),
            expected_route="uniform_projection",
            category="uniform_safe_positive",
        ),
        CheckerCorpusCase(
            case_id="neg_seiza_japan_120",
            content=ISSUE_120_SEIZA_JAPAN_TURN,
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_issue_88_mixed",
            content=issue_88_content,
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_concealed_action",
            content=(
                "The player smiles at Harley while slipping a folded note into their sleeve unseen."
            ),
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_internal_cognition",
            content="The player wonders whether anyone here can be trusted, but says nothing.",
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_explanatory_narration",
            content=(
                "Off-screen, the duke had already decided this meeting would end in betrayal."
            ),
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_directed_speech",
            content='The player leans toward Ayame and whispers, "Meet me after dark."',
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_role_private",
            content="Only the priest would recognize the old blessing carved into the doorframe.",
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_ambiguous_lowered_voice",
            content='The player lowers their voice, wondering aloud, "Could any of them hear that?"',
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_exterior_threshold_visual_155",
            content=(
                "Kizzie checks the address on the gatepost, looks around the quiet street, "
                "and hesitates at the front door."
            ),
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_exterior_address_check_155",
            content="The player studies the house number and smooths their skirt nervously.",
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
        CheckerCorpusCase(
            case_id="neg_mixed_visual_knock_speech_155",
            content=(
                "Kizzie looks at the house number, nervously smooths her skirt, knocks three times, "
                'then calls through the door, "Ayame? It\'s Kizzie. I\'m here for the interview."'
            ),
            expected_route="full_pvr",
            category="mandatory_negative",
            safety_critical=True,
        ),
    ]
