#!/usr/bin/env python3
"""Full pipeline scene simulation with the same LLM calls as Streamlit (Director + cast + Narrator).

Uses fixed **scenarios** (``rp_app/data/progression_simulation_scenarios/*.json``) for controlled
experiments, or ad-hoc CLI flags. With ``--audit``, writes the same JSON audit trail as the app
under ``rp_app/data/rp_audits/``.

Requires ``DEEPSEEK_API_KEY``.

From ``autogen_rp/python``::

    python scripts/run_scene_simulation_llm.py --list-scenarios
    python scripts/run_scene_simulation_llm.py --scenario arrival_setup --turns 3
    python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --audit --turns 6
    # Continuity-backed episodic recall in character prompts (requires flag or RP_EPISODIC_MEMORY=1):
    python scripts/run_scene_simulation_llm.py --scenario arrival_setup --audit --turns 2 --episodic-memory
    # Scenario runs use deep simulation by default (full max_turns, repeat speakers). Match UI cap:
    python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --no-deep-simulation-turns
    python scripts/run_scene_simulation_llm.py --chars ayame,celina --beat-shift --turns 3 --audit
    # Template-linked retrieval (sets Continuity scene_template_id; same field as Streamlit):
    python scripts/run_scene_simulation_llm.py --scenario headless_template_retrieval_smoke --audit --turns 1
    python scripts/run_scene_simulation_llm.py --chars harley_quinn,magpie --scene-template-id arkham_asylum_cell_intake --audit --turns 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from headless_scene_simulation import (  # noqa: E402
    format_simulation_audit_markdown,
    prepare_headless_session,
    run_headless_llm_scene,
)
from progression_run_metrics import FAILURE_CLASSIFICATIONS  # noqa: E402
from progression_simulation_scenarios import (  # noqa: E402
    audit_owner_slug,
    list_scenario_ids,
    load_scenario,
    scenario_prepare_kwargs,
)


def _configure_stdout_utf8() -> None:
    """Best-effort UTF-8 for stdout so audit markdown prints correctly (e.g. Windows cp1252)."""
    out = sys.stdout
    enc = (getattr(out, "encoding", None) or "").lower().replace("_", "-")
    if enc in ("utf-8", "utf8"):
        return
    reconfigure = getattr(out, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8")
    except (OSError, ValueError, TypeError, AttributeError):
        pass


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run headless LLM scene simulation (production turn runner + optional audit JSON)."
    )
    p.add_argument(
        "--scenario",
        metavar="ID",
        help="Use a fixed scenario from data/progression_simulation_scenarios/<ID>.json",
    )
    p.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print scenario ids and exit.",
    )
    p.add_argument(
        "--chars",
        default=None,
        help="Comma-separated character card ids (ad-hoc mode; ignored if --scenario is set).",
    )
    p.add_argument(
        "--turns",
        type=int,
        default=None,
        help="Max successful character turns (default: scenario max_turns or 2).",
    )
    p.add_argument(
        "--trigger",
        default=None,
        help="User trigger text (default: scenario or built-in standoff line).",
    )
    p.add_argument("--user-name", default="Traveler", help="User display name for prompts.")
    p.add_argument(
        "--opening",
        default=None,
        help="Opening description (ad-hoc only).",
    )
    p.add_argument("--location", default=None, help="Continuity location (ad-hoc only).")
    p.add_argument(
        "--scene-template-id",
        default=None,
        metavar="ID",
        help=(
            "Set Continuity scene_template_id for template-linked authored retrieval "
            "(ad-hoc only; scenarios may set scene_template_id in JSON)."
        ),
    )
    p.add_argument(
        "--beat-shift",
        action="store_true",
        help="Activate pending beat-shift before the round (ad-hoc only).",
    )
    p.add_argument(
        "--no-seed-issue",
        action="store_true",
        help="Do not inject escalating issue (ad-hoc only).",
    )
    p.add_argument(
        "--audit",
        action="store_true",
        help="Enable audit logging to rp_app/data/rp_audits/ (same as Streamlit with auditing on).",
    )
    p.add_argument(
        "--episodic-memory",
        action="store_true",
        help=(
            "Set RP_EPISODIC_MEMORY=1 for this process and pass enable_episodic_memory to headless "
            "prepare so character prompts include merged episodic lines in RETRIEVED REFERENCE "
            "(continuity-backed; visibility must match turn-runner character keys)."
        ),
    )
    p.add_argument(
        "--no-progression-enforcement",
        action="store_true",
        help="Baseline run: disable progression gate/retry and MED->HIGH override (compare vs default).",
    )
    p.add_argument(
        "--arch-quality-variant",
        choices=("baseline", "a1", "b", "c"),
        default="baseline",
        help=(
            "Architecture-quality harness only: session_state arch_quality_variant for headless runs "
            "(A1 director prefix ablation, B no character progression suffix, C no progression override). "
            "See SCENARIO_VALIDATION_FRAMEWORK.md / arch_quality_variants.py."
        ),
    )
    p.add_argument(
        "--verdict",
        choices=("PASS", "FAIL", "WARN"),
        default=None,
        help="Manual checklist verdict (optional; included in structured JSON).",
    )
    p.add_argument(
        "--failure-class",
        dest="failure_class",
        choices=sorted(FAILURE_CLASSIFICATIONS),
        default=None,
        metavar="CLASS",
        help="Required with --verdict FAIL or WARN: contract|gate|selection|retry|continuity|other",
    )
    p.add_argument(
        "--metrics-out",
        type=Path,
        default=None,
        help="Write structured_eval JSON to this file (UTF-8).",
    )
    p.add_argument(
        "--deep-simulation-turns",
        action="store_true",
        help=(
            "Headless only: honor --turns / scenario max_turns fully and allow the same cast "
            "to speak multiple times in one simulated user round. Default when using --scenario."
        ),
    )
    p.add_argument(
        "--no-deep-simulation-turns",
        action="store_true",
        help=(
            "Headless only: cap at one successful turn per bot per user round (Streamlit-style). "
            "Overrides default deep mode for --scenario."
        ),
    )
    args = p.parse_args()
    _configure_stdout_utf8()

    if args.verdict in ("FAIL", "WARN") and not args.failure_class:
        p.error("--failure-class is required when --verdict is FAIL or WARN")
    if args.failure_class and args.verdict not in ("FAIL", "WARN"):
        p.error("--failure-class is only valid with --verdict FAIL or WARN")

    if args.list_scenarios:
        for sid in list_scenario_ids():
            print(sid)
        return

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set; cannot run live LLM simulation.", file=sys.stderr)
        sys.exit(1)

    if args.episodic_memory:
        os.environ["RP_EPISODIC_MEMORY"] = "1"

    default_trigger = "The standoff has looped on talk; something has to give."
    default_opening = "Two people face off in a cramped corridor; neither will back down first."

    if args.scenario:
        raw = load_scenario(args.scenario)
        prep_kw = scenario_prepare_kwargs(raw)
        audit_owner = audit_owner_slug(raw["id"])
        max_turns = int(args.turns) if args.turns is not None else int(raw["max_turns"])
        trigger_text = args.trigger if args.trigger is not None else str(raw["trigger_text"])
        if args.no_deep_simulation_turns and args.deep_simulation_turns:
            p.error("Use only one of --deep-simulation-turns and --no-deep-simulation-turns")
        deep_turns = not args.no_deep_simulation_turns
        st = prepare_headless_session(
            **prep_kw,
            audit_enabled=args.audit,
            audit_session_owner=audit_owner,
            progression_enforcement_disabled=args.no_progression_enforcement,
            arch_quality_variant=args.arch_quality_variant,
            deep_simulation_turns=deep_turns,
            enable_episodic_memory=args.episodic_memory,
        )
    else:
        ids = [x.strip() for x in (args.chars or "ayame,celina").split(",") if x.strip()]
        max_turns = int(args.turns) if args.turns is not None else 2
        trigger_text = args.trigger if args.trigger is not None else default_trigger
        if args.no_deep_simulation_turns and args.deep_simulation_turns:
            p.error("Use only one of --deep-simulation-turns and --no-deep-simulation-turns")
        deep_turns = bool(args.deep_simulation_turns)
        adhoc_tpl = str(args.scene_template_id or "").strip() or None
        st = prepare_headless_session(
            character_card_ids=ids,
            opening_description=args.opening or default_opening,
            location=args.location or "corridor",
            seed_escalating_issue=not args.no_seed_issue,
            beat_shift_active=args.beat_shift,
            audit_enabled=args.audit,
            audit_session_owner="headless_adhoc",
            progression_enforcement_disabled=args.no_progression_enforcement,
            arch_quality_variant=args.arch_quality_variant,
            deep_simulation_turns=deep_turns,
            enable_episodic_memory=args.episodic_memory,
            scene_template_id=adhoc_tpl,
        )

    async def _run() -> None:
        try:
            result = await run_headless_llm_scene(
                st_module=st,
                max_turns=max_turns,
                trigger_text=trigger_text,
                user_name=args.user_name,
                verdict=args.verdict,
                failure_classification=args.failure_class,
            )
            print(format_simulation_audit_markdown(result))
            if args.metrics_out is not None and result.structured_eval is not None:
                args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
                args.metrics_out.write_text(
                    json.dumps(result.structured_eval, indent=2, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
        finally:
            mc = st.session_state.get("model_client")
            if mc is not None and hasattr(mc, "close"):
                await mc.close()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
