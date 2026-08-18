"""Legacy V1 compatibility shim over framework-neutral character card I/O."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2 = _REPO_ROOT / "v2"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.character_cards import (  # noqa: E402
    CHARACTER_MOVE_SCHEMA,
    CharacterCardLoader,
    make_agent_identifier,
    normalize_relationships,
)

_normalize_relationships = normalize_relationships


class CharacterLoader(CharacterCardLoader):
    """V1 loader: neutral card I/O plus legacy AutoGen agent construction."""

    def create_agent(self, character_card: dict[str, Any], model_client: Any) -> tuple[Any, Any]:
        from v1_autogen_agents import create_character_agent

        return create_character_agent(character_card, model_client)

    def load_and_create_agent(
        self,
        filename: str,
        model_client: Any,
    ) -> tuple[Any, Any]:
        card = self.load_character_card(filename)
        return self.create_agent(card, model_client)
