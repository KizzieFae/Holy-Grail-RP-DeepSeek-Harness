"""Holy Grail Domain API package (V2 boundary prototype)."""

from .contract import (
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionResult,
    DirectorDecisionValidationRequest,
    PromptContribution,
    PromptContributionManifest,
    RoundStartRequest,
    RoundStartResponse,
    SceneStateSnapshot,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import FixtureStore, RoundFixture, SceneFixture, create_prototype_scene
from .kernel import PROTOTYPE_DIRECTOR_DECISION, PROTOTYPE_VALID_MOVE, DomainKernel

__all__ = [
    "CommitRequest",
    "CommitResponse",
    "ContextPrepareRequest",
    "DirectorContextPrepareRequest",
    "DirectorDecisionResult",
    "DirectorDecisionValidationRequest",
    "DomainKernel",
    "FixtureStore",
    "PROTOTYPE_DIRECTOR_DECISION",
    "PROTOTYPE_VALID_MOVE",
    "PromptContribution",
    "PromptContributionManifest",
    "RoundFixture",
    "RoundStartRequest",
    "RoundStartResponse",
    "SceneFixture",
    "SceneStateSnapshot",
    "ValidationRequest",
    "ValidationResponse",
    "create_prototype_scene",
]
