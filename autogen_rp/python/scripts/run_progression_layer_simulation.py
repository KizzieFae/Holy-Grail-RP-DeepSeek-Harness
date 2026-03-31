#!/usr/bin/env python3
"""Headless progression-layer simulation -> audit-style markdown report.

This is the same *class* of pipeline as ``run_presence_scene_audit.py``: scripted
structured moves through production code paths, then a printable audit block.
It does **not** call live LLMs and does **not** write ``rp_audits/*.json`` (that
still requires the Streamlit app with auditing enabled, or a future headless
driver wired to ``audit_logger``).

Use for checklist sections **B/C/E** (contract, gate, MED→HIGH) before or
alongside manual review of JSON audits from real sessions.

From ``autogen_rp/python``::

    python scripts/run_progression_layer_simulation.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from beat_shift_state import default_pending_beat_shift, ensure_beat_shift_fields  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_state import IssueState, IssueStatus  # noqa: E402
from orchestration_helpers import resolve_progression_override_actor  # noqa: E402
from progression_enforcement import (  # noqa: E402
    collect_issue_signatures,
    progression_enforcement_gate_active,
    qualifies_as_progression_delta,
)


def _ts(m: ContinuityManager) -> datetime:
    n = m.turn_counter + 1
    return datetime.fromisoformat(f"2026-04-01T{10 + (n // 60):02d}:{n % 60:02d}:00")


def _turn(
    m: ContinuityManager,
    actor: str,
    move: dict,
    *,
    others: list[str],
) -> None:
    m.process_turn(
        acting_character=actor,
        move=move,
        director_decision={
            "next_actor": actor,
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "progression simulation",
        },
        other_characters=others,
        timestamp=_ts(m),
    )


def _orch_high_tension() -> dict:
    return {
        "scene_state": {"current_tension_level": "high", "scene_phase": "rising"},
        "recent_structured_moves": [],
        "beat_shift_scene_snapshots": [
            {"phase": "rising", "tension": "high"},
            {"phase": "rising", "tension": "high"},
        ],
        "pending_beat_shift": default_pending_beat_shift(),
    }


def _orch_beat_shift() -> dict:
    o = _orch_high_tension()
    pbs = o["pending_beat_shift"]
    pbs["active"] = True
    pbs["reason"] = "short_user_message"
    pbs["source_turn_id"] = "sim_user_round_1"
    return o


def run_all() -> list[tuple[str, str, dict]]:
    """Return list of (scene_id, PASS|FAIL, evidence dict)."""
    out: list[tuple[str, str, dict]] = []

    # --- S1: gate inactive (low tension, no beat-shift) — any non-empty qualify ok for "would pass if gated" ---
    m1 = ContinuityManager()
    m1.initialize_scene("room", "Test.", ["A", "B"])
    orch_low = {
        "scene_state": {"current_tension_level": "low", "scene_phase": "opening"},
        "recent_structured_moves": [],
        "beat_shift_scene_snapshots": [],
        "pending_beat_shift": default_pending_beat_shift(),
    }
    ensure_beat_shift_fields(orch_low)
    gate_low = progression_enforcement_gate_active(
        orchestration_state=orch_low, continuity_manager=m1
    )
    out.append(
        (
            "S1_gate_low_pressure_inactive",
            "PASS" if not gate_low else "FAIL",
            {"progression_enforcement_gate_active": gate_low},
        )
    )

    # --- S2: gate active (high pressure path) ---
    m2 = ContinuityManager()
    now = datetime.now(timezone.utc)
    m2.initialize_scene(
        "room",
        "Standoff.",
        ["A", "B"],
        initial_issues=[
            IssueState(
                issue_id="i1",
                description="Conflict",
                participants=["A", "B"],
                status=IssueStatus.ESCALATING,
                created_at=now,
                last_turn_index=None,
                status_reason="seed",
            )
        ],
    )
    m2.scene_state.current_tension_level = "high"
    orch_h = _orch_high_tension()
    ensure_beat_shift_fields(orch_h)
    gate_h = progression_enforcement_gate_active(
        orchestration_state=orch_h, continuity_manager=m2
    )
    out.append(
        (
            "S2_gate_high_pressure_active",
            "PASS" if gate_h else "FAIL",
            {"progression_enforcement_gate_active": gate_h},
        )
    )

    # --- S3: gate active via beat-shift OR ---
    orch_bs = _orch_beat_shift()
    ensure_beat_shift_fields(orch_bs)
    gate_bs = progression_enforcement_gate_active(
        orchestration_state=orch_bs, continuity_manager=m2
    )
    out.append(
        (
            "S3_gate_beat_shift_active",
            "PASS" if gate_bs else "FAIL",
            {"progression_enforcement_gate_active": gate_bs},
        )
    )

    # --- S4: dialogue-only weak move fails Q1–Q4 under gate (conceptual) ---
    m4 = ContinuityManager()
    m4.initialize_scene("room", "Loop.", ["A", "B"])
    ib = collect_issue_signatures(m4)
    weak = {
        "action": "shifts weight slightly",
        "dialogue": "Hmm.",
        "motivation": {
            "goal": "wait",
            "tactic": "stall",
            "emotional_driver": "neutral",
            "risk_level": "low",
        },
    }
    _turn(m4, "A", weak, others=["B"])
    ti = m4.turn_counter
    meta = m4.turn_metadata_by_index.get(ti, {})
    q = qualifies_as_progression_delta(
        continuity_manager=m4,
        turn_index=ti,
        turn_meta=meta if isinstance(meta, dict) else {},
        issues_before=ib,
        move=weak,
    )
    out.append(
        (
            "S4_dialogue_only_weak_move_no_delta",
            "PASS" if not q else "FAIL",
            {"qualifies": q, "consequences": meta.get("consequences")},
        )
    )

    # --- S5: move phrasing that ConsequenceClassifier maps to categories → Q1 ---
    # (Classifier uses substring markers, e.g. "blocked" not "blocking", and
    # control intent via words like "control" in goal/tactic.)
    m5 = ContinuityManager()
    m5.initialize_scene("room", "Tense.", ["A", "B"])
    ib5 = collect_issue_signatures(m5)
    strong = {
        "action": "blocked the doorway and held the frame",
        "dialogue": "Nobody moves until we settle this.",
        "motivation": {
            "goal": "establish control of the exit",
            "tactic": "block exit",
            "emotional_driver": "resolve",
            "risk_level": "high",
        },
    }
    _turn(m5, "A", strong, others=["B"])
    ti5 = m5.turn_counter
    meta5 = m5.turn_metadata_by_index.get(ti5, {})
    q5 = qualifies_as_progression_delta(
        continuity_manager=m5,
        turn_index=ti5,
        turn_meta=meta5 if isinstance(meta5, dict) else {},
        issues_before=ib5,
        move=strong,
    )
    out.append(
        (
            "S5_strong_move_qualifies",
            "PASS" if q5 else "FAIL",
            {"qualifies": q5, "consequences": meta5.get("consequences")},
        )
    )

    # --- S6: MED→HIGH override when gate on ---
    issues_dict = [
        {"status": "active", "participants": ["Ayame"]},
        {"status": "escalating", "participants": ["Celina"]},
    ]
    recent_moves = [
        {
            "speaker": "Ayame",
            "action": "wait",
            "dialogue": "",
            "motivation": {"goal": "x", "tactic": "y"},
            "consequences": [],
            "issue_updates": [],
            "presence_changes": [],
        },
        {
            "speaker": "Celina",
            "action": "push",
            "dialogue": "Now.",
            "motivation": {"goal": "x", "tactic": "y"},
            "consequences": ["escalation"],
            "issue_updates": [{}],
            "presence_changes": [],
        },
    ]
    ov_on = resolve_progression_override_actor(
        director_selected_actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=issues_dict,
        recent_structured_moves=recent_moves,
        progression_enforcement_gate=True,
    )
    ov_off = resolve_progression_override_actor(
        director_selected_actor="Ayame",
        available_actors=["Ayame", "Celina"],
        active_issues=issues_dict,
        recent_structured_moves=recent_moves,
        progression_enforcement_gate=False,
    )
    ok6 = ov_on == "Celina" and ov_off is None
    out.append(
        (
            "S6_med_to_high_override_only_when_gate",
            "PASS" if ok6 else "FAIL",
            {"override_gate_on": ov_on, "override_gate_off": ov_off},
        )
    )

    return out


def main() -> None:
    rows = run_all()
    print("## Progression layer simulation (headless audit report)\n")
    print(
        "_Pipeline: scripted moves -> `ContinuityManager.process_turn` -> "
        "`qualifies_as_progression_delta` / gate / override helpers. "
        "No LLM; no `rp_audits/*.json` (use Streamlit + audit toggle for JSON)._"
        "\n"
    )
    for sid, status, detail in rows:
        print(f"### {sid}\n")
        print(f"* **Result:** {status}\n")
        for k, v in sorted(detail.items()):
            print(f"* `{k}`: {v}\n")
        print()


if __name__ == "__main__":
    main()
