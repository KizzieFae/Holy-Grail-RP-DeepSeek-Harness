"""Phase 4A: retrieval audit helpers and strict verification (no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from retrieval_audit_helpers import (  # noqa: E402
    apply_retrieval_session_to_audit_summary,
    build_retrieval_session_audit,
    build_retrieval_summary_for_audit,
    merge_retrieval_session_into_audit_summary,
    retrieval_index_fingerprint,
    verify_retrieval_strict_or_raise,
)
from runtime_packets import RetrievedContextBundle, RetrievedItem  # noqa: E402
from turn_runner_audit import log_character_turn_audit  # noqa: E402


def test_build_retrieval_summary_empty() -> None:
    s = build_retrieval_summary_for_audit(RetrievedContextBundle(items=()))
    assert s["retrieved_block_present"] is False
    assert s["retrieved_item_count"] == 0
    assert s["retrieved_char_count"] == 0
    assert s["retrieved_source_refs"] == []


def test_build_retrieval_summary_caps_refs() -> None:
    items = tuple(
        RetrievedItem(
            text="x",
            source_kind="lore",
            source_ref=f"ref{i}",
            scope="s",
            relevance_tags=frozenset(),
            priority=1,
            non_authoritative=True,
            from_other_character=None,
        )
        for i in range(20)
    )
    s = build_retrieval_summary_for_audit(RetrievedContextBundle(items=items))
    assert s["retrieved_item_count"] == 20
    assert len(s["retrieved_source_refs"]) == 12


def test_build_retrieval_session_audit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_RETRIEVED_CONTEXT_INDEX", raising=False)
    s = build_retrieval_session_audit(saw_nonempty_bundle=False)
    assert s["retrieval_mode"] == "off"
    assert s["retrieval_index_path"] is None
    assert s["retrieval_verified_active"] is False
    assert s["retrieval_index_fingerprint"] is None


def test_build_retrieval_session_audit_on_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RP_RETRIEVED_CONTEXT_INDEX", "/tmp/fake_index.json")
    s = build_retrieval_session_audit(saw_nonempty_bundle=True)
    assert s["retrieval_mode"] == "on"
    assert s["retrieval_index_path"] == "/tmp/fake_index.json"
    assert s["retrieval_verified_active"] is True


def test_verify_strict_ok_when_on_and_nonempty() -> None:
    verify_retrieval_strict_or_raise(
        {
            "retrieval_mode": "on",
            "retrieval_verified_active": True,
        },
        scene_template_id="arkham_asylum_cell_intake",
    )


def test_verify_strict_raises_when_on_template_but_not_verified() -> None:
    with pytest.raises(ValueError, match="non-empty retrieved bundle"):
        verify_retrieval_strict_or_raise(
            {
                "retrieval_mode": "on",
                "retrieval_verified_active": False,
            },
            scene_template_id="arkham_asylum_cell_intake",
        )


def test_verify_strict_skips_when_off() -> None:
    verify_retrieval_strict_or_raise(
        {
            "retrieval_mode": "off",
            "retrieval_verified_active": False,
        },
        scene_template_id="arkham_asylum_cell_intake",
    )


def test_merge_retrieval_session_into_audit_summary(tmp_path: Path) -> None:
    p = tmp_path / "_audit_summary.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    sess = {"retrieval_mode": "on", "retrieval_verified_active": True}
    merge_retrieval_session_into_audit_summary(str(p), sess)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["x"] == 1
    assert data["retrieval_session"] == sess


def test_apply_retrieval_session_to_audit_summary_matches_build_and_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RP_RETRIEVED_CONTEXT_INDEX", raising=False)
    p = tmp_path / "_audit_summary.json"
    p.write_text(json.dumps({"k": "v"}), encoding="utf-8")
    out = apply_retrieval_session_to_audit_summary(str(p), saw_nonempty_bundle=False)
    expected = build_retrieval_session_audit(saw_nonempty_bundle=False)
    assert out == expected
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["retrieval_session"] == expected


def test_refresh_audit_summary_report_merges_retrieval_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Issue #36: Streamlit audit refresh uses the same retrieval_session merge as headless."""
    from app_state_audit import refresh_audit_summary_report

    p = tmp_path / "_audit_summary.json"
    p.write_text(json.dumps({"overview": {}}), encoding="utf-8")
    monkeypatch.delenv("RP_RETRIEVED_CONTEXT_INDEX", raising=False)

    class _St:
        session_state: dict

    st = _St()
    st.session_state = {
        "audit_enabled": True,
        "audit_session_owner": "operator",
        "audit_session_number": 1,
        "sim_retrieval_saw_nonempty_bundle": False,
        "audit_round_number": 0,
        "audit_turn_number": 0,
    }

    class _Logger:
        def write_summary_report(self, **kwargs):
            return str(p)

    refresh_audit_summary_report(
        st_module=st,
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("operator", 1, 0, 0),
        get_continuity_manager_fn=None,
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["overview"] == {}
    assert data["retrieval_session"]["retrieval_mode"] == "off"
    assert data["retrieval_session"]["retrieval_verified_active"] is False


def test_retrieval_index_fingerprint_missing() -> None:
    fp = retrieval_index_fingerprint("/nonexistent/path/that/does/not/exist_12345.json")
    assert fp is not None
    assert fp.startswith("missing|")


def test_log_character_turn_audit_includes_retrieval_summary() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    log_character_turn_audit(
        next_actor="Alice",
        move={"action": "", "dialogue": "hi"},
        task_prompt="sys",
        char_raw_response="{}",
        decision={},
        char_names=["Alice"],
        continuity_manager=None,
        round_number=1,
        turn_number=1,
        character_summary_block_audit={
            "summary_generation_eligible": True,
            "summary_blocks_generated_total": 0,
            "generated_summary_block_ids": [],
            "summary_blocks_available_count": 0,
            "available_summary_block_ids": [],
            "summary_blocks_selected_count": 0,
            "selected_summary_block_ids": [],
            "excluded_summary_block_ids": [],
            "selection_reason": "",
            "skipped_reason": "",
            "fallback_used": False,
            "summary_limit": None,
            "has_binding_constraints": False,
            "scene_binding_constraints_section": "",
            "retrieval_summary": {
                "retrieved_block_present": True,
                "retrieved_item_count": 2,
                "retrieved_char_count": 10,
                "retrieved_source_refs": ["a", "b"],
            },
        },
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
        effective_user_trigger="user says hi",
    )
    assert captured.get("effective_user_trigger") == "user says hi"
    meta = captured.get("metadata") or {}
    assert meta.get("retrieval_summary", {}).get("retrieved_item_count") == 2
    sb = meta.get("summary_blocks") or {}
    assert "retrieval_summary" not in sb
