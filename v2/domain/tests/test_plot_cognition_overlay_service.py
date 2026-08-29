"""#59 Plot Cognition Overlay service, scope, and integrity tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.cognition_composition import CognitionComposition  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.memory_scope import new_memory_scope_id  # noqa: E402
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    GLOBAL_PLOT_FRAME_SCHEMA,
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
    CognitionApplicability,
    CreationProvenance,
    GlobalPlotFrame,
    GoalLineage,
    PlotGoal,
    UnresolvedNarrativePressure,
    new_frame_id,
    new_goal_id,
    new_pressure_id,
)
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    BoundednessPolicy,
    LoadStatus,
    PlotCognitionOverlayStore,
    empty_store,
)
from domain_api.plot_cognition_scope import (  # noqa: E402
    new_plot_cognition_scope_id,
    resolve_plot_cognition_scope_id,
)
from domain_api.plot_cognition_scope_lock import PlotCognitionScopeLockRegistry  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import V2_HOST_METADATA_KEY  # noqa: E402


TEST_POLICY = BoundednessPolicy(max_active_goals=2, max_active_pressures=2)


def _goal(*, goal_id: str | None = None, state: str = "active") -> PlotGoal:
    gid = goal_id or new_goal_id()
    return PlotGoal(
        schema=PLOT_GOAL_SCHEMA,
        goal_id=gid,
        intended_direction="Steer toward the vault.",
        basis_note="Alice distrusts Bob.",
        basis_refs=(StableReference(ref_kind="public_event", stable_ref="event-1"),),
        applicability=CognitionApplicability(
            applicability_kind="character",
            primary_character_id="Alice",
            involved_character_ids=("Alice",),
        ),
        planning_horizon="SHORT",
        creation_provenance=CreationProvenance(source="storyteller"),
        lineage=GoalLineage(),
        activity_state=state,  # type: ignore[arg-type]
    )


def _pressure(*, pressure_id: str | None = None, state: str = "active") -> UnresolvedNarrativePressure:
    pid = pressure_id or new_pressure_id()
    return UnresolvedNarrativePressure(
        schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
        pressure_id=pid,
        pressure_text="The vault remains unopened.",
        dramatic_rationale="Tension persists.",
        basis_note=None,
        basis_refs=(),
        continuity_issue_refs=(),
        applicability=CognitionApplicability(
            applicability_kind="global",
            primary_character_id=None,
            involved_character_ids=(),
        ),
        creation_provenance=CreationProvenance(source="storyteller"),
        activity_state=state,  # type: ignore[arg-type]
    )


def _frame(*, frame_id: str | None = None) -> GlobalPlotFrame:
    fid = frame_id or new_frame_id()
    return GlobalPlotFrame(
        schema=GLOBAL_PLOT_FRAME_SCHEMA,
        frame_id=fid,
        direction_sense="Pressure is rising.",
        pacing_note=None,
        cross_character_note=None,
        opportunity_note=None,
        basis_refs=(),
        activity_state="active",
        superseded_by_frame_id=None,
        creation_provenance=CreationProvenance(source="storyteller"),
    )


class PlotCognitionScopeTests(unittest.TestCase):
    def test_explicit_plot_scope_wins(self) -> None:
        memory = new_memory_scope_id()
        plot = new_plot_cognition_scope_id()
        self.assertEqual(resolve_plot_cognition_scope_id(plot, memory), plot)

    def test_blank_defaults_to_memory_scope(self) -> None:
        memory = new_memory_scope_id()
        self.assertEqual(resolve_plot_cognition_scope_id(None, memory), memory)
        self.assertEqual(resolve_plot_cognition_scope_id("", memory), memory)


class PlotCognitionOverlayServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = PlotCognitionOverlayRepository(self._tmpdir)
        self.locks = PlotCognitionScopeLockRegistry()
        self.service = PlotCognitionOverlayService(self.repo, scope_locks=self.locks)
        self.scope = "hg-plot-cognition-scope-service"

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_absent_load(self) -> None:
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.ABSENT)
        self.assertIsNotNone(loaded.store)

    def test_invalid_policy_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BoundednessPolicy(max_active_goals=0, max_active_pressures=1)

    def test_within_budget_replace(self) -> None:
        goal = _goal()
        store = empty_store(self.scope)
        store.goals[goal.goal_id] = goal
        result = self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success)
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.READY)

    def test_goal_overflow_rejected(self) -> None:
        store = empty_store(self.scope)
        for index in range(3):
            goal = _goal(goal_id=f"goal-{index}")
            store.goals[goal.goal_id] = goal
        result = self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "budget_exceeded")

    def test_pressure_overflow_rejected(self) -> None:
        store = empty_store(self.scope)
        for index in range(3):
            pressure = _pressure(pressure_id=f"pressure-{index}")
            store.pressures[pressure.pressure_id] = pressure
        result = self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "budget_exceeded")

    def test_over_budget_store_loads_degraded(self) -> None:
        store = empty_store(self.scope)
        for index in range(3):
            store.goals[f"goal-{index}"] = _goal(goal_id=f"goal-{index}")
        self.repo.save_raw(self.scope, store.to_dict(), expected_revision=0)
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.DEGRADED)
        self.assertIsNone(
            self.service.operative_view(
                loaded.store,  # type: ignore[arg-type]
                policy=TEST_POLICY,
                load_status=loaded.status,
            )
        )

    def test_retired_goal_rejected_in_store(self) -> None:
        store = empty_store(self.scope)
        retired = _goal(state="retired")
        store.goals[retired.goal_id] = retired
        result = self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "integrity_invalid")

    def test_snapshot_removes_goal(self) -> None:
        goal = _goal()
        store = empty_store(self.scope)
        store.goals[goal.goal_id] = goal
        self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        empty = empty_store(self.scope)
        result = self.service.replace_snapshot(
            self.scope,
            empty,
            expected_revision=1,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success)
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        self.assertEqual(len(loaded.store.goals), 0)  # type: ignore[union-attr]

    def test_frame_replace_and_clear(self) -> None:
        frame = _frame()
        store = empty_store(self.scope)
        store.active_frame = frame
        self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        cleared = empty_store(self.scope)
        result = self.service.replace_snapshot(
            self.scope,
            cleared,
            expected_revision=1,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success)
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        self.assertIsNone(loaded.store.active_frame)  # type: ignore[union-attr]

    def test_operative_view_active_inactive_filter(self) -> None:
        active = _goal(goal_id="g-active")
        inactive = _goal(goal_id="g-inactive", state="inactive")
        store = empty_store(self.scope)
        store.goals[active.goal_id] = active
        store.goals[inactive.goal_id] = inactive
        self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        loaded = self.service.load(self.scope, policy=TEST_POLICY)
        view = self.service.operative_view(
            loaded.store,  # type: ignore[arg-type]
            policy=TEST_POLICY,
            load_status=loaded.status,
        )
        assert view is not None
        self.assertEqual(len(view.goals), 1)
        self.assertEqual(view.goals[0].goal_id, "g-active")

    def test_assimilation_equality_only(self) -> None:
        store = empty_store(self.scope)
        store.assimilated_through_domain_commit_id = "hg-commit-aaa"
        self.assertTrue(
            self.service.is_assimilation_current(
                store,
                current_domain_commit_id="hg-commit-aaa",
            )
        )
        self.assertTrue(
            self.service.is_assimilation_stale(
                store,
                current_domain_commit_id="hg-commit-bbb",
            )
        )
        store_null = empty_store(self.scope)
        self.assertTrue(
            self.service.is_assimilation_stale(
                store_null,
                current_domain_commit_id="hg-commit-bbb",
            )
        )

    def test_shared_scope_serializes_writes(self) -> None:
        store = empty_store(self.scope)
        self.service.replace_snapshot(
            self.scope,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        barrier = threading.Barrier(2)
        results: list[bool] = []

        def worker(revision: int, commit: str) -> None:
            barrier.wait(timeout=2)
            loaded = self.service.load(self.scope, policy=TEST_POLICY)
            assert loaded.store is not None
            updated = replace(
                loaded.store,
                assimilated_through_domain_commit_id=commit,
            )
            outcome = self.service.replace_snapshot(
                self.scope,
                updated,
                expected_revision=revision,
                policy=TEST_POLICY,
            )
            results.append(outcome.success)

        t1 = threading.Thread(target=worker, args=(1, "hg-commit-one"))
        t2 = threading.Thread(target=worker, args=(1, "hg-commit-two"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(sum(results), 1)


class PlotCognitionSessionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_session_persists_plot_scope(self) -> None:
        memory = new_memory_scope_id()
        plot = new_plot_cognition_scope_id()
        session = self.repo.create_session(
            cast=["Alice"],
            memory_scope_id=memory,
            plot_cognition_scope_id=plot,
        )
        self.assertEqual(session.plot_cognition_scope_id, plot)
        reopened = self.repo.open_session(session.hg_session_id)
        self.assertEqual(reopened.plot_cognition_scope_id, plot)

    def test_default_plot_scope_matches_memory_scope(self) -> None:
        memory = new_memory_scope_id()
        session = self.repo.create_session(cast=["Alice"], memory_scope_id=memory)
        self.assertEqual(session.plot_cognition_scope_id, memory)

    def test_shared_memory_different_plot_scopes(self) -> None:
        memory = new_memory_scope_id()
        plot_a = new_plot_cognition_scope_id()
        plot_b = new_plot_cognition_scope_id()
        session_a = self.repo.create_session(
            cast=["Alice"],
            memory_scope_id=memory,
            plot_cognition_scope_id=plot_a,
        )
        session_b = self.repo.create_session(
            cast=["Alice"],
            memory_scope_id=memory,
            plot_cognition_scope_id=plot_b,
        )
        self.assertEqual(session_a.memory_scope_id, session_b.memory_scope_id)
        self.assertNotEqual(session_a.plot_cognition_scope_id, session_b.plot_cognition_scope_id)

    def test_composition_wires_overlay_service(self) -> None:
        kernel = DomainKernel.for_repository(self.repo)
        self.assertIsNotNone(kernel.cognition.plot_cognition_overlay)

    def test_legacy_session_backfills_plot_scope_on_persist(self) -> None:
        memory = new_memory_scope_id()
        session = self.repo.create_session(cast=["Alice"], memory_scope_id=memory)
        session_id = session.hg_session_id
        self.repo.clear_cache()
        session_data = self.repo._session_manager.load_session(session_id)
        host_state = session_data["metadata"][V2_HOST_METADATA_KEY]
        host_state.pop("plot_cognition_scope_id", None)
        session_data["metadata"][V2_HOST_METADATA_KEY] = host_state
        self.repo._session_manager.save_session(
            session_id,
            session_data.get("team_state") or {},
            list(session_data.get("characters") or []),
            metadata=session_data.get("metadata"),
            player_character=session_data.get("player_character"),
            chat_history=session_data.get("chat_history") or [],
        )
        reopened = self.repo.open_session(session_id)
        self.assertEqual(reopened.plot_cognition_scope_id, memory)
        self.repo.persist(reopened)
        self.repo.clear_cache()
        final = self.repo.open_session(session_id)
        self.assertEqual(final.plot_cognition_scope_id, memory)


if __name__ == "__main__":
    unittest.main()
