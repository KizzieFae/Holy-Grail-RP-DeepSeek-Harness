"""Tests for scoped active-doctrine preflight."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PY / "rp_app"))
sys.path.insert(0, str(_PY / "validation_runs" / "issue251"))

from i251_doctrine_preflight import (  # noqa: E402
    active_physical_severance_contamination_hits,
    active_physical_severance_guarded_contamination_hits,
    build_physical_severance_guarded_preflight,
    build_physical_severance_preflight,
)
from prompt_topology_issue240 import (  # noqa: E402
    apply_issue251_physical_severance_guarded_prompt_overrides,
    apply_issue251_physical_severance_prompt_overrides,
    issue251_physical_severance_contamination_hits,
)


def _audit_prompt(session: str, turn: int) -> tuple[str, str]:
    d = _PY / "rp_app/data/rp_audits" / session / "round_001"
    hits = sorted(d.glob(f"*turn{turn:02d}_willow_reeves_full.json"))
    hits = [p for p in hits if "parse_retry" not in p.name]
    if not hits:
        pytest.skip("audit missing")
    audit = json.loads(hits[0].read_text(encoding="utf-8"))
    bot = str(audit.get("bot_name") or "Willow_Reeves")
    prod = next(
        m["content"]
        for m in audit["input_messages"]
        if m.get("role") == "system"
    )
    return apply_issue251_physical_severance_prompt_overrides(prod, bot), bot


def test_scoped_preflight_passes_gm3_and_899() -> None:
    for session, turn in (("session_912", 12), ("session_899", 9)):
        prompt, _ = _audit_prompt(session, turn)
        full_hits = issue251_physical_severance_contamination_hits(prompt)
        scoped_hits = active_physical_severance_contamination_hits(prompt)
        pf = build_physical_severance_preflight(prompt)
        assert pf["contamination_clean"] is True
        assert scoped_hits == []
        # full-prompt scan may false-positive on frozen audit body
        if session == "session_899":
            assert full_hits != []


def _audit_prompt_guarded(session: str, turn: int) -> str:
    d = _PY / "rp_app/data/rp_audits" / session / "round_001"
    hits = sorted(d.glob(f"*turn{turn:02d}_willow_reeves_full.json"))
    hits = [p for p in hits if "parse_retry" not in p.name]
    if not hits:
        pytest.skip("audit missing")
    audit = json.loads(hits[0].read_text(encoding="utf-8"))
    bot = str(audit.get("bot_name") or "Willow_Reeves")
    prod = next(
        m["content"]
        for m in audit["input_messages"]
        if m.get("role") == "system"
    )
    return apply_issue251_physical_severance_guarded_prompt_overrides(prod, bot)


def test_scoped_preflight_passes_arm_c_gm3() -> None:
    prompt = _audit_prompt_guarded("session_912", 12)
    assert active_physical_severance_guarded_contamination_hits(prompt) == []
    pf = build_physical_severance_guarded_preflight(prompt)
    assert pf["contamination_clean"] is True
    assert pf["doctrine_block_matches_spec"] is True
