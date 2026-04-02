"""SUPPLEMENTAL: monkeypatched Director parse failure and duplicate retry paths.

Primary coverage lives in ``test_simulation_memory_llm.py`` (natural simulation runs).
These tests inject one-shot failures so fallback / duplicate-retry logic is exercised
without relying on model behavior. Marked ``supplemental_simulation`` for filtering.

Requires ``DEEPSEEK_API_KEY`` (same as other LLM simulation tests).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PY_ROOT / "rp_app"))
sys.path.append(str(_PY_ROOT / "tests"))

import headless_scene_simulation as headless_sim  # noqa: E402
from headless_scene_simulation import (  # noqa: E402
    prepare_headless_session,
    run_headless_llm_scene,
)
from progression_simulation_scenarios import (  # noqa: E402
    load_scenario,
    scenario_prepare_kwargs,
)
from response_validation import parse_director_decision as real_parse_director  # noqa: E402

from simulation_assertions import (  # noqa: E402
    assert_chat_assistant_turns_at_least,
    rejected_entries,
    selector_text,
)

pytestmark = [
    pytest.mark.llm,
    pytest.mark.slow,
    pytest.mark.asyncio,
    pytest.mark.supplemental_simulation,
]


def _require_deepseek() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")


@pytest.mark.asyncio
async def test_supplemental_director_parse_fallback_then_normal(monkeypatch) -> None:
    """First Director response fails JSON parse; pipeline uses fallback, then real parses."""
    _require_deepseek()
    calls = {"n": 0}

    def _parse(content, participant_names, available_actors=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return None, "supplemental forced parse failure"
        return real_parse_director(content, participant_names, available_actors)

    monkeypatch.setattr(headless_sim, "parse_director_decision", _parse)

    raw = load_scenario("memory_fallback_director")
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, deep_simulation_turns=True)
    try:
        result = await run_headless_llm_scene(
            st_module=st,
            max_turns=min(5, int(raw["max_turns"]) + 2),
            trigger_text=str(raw["trigger_text"]),
            user_name="Traveler",
        )
    finally:
        mc = st.session_state.get("model_client")
        if mc is not None and hasattr(mc, "close"):
            await mc.close()

    sel = selector_text(result)
    assert "Fallback selection after director parse failure" in sel, sel[-1200:]
    assert calls["n"] >= 2
    assert_chat_assistant_turns_at_least(st, 1)


@pytest.mark.asyncio
async def test_supplemental_duplicate_retry_injected(monkeypatch) -> None:
    """First validate_bot_response fails with [DUPLICATE]; engine retries same actor."""
    _require_deepseek()
    real_validate = headless_sim.validate_bot_response
    calls = {"n": 0}

    def _validate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return False, "[DUPLICATE] supplemental injected duplicate"
        return real_validate(*args, **kwargs)

    monkeypatch.setattr(headless_sim, "validate_bot_response", _validate)

    raw = load_scenario("memory_duplicate_retry")
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, deep_simulation_turns=True)
    try:
        await run_headless_llm_scene(
            st_module=st,
            max_turns=min(6, int(raw["max_turns"])),
            trigger_text=str(raw["trigger_text"]),
            user_name="Traveler",
        )
    finally:
        mc = st.session_state.get("model_client")
        if mc is not None and hasattr(mc, "close"):
            await mc.close()

    assert any(
        "DUPLICATE" in str(e.get("reason", "")) for e in rejected_entries(st)
    ), rejected_entries(st)
    assert any(
        "Retrying" in str(line)
        for line in (st.session_state.get("selector_decisions") or [])
    )
