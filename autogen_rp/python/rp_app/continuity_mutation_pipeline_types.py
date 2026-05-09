"""Typed continuity mutation models (Issue #81 / #170 mechanical extraction)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ContinuityMutationError(ValueError):
    """Invalid mutation proposal or resolution; continuity commit must abort."""


class CanonicalAtom(str, Enum):
    """v1 canonical atoms; extend with new enum members only when adding slices."""

    LOCATION = "location"
    EXCURSION_LIFECYCLE = "excursion_lifecycle"


class MutationSourceClass(str, Enum):
    """Proposal source class for precedence (D wins over S wins over M)."""

    D = "D"
    S = "S"
    M = "M"


class ContinuityMutationType(str, Enum):
    """Closed mutation family set."""

    SPATIAL_TRANSITION = "SPATIAL_TRANSITION"
    EXCURSION_OPEN = "EXCURSION_OPEN"
    EXCURSION_UPDATE = "EXCURSION_UPDATE"
    EXCURSION_CLOSE = "EXCURSION_CLOSE"


_SOURCE_RANK = {
    MutationSourceClass.D: 3,
    MutationSourceClass.S: 2,
    MutationSourceClass.M: 1,
}

MAX_SPATIAL_LOCATION_LEN = 500
MAX_EXCURSION_ID_LEN = 200
MAX_EXCURSION_PARTICIPANTS = 64
_PENDING_OPEN_SCOPE = "__pending_open__"


@dataclass(frozen=True)
class MutationResolutionKey:
    """One canonical mutation slot per commit (one D/S/M winner per key)."""

    atom: CanonicalAtom
    """For ``EXCURSION_LIFECYCLE``, non-empty scope (excursion_id or pending-open sentinel)."""

    excursion_scope: str = ""

    @staticmethod
    def for_location() -> MutationResolutionKey:
        return MutationResolutionKey(CanonicalAtom.LOCATION, "")

    @staticmethod
    def for_excursion_scope(scope: str) -> MutationResolutionKey:
        sk = str(scope or "").strip()
        if not sk:
            raise ContinuityMutationError("excursion resolution scope must be non-empty")
        if len(sk) > MAX_EXCURSION_ID_LEN:
            raise ContinuityMutationError("excursion id exceeds maximum length")
        return MutationResolutionKey(CanonicalAtom.EXCURSION_LIFECYCLE, sk)

    def audit_slug(self) -> str:
        if self.atom == CanonicalAtom.LOCATION:
            return CanonicalAtom.LOCATION.value
        return f"{CanonicalAtom.EXCURSION_LIFECYCLE.value}:{self.excursion_scope}"


@dataclass(frozen=True)
class MutationRequest:
    mutation_type: ContinuityMutationType
    atom: CanonicalAtom
    source: MutationSourceClass
    payload: dict[str, Any]
