"""Issue #109 — opaque UUID session_id; Streamlit audit slug from session_id only."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_identity import streamlit_audit_owner_label_from_session_id
from session_manager import SessionManager

_UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def test_generate_session_id_is_uuid_v4_opaque(tmp_path: Path) -> None:
    m = SessionManager(tmp_path)
    sid = m.generate_session_id()
    assert _UUID_V4_RE.match(sid), sid


def test_generate_session_id_unique_per_call(tmp_path: Path) -> None:
    m = SessionManager(tmp_path)
    ids = {m.generate_session_id() for _ in range(50)}
    assert len(ids) == 50


def test_streamlit_audit_slug_is_deterministic_filesystem_friendly() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    a = streamlit_audit_owner_label_from_session_id(sid)
    b = streamlit_audit_owner_label_from_session_id(sid)
    assert a == b == "550e8400_e29b_41d4_a716_446655440000"
    assert "/" not in a and "\\" not in a


@pytest.mark.parametrize("empty", ["", "   "])
def test_streamlit_audit_slug_empty_session_id_fallback(empty: str) -> None:
    assert streamlit_audit_owner_label_from_session_id(empty) == "streamlit_session"
