"""Simulation-primary memory and selection checks (DeepSeek full pipeline).

Core assertions use ``st_module``, ``HeadlessSimulationResult``, and runtime session
state only. Audit-based checks are optional (see ``simulation_assertions`` helpers
with ``_if_audit``); this module does not require ``--audit``.

Requires ``DEEPSEEK_API_KEY``. Run::

    cd autogen_rp/python
    pytest tests/test_simulation_memory_llm.py -m llm -v

Skip live LLM::

    pytest -m "not llm"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_PY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PY_ROOT / "rp_app"))
sys.path.append(str(_PY_ROOT / "tests"))

from headless_scene_simulation import (  # noqa: E402
    prepare_headless_session,
    run_headless_llm_scene,
)
from progression_simulation_scenarios import (  # noqa: E402
    load_scenario,
    scenario_prepare_kwargs,
)

from simulation_assertions import (  # noqa: E402
    assert_chat_assistant_turns_at_least,
    assert_memory_bounded,
    memory_combined_text,
    selector_text,
    session_agent_names,
)

pytestmark = [pytest.mark.llm, pytest.mark.slow, pytest.mark.asyncio]

_NAMES = ("Ayame", "Celina", "Hannah Lovelace")


def _require_deepseek() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")


async def _run_scenario(
    scenario_id: str,
    *,
    deep_simulation_turns: bool = True,
    extra_prepare: dict | None = None,
    max_turns_override: int | None = None,
):
    raw = load_scenario(scenario_id)
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(
        **prep,
        deep_simulation_turns=deep_simulation_turns,
        **(extra_prepare or {}),
    )
    try:
        result = await run_headless_llm_scene(
            st_module=st,
            max_turns=(
                max_turns_override
                if max_turns_override is not None
                else int(raw["max_turns"])
            ),
            trigger_text=str(raw["trigger_text"]),
            user_name="Traveler",
        )
        return result, st, raw
    finally:
        mc = st.session_state.get("model_client")
        if mc is not None and hasattr(mc, "close"):
            await mc.close()


@pytest.mark.asyncio
async def test_memory_public_propagation_simulation() -> None:
    """Observers should retain public content (anchor substring from trigger)."""
    _require_deepseek()
    result, st, _raw = await _run_scenario("memory_public_propagation")
    assert result.scenario_id == "memory_public_propagation"
    assert_chat_assistant_turns_at_least(st, 2)
    for name in _NAMES:
        assert_memory_bounded(st, name, max_summary=20, max_private=40)
    observers = ("Celina", "Hannah Lovelace")
    rumor_any = any(
        "rumor" in memory_combined_text(st, n).lower() for n in observers
    )
    assert rumor_any, (
        "Expected at least one observer memory to contain public anchor 'rumor'; "
        f"selector tail: {selector_text(result)[-800:]!r}"
    )


@pytest.mark.asyncio
async def test_memory_private_directed_simulation() -> None:
    """Whispered codeword to Celina only; Hannah must not retain it."""
    _require_deepseek()
    result, st, _raw = await _run_scenario("memory_private_directed")
    assert result.scenario_id == "memory_private_directed"
    assert_chat_assistant_turns_at_least(st, 2)
    token = "ZEPHYR-OMEGA-NINE"
    celina_blob = memory_combined_text(st, "Celina")
    assert token.lower() in celina_blob.lower(), (
        f"Expected Celina memory to contain codeword (case-insensitive); len={len(celina_blob)}"
    )
    hannah_blob = memory_combined_text(st, "Hannah Lovelace")
    assert token.lower() not in hannah_blob.lower(), (
        "Hannah memory should not retain the whispered codeword"
    )


@pytest.mark.asyncio
async def test_memory_duplicate_retry_simulation() -> None:
    """Natural run: pipeline completes; memory lists stay bounded."""
    _require_deepseek()
    result, st, _raw = await _run_scenario("memory_duplicate_retry")
    assert result.scenario_id == "memory_duplicate_retry"
    assert_chat_assistant_turns_at_least(st, 2)
    for name in ("Ayame", "Celina"):
        assert_memory_bounded(st, name, max_summary=20, max_private=40)
    assert result.continuity_turn_counter >= 0


@pytest.mark.asyncio
async def test_memory_fallback_director_simulation() -> None:
    """Typical Director JSON path; structured moves and chat accumulate."""
    _require_deepseek()
    result, st, _raw = await _run_scenario("memory_fallback_director")
    assert result.scenario_id == "memory_fallback_director"
    assert_chat_assistant_turns_at_least(st, 1)
    assert result.recent_structured_moves or result.chat_history


@pytest.mark.asyncio
async def test_memory_long_session_simulation() -> None:
    """Many turns without unbounded episodic lists."""
    _require_deepseek()
    result, st, _raw = await _run_scenario("memory_long_session")
    assert result.scenario_id == "memory_long_session"
    assert_chat_assistant_turns_at_least(st, 6)
    for name in ("Ayame", "Celina"):
        assert_memory_bounded(st, name, max_summary=25, max_private=50)


@pytest.mark.asyncio
async def test_memory_forced_speaker_simulation() -> None:
    """Session preseed: Celina forced before Director model pick."""
    _require_deepseek()
    raw = load_scenario("memory_forced_speaker")
    prep = scenario_prepare_kwargs(raw)
    st = prepare_headless_session(**prep, deep_simulation_turns=True)
    st.session_state["pending_forced_speaker"] = "Celina"
    st.session_state["forced_speaker_consumed"] = False
    try:
        result = await run_headless_llm_scene(
            st_module=st,
            max_turns=int(raw["max_turns"]),
            trigger_text=str(raw["trigger_text"]),
            user_name="Traveler",
        )
    finally:
        mc = st.session_state.get("model_client")
        if mc is not None and hasattr(mc, "close"):
            await mc.close()
    assert result.scenario_id == "memory_forced_speaker"
    moves = list(result.recent_structured_moves or [])
    assert moves, "expected at least one structured move"
    assert str(moves[0].get("speaker", "")) == "Celina", (
        f"expected first structured speaker Celina; got {moves[0]!r}; "
        f"session agent keys={session_agent_names(st)!r}"
    )
    sel_blob = selector_text(result)
    supporting = (
        "Forced speaker selected: Celina" in sel_blob
        or (
            "Forced speaker selected" in sel_blob
            and "Celina" in sel_blob
        )
        or "Director override to addressed character: Celina" in sel_blob
        or any(
            str(line).startswith("Director selected Celina")
            for line in (result.selector_decisions or [])[:6]
        )
    )
    assert supporting, (
        "expected a selector signal (forced Celina or early Director selected Celina); "
        f"selector_decisions={result.selector_decisions!r}"
    )
    assert_chat_assistant_turns_at_least(st, 1)
