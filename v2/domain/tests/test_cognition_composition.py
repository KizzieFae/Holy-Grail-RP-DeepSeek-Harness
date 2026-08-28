"""Focused validation for #53 C1 cognition composition architecture."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.cognition_composition import CognitionComposition  # noqa: E402
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.librarian_service import LibrarianService  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.storyteller_service import StorytellerService  # noqa: E402


class CognitionCompositionTests(unittest.TestCase):
    def test_canonical_graph_is_constructible(self) -> None:
        composition = CognitionComposition.for_tests()
        self.assertIsNotNone(composition.retrieval)
        self.assertIsInstance(composition.librarian, LibrarianService)
        self.assertIsInstance(composition.storyteller, StorytellerService)
        self.assertIsNotNone(composition.librarian_proposals)
        self.assertIsNotNone(composition.character_knowledge)
        self.assertIsNone(composition.story_knowledge)

    def test_production_requires_both_repositories(self) -> None:
        with self.assertRaises(ValueError):
            CognitionComposition.create_for_production(
                scope_knowledge_repository=None,  # type: ignore[arg-type]
                story_knowledge_repository=None,  # type: ignore[arg-type]
            )

    def test_storyteller_reuses_composed_librarian_instance(self) -> None:
        composition = CognitionComposition.for_tests()
        self.assertIs(composition.storyteller._librarian, composition.librarian)

    def test_for_tests_delegates_to_create(self) -> None:
        direct = CognitionComposition.create(
            scope_knowledge_repository=None,
            story_knowledge_repository=None,
        )
        via_helper = CognitionComposition.for_tests()
        self.assertEqual(type(direct.librarian), type(via_helper.librarian))
        self.assertEqual(type(direct.storyteller), type(via_helper.storyteller))

    def test_kernel_delegates_with_stable_cognition_identity(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        first = kernel.cognition.storyteller
        second = kernel.cognition.storyteller
        self.assertIs(first, second)
        self.assertIs(kernel.cognition.librarian, kernel.cognition.storyteller._librarian)

    def test_for_repository_uses_production_composition(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            repo = SessionRepository(tmp)
            kernel = DomainKernel.for_repository(repo)
            self.assertIsNotNone(kernel.cognition.story_knowledge)
            self.assertIs(kernel.cognition.storyteller._librarian, kernel.cognition.librarian)

    def test_storyteller_dependency_failure_surfaces_at_composition_tier(self) -> None:
        with patch(
            "domain_api.cognition_composition.StorytellerService",
            side_effect=NameError("StorytellerService"),
        ):
            with self.assertRaises(NameError):
                CognitionComposition.for_tests()

    def test_for_repository_enforces_production_repositories(self) -> None:
        class _RepoMissingScope:
            scope_knowledge_repo = None
            story_knowledge_repo = object()

        with self.assertRaises(ValueError):
            DomainKernel.for_repository(_RepoMissingScope())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
