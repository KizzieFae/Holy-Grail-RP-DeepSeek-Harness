"""Deterministic tests for unified turn forensic navigator (#101)."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from investigation._turn_forensics import (  # noqa: E402
    AUTHORITY_DERIVED,
    AUTHORITY_FORENSIC,
    AUTHORITY_MEDIATED,
    TURN_INVESTIGATOR_SCHEMA,
    TurnForensicsSession,
)
from investigation.trace_turn_forensics import run, parse_args  # noqa: E402

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "turn_forensic_acceptance"
NI_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "ni_forensic_acceptance"
SESSIONS_ROOT = FIXTURE_ROOT / "sessions"
EVIDENCE_ROOT = NI_FIXTURE_ROOT / "execution_evidence"
TURN_EVIDENCE_ROOT = FIXTURE_ROOT / "execution_evidence"
TAGS_ROOT = NI_FIXTURE_ROOT / "audit_tags"
STORY_ROOT = FIXTURE_ROOT / "story_knowledge"
PC_ROOT = FIXTURE_ROOT / "plot_cognition_forensics"


def open_session(
    hg_session_id: str,
    *,
    evidence_root: Path = EVIDENCE_ROOT,
) -> TurnForensicsSession:
    return TurnForensicsSession.open(
        hg_session_id,
        sessions_root=SESSIONS_ROOT,
        evidence_root=evidence_root,
        tags_root=TAGS_ROOT,
        story_knowledge_root=STORY_ROOT,
        plot_cognition_root=PC_ROOT,
    )


def test_commit_reconstruction_success():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    assert envelope["schema"] == TURN_INVESTIGATOR_SCHEMA
    assert envelope["view"] == "commit"
    contracts = {surface["contract"] for surface in envelope["surfaces"]}
    assert "session_rp_history" in contracts
    assert "execution_evidence" in contracts
    assert "librarian_proposal_audit" in contracts
    assert "story_knowledge" in contracts
    assert "plot_cognition_chronicle" in contracts
    assert envelope["resolved"]["domain_commit_ids"] == ["commit-ni-1"]


def test_round_reconstruction_success():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="hg_round_id",
        anchor_value="round-1",
    )
    assert envelope["view"] == "round"
    roles = {
        (surface.get("correlation") or {}).get("role")
        for surface in envelope["surfaces"]
        if surface["contract"] == "execution_evidence"
    }
    assert "director" in roles
    assert "character" in roles or "librarian" in roles


def test_retry_rejection_chain_visible_in_round_view(tmp_path: Path):
    evidence_root = tmp_path / "execution_evidence"
    session_dir = evidence_root / "hg-session-ni-acc-1"
    attempts_dir = session_dir / "attempts"
    attempts_dir.mkdir(parents=True)
    index = json.loads((EVIDENCE_ROOT / "hg-session-ni-acc-1" / "index.json").read_text(encoding="utf-8"))
    for evidence_id in index["attempt_ids"]:
        src = EVIDENCE_ROOT / "hg-session-ni-acc-1" / "attempts" / f"{evidence_id}.json"
        (attempts_dir / f"{evidence_id}.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    retry_attempt = {
        "evidence_id": "ev-narrator-retry-1",
        "correlation": {
            "hg_session_id": "hg-session-ni-acc-1",
            "hg_round_id": "round-1",
            "role": "narrator",
            "inference_id": "inf-narrator-1",
            "attempt_index": 0,
            "prior_attempt_id": None,
        },
        "decision": {
            "outcome": "rejected",
            "terminal_disposition": "retry",
        },
    }
    accept_attempt = {
        "evidence_id": "ev-narrator-accept-1",
        "correlation": {
            "hg_session_id": "hg-session-ni-acc-1",
            "hg_round_id": "round-1",
            "role": "narrator",
            "inference_id": "inf-narrator-1",
            "attempt_index": 1,
            "prior_attempt_id": "ev-narrator-retry-1",
        },
        "decision": {
            "outcome": "accepted",
            "terminal_disposition": "accepted",
        },
    }
    (attempts_dir / "ev-narrator-retry-1.json").write_text(json.dumps(retry_attempt), encoding="utf-8")
    (attempts_dir / "ev-narrator-accept-1.json").write_text(json.dumps(accept_attempt), encoding="utf-8")
    index["attempt_ids"].extend(["ev-narrator-retry-1", "ev-narrator-accept-1"])
    index["rounds"]["round-1"].extend(["ev-narrator-retry-1", "ev-narrator-accept-1"])
    (session_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    envelope = open_session("hg-session-ni-acc-1", evidence_root=evidence_root).investigate(
        anchor_type="hg_round_id",
        anchor_value="round-1",
    )
    narrator = [
        surface
        for surface in envelope["surfaces"]
        if surface["contract"] == "execution_evidence"
        and (surface.get("correlation") or {}).get("role") == "narrator"
    ]
    assert len(narrator) >= 2
    dispositions = {(item["summary"] or {}).get("terminal_disposition") for item in narrator}
    assert "retry" in dispositions or "accepted" in dispositions


def test_s4_librarian_correlation():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    mediated = [surface for surface in envelope["surfaces"] if surface["authority"] == AUTHORITY_MEDIATED]
    assert mediated
    assert mediated[0]["contract"] == "librarian_proposal_audit"


def test_story_knowledge_correlation():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    derived = [surface for surface in envelope["surfaces"] if surface["authority"] == AUTHORITY_DERIVED]
    assert derived
    assert derived[0]["correlation"]["source_domain_commit_id"] == "commit-ni-1"


def test_plot_cognition_correlation():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    pc = [surface for surface in envelope["surfaces"] if surface["contract"] == "plot_cognition_chronicle"]
    assert pc
    assert pc[0]["correlation"]["record_id"] == "rec-pc-1"


def test_missing_execution_evidence():
    envelope = open_session("hg-session-no-evidence", evidence_root=FIXTURE_ROOT / "missing_evidence").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-no-ev-1",
    )
    codes = {item["code"] for item in envelope["limitations"]}
    assert "evidence_missing" in codes
    assert any(surface["contract"] == "session_rp_history" for surface in envelope["surfaces"])


def test_historical_unavailable_contract(tmp_path: Path):
    evidence_root = tmp_path / "execution_evidence"
    session_dir = evidence_root / "hg-session-pre45-1"
    attempts_dir = session_dir / "attempts"
    attempts_dir.mkdir(parents=True)
    src_attempt = NI_FIXTURE_ROOT / "execution_evidence" / "hg-session-pre45-1" / "attempts" / "legacy-director-1.json"
    (attempts_dir / "legacy-director-1.json").write_text(src_attempt.read_text(encoding="utf-8"), encoding="utf-8")
    index = {
        "schema": "hg_execution_evidence_index_v1",
        "hg_session_id": "hg-session-pre45-1",
        "attempt_ids": ["legacy-director-1"],
        "rounds": {"round-legacy": ["legacy-director-1"]},
        "ni": {},
    }
    (session_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    envelope = open_session("hg-session-pre45-1", evidence_root=evidence_root).investigate(
        anchor_type="hg_round_id",
        anchor_value="round-legacy",
    )
    codes = {item["code"] for item in envelope["limitations"]}
    assert "contract_unavailable" in codes


def test_unresolved_scope():
    envelope = open_session("hg-session-no-scope", evidence_root=TURN_EVIDENCE_ROOT).investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-no-scope-1",
    )
    codes = {item["code"] for item in envelope["limitations"]}
    assert "scope_unresolved" in codes


def test_conflicting_surfaces(tmp_path: Path):
    evidence_root = tmp_path / "execution_evidence"
    session_dir = evidence_root / "hg-session-ni-acc-1"
    attempts_dir = session_dir / "attempts"
    attempts_dir.mkdir(parents=True)
    index = json.loads((EVIDENCE_ROOT / "hg-session-ni-acc-1" / "index.json").read_text(encoding="utf-8"))
    for evidence_id in index["attempt_ids"]:
        src = EVIDENCE_ROOT / "hg-session-ni-acc-1" / "attempts" / f"{evidence_id}.json"
        (attempts_dir / f"{evidence_id}.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    narrator = {
        "evidence_id": "ev-narrator-conflict-1",
        "correlation": {
            "hg_session_id": "hg-session-ni-acc-1",
            "hg_round_id": "round-1",
            "role": "narrator",
            "domain_commit_id": "commit-ni-1",
        },
        "decision": {
            "candidate_presentation_text": "Different forensic narrator candidate text.",
        },
    }
    (attempts_dir / "ev-narrator-conflict-1.json").write_text(json.dumps(narrator), encoding="utf-8")
    index["attempt_ids"].append("ev-narrator-conflict-1")
    index["rounds"]["round-1"].append("ev-narrator-conflict-1")
    (session_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    envelope = open_session("hg-session-ni-acc-1", evidence_root=evidence_root).investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    assert envelope["conflicts"]
    assert envelope["conflicts"][0]["field"] == "presentation_text"


def test_entry_anchor_without_commit():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="entry_id",
        anchor_value="entry-user-1",
    )
    assert envelope["view"] == "round"
    codes = {item["code"] for item in envelope["limitations"]}
    assert "correlation_incomplete" in codes


def test_multi_commit_round():
    envelope = open_session("hg-session-multi-1", evidence_root=TURN_EVIDENCE_ROOT).investigate(
        anchor_type="hg_round_id",
        anchor_value="round-multi",
    )
    assert envelope["resolved"]["domain_commit_ids"] == ["commit-multi-1", "commit-multi-2"]
    director = [
        surface
        for surface in envelope["surfaces"]
        if surface["contract"] == "execution_evidence"
        and (surface.get("correlation") or {}).get("role") == "director"
    ]
    assert director
    assert director[0]["correlation"]["domain_commit_id"] is None


def test_turn_anchor_resolves_to_commit():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="continuity_turn_index",
        anchor_value="1",
    )
    assert envelope["view"] == "commit"
    assert envelope["resolved"]["domain_commit_ids"] == ["commit-ni-1"]


def test_tag_anchor():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="tag_id",
        anchor_value="tag-ni-acc-1",
    )
    assert envelope["view"] == "commit"
    assert "tag-ni-acc-1" in envelope["resolved"]["entry_ids"] or any(
        surface["contract"] == "audit_tags" for surface in envelope["surfaces"]
    )


def test_authority_labels_present():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    authorities = {surface["authority"] for surface in envelope["surfaces"]}
    assert AUTHORITY_MEDIATED in authorities
    assert AUTHORITY_FORENSIC in authorities


def test_deterministic_ordering():
    first = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    second = deepcopy(first)
    assert [surface["reference"] for surface in first["surfaces"]] == [
        surface["reference"] for surface in second["surfaces"]
    ]
    assert [item["code"] for item in first["limitations"]] == [item["code"] for item in second["limitations"]]


def test_stable_json_envelope_cli():
    args = parse_args(
        ["hg-session-ni-acc-1", "commit", "commit-ni-1", "--json", "--sessions-root", str(SESSIONS_ROOT)]
    )
    args.evidence_root = EVIDENCE_ROOT
    args.tags_root = TAGS_ROOT
    args.story_knowledge_root = STORY_ROOT
    args.plot_cognition_root = PC_ROOT
    envelope = run(args)
    dumped = json.dumps(envelope, sort_keys=True)
    assert TURN_INVESTIGATOR_SCHEMA in dumped


def test_specialist_handoffs_generated():
    envelope = open_session("hg-session-ni-acc-1").investigate(
        anchor_type="domain_commit_id",
        anchor_value="commit-ni-1",
    )
    tools = {item["tool"] for item in envelope["handoffs"]}
    assert "trace_ni_forensics.py" in tools
    assert "list_execution_evidence.py" in tools
    assert "trace_plot_cognition_forensics.py" in tools


def test_read_only_no_durable_output(tmp_path: Path):
    session = open_session("hg-session-ni-acc-1")
    before = list(PC_ROOT.glob("**/*"))
    session.investigate(anchor_type="domain_commit_id", anchor_value="commit-ni-1")
    after = list(PC_ROOT.glob("**/*"))
    assert before == after
