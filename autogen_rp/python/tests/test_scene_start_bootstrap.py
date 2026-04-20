"""GitHub #83 — scene-start bootstrap (continuity init/apply spine + opening helpers)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_continuity import restore_or_initialize_continuity_manager  # noqa: E402
from app_state_scene import build_initial_scene_issues  # noqa: E402
from scene_start_bootstrap import (  # noqa: E402
    mirror_opening_into_scene_state,
    resolve_streamlit_opening_narrative,
)


def test_restore_passes_opening_into_initialize_scene() -> None:
    captured_opening: list[str] = []

    class FakeManager:
        def __init__(self) -> None:
            self.scene_state = None

        def initialize_scene(
            self, location, opening_description, present_characters, initial_issues=None
        ) -> None:
            captured_opening.append(str(opening_description))
            self.scene_state = SimpleNamespace(
                present_characters=list(present_characters),
                opening_description=opening_description,
                environment_description=None,
            )

        def bootstrap_present_characters_from_cast(self, character_names: list[str]) -> None:
            pass

    fake_st = SimpleNamespace(session_state={})
    restore_or_initialize_continuity_manager(
        st_module=fake_st,
        continuity_state=None,
        character_names=["A", "B"],
        opening_description="Final opening text.",
        scene_setup=None,
        continuity_manager_cls=FakeManager,
        build_initial_scene_issues_fn=build_initial_scene_issues,
        apply_scene_setup_to_scene_state_fn=lambda *_a, **_k: None,
        sync_orchestration_state_from_continuity_fn=lambda: None,
    )
    assert captured_opening == ["Final opening text."]


def test_mirror_opening_sets_environment_description() -> None:
    cm = SimpleNamespace(
        scene_state=SimpleNamespace(
            opening_description="",
            environment_description=None,
        )
    )
    mirror_opening_into_scene_state(cm, "Prose here.")
    assert cm.scene_state.opening_description == "Prose here."
    assert cm.scene_state.environment_description == "Prose here."


@pytest.mark.asyncio
async def test_resolve_streamlit_opening_uses_static_text_without_narrator() -> None:
    opening = await resolve_streamlit_opening_narrative(
        scene_setup={"opening_text": "Static."},
        opener=None,
        resolve_opening_text_fn=lambda setup, _op: str(setup.get("opening_text", "") if setup else ""),
        display_char_names=["A"],
        char_names=["A"],
        user_name="U",
        scene_owner="O",
        build_scene_role_prompt_context_fn=lambda *_a, **_k: [],
        narrator=MagicMock(),
    )
    assert opening == "Static."
    narrator = MagicMock()
    narrator.on_messages = AsyncMock(
        return_value=SimpleNamespace(
            chat_message=SimpleNamespace(content="LLM opening")
        )
    )
    out = await resolve_streamlit_opening_narrative(
        scene_setup=None,
        opener=None,
        resolve_opening_text_fn=lambda _s, _o: "",
        display_char_names=["A"],
        char_names=["A"],
        user_name="U",
        scene_owner="O",
        build_scene_role_prompt_context_fn=lambda *_a, **_k: [],
        narrator=narrator,
    )
    assert out == "LLM opening"
    narrator.on_messages.assert_called_once()
