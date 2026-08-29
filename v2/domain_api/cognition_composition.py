"""Bounded cognition service composition for the Domain Host (#53 C1)."""

from __future__ import annotations

from dataclasses import dataclass

from .character_service import CharacterKnowledgeService
from .librarian_proposal_service import LibrarianProposalService
from .librarian_service import LibrarianService
from .retrieval_service import RetrievalService
from .plot_cognition_initialization_service import PlotCognitionInitializationService
from .plot_cognition_overlay_repository import PlotCognitionOverlayRepository
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_scope_lock import PlotCognitionScopeLockRegistry
from .plot_cognition_update_service import PlotCognitionUpdateService
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
    plot_cognition_overlay: PlotCognitionOverlayService | None
    plot_cognition_initialization: PlotCognitionInitializationService | None
    plot_cognition_update: PlotCognitionUpdateService | None

    @classmethod
    def create(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository | None,
        story_knowledge_repository: StoryKnowledgeRepository | None,
        plot_cognition_overlay_repository: PlotCognitionOverlayRepository | None = None,
        plot_cognition_scope_locks: PlotCognitionScopeLockRegistry | None = None,
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
        plot_cognition_overlay = (
            PlotCognitionOverlayService(
                plot_cognition_overlay_repository,
                scope_locks=plot_cognition_scope_locks,
            )
            if plot_cognition_overlay_repository is not None
            else None
        )
        plot_cognition_initialization = (
            PlotCognitionInitializationService(plot_cognition_overlay)
            if plot_cognition_overlay is not None
            else None
        )
        plot_cognition_update = (
            PlotCognitionUpdateService(plot_cognition_overlay)
            if plot_cognition_overlay is not None
            else None
        )
        return cls(
            retrieval=retrieval,
            librarian=librarian,
            storyteller=storyteller,
            librarian_proposals=librarian_proposals,
            character_knowledge=character_knowledge,
            story_knowledge=story_knowledge,
            plot_cognition_overlay=plot_cognition_overlay,
            plot_cognition_initialization=plot_cognition_initialization,
            plot_cognition_update=plot_cognition_update,
        )

    @classmethod
    def create_for_production(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository,
        story_knowledge_repository: StoryKnowledgeRepository,
        plot_cognition_overlay_repository: PlotCognitionOverlayRepository | None = None,
        plot_cognition_scope_locks: PlotCognitionScopeLockRegistry | None = None,
    ) -> CognitionComposition:
        """Production bootstrap: fail if required repositories are missing."""
        if scope_knowledge_repository is None or story_knowledge_repository is None:
            raise ValueError(
                "production cognition composition requires scope and story knowledge repositories"
            )
        return cls.create(
            scope_knowledge_repository=scope_knowledge_repository,
            story_knowledge_repository=story_knowledge_repository,
            plot_cognition_overlay_repository=plot_cognition_overlay_repository,
            plot_cognition_scope_locks=plot_cognition_scope_locks,
        )

    @classmethod
    def for_tests(
        cls,
        *,
        scope_knowledge_repository: ScopeKnowledgeRepository | None = None,
        story_knowledge_repository: StoryKnowledgeRepository | None = None,
        plot_cognition_overlay_repository: PlotCognitionOverlayRepository | None = None,
        plot_cognition_scope_locks: PlotCognitionScopeLockRegistry | None = None,
    ) -> CognitionComposition:
        """Test helper — delegates to the canonical create() path."""
        return cls.create(
            scope_knowledge_repository=scope_knowledge_repository,
            story_knowledge_repository=story_knowledge_repository,
            plot_cognition_overlay_repository=plot_cognition_overlay_repository,
            plot_cognition_scope_locks=plot_cognition_scope_locks,
        )
