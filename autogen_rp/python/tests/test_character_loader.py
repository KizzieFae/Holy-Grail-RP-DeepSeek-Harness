"""Character loader tests for internal agent identifiers."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_loader import CharacterLoader, make_agent_identifier


def test_make_agent_identifier_sanitizes_display_names() -> None:
    assert make_agent_identifier("Dr. Jeremiah Arkham") == "Dr_Jeremiah_Arkham"
    assert make_agent_identifier("Poison Ivy") == "Poison_Ivy"


def test_create_agent_uses_identifier_but_preserves_display_name() -> None:
    loader = CharacterLoader()
    card = {
        "name": "Dr. Jeremiah Arkham",
        "description": "Clinical institutional authority.",
        "personality": "Cold and controlled.",
        "speaking_style": "Clinical and patronizing.",
        "goals": "Maintain institutional control.",
    }

    agent, state = loader.create_agent(card, MagicMock())

    assert agent.name == "Dr_Jeremiah_Arkham"
    assert state.name == "Dr. Jeremiah Arkham"
