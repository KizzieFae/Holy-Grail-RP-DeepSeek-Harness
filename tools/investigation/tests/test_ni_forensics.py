"""Deterministic tests for Package B NI forensic investigator (#46)."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from investigation._ni_forensics import (  # noqa: E402
    DISPOSITION_INCOMPLETE,
    DISPOSITION_OMITTED,
    DISPOSITION_PROPAGATED,
    INVESTIGATOR_SCHEMA,
    NiSession,
    librarian_omitted_candidate_id,
)
from investigation.trace_ni_forensics import run, parse_args  # noqa: E402

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "ni_forensic_acceptance"
EVIDENCE_ROOT = FIXTURE_ROOT / "execution_evidence"
TAGS_ROOT = FIXTURE_ROOT / "audit_tags"
SESSION_ID = "hg-session-ni-acc-1"
PRE45_SESSION = "hg-session-pre45-1"


@pytest.fixture
def ni_session() -> NiSession:
    return NiSession.open(
        SESSION_ID,
        EVIDENCE_ROOT,
        tags_root=TAGS_ROOT,
    )


def test_librarian_omitted_candidate_id_helper():
    catalog = ["lmi:cand:ni-fact-f", "lmi:cand:ni-fact-g"]
    selected = ["lmi:cand:ni-fact-g"]
    assert librarian_omitted_candidate_id(catalog, selected, "ni-fact-f") == "ni-fact-f"
    assert librarian_omitted_candidate_id(catalog, selected, "ni-fact-g") is None


def test_tag_to_ni_chain(ni_session: NiSession):
    envelope = ni_session.view_tag("tag-ni-acc-1")
    assert envelope["schema"] == INVESTIGATOR_SCHEMA
    payload = envelope["payload"]
    assert payload["forensic_scope"]["resolution_status"] == "complete"
    chains = payload["character_chains"]
    assert chains
    assert chains[0]["entry_points"]["mediation_evidence_id"] == "ev-med-char-1"


def test_round_participating_ni_activity(ni_session: NiSession):
    envelope = ni_session.view_round("round-1")
    kinds = {item["inference_kind"] for item in envelope["payload"]["activities"]}
    assert "librarian_mediation" in kinds
    assert "character_move" in kinds
    assert "storyteller_assessment" in kinds


def test_session_forensic_map(ni_session: NiSession):
    envelope = ni_session.view_session()
    payload = envelope["payload"]
    assert payload["ni_attempt_count"] >= 6
    assert payload["rounds"][0]["hg_round_id"] == "round-1"
    assert payload["commits"][0]["domain_commit_id"] == "commit-ni-1"


def test_lineage_fact_f_omission_discovered(ni_session: NiSession):
    envelope = ni_session.trace_lineage("ni-fact-f")
    assert envelope["payload"]["disposition"] == DISPOSITION_OMITTED
    assert envelope["payload"]["owning_seam"] == "librarian_mediation"


def test_lineage_fact_g_propagation_discovered(ni_session: NiSession):
    envelope = ni_session.trace_lineage("lmi:cand:ni-fact-g")
    assert envelope["payload"]["disposition"] == DISPOSITION_PROPAGATED


def test_storyteller_director_influence(ni_session: NiSession):
    envelope = ni_session.view_storyteller()
    influence = envelope["payload"]["director_influence"][0]
    assert influence["storyteller_assessment_evidence_id"] == "ev-st-assess-1"
    assert "Betrayal" in influence["request_excerpt"]


def test_character_actual_request_evidence(ni_session: NiSession):
    envelope = ni_session.view_character()
    assert "FACT_G_VISIBLE_MARKER" in envelope["payload"]["request_excerpt"]
    assert "semantic adequacy" in envelope["payload"]["semantic_adequacy_note"].lower()


def test_s4_chain(ni_session: NiSession):
    envelope = ni_session.view_s4("commit-ni-1")
    payload = envelope["payload"]
    assert payload["move_evidence_id"] == "ev-move-char-1"
    assert payload["proposal_evidence_id"] == "ev-proposal-1"
    stages = [step["stage"] for step in payload["chain"]]
    assert "host_validation" in stages
    assert "continuity_disposition" in stages


def test_investigator_json_schema_stable(ni_session: NiSession):
    envelope = ni_session.trace_lineage("ni-fact-f")
    assert envelope["schema"] == INVESTIGATOR_SCHEMA
    assert envelope["index_source"] in ("persisted", "rebuilt")
    assert "limitations" in envelope
    assert "payload" in envelope


def test_missing_artifact_handling(ni_session: NiSession):
    index = deepcopy(ni_session.index)
    index["ni"]["by_round"]["round-1"]["inf-character-alice-1"]["character_move"] = "ev-missing"
    ni_session.index = index
    envelope = ni_session.view_round("round-1")
    codes = {lim["code"] for lim in envelope["limitations"]}
    assert "missing_artifact" in codes


def test_incomplete_association_handling(ni_session: NiSession):
    move = ni_session.find_character_move()
    assert move is not None
    move = deepcopy(move)
    move["associations"] = {}
    ni_session._attempt_cache[move["evidence_id"]] = move
    envelope = ni_session.trace_lineage("ni-fact-g")
    assert envelope["payload"]["disposition"] in (
        DISPOSITION_PROPAGATED,
        DISPOSITION_INCOMPLETE,
    )


def test_evidence_disabled_tag():
    tag_path = TAGS_ROOT / SESSION_ID / "tags" / "tag-ni-acc-1.json"
    original = tag_path.read_text(encoding="utf-8")
    try:
        disabled_tag = json.loads(original)
        disabled_tag["forensic_scope"] = {"resolution_status": "evidence_disabled"}
        tag_path.write_text(json.dumps(disabled_tag, indent=2), encoding="utf-8")
        session = NiSession.open(SESSION_ID, EVIDENCE_ROOT, tags_root=TAGS_ROOT)
        envelope = session.view_tag("tag-ni-acc-1")
        assert any(lim["code"] == "evidence_disabled" for lim in envelope["limitations"])
    finally:
        tag_path.write_text(original, encoding="utf-8")


def test_pre45_limitation_reporting():
    session = NiSession.open(PRE45_SESSION, EVIDENCE_ROOT)
    envelope = session.view_session()
    codes = {lim["code"] for lim in envelope["limitations"]}
    assert "ni_contract_unavailable" in codes


def test_in_memory_index_rebuild():
    session = NiSession.open(SESSION_ID, EVIDENCE_ROOT, tags_root=TAGS_ROOT, rebuild_index=True)
    assert session.index_source == "rebuilt"
    envelope = session.view_round("round-1")
    assert envelope["payload"]["activities"]


def test_cli_run_lineage():
    args = parse_args(
        [
            SESSION_ID,
            "lineage",
            "ni-fact-f",
            "--evidence-root",
            str(EVIDENCE_ROOT),
            "--tags-root",
            str(TAGS_ROOT),
        ]
    )
    envelope = run(args)
    assert envelope["payload"]["disposition"] == DISPOSITION_OMITTED


def test_cli_mediation_view():
    args = parse_args(
        [
            SESSION_ID,
            "mediation",
            "--evidence-root",
            str(EVIDENCE_ROOT),
        ]
    )
    envelope = run(args)
    assert "ni-fact-f" in str(envelope["payload"]["omitted_source_ids"])
