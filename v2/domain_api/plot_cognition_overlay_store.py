"""Plot Cognition Overlay current-state store types and integrity (#59)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from .plot_cognition_overlay_contract import (
    GlobalPlotFrame,
    PlotGoal,
    UnresolvedNarrativePressure,
    global_plot_frame_from_dict,
    global_plot_frame_to_dict,
    plot_goal_from_dict,
    plot_goal_to_dict,
    unresolved_narrative_pressure_from_dict,
    unresolved_narrative_pressure_to_dict,
    validate_global_plot_frame,
    validate_plot_goal,
    validate_unresolved_narrative_pressure,
)

PLOT_COGNITION_OVERLAY_STORE_SCHEMA = "hg_plot_cognition_overlay_store_v1"
ASSIMILATED_AUTHORITY_SCHEMA = "hg_plot_cognition_assimilated_authority_v1"

AuthorityFreshnessStatus = Literal[
    "fresh",
    "authority_generation_changed_unchecked",
    "semantic_assimilation_pending",
    "lineage_incomplete",
    "shared_scope_ambiguous",
    "freshness_unprovable",
    "overlay_unavailable",
]


@dataclass(frozen=True)
class AssimilatedSessionAuthority:
    hg_scene_id: str
    through_domain_commit_id: str | None
    through_continuity_version: int
    authority_source_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hg_scene_id": self.hg_scene_id,
            "through_domain_commit_id": self.through_domain_commit_id,
            "through_continuity_version": self.through_continuity_version,
            "authority_source_fingerprint": self.authority_source_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssimilatedSessionAuthority:
        return cls(
            hg_scene_id=str(data.get("hg_scene_id", "")),
            through_domain_commit_id=data.get("through_domain_commit_id"),
            through_continuity_version=int(data.get("through_continuity_version", 0)),
            authority_source_fingerprint=str(data.get("authority_source_fingerprint", "")),
        )


@dataclass
class AssimilatedAuthority:
    schema: str
    sessions: tuple[AssimilatedSessionAuthority, ...]
    scope_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "sessions": [session.to_dict() for session in self.sessions],
        }
        if self.scope_status is not None:
            payload["scope_status"] = self.scope_status
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssimilatedAuthority:
        sessions_raw = data.get("sessions") or []
        sessions: list[AssimilatedSessionAuthority] = []
        if isinstance(sessions_raw, list):
            for item in sessions_raw:
                if isinstance(item, dict):
                    sessions.append(AssimilatedSessionAuthority.from_dict(item))
        return cls(
            schema=str(data.get("schema", "")),
            sessions=tuple(sessions),
            scope_status=data.get("scope_status"),
        )


class LoadStatus(str, Enum):
    ABSENT = "absent"
    READY = "ready"
    DEGRADED = "degraded"
    CORRUPT = "corrupt"
    UNSUPPORTED_VERSION = "unsupported_version"


@dataclass(frozen=True)
class BoundednessPolicy:
    max_active_goals: int
    max_active_pressures: int

    def __post_init__(self) -> None:
        if self.max_active_goals <= 0:
            raise ValueError("max_active_goals must be > 0")
        if self.max_active_pressures <= 0:
            raise ValueError("max_active_pressures must be > 0")


@dataclass
class PlotCognitionOverlayStore:
    store_schema: str
    plot_cognition_scope_id: str
    store_revision: int
    assimilated_through_domain_commit_id: str | None
    goals: dict[str, PlotGoal]
    pressures: dict[str, UnresolvedNarrativePressure]
    active_frame: GlobalPlotFrame | None = None
    assimilated_authority: AssimilatedAuthority | None = None
    pending_work: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "store_schema": self.store_schema,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "store_revision": self.store_revision,
            "assimilated_through_domain_commit_id": self.assimilated_through_domain_commit_id,
            "goals": {
                goal_id: plot_goal_to_dict(goal)
                for goal_id, goal in sorted(self.goals.items())
            },
            "pressures": {
                pressure_id: unresolved_narrative_pressure_to_dict(pressure)
                for pressure_id, pressure in sorted(self.pressures.items())
            },
            "active_frame": (
                global_plot_frame_to_dict(self.active_frame)
                if self.active_frame is not None
                else None
            ),
        }
        if self.assimilated_authority is not None:
            payload["assimilated_authority"] = self.assimilated_authority.to_dict()
        if self.pending_work is not None:
            payload["pending_work"] = dict(self.pending_work)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionOverlayStore:
        goals_raw = data.get("goals") or {}
        pressures_raw = data.get("pressures") or {}
        frame_raw = data.get("active_frame")
        goals: dict[str, PlotGoal] = {}
        if isinstance(goals_raw, dict):
            for goal_id, item in goals_raw.items():
                if isinstance(item, dict):
                    goals[str(goal_id)] = plot_goal_from_dict(item)
        pressures: dict[str, UnresolvedNarrativePressure] = {}
        if isinstance(pressures_raw, dict):
            for pressure_id, item in pressures_raw.items():
                if isinstance(item, dict):
                    pressures[str(pressure_id)] = unresolved_narrative_pressure_from_dict(item)
        active_frame = (
            global_plot_frame_from_dict(frame_raw)
            if isinstance(frame_raw, dict)
            else None
        )
        authority_raw = data.get("assimilated_authority")
        assimilated_authority = (
            AssimilatedAuthority.from_dict(authority_raw)
            if isinstance(authority_raw, dict)
            else None
        )
        return cls(
            store_schema=str(data.get("store_schema", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            store_revision=int(data.get("store_revision", 0)),
            assimilated_through_domain_commit_id=data.get("assimilated_through_domain_commit_id"),
            goals=goals,
            pressures=pressures,
            active_frame=active_frame,
            assimilated_authority=assimilated_authority,
            pending_work=dict(data["pending_work"]) if isinstance(data.get("pending_work"), dict) else None,
        )


@dataclass(frozen=True)
class IntegrityReport:
    ok: bool
    over_budget: bool = False
    violations: tuple[str, ...] = ()
    malformed_goal_ids: tuple[str, ...] = ()
    malformed_pressure_ids: tuple[str, ...] = ()
    malformed_frame: bool = False
    retired_goal_ids: tuple[str, ...] = ()
    retired_pressure_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperativePlotCognitionView:
    goals: tuple[PlotGoal, ...]
    pressures: tuple[UnresolvedNarrativePressure, ...]
    active_frame: GlobalPlotFrame | None


@dataclass(frozen=True)
class LoadResult:
    status: LoadStatus
    store: PlotCognitionOverlayStore | None
    integrity: IntegrityReport
    diagnostics: tuple[str, ...] = ()
    quarantine_path: str | None = None


@dataclass(frozen=True)
class ReplaceResult:
    success: bool
    prior_revision: int | None
    new_revision: int | None
    integrity: IntegrityReport
    error_code: str | None = None
    error_message: str | None = None


def empty_store(plot_cognition_scope_id: str) -> PlotCognitionOverlayStore:
    return PlotCognitionOverlayStore(
        store_schema=PLOT_COGNITION_OVERLAY_STORE_SCHEMA,
        plot_cognition_scope_id=plot_cognition_scope_id,
        store_revision=0,
        assimilated_through_domain_commit_id=None,
        goals={},
        pressures={},
        active_frame=None,
    )


def count_active_goals(store: PlotCognitionOverlayStore) -> int:
    return sum(1 for goal in store.goals.values() if goal.activity_state == "active")


def count_active_pressures(store: PlotCognitionOverlayStore) -> int:
    return sum(
        1 for pressure in store.pressures.values() if pressure.activity_state == "active"
    )


def validate_store_entries(store: PlotCognitionOverlayStore) -> IntegrityReport:
    violations: list[str] = []
    malformed_goal_ids: list[str] = []
    malformed_pressure_ids: list[str] = []
    retired_goal_ids: list[str] = []
    retired_pressure_ids: list[str] = []

    if store.store_schema != PLOT_COGNITION_OVERLAY_STORE_SCHEMA:
        violations.append("store_schema_mismatch")
    if not str(store.plot_cognition_scope_id or "").strip():
        violations.append("plot_cognition_scope_id_required")

    for goal_id, goal in store.goals.items():
        if goal.activity_state == "retired":
            retired_goal_ids.append(goal_id)
            violations.append(f"retired_goal_in_current_store:{goal_id}")
            continue
        ok, goal_violations = validate_plot_goal(goal)
        if not ok:
            malformed_goal_ids.append(goal_id)
            violations.extend(f"goal:{goal_id}:{item}" for item in goal_violations)

    for pressure_id, pressure in store.pressures.items():
        if pressure.activity_state == "retired":
            retired_pressure_ids.append(pressure_id)
            violations.append(f"retired_pressure_in_current_store:{pressure_id}")
            continue
        ok, pressure_violations = validate_unresolved_narrative_pressure(pressure)
        if not ok:
            malformed_pressure_ids.append(pressure_id)
            violations.extend(
                f"pressure:{pressure_id}:{item}" for item in pressure_violations
            )

    malformed_frame = False
    if store.active_frame is not None:
        ok, frame_violations = validate_global_plot_frame(store.active_frame)
        if not ok:
            malformed_frame = True
            violations.extend(f"frame:{item}" for item in frame_violations)
        elif store.active_frame.activity_state != "active":
            violations.append("active_frame_must_be_active")

    return IntegrityReport(
        ok=len(violations) == 0,
        violations=tuple(violations),
        malformed_goal_ids=tuple(malformed_goal_ids),
        malformed_pressure_ids=tuple(malformed_pressure_ids),
        malformed_frame=malformed_frame,
        retired_goal_ids=tuple(retired_goal_ids),
        retired_pressure_ids=tuple(retired_pressure_ids),
    )


def validate_boundedness(
    store: PlotCognitionOverlayStore,
    *,
    policy: BoundednessPolicy,
) -> IntegrityReport:
    entry_report = validate_store_entries(store)
    if not entry_report.ok:
        return entry_report

    violations = list(entry_report.violations)
    active_goals = count_active_goals(store)
    active_pressures = count_active_pressures(store)
    over_budget = False
    if active_goals > policy.max_active_goals:
        over_budget = True
        violations.append("active_goals_over_budget")
    if active_pressures > policy.max_active_pressures:
        over_budget = True
        violations.append("active_pressures_over_budget")

    return IntegrityReport(
        ok=len(violations) == 0,
        over_budget=over_budget,
        violations=tuple(violations),
        malformed_goal_ids=entry_report.malformed_goal_ids,
        malformed_pressure_ids=entry_report.malformed_pressure_ids,
        malformed_frame=entry_report.malformed_frame,
        retired_goal_ids=entry_report.retired_goal_ids,
        retired_pressure_ids=entry_report.retired_pressure_ids,
    )


def build_operative_view(store: PlotCognitionOverlayStore) -> OperativePlotCognitionView:
    active_goals = tuple(
        goal for goal in store.goals.values() if goal.activity_state == "active"
    )
    active_pressures = tuple(
        pressure
        for pressure in store.pressures.values()
        if pressure.activity_state == "active"
    )
    return OperativePlotCognitionView(
        goals=active_goals,
        pressures=active_pressures,
        active_frame=store.active_frame,
    )


def is_assimilation_current(
    store: PlotCognitionOverlayStore,
    *,
    current_domain_commit_id: str | None,
) -> bool:
    current = str(current_domain_commit_id or "").strip() or None
    if current is None:
        return True
    assimilated = str(store.assimilated_through_domain_commit_id or "").strip() or None
    if assimilated is None:
        return False
    return assimilated == current


def is_assimilation_stale(
    store: PlotCognitionOverlayStore,
    *,
    current_domain_commit_id: str | None,
) -> bool:
    current = str(current_domain_commit_id or "").strip() or None
    if current is None:
        return False
    return not is_assimilation_current(
        store,
        current_domain_commit_id=current,
    )


def _session_authority_for_scene(
    authority: AssimilatedAuthority | None,
    *,
    hg_scene_id: str,
) -> AssimilatedSessionAuthority | None:
    if authority is None:
        return None
    target = str(hg_scene_id or "").strip()
    for session in authority.sessions:
        if session.hg_scene_id == target:
            return session
    return None


def sync_legacy_commit_lineage(
    store: PlotCognitionOverlayStore,
    *,
    sole_contributor_hg_scene_id: str | None = None,
) -> PlotCognitionOverlayStore:
    """Keep legacy scalar aligned with sole-contributor vector entry."""
    authority = store.assimilated_authority
    if authority is None or len(authority.sessions) != 1:
        return store
    session = authority.sessions[0]
    if sole_contributor_hg_scene_id and session.hg_scene_id != sole_contributor_hg_scene_id:
        return store
    store.assimilated_through_domain_commit_id = session.through_domain_commit_id
    return store


def authority_freshness_status(
    store: PlotCognitionOverlayStore,
    *,
    current_domain_commit_id: str | None,
    current_continuity_version: int,
    current_authority_source_fingerprint: str | None,
    contributor_hg_scene_ids: tuple[str, ...] = (),
) -> AuthorityFreshnessStatus:
    authority = store.assimilated_authority
    if authority is None:
        return "freshness_unprovable"

    expected_contributors = tuple(
        str(item).strip() for item in contributor_hg_scene_ids if str(item).strip()
    )
    known_ids = {session.hg_scene_id for session in authority.sessions}
    if expected_contributors:
        if not set(expected_contributors).issubset(known_ids):
            return "shared_scope_ambiguous"
        if len(authority.sessions) != len(expected_contributors):
            return "shared_scope_ambiguous"

    current_commit = str(current_domain_commit_id or "").strip() or None
    if len(authority.sessions) == 1:
        session = authority.sessions[0]
        assimilated_commit = str(session.through_domain_commit_id or "").strip() or None
        if current_commit is not None and assimilated_commit != current_commit:
            return "semantic_assimilation_pending"
        if current_continuity_version == session.through_continuity_version:
            return "fresh"
        if (
            current_authority_source_fingerprint is not None
            and current_authority_source_fingerprint == session.authority_source_fingerprint
        ):
            return "authority_generation_changed_unchecked"
        return "semantic_assimilation_pending"

    if not authority.sessions:
        return "freshness_unprovable"

    for session in authority.sessions:
        if not str(session.hg_scene_id or "").strip():
            return "shared_scope_ambiguous"
        if not str(session.authority_source_fingerprint or "").strip():
            return "shared_scope_ambiguous"

    if expected_contributors:
        for scene_id in expected_contributors:
            session = _session_authority_for_scene(authority, hg_scene_id=scene_id)
            if session is None:
                return "shared_scope_ambiguous"
            if current_continuity_version != session.through_continuity_version:
                return "shared_scope_ambiguous"
    return "shared_scope_ambiguous"


def is_authority_fresh(
    store: PlotCognitionOverlayStore,
    *,
    current_domain_commit_id: str | None,
    current_continuity_version: int,
    current_authority_source_fingerprint: str | None,
    contributor_hg_scene_ids: tuple[str, ...] = (),
) -> bool:
    return (
        authority_freshness_status(
            store,
            current_domain_commit_id=current_domain_commit_id,
            current_continuity_version=current_continuity_version,
            current_authority_source_fingerprint=current_authority_source_fingerprint,
            contributor_hg_scene_ids=contributor_hg_scene_ids,
        )
        == "fresh"
    )


def classify_load_status(
    *,
    raw_present: bool,
    envelope_ok: bool,
    unsupported_version: bool,
    integrity: IntegrityReport,
) -> LoadStatus:
    if not raw_present:
        return LoadStatus.ABSENT
    if unsupported_version:
        return LoadStatus.UNSUPPORTED_VERSION
    if not envelope_ok:
        return LoadStatus.CORRUPT
    if integrity.ok:
        return LoadStatus.READY
    return LoadStatus.DEGRADED
