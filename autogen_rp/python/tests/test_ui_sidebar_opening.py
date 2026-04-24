"""Tests for Streamlit opener UI helpers (Issue #101)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_TEMPLATE,
)
from scene_opener import SceneOpener
from ui_sidebar_opening import (
    _selection_resolves_for_multi_opener_list,
    streamlit_opener_selection_error,
)


def _pair() -> tuple[SceneOpener, SceneOpener]:
    return (
        SceneOpener(
            id="a",
            source="template",
            owner="t1",
            label="Alpha",
            text="t1",
            tags=[],
            description="First desc",
        ),
        SceneOpener(
            id="b",
            source="template",
            owner="t1",
            label="Beta",
            text="t2",
            tags=[],
        ),
    )


def test_selection_resolves_multi_requires_non_empty_or_match() -> None:
    a, b = _pair()
    assert _selection_resolves_for_multi_opener_list([a, b], None) is False
    assert _selection_resolves_for_multi_opener_list([a, b], "") is False
    assert _selection_resolves_for_multi_opener_list([a, b], "a") is True
    assert _selection_resolves_for_multi_opener_list([a, b], "Alpha") is True


def test_selection_resolves_single_always_true_for_compose() -> None:
    a, _ = _pair()
    assert _selection_resolves_for_multi_opener_list([a], None) is True


def test_streamlit_opener_selection_error_template_multi_none() -> None:
    a, b = _pair()

    class _OM:
        def get_template_openers(self, tid: str):
            assert tid == "tpl"
            return [a, b]

        def get_character_openers(self, _f: str):
            return []

    err = streamlit_opener_selection_error(
        opening_mode=STREAMLIT_OPENING_MODE_TEMPLATE,
        selected_opener_id=None,
        scene_setup={"template_id": "tpl"},
        selected_chars=["x.json"],
        scene_owner="X",
        opener_manager=_OM(),
        character_loader_cls=object,
        resolve_character_file_fn=lambda _l, _s: None,
    )
    assert err is not None
    assert "template opening" in err.lower()


def test_streamlit_opener_selection_error_template_multi_picked() -> None:
    a, b = _pair()

    class _OM:
        def get_template_openers(self, tid: str):
            return [a, b]

        def get_character_openers(self, _f: str):
            return []

    assert (
        streamlit_opener_selection_error(
            opening_mode=STREAMLIT_OPENING_MODE_TEMPLATE,
            selected_opener_id="a",
            scene_setup={"template_id": "tpl"},
            selected_chars=[],
            scene_owner="",
            opener_manager=_OM(),
            character_loader_cls=object,
            resolve_character_file_fn=lambda _l, _s: None,
        )
        is None
    )


def test_streamlit_opener_selection_error_custom_skips() -> None:
    a, b = _pair()

    class _OM:
        def get_template_openers(self, _tid: str):
            return [a, b]

    assert (
        streamlit_opener_selection_error(
            opening_mode=STREAMLIT_OPENING_MODE_CUSTOM,
            selected_opener_id=None,
            scene_setup={"template_id": "tpl"},
            selected_chars=[],
            scene_owner="",
            opener_manager=_OM(),
            character_loader_cls=object,
            resolve_character_file_fn=lambda _l, _s: None,
        )
        is None
    )


def test_streamlit_opener_selection_error_character_multi() -> None:
    a, b = _pair()

    class _OM:
        def get_template_openers(self, _tid: str):
            return []

        def get_character_openers(self, f: str):
            assert f == "harley.json"
            return [a, b]

    err = streamlit_opener_selection_error(
        opening_mode=STREAMLIT_OPENING_MODE_CHARACTER,
        selected_opener_id=None,
        scene_setup=None,
        selected_chars=["harley.json"],
        scene_owner="Harley",
        opener_manager=_OM(),
        character_loader_cls=object,
        resolve_character_file_fn=lambda _l, name: "harley.json"
        if "Harley" in (name or "")
        else None,
    )
    assert err is not None
    assert "character opener" in err.lower()
