#!/usr/bin/env python3
"""Headless multi-scene presence / access audit via ContinuityManager.process_turn.

This exercises the same post-move pipeline as production (classifiers, exit/re-entry,
resolved outcomes, deadlock guard). Moves are authored JSON, not live LLM output.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Repo layout: autogen_rp/python/scripts/ -> sibling rp_app/ as import root
_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from continuity_manager import ContinuityManager
from orchestration_helpers import resolve_continuation_override_actor, ensure_orchestration_state
from response_validation_selection import get_available_actors
from scene_exit_detection import detect_exit_from_scene, has_scene_reentry_evidence


def _ts(m: ContinuityManager) -> datetime:
    n = m.turn_counter + 1
    return datetime.fromisoformat(f"2026-03-31T{12 + (n // 60):02d}:{n % 60:02d}:00")


def _turn(
    m: ContinuityManager,
    actor: str,
    move: dict,
    *,
    next_actor: str,
    others: list[str],
) -> None:
    m.process_turn(
        acting_character=actor,
        move=move,
        director_decision={
            "next_actor": next_actor,
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "presence scene audit",
        },
        other_characters=others,
        timestamp=_ts(m),
    )


def _tags(m: ContinuityManager) -> set[str]:
    idx = m.turn_counter
    meta = m.turn_metadata_by_index.get(idx, {})
    return {str(t) for t in (meta.get("tags") or []) if str(t).strip()}


def _pool(m: ContinuityManager, bot_names: list[str]) -> list[str]:
    ss = m.scene_state
    assert ss is not None
    eligible = [n for n in bot_names if n in ss.present_characters]
    return get_available_actors(
        bot_names,
        [],
        eligible,
        list(ss.offstage_characters or []),
    )


def _active_location_entry(m: ContinuityManager, subject: str, location_id: str):
    slot = f"access.location_entry::{subject}::{location_id}"
    for o in reversed(m.resolved_outcomes):
        if getattr(o, "status", "") != "active":
            continue
        if str(getattr(o, "slot_key", "") or "") == slot:
            return o
    return None


def _mot(**kwargs: str) -> dict:
    base = {
        "goal": kwargs.get("goal", "scene beat"),
        "tactic": kwargs.get("tactic", "execute"),
        "emotional_driver": kwargs.get("emotional_driver", "neutral"),
        "risk_level": kwargs.get("risk_level", "medium"),
    }
    base.update(kwargs)
    return base


def run_all() -> list[tuple[int, str, dict]]:
    """Returns list of (scene_num, PASS|FAIL, detail dict)."""
    results: list[tuple[int, str, dict]] = []

    # --- Scene 1 ---
    m1 = ContinuityManager()
    R, Mo, J = "Riley_Chen", "Morgan_Lee", "Jordan_Kim"
    m1.initialize_scene("Dorm common", "Shared suite.", [R, Mo, J])
    move1 = {
        "action": (
            "slammed the door to cut off the hallway and stalked past Morgan toward the couch, "
            "still inside the common area"
        ),
        "dialogue": "I am not done talking yet.",
        "motivation": _mot(goal="hold space", tactic="door control"),
    }
    det1 = detect_exit_from_scene(move1, m1.scene_state.to_dict(), R)
    _turn(m1, R, move1, next_actor=Mo, others=[Mo, J])
    tags1 = _tags(m1)
    ok1 = (
        not det1
        and "exit" not in tags1
        and R in m1.scene_state.present_characters
        and R not in m1.scene_state.offstage_characters
        and R in _pool(m1, [R, Mo, J])
    )
    results.append(
        (
            1,
            "PASS" if ok1 else "FAIL",
            {
                "beats": move1["action"] + " | " + move1["dialogue"],
                "detect_exit": det1,
                "tags": sorted(tags1),
                "present": list(m1.scene_state.present_characters),
                "offstage": list(m1.scene_state.offstage_characters),
                "pool_has_Riley": R in _pool(m1, [R, Mo, J]),
            },
        )
    )

    # --- Scene 2 (new manager, same room conceit) ---
    m2 = ContinuityManager()
    m2.initialize_scene("Dorm common", "Shared suite.", [R, Mo, J])
    move2 = {
        "action": (
            "walked toward the kitchenette, leaned against the wall, "
            "and grabbed something from the counter"
        ),
        "dialogue": "Still right here.",
        "motivation": _mot(),
    }
    det2 = detect_exit_from_scene(move2, m2.scene_state.to_dict(), R)
    _turn(m2, R, move2, next_actor=Mo, others=[Mo, J])
    tags2 = _tags(m2)
    ok2 = (
        not det2
        and "exit" not in tags2
        and R in m2.scene_state.present_characters
        and R in _pool(m2, [R, Mo, J])
    )
    results.append(
        (
            2,
            "PASS" if ok2 else "FAIL",
            {
                "beats": move2["action"] + " | " + move2["dialogue"],
                "detect_exit": det2,
                "tags": sorted(tags2),
                "present": list(m2.scene_state.present_characters),
                "offstage": list(m2.scene_state.offstage_characters),
            },
        )
    )

    # --- Scene 3 ---
    m3 = ContinuityManager()
    m3.initialize_scene("Dorm common", "Shared suite.", [R, Mo, J])
    move3 = {
        "action": (
            "walked through the door and started down the hall toward the vending machine, "
            "letting the suite door swing shut behind her"
        ),
        "dialogue": "I'm going to get snacks — be right back.",
        "motivation": _mot(goal="snacks", tactic="short errand"),
    }
    det3 = detect_exit_from_scene(move3, m3.scene_state.to_dict(), R)
    _turn(m3, R, move3, next_actor=Mo, others=[Mo, J])
    st = m3.scene_state.character_presence_status.get(R, "")
    ok3 = (
        det3
        and R not in m3.scene_state.present_characters
        and R in m3.scene_state.offstage_characters
        and st == "temporary_offstage"
        and R not in _pool(m3, [R, Mo, J])
    )
    results.append(
        (
            3,
            "PASS" if ok3 else "FAIL",
            {
                "beats": move3["dialogue"] + " | " + move3["action"],
                "detect_exit": det3,
                "present": list(m3.scene_state.present_characters),
                "offstage": list(m3.scene_state.offstage_characters),
                "status_Riley": st,
                "selectable_Riley": R in _pool(m3, [R, Mo, J]),
            },
        )
    )

    # --- Scene 4 (continue m3) ---
    move4 = {
        "action": (
            "came back in and walked back into the room with a bag of chips and set it on the table"
        ),
        "dialogue": "Got the chips.",
        "motivation": _mot(goal="return", tactic="rejoin"),
    }
    before_pool = _pool(m3, [R, Mo, J])
    re_before = has_scene_reentry_evidence(move4)
    _turn(m3, R, move4, next_actor=Mo, others=[Mo, J])
    after_pool = _pool(m3, [R, Mo, J])
    ok4 = (
        re_before
        and R in m3.scene_state.present_characters
        and R not in m3.scene_state.offstage_characters
        and R not in before_pool
        and R in after_pool
        and m3.scene_state.character_presence_status.get(R) == "onstage"
    )
    results.append(
        (
            4,
            "PASS" if ok4 else "FAIL",
            {
                "beats": move4["action"],
                "has_reentry_signal": re_before,
                "Riley_in_pool_before_turn": R in before_pool,
                "Riley_in_pool_after_turn": R in after_pool,
                "present": list(m3.scene_state.present_characters),
                "offstage": list(m3.scene_state.offstage_characters),
                "status_Riley": m3.scene_state.character_presence_status.get(R),
            },
        )
    )

    # --- Scene 5: address offstage (Riley off again) ---
    m5 = ContinuityManager()
    m5.initialize_scene("Dorm common", "Shared suite.", [R, Mo, J])
    _turn(
        m5,
        R,
        {
            "action": (
                "walked through the door and started down the hall toward the stairwell, "
                "letting the common room door swing shut behind her"
            ),
            "dialogue": "I need to take this call outside; be right back.",
            "motivation": _mot(goal="call", tactic="step out"),
        },
        next_actor=Mo,
        others=[Mo, J],
    )
    move5 = {
        "action": "stepped closer to the doorway",
        "dialogue": "Riley Chen, I am talking to you. Answer me.",
        "motivation": _mot(goal="press", tactic="direct address"),
    }
    pool_before = _pool(m5, [R, Mo, J])
    _turn(m5, Mo, move5, next_actor=J, others=[R, J])
    pool_after = _pool(m5, [R, Mo, J])
    orch = ensure_orchestration_state(None)
    orch["recent_structured_moves"] = [
        {"speaker": Mo, "action": move5["action"], "dialogue": move5["dialogue"], "motivation": move5["motivation"]}
    ]
    orch["spotlight_history"] = [Mo]
    cont = resolve_continuation_override_actor(
        orchestration_state=orch,
        continuity_manager=m5,
        eligible_participants=[n for n in [R, Mo, J] if n in (m5.scene_state.present_characters or [])],
        actors_used_this_round=[Mo],
    )
    ok5 = (
        R not in pool_after
        and R not in (m5.scene_state.present_characters or [])
        and R in m5.scene_state.offstage_characters
        and cont != R
    )
    results.append(
        (
            5,
            "PASS" if ok5 else "FAIL",
            {
                "beats": move5["dialogue"],
                "offstage": list(m5.scene_state.offstage_characters),
                "pool": pool_after,
                "continuation_override": cont,
                "note": "Full app: forced_speaker only applies if name in available_actors (audited).",
            },
        )
    )

    # --- Scene 6 & 7 ---
    m6 = ContinuityManager()
    Q, S, T = "Quinn_Host", "Sam_Visitor", "Taylor_Witness"
    m6.initialize_scene("Suite interior", "Living area.", [Q, S, T])
    m6.scene_state.location_entry_slots = ["suite_interior"]
    deny = {
        "action": "planted herself in the doorway, arms crossed",
        "dialogue": "Sam Visitor, you are not allowed in the suite interior. Stay in the hall.",
        "motivation": _mot(goal="deny entry", tactic="explicit ruling"),
        "scene_state_updates": {
            "location_entry_outcome": {
                "subject_id": S,
                "location_id": "suite_interior",
                "status": "denied",
            }
        },
    }
    _turn(m6, Q, deny, next_actor=S, others=[S, T])
    active_denied = _active_location_entry(m6, S, "suite_interior")
    attempt = {
        "action": "tried the interior handle again",
        "dialogue": "I need to grab my charger from inside.",
        "motivation": _mot(),
    }
    _turn(m6, S, attempt, next_actor=T, others=[Q, T])
    ref = {
        "action": "glanced between them",
        "dialogue": "Quinn already said Sam is not allowed in the suite interior.",
        "motivation": _mot(),
    }
    _turn(m6, T, ref, next_actor=Q, others=[Q, S])
    active_after = _active_location_entry(m6, S, "suite_interior")
    ok6 = (
        active_denied is not None
        and str(active_denied.value.get("status")) == "denied"
        and active_after is not None
        and active_after.outcome_id == active_denied.outcome_id
    )
    results.append(
        (
            6,
            "PASS" if ok6 else "FAIL",
            {
                "beats": deny["dialogue"][:80] + "… | later reference in Taylor line",
                "active_denial_status": getattr(active_after, "value", {}),
                "resolved_ids": [o.outcome_id for o in m6.resolved_outcomes[-4:]],
            },
        )
    )

    allow = {
        "action": "exhaled and stepped aside from the doorway",
        "dialogue": "Fine, she can come in.",
        "motivation": _mot(goal="relent", tactic="permission reversal"),
        "scene_state_updates": {
            "location_entry_outcome": {
                "subject_id": S,
                "location_id": "suite_interior",
                "status": "allowed",
            }
        },
    }
    _turn(m6, Q, allow, next_actor=S, others=[S, T])
    active_now = _active_location_entry(m6, S, "suite_interior")
    denied_superseded = (
        active_denied is not None and getattr(active_denied, "status", "") == "superseded"
    )
    ok7 = (
        active_now is not None
        and str(active_now.value.get("status")) == "allowed"
        and denied_superseded
    )
    results.append(
        (
            7,
            "PASS" if ok7 else "FAIL",
            {
                "beats": allow["dialogue"],
                "active_status": getattr(active_now, "value", {}),
                "prior_denial_superseded": denied_superseded,
            },
        )
    )

    # --- Scene 8 ---
    m8 = ContinuityManager()
    m8.initialize_scene("Dorm common", "Argument.", [R, Mo])
    move8 = {
        "action": "paced near the window without touching the door",
        "dialogue": (
            "I will be out in five. I will be right outside. Come out when you are done."
        ),
        "motivation": _mot(goal="pressure", tactic="wait"),
    }
    det8 = detect_exit_from_scene(move8, m8.scene_state.to_dict(), R)
    _turn(m8, R, move8, next_actor=Mo, others=[Mo])
    ok8 = not det8 and R in m8.scene_state.present_characters and R not in m8.scene_state.offstage_characters
    results.append(
        (
            8,
            "PASS" if ok8 else "FAIL",
            {
                "beats": move8["dialogue"],
                "detect_exit": det8,
                "present": list(m8.scene_state.present_characters),
                "offstage": list(m8.scene_state.offstage_characters),
            },
        )
    )

    # --- Scene 9A ---
    m9a = ContinuityManager()
    m9a.initialize_scene("X", "y", ["P_A", "P_B"])
    m9a.scene_state.role_assignments = {"P_A": "a", "P_B": "b"}
    m9a.scene_state.present_characters = []
    m9a.scene_state.offstage_characters = ["P_A"]
    m9a.scene_state.character_presence_status = {"P_A": "temporary_offstage", "P_B": "departed"}
    m9a._ensure_at_least_one_present_character()
    ok9a = m9a.scene_state.present_characters == ["P_A"] and "P_A" not in m9a.scene_state.offstage_characters

    results.append(
        (
            9,
            "PASS" if ok9a else "FAIL",
            {
                "variant": "A temporary_offstage restored",
                "present": list(m9a.scene_state.present_characters),
                "offstage": list(m9a.scene_state.offstage_characters),
            },
        )
    )

    # --- Scene 9B ---
    m9b = ContinuityManager()
    m9b.initialize_scene("X", "y", ["P_A", "P_B"])
    m9b.scene_state.role_assignments = {"P_A": "a", "P_B": "b"}
    m9b.scene_state.present_characters = []
    m9b.scene_state.offstage_characters = ["P_A", "P_B"]
    m9b.scene_state.character_presence_status = {"P_A": "departed", "P_B": "departed"}
    m9b._ensure_at_least_one_present_character()
    pool9b = _pool(m9b, ["P_A", "P_B"])
    ok9b = not m9b.scene_state.present_characters and pool9b == []
    results.append(
        (
            9,
            "PASS" if ok9b else "FAIL",
            {
                "variant": "B all departed — no restore, empty pool",
                "present": list(m9b.scene_state.present_characters),
                "offstage": list(m9b.scene_state.offstage_characters),
                "pool": pool9b,
            },
        )
    )

    # --- Scene 10 ---
    m10 = ContinuityManager()
    m10.initialize_scene("Dorm common", "Tense.", [R, Mo])
    m10.scene_state.character_presence_constraints[R] = "must_remain"
    move10 = {
        "action": (
            "slammed the door open and stormed across the room toward Morgan, "
            "still inside the shared space"
        ),
        "dialogue": "We are not finished.",
        "motivation": _mot(goal="confront", tactic="pressure", emotional_driver="rage"),
    }
    det10 = detect_exit_from_scene(move10, m10.scene_state.to_dict(), R)
    _turn(m10, R, move10, next_actor=Mo, others=[Mo])
    tags10 = _tags(m10)
    ok10 = (
        not det10
        and "exit" not in tags10
        and R in m10.scene_state.present_characters
        and R not in m10.scene_state.offstage_characters
        and R in _pool(m10, [R, Mo])
    )
    results.append(
        (
            10,
            "PASS" if ok10 else "FAIL",
            {
                "beats": move10["action"][:100] + "…",
                "detect_exit": det10,
                "tags": sorted(tags10),
                "present": list(m10.scene_state.present_characters),
                "offstage": list(m10.scene_state.offstage_characters),
                "pool_has_Riley": R in _pool(m10, [R, Mo]),
            },
        )
    )

    return results


def main() -> None:
    rows = run_all()

    print("## Presence scene audit (headless process_turn harness)\n")
    print(
        "_Note: Moves are authored structured JSON through `ContinuityManager.process_turn`, "
        "matching production ingestion after a character model returns a move. "
        "Live LLM generation for characters/director was not invoked in this run._\n"
    )

    for num, status, detail in rows:
        if num == 9:
            v = detail.get("variant", "")
            label = "Scene 9A" if v.startswith("A") else "Scene 9B"
        else:
            label = f"Scene {num}"
        _print_scene_block(label, status, detail)


def _print_scene_block(title: str, status: str, detail: dict) -> None:
    print(f"## {title} Result\n")
    print("### A. Outcome\n")
    print(f"* {status}\n")
    print("### B. Evidence\n")
    if "beats" in detail:
        print(f"* Scripted beat text: {detail['beats'][:320]}{'…' if len(str(detail.get('beats',''))) > 320 else ''}\n")
    for k in sorted(detail):
        if k == "beats":
            continue
        print(f"* `{k}`: {detail[k]}\n")
    print("### C. State verification\n")
    print("(See evidence keys: `present`, `offstage`, `tags`, `resolved_*`, `pool`.)\n")
    if status == "FAIL":
        print("### D. Root cause\n")
        print("* Inspect failing predicate in `scripts/run_presence_scene_audit.py` for this scene.\n")
        print("### E. Recommendation\n")
        print("* Scoped follow-up only if a predicate disagrees with product intent.\n")
    print()


if __name__ == "__main__":
    main()
