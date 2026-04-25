"""Issue #106 — audit identity: audit_session_owner only; Streamlit session-derived label."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_audit import AuditIdentityMissingError, get_audit_context
from audit_identity import streamlit_audit_owner_label_from_session_id
from progression_simulation_scenarios import audit_owner_slug


def test_streamlit_audit_owner_label_is_session_derived_not_cast() -> None:
    sid = "sess-ABC-123.xyz"
    label = streamlit_audit_owner_label_from_session_id(sid)
    assert label == "sess_abc_123_xyz"
    assert label != "ayame"
    assert streamlit_audit_owner_label_from_session_id("") == "streamlit_session"


def test_get_audit_context_uses_audit_session_owner_only() -> None:
    st = type("S", (), {})()
    st.session_state = {
        "audit_enabled": True,
        "audit_session_owner": "ui_audit_slug",
        "scene_owner": "First Cast Name",
        "audit_session_number": 3,
        "audit_round_number": 1,
        "audit_turn_number": 0,
    }

    owner, num, rn, tn = get_audit_context(
        st_module=st,
        is_audit_enabled_fn=lambda: bool(st.session_state.get("audit_enabled")),
        get_audit_logger_fn=lambda: None,
    )
    assert owner == "ui_audit_slug"
    assert num == 3
    assert rn == 1
    assert tn == 0


def test_get_audit_context_no_scene_owner_fallback() -> None:
    st = type("S", (), {})()
    st.session_state = {
        "audit_enabled": True,
        "audit_session_owner": None,
        "scene_owner": "OnlySceneOwner",
        "audit_session_number": 1,
    }
    with pytest.raises(AuditIdentityMissingError):
        get_audit_context(
            st_module=st,
            is_audit_enabled_fn=lambda: bool(st.session_state.get("audit_enabled")),
            get_audit_logger_fn=lambda: None,
        )


def test_get_audit_context_audit_off_allows_missing_owner() -> None:
    st = type("S", (), {})()
    st.session_state = {
        "audit_enabled": False,
        "audit_session_owner": None,
        "scene_owner": "X",
    }
    owner, num, _, _ = get_audit_context(
        st_module=st,
        is_audit_enabled_fn=lambda: bool(st.session_state.get("audit_enabled")),
        get_audit_logger_fn=lambda: None,
    )
    assert owner == ""
    assert num == 0


def test_headless_audit_owner_slug_unchanged() -> None:
    assert audit_owner_slug("arrival_setup") == "arrival_setup"
    assert audit_owner_slug("emotional_loop_2char") == "emotional_loop_2char"
