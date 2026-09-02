"""Issue #100 — S4 mutation envelope structural enforcement (Layers 1–3)."""

from __future__ import annotations

import ast
import copy
import inspect
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_librarian_issue_pressure import apply_accepted_librarian_proposals  # noqa: E402
from continuity_state import IssueState, IssueStatus, PublicEvent  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    S4B_MUTATING_PROPOSAL_KINDS,
    S4_DURABLE_MUTATION_SURFACES,
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


def snapshot_s4_authoritative_guard(manager) -> dict:
    """Authoritative Continuity surfaces S4 must not mutate."""
    scene_state = manager.scene_state.to_dict() if manager.scene_state is not None else None
    return {
        "turn_counter": manager.turn_counter,
        "issues": {
            issue_id: issue.to_dict() for issue_id, issue in manager.issues.items()
        },
        "scene_state": copy.deepcopy(scene_state),
        "known_by": [list(event.known_by or []) for event in manager.public_events],
        "public_event_core": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "summary": event.summary,
                "significance": event.significance,
                "turn_index": event.turn_index,
            }
            for event in manager.public_events
        ],
        "interpretations": copy.deepcopy(manager.interpretations),
        "excursions": {
            eid: rec.to_dict() for eid, rec in getattr(manager, "excursions", {}).items()
        },
        "resolved_outcomes": [
            outcome.to_dict() for outcome in getattr(manager, "resolved_outcomes", [])
        ],
        "canon_anchors": [anchor.to_dict() for anchor in manager.canon_anchors],
        "summary_blocks": [block.to_dict() for block in manager.summary_blocks],
        "continuity_audit_origin_log": copy.deepcopy(
            getattr(manager, "continuity_audit_origin_log", []) or []
        ),
    }


def snapshot_s4_allowlisted_surfaces(manager) -> dict:
    return {
        "issue_pressure_semantic_overlays": copy.deepcopy(
            getattr(manager, "issue_pressure_semantic_overlays", {}) or {}
        ),
        "revelation_significance_by_character": [
            copy.deepcopy(getattr(event, "revelation_significance_by_character", None))
            for event in manager.public_events
        ],
    }


def assert_only_allowlisted_s4_surfaces_changed(before: dict, after: dict) -> None:
    assert before["authoritative"] == after["authoritative"], (
        "S4 mutated authoritative Continuity state outside the allowlist"
    )
    if before["allowlisted"] == after["allowlisted"]:
        raise AssertionError("expected allowlisted S4 surface change but none observed")


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


def _b2_result(*, commit_id: str, issue_id: str) -> dict:
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
                    "issue_ref": issue_id,
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


def _manager_attribute_writes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            targets = [node.target]
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "manager"
            ):
                attrs.add(target.attr)
    return attrs


def _event_attribute_writes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            targets = [node.target]
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "event"
            ):
                attrs.add(target.attr)
    return attrs


class S4MutationEnvelopeTests(unittest.TestCase):
    def test_contract_surfaces_match_mutating_kind_count(self) -> None:
        self.assertEqual(len(S4_DURABLE_MUTATION_SURFACES), 2)
        self.assertEqual(len(S4B_MUTATING_PROPOSAL_KINDS), 2)

    def test_layer1_mutating_kinds_match_dispatcher(self) -> None:
        self.assertEqual(_dispatcher_mutating_kinds(), set(S4B_MUTATING_PROPOSAL_KINDS))

    def test_layer2_s4b_mutates_only_allowlisted_surfaces(self) -> None:
        fixture, request, event = _session_s4b()
        service = LibrarianProposalService()
        before = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_result(commit_id=request.domain_commit_id, event_id=event.event_id),
        )
        after = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        assert_only_allowlisted_s4_surfaces_changed(before, after)

    def test_layer2_b2_mutates_only_allowlisted_surfaces(self) -> None:
        fixture, request, issue = _session_b2()
        service = LibrarianProposalService()
        before = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_b2_result(
                commit_id=request.domain_commit_id,
                issue_id=issue.issue_id,
            ),
        )
        after = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        assert_only_allowlisted_s4_surfaces_changed(before, after)
        self.assertIn(issue.issue_id, fixture.manager.issue_pressure_semantic_overlays)

    def test_layer2_non_mutating_salience_leaves_state_unchanged(self) -> None:
        fixture, request, _event = _session_s4b()
        service = LibrarianProposalService()
        before = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_salience_result(commit_id=request.domain_commit_id),
        )
        after = {
            "authoritative": snapshot_s4_authoritative_guard(fixture.manager),
            "allowlisted": snapshot_s4_allowlisted_surfaces(fixture.manager),
        }
        self.assertEqual(before, after)

    def test_layer2_at_most_once_via_kernel_skips_second_finalize(self) -> None:
        fixture, request, event = _session_s4b(commit_id="commit-env-once")
        repo = SessionRepository()
        repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
        kernel = DomainKernel.for_repository(repo)
        proposal_result = _s4b_result(
            commit_id=request.domain_commit_id,
            event_id=event.event_id,
        )
        before = snapshot_s4_allowlisted_surfaces(fixture.manager)
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
        )
        after_first = snapshot_s4_allowlisted_surfaces(fixture.manager)
        self.assertNotEqual(before, after_first)
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
        after_second = snapshot_s4_allowlisted_surfaces(fixture.manager)
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
            )
            reloaded = repo.open_session(fixture.hg_scene_id)
            annotations = reloaded.manager.public_events[0].revelation_significance_by_character
            self.assertIsNotNone(annotations)
            assert annotations is not None
            self.assertEqual(annotations["Alice"]["revelation_significance_level"], "major")
            self.assertIsNotNone(find_terminal_audit_for_commit(reloaded, request.domain_commit_id))

    def test_layer3_knowledge_significance_apply_source_policy(self) -> None:
        self.assertEqual(_manager_attribute_writes(_KNOWLEDGE_SIGNIFICANCE_PATH), set())
        self.assertEqual(
            _event_attribute_writes(_KNOWLEDGE_SIGNIFICANCE_PATH),
            {"revelation_significance_by_character"},
        )

    def test_layer3_issue_pressure_apply_source_policy(self) -> None:
        self.assertEqual(
            _manager_attribute_writes(_ISSUE_PRESSURE_PATH),
            {"issue_pressure_semantic_overlays"},
        )
        self.assertEqual(_event_attribute_writes(_ISSUE_PRESSURE_PATH), set())


if __name__ == "__main__":
    unittest.main()
