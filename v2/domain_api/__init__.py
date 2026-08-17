"""Holy Grail Domain API package (V2 boundary prototype)."""

from .contract import (
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
    SceneStateSnapshot,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import FixtureStore, SceneFixture, create_prototype_scene
from .kernel import PROTOTYPE_VALID_MOVE, DomainKernel

__all__ = [
    "CommitRequest",
    "CommitResponse",
    "ContextPrepareRequest",
    "DomainKernel",
    "FixtureStore",
    "PROTOTYPE_VALID_MOVE",
    "PromptContribution",
    "PromptContributionManifest",
    "SceneFixture",
    "SceneStateSnapshot",
    "ValidationRequest",
    "ValidationResponse",
    "create_prototype_scene",
]
