"""Tests for scene_lifecycle_actions (Streamlit end/close helpers)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from scene_lifecycle_actions import close_active_scene_if_needed


class FakeSt:
    def __init__(self) -> None:
        self.session_state: dict = {
            "scene_started": True,
            "selected_chars": ["a.json"],
            "npc_selection": ["a"],
            "scene_owner": "OldOwner",
        }


@pytest.mark.asyncio
async def test_close_active_scene_if_needed_clears_fresh_setup_state_issue_104() -> None:
    """After close, Issue #104 keys are cleared for the next pre-start (same as end_scene)."""
    st = FakeSt()
    save_calls: list[object] = []

    async def fake_save(*_a, **_kw) -> None:
        save_calls.append(True)

    await close_active_scene_if_needed(
        st_module=st,
        reason="test_reason",
        save_current_session_fn=fake_save,
    )

    assert save_calls
    assert st.session_state.get("scene_started") is False
    assert st.session_state.get("scene_ended") is True
    assert st.session_state.get("selected_chars") == []
    assert "npc_selection" not in st.session_state
    assert st.session_state.get("scene_owner") is None
