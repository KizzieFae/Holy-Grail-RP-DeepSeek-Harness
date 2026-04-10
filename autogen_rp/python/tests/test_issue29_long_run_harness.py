"""Issue #29 long-run harness helpers (headless only)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from headless_scene_simulation import (  # noqa: E402
    HeadlessStreamlit,
    _issue29_resolve_synthetic_available_actors,
    _wrap_get_available_actors_for_issue29_long_run,
)


def test_issue29_resolve_synthetic_prefers_last_successful() -> None:
    assert _issue29_resolve_synthetic_available_actors(
        ["A", "B"],
        last_successful_actor="B",
        actors_used_this_round_tail="A",
    ) == ["B"]


def test_issue29_resolve_synthetic_then_used_tail() -> None:
    assert _issue29_resolve_synthetic_available_actors(
        ["A", "B"],
        last_successful_actor="",
        actors_used_this_round_tail="A",
    ) == ["A"]


def test_issue29_resolve_synthetic_then_first_participant() -> None:
    assert _issue29_resolve_synthetic_available_actors(
        ["Z", "Y"],
        last_successful_actor="nomatch",
        actors_used_this_round_tail="nomatch",
    ) == ["Z"]


def test_issue29_wrap_injects_when_harness_and_inner_empty() -> None:
    st = HeadlessStreamlit()
    st.session_state["issue29_long_run_harness"] = True
    st.session_state["issue29_last_successful_actor"] = "B"
    st.session_state["issue29_actors_used_this_round_tail"] = "A"

    def inner(
        _pn: list[str],
        _u: list[str] | None,
        _e: list[str] | None,
        _o: list[str] | None,
    ) -> list[str]:
        return []

    wrapped = _wrap_get_available_actors_for_issue29_long_run(
        inner,
        st_module=st,
    )
    assert wrapped(["A", "B"], None, None, None) == ["B"]


def test_issue29_wrap_no_inject_when_inner_nonempty() -> None:
    st = HeadlessStreamlit()
    st.session_state["issue29_long_run_harness"] = True

    def inner(
        _pn: list[str],
        _u: list[str] | None,
        _e: list[str] | None,
        _o: list[str] | None,
    ) -> list[str]:
        return ["A"]

    wrapped = _wrap_get_available_actors_for_issue29_long_run(
        inner,
        st_module=st,
    )
    assert wrapped(["A", "B"], None, None, None) == ["A"]


def test_issue29_wrap_harness_off_returns_empty() -> None:
    st = HeadlessStreamlit()

    def inner(
        _pn: list[str],
        _u: list[str] | None,
        _e: list[str] | None,
        _o: list[str] | None,
    ) -> list[str]:
        return []

    wrapped = _wrap_get_available_actors_for_issue29_long_run(
        inner,
        st_module=st,
    )
    assert wrapped(["A"], None, None, None) == []
