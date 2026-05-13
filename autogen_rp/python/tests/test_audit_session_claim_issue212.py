"""Issue #212 — exclusive audit session claim and identity validation."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_logger import AuditLogger  # noqa: E402
from audit_logger_paths import claim_next_audit_session_number  # noqa: E402
from audit_session_identity import AuditSessionIntegrityError  # noqa: E402


def _minimal_move() -> dict:
    return {
        "action": "acts",
        "dialogue": "hi",
        "motivation": {"goal": "g", "tactic": "t"},
    }


def _minimal_decision() -> dict:
    return {"reason": "r", "environment_event": "", "tension_shift": ""}


def test_t1_new_audited_session_manifest_then_turn(tmp_path: Path) -> None:
    """T1: Normal new session — claim, manifest, narrative."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    assert sn == 1
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    logger.update_narrative_summary(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        rendered_output="First beat.",
        character_move=_minimal_move(),
        director_decision=_minimal_decision(),
    )
    sp = base / f"session_{sn:03d}"
    nar = json.loads((sp / "_narrative.json").read_text(encoding="utf-8"))
    assert nar["session_owner"] == "scenario_a"
    assert nar["session_number"] == sn
    assert "First beat." in nar["complete_narrative"]


def test_t2_legitimate_second_turn_append(tmp_path: Path) -> None:
    """T2: Same session second narrative append."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    logger.update_narrative_summary(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        rendered_output="One.",
        character_move=_minimal_move(),
        director_decision=_minimal_decision(),
    )
    logger.update_narrative_summary(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=2,
        acting_character="A",
        rendered_output="Two.",
        character_move=_minimal_move(),
        director_decision=_minimal_decision(),
    )
    nar = json.loads(
        (base / f"session_{sn:03d}" / "_narrative.json").read_text(encoding="utf-8")
    )
    assert nar["complete_narrative"].count("Two.") == 1
    assert "One." in nar["complete_narrative"]


def test_t3_narrative_owner_mismatch_fails_before_append(tmp_path: Path) -> None:
    """T3: Pre-seeded narrative wrong owner → append fails loudly."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    sp = base / f"session_{sn:03d}"
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    nar_bad = {
        "session_owner": "scenario_b",
        "session_number": sn,
        "complete_narrative": "stale",
        "turns": [],
        "character_stats": {},
        "scene_template": {},
    }
    (sp / "_narrative.json").write_text(json.dumps(nar_bad), encoding="utf-8")
    with pytest.raises(AuditSessionIntegrityError, match="session_owner mismatch"):
        logger.update_narrative_summary(
            session_owner="scenario_a",
            session_number=sn,
            round_number=1,
            turn_number=1,
            acting_character="A",
            rendered_output="nope",
            character_move=_minimal_move(),
            director_decision=_minimal_decision(),
        )


def test_t4_round_index_explicit_session_number_mismatch_fails(
    tmp_path: Path,
) -> None:
    """T4: _round_index.json declares wrong session_number → fail."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    sp = base / f"session_{sn:03d}"
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    (sp / "_round_index.json").write_text(
        json.dumps(
            {"session_owner": "scenario_a", "session_number": 99999, "rounds": []}
        ),
        encoding="utf-8",
    )
    with pytest.raises(AuditSessionIntegrityError, match="session_number mismatch"):
        logger.write_round_index(
            session_owner="scenario_a",
            session_number=sn,
            round_number=1,
            turn_number=1,
            acting_character="A",
            director_choice_reason="r",
        )


def test_t5_parallel_claims_yield_distinct_sessions(tmp_path: Path) -> None:
    """T5: Simulated allocation collision — all claims succeed uniquely."""

    base = tmp_path / "par"
    claimed: list[int] = []
    barrier = threading.Barrier(8)

    def worker() -> int:
        barrier.wait()
        return claim_next_audit_session_number(base_dir=base)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(worker) for _ in range(8)]
        for fut in as_completed(futures):
            claimed.append(fut.result())

    assert len(claimed) == 8
    assert len(set(claimed)) == 8


def test_t6_manifest_only_then_first_narrative_succeeds(tmp_path: Path) -> None:
    """T6: Manifest present, no narrative — first narrative initializes."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    logger.update_narrative_summary(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        rendered_output="Fresh.",
        character_move=_minimal_move(),
        director_decision=_minimal_decision(),
    )
    assert (base / f"session_{sn:03d}" / "_narrative.json").exists()


def test_t7_corrupted_narrative_mid_session_second_write_fails(
    tmp_path: Path,
) -> None:
    """T7: After first OK write, corrupt narrative owner → second write fails."""

    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    sp = base / f"session_{sn:03d}"
    rdir = sp / "round_001"
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    logger.write_round_index(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        director_choice_reason="r",
    )
    logger.update_narrative_summary(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        rendered_output="OK1",
        character_move=_minimal_move(),
        director_decision=_minimal_decision(),
    )
    entry = logger.create_entry(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        bot_name="Director",
        bot_type="director",
        input_messages=[],
        raw_response="{}",
        parsed_output={},
    )
    logger.log_bot_interaction(entry)
    n_before = len(list(rdir.glob("*_full.json")))

    nar = json.loads((sp / "_narrative.json").read_text(encoding="utf-8"))
    nar["session_owner"] = "evil_other"
    (sp / "_narrative.json").write_text(json.dumps(nar), encoding="utf-8")

    with pytest.raises(AuditSessionIntegrityError):
        logger.update_narrative_summary(
            session_owner="scenario_a",
            session_number=sn,
            round_number=1,
            turn_number=2,
            acting_character="A",
            rendered_output="after corruption",
            character_move=_minimal_move(),
            director_decision=_minimal_decision(),
        )

    assert len(list(rdir.glob("*_full.json"))) == n_before


def test_manifest_write_rejected_when_narrative_cross_owner(tmp_path: Path) -> None:
    """695-style: stale narrative blocks manifest refresh for different owner."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    sp = base / f"session_{sn:03d}"
    (sp / "_narrative.json").write_text(
        json.dumps(
            {
                "session_owner": "memory_private_directed",
                "session_number": sn,
                "complete_narrative": "X",
                "turns": [],
                "character_stats": {},
                "scene_template": {},
            }
        ),
        encoding="utf-8",
    )
    logger = AuditLogger(str(base))
    with pytest.raises(AuditSessionIntegrityError, match="session_owner mismatch"):
        logger.write_session_manifest(
            session_owner="strong_user_steer",
            session_number=sn,
            cast=["A"],
            opening_description="open",
            user_name="U",
        )


def test_narrative_without_manifest_fails(tmp_path: Path) -> None:
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    logger = AuditLogger(str(base))
    with pytest.raises(AuditSessionIntegrityError, match="_manifest.json is required"):
        logger.update_narrative_summary(
            session_owner="scenario_a",
            session_number=sn,
            round_number=1,
            turn_number=1,
            acting_character="A",
            rendered_output="orphan",
            character_move=_minimal_move(),
            director_decision=_minimal_decision(),
        )


def test_legacy_round_index_without_identity_backfills_and_appends(
    tmp_path: Path,
) -> None:
    """Continuation-compatible legacy index has rounds key only; manifest aligns."""
    base = tmp_path / "audits"
    sn = claim_next_audit_session_number(base_dir=base)
    sp = base / f"session_{sn:03d}"
    logger = AuditLogger(str(base))
    logger.write_session_manifest(
        session_owner="scenario_a",
        session_number=sn,
        cast=["A"],
        opening_description="open",
        user_name="U",
    )
    (sp / "_round_index.json").write_text(json.dumps({"rounds": []}), encoding="utf-8")
    logger.write_round_index(
        session_owner="scenario_a",
        session_number=sn,
        round_number=1,
        turn_number=1,
        acting_character="A",
        director_choice_reason="r",
    )
    idx = json.loads((sp / "_round_index.json").read_text(encoding="utf-8"))
    assert idx["session_owner"] == "scenario_a"
    assert idx["session_number"] == sn
