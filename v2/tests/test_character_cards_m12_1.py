"""M12.1 framework-neutral character card I/O tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.character_cards import (  # noqa: E402
    CHARACTER_MOVE_SCHEMA,
    CharacterCardLoader,
    make_agent_identifier,
    normalize_relationships,
    validate_character_card,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class CharacterCardsM121Tests(unittest.TestCase):
    def test_make_agent_identifier_sanitizes_display_names(self) -> None:
        self.assertEqual(make_agent_identifier("Dr. Jeremiah Arkham"), "Dr_Jeremiah_Arkham")
        self.assertEqual(make_agent_identifier("Poison Ivy"), "Poison_Ivy")

    def test_normalize_relationships_string_stance(self) -> None:
        result = normalize_relationships({"Player": "ally"})
        self.assertEqual(result["Player"]["stance"], "ally")
        self.assertEqual(result["Player"]["entity_type"], "character")

    def test_load_and_list_real_cards(self) -> None:
        loader = CharacterCardLoader()
        file_ids = loader.list_available_characters()
        self.assertIn("kizzie", file_ids)
        card = loader.load_character_card("kizzie")
        self.assertEqual(card["name"], "Kizzie")
        validate_character_card(card)

    def test_custom_dir_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            card_path = Path(tmpdir) / "test_char.json"
            card_path.write_text(
                json.dumps(
                    {
                        "name": "Test Hero",
                        "description": "A test card.",
                    }
                ),
                encoding="utf-8",
            )
            loader = CharacterCardLoader(tmpdir)
            self.assertEqual(loader.list_available_characters(), ["test_char"])
            loaded = loader.load_character_card("test_char")
            self.assertEqual(loaded["name"], "Test Hero")

    def test_v2_session_setup_uses_neutral_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SessionRepository(tmpdir)
            kernel = DomainKernel.for_repository(repo)
            info = kernel.create_session(
                characters=["kizzie"],
                opening={"mode": "minimal"},
            )
            fixture = repo.require(info.hg_session_id)
            self.assertIn("kizzie", fixture.setup_snapshot.get("character_cards", {}))
            self.assertEqual(fixture.character_file_ids.get("Kizzie"), "kizzie")

    def test_catalog_uses_neutral_loader(self) -> None:
        from domain_api.setup_catalog import list_characters_catalog

        catalog = list_characters_catalog()
        kizzie = next(item for item in catalog if item["character_id"] == "kizzie")
        self.assertEqual(kizzie["display_name"], "Kizzie")
        self.assertNotIn("system_prompt", kizzie)
        self.assertNotIn("lore_facts", kizzie)

    def test_character_move_schema_exported(self) -> None:
        self.assertEqual(CHARACTER_MOVE_SCHEMA["required"], [
            "move_schema_version",
            "beats",
            "motivation",
            "semantic_evaluation",
        ])

    def test_import_without_autogen_in_subprocess(self) -> None:
        root = str(_ROOT)
        script = f"""
import sys
sys.path.insert(0, {root!r} + "/v2")
from domain.character_cards import CharacterCardLoader
loader = CharacterCardLoader()
ids = loader.list_available_characters()
assert "kizzie" in ids
card = loader.load_character_card("kizzie")
assert card["name"] == "Kizzie"
print("ok")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(_ROOT / "v2" / "tests"),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_v2_production_does_not_import_legacy_character_loader(self) -> None:
        domain_api = _V2 / "domain_api"
        offenders: list[str] = []
        for path in domain_api.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "character_loader" in text:
                offenders.append(str(path.relative_to(_ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
