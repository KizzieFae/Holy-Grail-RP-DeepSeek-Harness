"""Bounded cognition service composition for the Domain Host (#53 C1)."""

from __future__ import annotations

from dataclasses import dataclass

from .character_service import CharacterKnowledgeService
from .librarian_proposal_service import LibrarianProposalService
from .librarian_service import LibrarianService
from .retrieval_service import RetrievalService
from .scope_knowledge_repository import ScopeKnowledgeRepository
from .story_knowledge_repository import StoryKnowledgeRepository
from .story_knowledge_service import StoryKnowledgeService
from .storyteller_service import StorytellerService


@dataclass(frozen=True)
class CognitionComposition:
    """Application-scoped cognition service graph (bootstrap-owned, not repository-owned)."""

    retrieval: RetrievalService
    librarian: LibrarianService
    storyteller: StorytellerService
    librarian_proposals: LibrarianProposalService
    character_knowledge: CharacterKnowledgeService
    story_knowledge: StoryKnowledgeService | None

    @classmethod
    def create(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository | None,
        story_knowledge_repository: StoryKnowledgeRepository | None,
    ) -> CognitionComposition:
        """Canonical cognition graph wiring (production and tests)."""
        retrieval = RetrievalService(
            scope_repo=scope_knowledge_repository,
            story_knowledge_repo=story_knowledge_repository,
        )
        librarian = LibrarianService(retrieval_service=retrieval)
        storyteller = StorytellerService(librarian_service=librarian)
        librarian_proposals = LibrarianProposalService()
        character_knowledge = CharacterKnowledgeService()
        story_knowledge = (
            StoryKnowledgeService(story_knowledge_repository)
            if story_knowledge_repository is not None
            else None
        )
        return cls(
            retrieval=retrieval,
            librarian=librarian,
            storyteller=storyteller,
            librarian_proposals=librarian_proposals,
            character_knowledge=character_knowledge,
            story_knowledge=story_knowledge,
        )

    @classmethod
    def create_for_production(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository,
        story_knowledge_repository: StoryKnowledgeRepository,
    ) -> CognitionComposition:
        """Production bootstrap: fail if required repositories are missing."""
        if scope_knowledge_repository is None or story_knowledge_repository is None:
            raise ValueError(
                "production cognition composition requires scope and story knowledge repositories"
            )
        return cls.create(
            scope_knowledge_repository=scope_knowledge_repository,
            story_knowledge_repository=story_knowledge_repository,
        )

    @classmethod
    def for_tests(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository | None = None,
        story_knowledge_repository: StoryKnowledgeRepository | None = None,
    ) -> CognitionComposition:
        """Test helper — delegates to the canonical create() path."""
        return cls.create(
            scope_knowledge_repository=scope_knowledge_repository,
            story_knowledge_repository=story_knowledge_repository,
        )
