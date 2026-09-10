"""Issue #100 — S4 mutation envelope structural enforcement (Layers 1–3)."""

from __future__ import annotations

import ast
import copy
import inspect
import sys
import tempfile
import textwrap
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_librarian_issue_pressure import apply_accepted_librarian_proposals  # noqa: E402
from continuity_scene_helpers import serialize_manager_state  # noqa: E402
from continuity_state import IssueState, IssueStatus, PublicEvent  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    S4A_ACTIVE_PROPOSAL_KINDS,
    S4B_LEGACY_MUTATING_PROPOSAL_KINDS,
    S4B_MUTATING_PROPOSAL_KINDS,
    S4_DURABLE_MUTATION_SURFACES,
    S4_DURABLE_MUTATION_SURFACES_BY_KIND,
)
from domain_api.librarian_proposal_service import (  # noqa: E402
    LibrarianProposalService,
    build_post_commit_proposal_request,
    find_terminal_audit_for_commit,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402

_DOMAIN_MODULES = _V2 / "domain" / "modules"
_KNOWLEDGE_SIGNIFICANCE_PATH = _DOMAIN_MODULES / "continuity_librarian_knowledge_significance.py"
_ISSUE_PRESSURE_PATH = _DOMAIN_MODULES / "continuity_librarian_issue_pressure.py"

_SURFACE_MANAGER_OVERLAYS = "manager.issue_pressure_semantic_overlays"
_SURFACE_EVENT_REVELATION = "public_event.revelation_significance_by_character"


def _minimal_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "dialogue", "dialogue": "We need the key."}],
        "motivation": {
            "goal": "advance",
            "tactic": "ask",
            "emotional_driver": "urgency",
            "risk_level": "low",
        },
    }


def canonical_manager_state(manager) -> dict[str, Any]:
    """Full durable Continuity serialization via ContinuityManager.to_dict()."""
    return copy.deepcopy(manager.to_dict())


def extract_s4_surface_values(canonical: dict[str, Any]) -> dict[str, Any]:
    return {
        _SURFACE_MANAGER_OVERLAYS: copy.deepcopy(
            canonical.get("issue_pressure_semantic_overlays", {})
        ),
        _SURFACE_EVENT_REVELATION: [
            copy.deepcopy(event.get("revelation_significance_by_character"))
            for event in canonical.get("public_events", []) or []
            if isinstance(event, dict)
        ],
    }


def normalize_s4_allowlisted_surfaces(
    canonical: dict[str, Any],
    *,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Replace allowlisted S4 surfaces in `canonical` with values from `baseline`."""
    normalized = copy.deepcopy(canonical)
    normalized["issue_pressure_semantic_overlays"] = copy.deepcopy(
        baseline.get("issue_pressure_semantic_overlays", {})
    )
    baseline_events = baseline.get("public_events", []) or []
    after_events = normalized.get("public_events", []) or []
    for idx, after_event in enumerate(after_events):
        if not isinstance(after_event, dict):
            continue
        baseline_event = baseline_events[idx] if idx < len(baseline_events) else {}
        if isinstance(baseline_event, dict):
            after_event["revelation_significance_by_character"] = copy.deepcopy(
                baseline_event.get("revelation_significance_by_character")
            )
    return normalized


def changed_s4_surfaces(*, before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    before_values = extract_s4_surface_values(before)
    after_values = extract_s4_surface_values(after)
    return {
        surface
        for surface in S4_DURABLE_MUTATION_SURFACES
        if before_values.get(surface) != after_values.get(surface)
    }


def assert_s4_mutating_envelope(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    expected_surfaces: frozenset[str],
) -> None:
    normalized_after = normalize_s4_allowlisted_surfaces(after, baseline=before)
    if normalized_after != before:
        raise AssertionError(
            "S4 mutated durable Continuity state outside the allowlist "
            f"(canonical manager.to_dict() diff after normalizing allowlisted surfaces)"
        )
    changed = changed_s4_surfaces(before=before, after=after)
    if changed != set(expected_surfaces):
        raise AssertionError(
            f"expected S4 surface change {set(expected_surfaces)!r}, got {changed!r}"
        )
    if not changed:
        raise AssertionError("expected allowlisted S4 surface change but none observed")


@dataclass(frozen=True)
class S4SurfaceWrite:
    root: str
    attr: str
    form: str


class S4ApplyModuleWriteAnalyzer:
    """Scoped one-hop alias-aware write detection for S4 apply modules."""

    _HELPER_RETURNS: dict[str, tuple[str, str]] = {
        "_overlay_store": ("manager", "issue_pressure_semantic_overlays"),
    }
    _MUTATING_METHODS = frozenset(
        {"update", "setdefault", "pop", "popitem", "clear", "append", "extend"}
    )

    def __init__(
        self,
        *,
        allowed_manager_attrs: frozenset[str],
        allowed_event_attrs: frozenset[str],
    ) -> None:
        self._allowed_manager_attrs = allowed_manager_attrs
        self._allowed_event_attrs = allowed_event_attrs
        self._aliases: dict[str, tuple[str, str]] = {}
        self.writes: list[S4SurfaceWrite] = []

    def analyze_module(self, path: Path) -> list[S4SurfaceWrite]:
        self._aliases = {}
        self.writes = []
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self._visit_function(node)
        return list(self.writes)

    def analyze_source(self, source: str) -> list[S4SurfaceWrite]:
        self._aliases = {}
        self.writes = []
        tree = ast.parse(textwrap.dedent(source))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self._visit_function(node)
        return list(self.writes)

    def _visit_function(self, node: ast.FunctionDef) -> None:
        function_aliases: dict[str, tuple[str, str]] = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                self._record_assign(child, function_aliases)
            elif isinstance(child, ast.AnnAssign) and child.target is not None:
                self._record_single_target(child.target, child.value, function_aliases)
            elif isinstance(child, ast.AugAssign):
                self._record_write_target(child.target, "augassign", function_aliases)
            elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                self._record_mutating_call(child, function_aliases)

    def _record_assign(self, node: ast.Assign, aliases: dict[str, tuple[str, str]]) -> None:
        for target in node.targets:
            self._record_single_target(target, node.value, aliases)

    def _record_single_target(
        self,
        target: ast.expr,
        value: ast.expr | None,
        aliases: dict[str, tuple[str, str]],
    ) -> None:
        binding = self._resolve_surface(value, aliases) if value is not None else None
        if isinstance(target, ast.Name) and binding is not None:
            aliases[target.id] = binding
            return
        self._record_write_target(target, "assign", aliases)

    def _record_write_target(
        self,
        target: ast.expr,
        form: str,
        aliases: dict[str, tuple[str, str]],
    ) -> None:
        surface = self._surface_from_target(target, aliases)
        if surface is not None:
            self.writes.append(S4SurfaceWrite(surface[0], surface[1], form))

    def _record_mutating_call(
        self,
        node: ast.Call,
        aliases: dict[str, tuple[str, str]],
    ) -> None:
        if not isinstance(node.func, ast.Attribute):
            return
        if node.func.attr not in self._MUTATING_METHODS:
            return
        surface = self._surface_from_expr(node.func.value, aliases)
        if surface is not None:
            self.writes.append(S4SurfaceWrite(surface[0], surface[1], f"call:{node.func.attr}"))

    def _surface_from_target(
        self,
        target: ast.expr,
        aliases: dict[str, tuple[str, str]],
    ) -> tuple[str, str] | None:
        if isinstance(target, ast.Attribute):
            return self._surface_from_expr(target, aliases)
        if isinstance(target, ast.Subscript):
            return self._surface_from_expr(target.value, aliases)
        return None

    def _surface_from_expr(
        self,
        expr: ast.expr,
        aliases: dict[str, tuple[str, str]],
    ) -> tuple[str, str] | None:
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
            if expr.value.id == "manager":
                return ("manager", expr.attr)
            if expr.value.id == "event":
                return ("event", expr.attr)
        if isinstance(expr, ast.Name):
            return aliases.get(expr.id)
        return None

    def _resolve_surface(
        self,
        expr: ast.expr,
        aliases: dict[str, tuple[str, str]],
    ) -> tuple[str, str] | None:
        direct = self._surface_from_expr(expr, aliases)
        if direct is not None:
            return direct
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
            return self._HELPER_RETURNS.get(expr.func.id)
        return None

    def classify_writes(self, writes: list[S4SurfaceWrite]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
        allowed: set[tuple[str, str]] = set()
        forbidden: set[tuple[str, str]] = set()
        for write in writes:
            if write.root == "manager":
                bucket = allowed if write.attr in self._allowed_manager_attrs else forbidden
            elif write.root == "event":
                bucket = allowed if write.attr in self._allowed_event_attrs else forbidden
            else:
                forbidden.add((write.root, write.attr))
                continue
            bucket.add((write.root, write.attr))
        return allowed, forbidden


def _analyze_apply_module(
    path: Path,
    *,
    allowed_manager_attrs: frozenset[str],
    allowed_event_attrs: frozenset[str],
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    analyzer = S4ApplyModuleWriteAnalyzer(
        allowed_manager_attrs=allowed_manager_attrs,
        allowed_event_attrs=allowed_event_attrs,
    )
    writes = analyzer.analyze_module(path)
    return analyzer.classify_writes(writes)


def _session_s4b(*, commit_id: str = "commit-env-s4b") -> tuple:
    fixture = initialize_live_session(cast=["Alice", "Bob"], hg_session_id="session-env-s4b")
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="reveals",
        hg_round_id="round-env-1",
        domain_commit_id=commit_id,
        actor_id="Alice",
        metadata={"continuity_turn_index": 1, "structured_move": _minimal_move()},
    )
    event = PublicEvent(
        event_id="evt-env-1",
        timestamp=datetime.now(timezone.utc),
        event_type="revelation",
        participants=["Alice"],
        summary="Alice reveals the vault location.",
        turn_index=1,
        significance="minor",
        observed_by=["Alice"],
        known_by=["Alice", "Bob"],
    )
    fixture.manager.public_events.append(event)
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-env-s4b",
        hg_round_id="round-env-1",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-env-s4b",
    )
    return fixture, request, event


def _session_b2(*, commit_id: str = "commit-env-b2") -> tuple:
    fixture = initialize_live_session(cast=["Alice", "Bob"], hg_session_id="session-env-b2")
    issue = IssueState(
        issue_id="issue-env-1",
        description="Vault blocked.",
        participants=["Alice", "Bob"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="access_conflict",
        blocked_what="Vault access",
        required_next_step="Find the key.",
        last_change="Alice refused.",
    )
    fixture.manager.issues[issue.issue_id] = issue
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.active_issue_ids = [issue.issue_id]
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="blocked",
        hg_round_id="round-env-b2",
        domain_commit_id=commit_id,
        actor_id="Alice",
        metadata={"continuity_turn_index": 1, "structured_move": _minimal_move()},
    )
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-env-b2",
        hg_round_id="round-env-b2",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-env-b2",
    )
    return fixture, request, issue


def _s4b_result(*, commit_id: str, event_id: str) -> dict:
    return {
        "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
        "proposals": [
            {
                "proposal_id": "prop-env-s4b",
                "proposal_kind": "knowledge_revelation_significance",
                "derivation_summary": "Major revelation significance.",
                "confidence": "likely",
                "evidence_anchors": [
                    {
                        "anchor_id": f"committed_move:{commit_id}",
                        "evidence_kind": "committed_move",
                        "anchor_commit_id": commit_id,
                    },
                    {
                        "anchor_id": f"public_event:{event_id}",
                        "evidence_kind": "public_event",
                        "anchor_commit_id": commit_id,
                    },
                ],
                "proposed_payload": {
                    "event_ref": event_id,
                    "subject_character": "Alice",
                    "revelation_significance_level": "major",
                    "interpretation_scope": "utterance_occurrence",
                },
            }
        ],
    }


def _b2_result(*, commit_id: str, issue_id: str, issue_ref: str | None = None) -> dict:
    resolved_issue_ref = issue_ref if issue_ref is not None else issue_id
    return {
        "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
        "proposals": [
            {
                "proposal_id": "prop-env-b2",
                "proposal_kind": "issue_tension_pressure",
                "derivation_summary": "Semantic pressure on vault access.",
                "confidence": "likely",
                "evidence_anchors": [
                    {
                        "anchor_id": f"committed_move:{commit_id}",
                        "evidence_kind": "committed_move",
                        "anchor_commit_id": commit_id,
                    },
                    {
                        "anchor_id": f"continuity_issue:{issue_id}",
                        "evidence_kind": "continuity_issue",
                        "anchor_commit_id": commit_id,
                    },
                ],
                "proposed_payload": {
                    "issue_ref": resolved_issue_ref,
                    "semantic_unmet_condition": "The vault remains sealed.",
                },
            }
        ],
    }


def _salience_result(*, commit_id: str) -> dict:
    return {
        "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
        "proposals": [
            {
                "proposal_id": "prop-env-salience",
                "proposal_kind": "information_salience",
                "derivation_summary": "Salience only.",
                "confidence": "likely",
                "evidence_anchors": [
                    {
                        "anchor_id": f"committed_move:{commit_id}",
                        "evidence_kind": "committed_move",
                        "anchor_commit_id": commit_id,
                    }
                ],
                "proposed_payload": {
                    "subject_ref": f"commit:{commit_id}",
                    "salience_level": "minor",
                },
            }
        ],
    }


def _dispatcher_mutating_kinds() -> set[str]:
    source = inspect.getsource(apply_accepted_librarian_proposals)
    tree = ast.parse(source)
    kinds: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.Name)
            and test.left.id == "kind"
            and test.comparators
            and isinstance(test.comparators[0], ast.Constant)
            and isinstance(test.comparators[0].value, str)
        ):
            continue
        kinds.add(test.comparators[0].value)
    return kinds


class S4MutationEnvelopeTests(unittest.TestCase):
    def test_layer2_canonical_serialization_matches_serialize_manager_state(self) -> None:
        fixture, _, _ = _session_s4b()
        self.assertEqual(
            set(fixture.manager.to_dict().keys()),
            set(serialize_manager_state(manager=fixture.manager).keys()),
        )

    def test_contract_mapping_keys_match_mutating_kinds(self) -> None:
        self.assertEqual(
            frozenset(S4_DURABLE_MUTATION_SURFACES_BY_KIND.keys()),
            S4B_LEGACY_MUTATING_PROPOSAL_KINDS,
        )

    def test_contract_mapping_excludes_non_mutating_kinds(self) -> None:
        non_mutating = set(S4A_ACTIVE_PROPOSAL_KINDS) - set(S4B_MUTATING_PROPOSAL_KINDS)
        self.assertEqual(non_mutating, set())
        for kind in non_mutating:
            self.assertNotIn(kind, S4_DURABLE_MUTATION_SURFACES_BY_KIND)

    def test_contract_flat_allowlist_equals_mapping_union(self) -> None:
        union = frozenset(
            surface
            for surfaces in S4_DURABLE_MUTATION_SURFACES_BY_KIND.values()
            for surface in surfaces
        )
        self.assertEqual(S4_DURABLE_MUTATION_SURFACES, union)
        self.assertEqual(
            S4_DURABLE_MUTATION_SURFACES_BY_KIND["knowledge_revelation_significance"],
            frozenset({_SURFACE_EVENT_REVELATION}),
        )
        self.assertEqual(
            S4_DURABLE_MUTATION_SURFACES_BY_KIND["issue_tension_pressure"],
            frozenset({_SURFACE_MANAGER_OVERLAYS}),
        )

    def test_layer1_mutating_kinds_match_dispatcher(self) -> None:
        self.assertEqual(_dispatcher_mutating_kinds(), set(S4B_LEGACY_MUTATING_PROPOSAL_KINDS))

    def test_layer2_s4b_mutates_only_mapped_surface(self) -> None:
        fixture, request, event = _session_s4b()
        service = LibrarianProposalService()
        before = canonical_manager_state(fixture.manager)
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_result(commit_id=request.domain_commit_id, event_id=event.event_id),
            allow_legacy_kinds=True,
        )
        after = canonical_manager_state(fixture.manager)
        assert_s4_mutating_envelope(
            before=before,
            after=after,
            expected_surfaces=S4_DURABLE_MUTATION_SURFACES_BY_KIND[
                "knowledge_revelation_significance"
            ],
        )

    def test_layer2_b2_mutates_only_mapped_surface(self) -> None:
        fixture, request, issue = _session_b2()
        service = LibrarianProposalService()
        before = canonical_manager_state(fixture.manager)
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_b2_result(
                commit_id=request.domain_commit_id,
                issue_id=issue.issue_id,
            ),
        )
        after = canonical_manager_state(fixture.manager)
        assert_s4_mutating_envelope(
            before=before,
            after=after,
            expected_surfaces=S4_DURABLE_MUTATION_SURFACES_BY_KIND["issue_tension_pressure"],
        )
        self.assertIn(issue.issue_id, fixture.manager.issue_pressure_semantic_overlays)

    def test_layer2_b2_finalize_with_stable_ref_issue_ref(self) -> None:
        fixture, request, issue = _session_b2()
        service = LibrarianProposalService()
        stable_ref = f"issue:{issue.issue_id}"
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_b2_result(
                commit_id=request.domain_commit_id,
                issue_id=issue.issue_id,
                issue_ref=stable_ref,
            ),
        )
        self.assertIsNotNone(result.continuity_decision)
        self.assertEqual(result.continuity_decision.accepted_count, 1)
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        self.assertEqual(overlay["accepted_payload"]["issue_ref"], stable_ref)

    def test_layer2_non_mutating_salience_leaves_canonical_state_unchanged(self) -> None:
        fixture, request, _event = _session_s4b()
        service = LibrarianProposalService()
        before = canonical_manager_state(fixture.manager)
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_salience_result(commit_id=request.domain_commit_id),
            allow_legacy_kinds=True,
        )
        after = canonical_manager_state(fixture.manager)
        self.assertEqual(before, after)

    def test_layer2_canonical_guard_detects_unlisted_serialization_delta(self) -> None:
        fixture, _, _ = _session_s4b()
        before = canonical_manager_state(fixture.manager)
        after = copy.deepcopy(before)
        after["event_counter"] = int(after.get("event_counter", 0)) + 1
        with self.assertRaises(AssertionError):
            assert_s4_mutating_envelope(
                before=before,
                after=after,
                expected_surfaces=S4_DURABLE_MUTATION_SURFACES_BY_KIND[
                    "knowledge_revelation_significance"
                ],
            )

    def test_layer2_at_most_once_via_kernel_skips_second_finalize(self) -> None:
        fixture, request, event = _session_s4b(commit_id="commit-env-once")
        repo = SessionRepository()
        repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
        kernel = DomainKernel.for_repository(repo)
        proposal_result = _s4b_result(
            commit_id=request.domain_commit_id,
            event_id=event.event_id,
        )
        before = canonical_manager_state(fixture.manager)
        first = kernel.finalize_librarian_proposals(
            hg_scene_id=fixture.hg_scene_id,
            inference_id=request.librarian_inference_id,
            proposal_context_request={
                "request_id": request.request_id,
                "hg_round_id": request.hg_round_id,
                "turn_index": request.turn_index,
                "domain_commit_id": request.domain_commit_id,
            },
            proposal_result=proposal_result,
            allow_legacy_kinds=True,
        )
        after_first = canonical_manager_state(fixture.manager)
        assert_s4_mutating_envelope(
            before=before,
            after=after_first,
            expected_surfaces=S4_DURABLE_MUTATION_SURFACES_BY_KIND[
                "knowledge_revelation_significance"
            ],
        )
        second = kernel.finalize_librarian_proposals(
            hg_scene_id=fixture.hg_scene_id,
            inference_id="inf-librarian-env-once-retry",
            proposal_context_request={
                "request_id": "lpr-retry",
                "hg_round_id": request.hg_round_id,
                "turn_index": request.turn_index,
                "domain_commit_id": request.domain_commit_id,
            },
            proposal_result=proposal_result,
        )
        self.assertTrue(second.get("skipped"))
        self.assertEqual(second.get("orchestration_status"), "already_terminal")
        after_second = canonical_manager_state(fixture.manager)
        self.assertEqual(after_first, after_second)
        self.assertIsNotNone(first.get("batch_id"))

    def test_layer2_persist_and_rehydrate_preserves_allowlisted_state(self) -> None:
        fixture, request, event = _session_s4b(commit_id="commit-env-persist")
        with tempfile.TemporaryDirectory() as tmp:
            repo = SessionRepository(tmp)
            repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
            kernel = DomainKernel.for_repository(repo)
            kernel.finalize_librarian_proposals(
                hg_scene_id=fixture.hg_scene_id,
                inference_id=request.librarian_inference_id,
                proposal_context_request={
                    "request_id": request.request_id,
                    "hg_round_id": request.hg_round_id,
                    "turn_index": request.turn_index,
                    "domain_commit_id": request.domain_commit_id,
                },
                proposal_result=_s4b_result(
                    commit_id=request.domain_commit_id,
                    event_id=event.event_id,
                ),
                allow_legacy_kinds=True,
            )
            reloaded = repo.open_session(fixture.hg_scene_id)
            annotations = reloaded.manager.public_events[0].revelation_significance_by_character
            self.assertIsNotNone(annotations)
            assert annotations is not None
            self.assertEqual(annotations["Alice"]["revelation_significance_level"], "major")
            self.assertIsNotNone(find_terminal_audit_for_commit(reloaded, request.domain_commit_id))

    def test_layer3_knowledge_significance_apply_source_policy(self) -> None:
        allowed, forbidden = _analyze_apply_module(
            _KNOWLEDGE_SIGNIFICANCE_PATH,
            allowed_manager_attrs=frozenset(),
            allowed_event_attrs=frozenset({"revelation_significance_by_character"}),
        )
        self.assertEqual(allowed, {("event", "revelation_significance_by_character")})
        self.assertEqual(forbidden, set())

    def test_layer3_issue_pressure_apply_source_policy(self) -> None:
        allowed, forbidden = _analyze_apply_module(
            _ISSUE_PRESSURE_PATH,
            allowed_manager_attrs=frozenset({"issue_pressure_semantic_overlays"}),
            allowed_event_attrs=frozenset(),
        )
        self.assertEqual(allowed, {("manager", "issue_pressure_semantic_overlays")})
        self.assertEqual(forbidden, set())

    def test_layer3_analyzer_rejects_forbidden_direct_assignment(self) -> None:
        analyzer = S4ApplyModuleWriteAnalyzer(
            allowed_manager_attrs=frozenset({"issue_pressure_semantic_overlays"}),
            allowed_event_attrs=frozenset(),
        )
        writes = analyzer.analyze_source(
            """
            def apply_bad(manager):
                manager.turn_counter = 1
            """
        )
        _, forbidden = analyzer.classify_writes(writes)
        self.assertIn(("manager", "turn_counter"), forbidden)

    def test_layer3_analyzer_rejects_forbidden_subscript_via_alias(self) -> None:
        analyzer = S4ApplyModuleWriteAnalyzer(
            allowed_manager_attrs=frozenset({"issue_pressure_semantic_overlays"}),
            allowed_event_attrs=frozenset(),
        )
        writes = analyzer.analyze_source(
            """
            def apply_bad(manager):
                store = manager.issues
                store["issue-1"] = object()
            """
        )
        _, forbidden = analyzer.classify_writes(writes)
        self.assertIn(("manager", "issues"), forbidden)

    def test_layer3_analyzer_rejects_forbidden_mutating_method_via_alias(self) -> None:
        analyzer = S4ApplyModuleWriteAnalyzer(
            allowed_manager_attrs=frozenset({"issue_pressure_semantic_overlays"}),
            allowed_event_attrs=frozenset(),
        )
        writes = analyzer.analyze_source(
            """
            def apply_bad(manager):
                store = manager.issues
                store.update({"issue-1": object()})
            """
        )
        _, forbidden = analyzer.classify_writes(writes)
        self.assertIn(("manager", "issues"), forbidden)

    def test_layer3_analyzer_allows_issue_pressure_alias_subscript(self) -> None:
        analyzer = S4ApplyModuleWriteAnalyzer(
            allowed_manager_attrs=frozenset({"issue_pressure_semantic_overlays"}),
            allowed_event_attrs=frozenset(),
        )
        writes = analyzer.analyze_source(
            """
            def _overlay_store(manager):
                return manager.issue_pressure_semantic_overlays

            def apply_ok(manager):
                store = _overlay_store(manager)
                store["issue-1"] = {"semantic_unmet_condition": "blocked"}
            """
        )
        allowed, forbidden = analyzer.classify_writes(writes)
        self.assertIn(("manager", "issue_pressure_semantic_overlays"), allowed)
        self.assertEqual(forbidden, set())

    def test_layer3_analyzer_allows_revelation_significance_write(self) -> None:
        analyzer = S4ApplyModuleWriteAnalyzer(
            allowed_manager_attrs=frozenset(),
            allowed_event_attrs=frozenset({"revelation_significance_by_character"}),
        )
        writes = analyzer.analyze_source(
            """
            def apply_ok(manager, event):
                event.revelation_significance_by_character = {"Alice": {"level": "major"}}
            """
        )
        allowed, forbidden = analyzer.classify_writes(writes)
        self.assertIn(("event", "revelation_significance_by_character"), allowed)
        self.assertEqual(forbidden, set())


if __name__ == "__main__":
    unittest.main()
