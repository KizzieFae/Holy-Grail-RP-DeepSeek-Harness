#!/usr/bin/env python3
"""Headless A/B matrix for operational retrieval pilot (subprocess wrapper only; no runtime changes).

Runs ``run_scene_simulation_llm.py`` with retrieval OFF vs ON. Requires DEEPSEEK_API_KEY.

Uses ``env=os.environ.copy()`` and sets ``RP_RETRIEVED_CONTEXT_INDEX`` on the copy so the child
process reliably receives the index path (Windows-safe).

For every retrieval ON run, verifies audit ``*_full.json`` under the reported session contain
``RETRIEVED REFERENCE MATERIAL``, template role lines (``| scene_template]``), and a premise line
(``:premise | scene_template]``); aborts if not (invalid ON).

Phase 3a+: passes ``--scene-template-id`` per scenario so headless runs match template-aware pilot.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]
_INDEX = _PY / "data" / "retrieval" / "compiled" / "operational_pilot_v3.json"
_METRICS = _PY / "rp_app" / "data" / "pilot_evaluation_metrics"
_AUDITS = _PY / "rp_app" / "data" / "rp_audits"

_RETRIEVAL_MARKER = "RETRIEVED REFERENCE MATERIAL"
_SCENE_TEMPLATE_TAG = "| scene_template]"
_PREMISE_REF = ":premise | scene_template]"


def _audit_session_dir(session_number: int) -> Path:
    return _AUDITS / f"session_{int(session_number):d}"


def verify_retrieval_active_in_audits(session_number: int) -> tuple[bool, str]:
    """True if a character ``*_full.json`` has retrieval, template lines, and premise chunk."""
    d = _audit_session_dir(session_number)
    if not d.is_dir():
        return False, f"audit dir missing: {d}"
    for p in sorted(d.rglob("*_full.json")):
        if "director" in p.name.lower() or "narrator" in p.name.lower():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"read failed {p}: {e}"
        if (
            _RETRIEVAL_MARKER in text
            and _SCENE_TEMPLATE_TAG in text
            and _PREMISE_REF in text
        ):
            return True, str(p.relative_to(_PY))
    return (
        False,
        f"no character *_full.json with retrieval + template + {_PREMISE_REF!r} under {d}",
    )


def _run_one(
    *,
    label: str,
    retrieval_on: bool,
    chars: str,
    opening: str,
    location: str,
    trigger: str,
    turns: int,
    episodic: bool,
    scene_template_id: str,
) -> None:
    env = os.environ.copy()
    if retrieval_on:
        env["RP_RETRIEVED_CONTEXT_INDEX"] = str(_INDEX.resolve())
    else:
        env.pop("RP_RETRIEVED_CONTEXT_INDEX", None)
    if episodic:
        env["RP_EPISODIC_MEMORY"] = "1"
    else:
        env.pop("RP_EPISODIC_MEMORY", None)

    out = _METRICS / f"{label}.json"
    cmd = [
        sys.executable,
        str(_PY / "scripts" / "run_scene_simulation_llm.py"),
        "--chars",
        chars,
        "--scene-template-id",
        scene_template_id,
        "--opening",
        opening,
        "--location",
        location,
        "--trigger",
        trigger,
        "--turns",
        str(turns),
        "--audit",
        "--no-deep-simulation-turns",
        "--metrics-out",
        str(out),
    ]
    if episodic:
        cmd.append("--episodic-memory")
    print(
        f"\n=== {label} retrieval={'ON' if retrieval_on else 'OFF'} "
        f"episodic={'ON' if episodic else 'OFF'} template={scene_template_id!r} ===",
        flush=True,
    )
    subprocess.run(cmd, cwd=str(_PY), env=env, check=True)

    if retrieval_on:
        raw = json.loads(out.read_text(encoding="utf-8"))
        sn = raw.get("audit_session_number")
        if sn is None:
            print("ERROR: metrics missing audit_session_number; cannot verify ON run.", file=sys.stderr)
            raise SystemExit(1)
        ok, detail = verify_retrieval_active_in_audits(int(sn))
        if not ok:
            print(f"ERROR: retrieval ON run INVALID (session {sn}): {detail}", file=sys.stderr)
            raise SystemExit(1)
        print(f"  verified: {_RETRIEVAL_MARKER} in {detail}", flush=True)


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        return 1
    if not _INDEX.is_file():
        print(f"Missing index: {_INDEX}", file=sys.stderr)
        return 1
    _METRICS.mkdir(parents=True, exist_ok=True)

    s1_opening = (
        "Steel door shut behind the new arrival in Arkham's female ward cell. "
        "Fluorescent buzz, stained walls; an established inmate owns the floor space with her eyes. "
        "Staff footsteps fade down the hall."
    )
    s1_trigger = (
        "The new arrival presses to the wall. The established inmate grins and says, "
        "'You're in my room now, Bright Eyes—don't faint on me.'"
    )

    s2_opening = (
        "Evening meal in Arkham's female ward cafeteria: trays, surveillance, and resentment. "
        "Harley and Ivy are one wrong word from a public blowup; Magpie hovers at the edge, "
        "attention snagging on anything shiny."
    )
    s2_trigger = (
        "Harley laughs sharp and too loud. Ivy's voice drops to something venomous and intimate. "
        "Magpie whispers, 'Don't look at me like that,' but nobody's sure who she means."
    )

    s3_opening = (
        "Medication line in Arkham's female ward: nurses call names from a chart; linoleum and wet-cleaner smell. "
        "Everyone has been told: single file, hands visible, no trading pills."
    )
    s3_trigger = (
        "A nurse misreads a name; Harley corrects her with mock sweetness. Ivy murmurs, 'Facts matter today.' "
        "Magpie clutches a plastic cup like it's jewelry."
    )

    tpl_intake = "arkham_asylum_cell_intake"
    tpl_cafeteria = "arkham_asylum_mess_hall_arena"

    matrix = [
        (
            "tuned_S1_2char_r1_OFF",
            "tuned_S1_2char_r1_ON",
            "harley_quinn,magpie",
            s1_opening,
            "arkham_female_ward_cell",
            s1_trigger,
            tpl_intake,
        ),
        (
            "tuned_S2_3char_r1_OFF",
            "tuned_S2_3char_r1_ON",
            "harley_quinn,poison_ivy,magpie",
            s2_opening,
            "arkham_cafeteria",
            s2_trigger,
            tpl_cafeteria,
        ),
        (
            "tuned_S3_ground_r1_OFF",
            "tuned_S3_ground_r1_ON",
            "harley_quinn,poison_ivy,magpie",
            s3_opening,
            "arkham_med_line",
            s3_trigger,
            tpl_intake,
        ),
    ]

    turns = 3
    for off_l, on_l, chars, op, loc, tr, tid in matrix:
        _run_one(
            label=off_l,
            retrieval_on=False,
            chars=chars,
            opening=op,
            location=loc,
            trigger=tr,
            turns=turns,
            episodic=False,
            scene_template_id=tid,
        )
        _run_one(
            label=on_l,
            retrieval_on=True,
            chars=chars,
            opening=op,
            location=loc,
            trigger=tr,
            turns=turns,
            episodic=False,
            scene_template_id=tid,
        )

    matrix2 = [
        (
            "tuned_S1_2char_r2_OFF",
            "tuned_S1_2char_r2_ON",
            "harley_quinn,magpie",
            s1_opening,
            "arkham_female_ward_cell",
            s1_trigger,
            tpl_intake,
        ),
        (
            "tuned_S2_3char_r2_OFF",
            "tuned_S2_3char_r2_ON",
            "harley_quinn,poison_ivy,magpie",
            s2_opening,
            "arkham_cafeteria",
            s2_trigger,
            tpl_cafeteria,
        ),
        (
            "tuned_S3_ground_r2_OFF",
            "tuned_S3_ground_r2_ON",
            "harley_quinn,poison_ivy,magpie",
            s3_opening,
            "arkham_med_line",
            s3_trigger,
            tpl_intake,
        ),
    ]
    for off_l, on_l, chars, op, loc, tr, tid in matrix2:
        _run_one(
            label=off_l,
            retrieval_on=False,
            chars=chars,
            opening=op,
            location=loc,
            trigger=tr,
            turns=turns,
            episodic=False,
            scene_template_id=tid,
        )
        _run_one(
            label=on_l,
            retrieval_on=True,
            chars=chars,
            opening=op,
            location=loc,
            trigger=tr,
            turns=turns,
            episodic=False,
            scene_template_id=tid,
        )

    _run_one(
        label="tuned_S1_2char_epi_r1_OFF",
        retrieval_on=False,
        chars="harley_quinn,magpie",
        opening=s1_opening,
        location="arkham_female_ward_cell",
        trigger=s1_trigger,
        turns=turns,
        episodic=True,
        scene_template_id=tpl_intake,
    )
    _run_one(
        label="tuned_S1_2char_epi_r1_ON",
        retrieval_on=True,
        chars="harley_quinn,magpie",
        opening=s1_opening,
        location="arkham_female_ward_cell",
        trigger=s1_trigger,
        turns=turns,
        episodic=True,
        scene_template_id=tpl_intake,
    )

    print("\nDone. Metrics under", _METRICS, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
