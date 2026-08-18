"""Holy Grail Domain API package (V2)."""

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
    SessionCreateRequest,
    SessionInfoResponse,
    SessionOpenRequest,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import FixtureStore, create_prototype_scene
from .kernel import PROTOTYPE_DIRECTOR_DECISION, PROTOTYPE_VALID_MOVE, DomainKernel
from .session_repository import PersistenceError, SessionRepository
from .session_state import LiveSession, RoundFixture, SceneFixture

__all__ = [
    "CommitRequest",
    "CommitResponse",
    "ContextPrepareRequest",
    "DirectorContextPrepareRequest",
    "DirectorDecisionResult",
    "DirectorDecisionValidationRequest",
    "DomainKernel",
    "FixtureStore",
    "LiveSession",
    "PersistenceError",
    "PROTOTYPE_DIRECTOR_DECISION",
    "PROTOTYPE_VALID_MOVE",
    "PromptContribution",
    "PromptContributionManifest",
    "RoundFixture",
    "RoundStartRequest",
    "RoundStartResponse",
    "SceneFixture",
    "SceneStateSnapshot",
    "SessionCreateRequest",
    "SessionInfoResponse",
    "SessionOpenRequest",
    "SessionRepository",
    "ValidationRequest",
    "ValidationResponse",
    "create_prototype_scene",
]
