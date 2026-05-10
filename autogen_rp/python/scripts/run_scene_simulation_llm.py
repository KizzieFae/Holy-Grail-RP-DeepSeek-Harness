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
    python scripts/run_scene_simulation_llm.py --chars ayame,celina --audit --llm-audit --turns 1 --no-deep-simulation-turns
    # Continuity-backed episodic recall in character prompts (requires flag or RP_EPISODIC_MEMORY=1):
    python scripts/run_scene_simulation_llm.py --scenario arrival_setup --audit --turns 2 --episodic-memory
    # Scenario runs use deep simulation by default (full max_turns, repeat speakers). Match UI cap:
    python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --no-deep-simulation-turns
    python scripts/run_scene_simulation_llm.py --chars ayame,celina --beat-shift --turns 3 --audit
    # Template-linked retrieval (sets Continuity scene_template_id; same field as Streamlit):
    python scripts/run_scene_simulation_llm.py --scenario headless_template_retrieval_smoke --audit --turns 1
    python scripts/run_scene_simulation_llm.py --chars harley_quinn,magpie --scene-template-id arkham_asylum_cell_intake --scene-template-roles harley_quinn=cell_resident,magpie=new_arrival --audit --turns 1
    # After an audited run, optional offline fact-track (GitHub #62; explicit fact_spec only):
    # python scripts/run_scene_simulation_llm.py --scenario arrival_setup --audit --turns 1 --fact-spec path/to/spec.json
    # Authored retrieval ON/OFF (sets RP_RETRIEVED_CONTEXT_INDEX for this process; omit flag to leave env unchanged):
    python scripts/run_scene_simulation_llm.py --scenario headless_template_retrieval_smoke --audit --turns 1 --retrieved-context-index data/retrieval/compiled/operational_pilot_v3.json
    python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --audit --turns 1 --retrieved-context-index
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

from audit_fact_tracking import run_fact_track_postprocess  # noqa: E402
from headless_scene_simulation import (  # noqa: E402
    format_simulation_audit_markdown,
    prepare_headless_session,
    run_headless_llm_scene,
)
from progression_run_metrics import FAILURE_CLASSIFICATIONS  # noqa: E402
from progression_simulation_scenarios import (  # noqa: E402
    audit_owner_slug,
    effective_round1_trigger_text_headless,
    list_scenario_ids,
    load_scenario,
    parse_cli_scene_template_role_assignments,
    scenario_prepare_kwargs,
)
from user_trigger_schedule import (  # noqa: E402
    UserTriggerScheduleError,
    load_user_trigger_schedule,
    make_resolve_effective_user_trigger,
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
        help=(
            "Override round-1 user trigger. If omitted: ad-hoc uses finalized opening; "
            "scenarios use startup_trigger_mode (parity → opening, overlay → manifest trigger)."
        ),
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
            "(ad-hoc only; scenarios may set scene_template_id in JSON). "
            "Requires --scene-template-roles."
        ),
    )
    p.add_argument(
        "--scene-template-roles",
        default=None,
        metavar="MAP",
        help=(
            "Ad-hoc only, required with --scene-template-id: comma-separated card=role "
            "assignments (Issue #80). Example: harley_quinn=cell_resident,magpie=new_arrival"
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
        "--llm-audit",
        action="store_true",
        help=(
            "Enable Audit V2 LLM advisory passes (requires --audit). Same as session "
            "llm_audit_enabled in the app; runs sync LLM calls when escalation qualifies."
        ),
    )
    p.add_argument(
        "--retrieved-context-index",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help=(
            "Set RP_RETRIEVED_CONTEXT_INDEX before session setup (authored retrieval). "
            "Omit this flag entirely to leave the environment unchanged. "
            "Pass --retrieved-context-index alone (no PATH) to force retrieval OFF (empty index). "
            "Otherwise pass the compiled JSON path (e.g. data/retrieval/compiled/operational_pilot_v3.json)."
        ),
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
        "--fact-spec",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "After an audited run, load fact_spec.v1 JSON and write a companion fact-track "
            "artifact under the audit session directory via run_fact_track_postprocess (requires "
            "--audit). GitHub #62; no merge into _audit_summary.json."
        ),
    )
    p.add_argument(
        "--fact-track-out",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Optional explicit path for fact-track companion JSON (UTF-8). Requires "
            "--fact-spec. Default naming is under the session directory."
        ),
    )
    p.add_argument(
        "--user-trigger-schedule",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Optional JSON file: per-orchestration-turn user trigger overrides (headless harness). "
            "Validated before the run; see user_trigger_schedule / Issue tracking docs."
        ),
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
    p.add_argument(
        "--ignore-end-round",
        action="store_true",
        help=(
            "Headless only, Issue #29 scenarios (investigate_i29_*): do not stop the character loop "
            "when the Director returns end_round. If next_actor is empty, use the first available "
            "actor. Normal Streamlit sessions ignore this flag. Prefer --issue29-long-run-harness "
            "for full Issue #29 durability harness (includes this behavior)."
        ),
    )
    p.add_argument(
        "--issue29-long-run-harness",
        action="store_true",
        help=(
            "Headless only, Issue #29 scenarios (investigate_i29_*): enable issue29_long_run_harness "
            "(synthetic available_actors when pool is empty, Director stalemate fallback, and "
            "ignore end_round). Investigation-only; does not change continuity or Streamlit."
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

    if args.llm_audit and not args.audit:
        p.error("--llm-audit requires --audit")
    if args.fact_spec is not None and not args.audit:
        p.error("--fact-spec requires --audit")
    if args.fact_track_out is not None and args.fact_spec is None:
        p.error("--fact-track-out requires --fact-spec")

    _issue29_prefix = "investigate_i29_"
    if args.ignore_end_round:
        if not args.scenario:
            p.error("--ignore-end-round requires --scenario")
        if not str(args.scenario).startswith(_issue29_prefix):
            p.error(
                "--ignore-end-round is only allowed for Issue #29 scenarios "
                f"(scenario id must start with {_issue29_prefix!r})"
            )
    if args.issue29_long_run_harness:
        if not args.scenario:
            p.error("--issue29-long-run-harness requires --scenario")
        if not str(args.scenario).startswith(_issue29_prefix):
            p.error(
                "--issue29-long-run-harness is only allowed for Issue #29 scenarios "
                f"(scenario id must start with {_issue29_prefix!r})"
            )

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set; cannot run live LLM simulation.", file=sys.stderr)
        sys.exit(1)

    if args.episodic_memory:
        os.environ["RP_EPISODIC_MEMORY"] = "1"

    if args.retrieved_context_index is not None:
        os.environ["RP_RETRIEVED_CONTEXT_INDEX"] = args.retrieved_context_index

    default_trigger = "The standoff has looped on talk; something has to give."
    default_opening = "Two people face off in a cramped corridor; neither will back down first."

    raw_scenario: dict | None = None
    if args.scenario:
        raw_scenario = load_scenario(args.scenario)
        max_turns = (
            int(args.turns)
            if args.turns is not None
            else int(raw_scenario["max_turns"])
        )
        built_in_fallback = str(raw_scenario["trigger_text"])
    else:
        max_turns = int(args.turns) if args.turns is not None else 2
        built_in_fallback = default_trigger

    cli_trigger_provided = args.trigger is not None
    cli_trigger_value = args.trigger if cli_trigger_provided else ""
    trigger_text = cli_trigger_value if cli_trigger_provided else built_in_fallback

    get_effective_user_trigger = None
    if args.user_trigger_schedule is not None:
        try:
            by_turn, json_default = load_user_trigger_schedule(
                args.user_trigger_schedule,
                max_orchestration_turn=max_turns,
            )
        except UserTriggerScheduleError as exc:
            print(f"user trigger schedule: {exc}", file=sys.stderr)
            sys.exit(1)
        get_effective_user_trigger = make_resolve_effective_user_trigger(
            by_turn,
            cli_trigger_provided=cli_trigger_provided,
            cli_trigger_value=cli_trigger_value,
            json_default=json_default,
            built_in_fallback=built_in_fallback,
        )

    cli_for_bootstrap_composition: str | None = None
    if get_effective_user_trigger is None and cli_trigger_provided:
        cli_for_bootstrap_composition = str(cli_trigger_value).strip() or None

    if args.scenario:
        assert raw_scenario is not None
        raw = raw_scenario
        prep_kw = scenario_prepare_kwargs(raw)
        audit_owner = audit_owner_slug(raw["id"])
        if args.no_deep_simulation_turns and args.deep_simulation_turns:
            p.error("Use only one of --deep-simulation-turns and --no-deep-simulation-turns")
        deep_turns = not args.no_deep_simulation_turns
        st = prepare_headless_session(
            **prep_kw,
            user_name=args.user_name,
            audit_enabled=args.audit,
            llm_audit_enabled=args.llm_audit,
            audit_session_owner=audit_owner,
            progression_enforcement_disabled=args.no_progression_enforcement,
            arch_quality_variant=args.arch_quality_variant,
            deep_simulation_turns=deep_turns,
            enable_episodic_memory=args.episodic_memory,
            ignore_director_end_round=bool(args.ignore_end_round),
            issue29_long_run_harness=bool(args.issue29_long_run_harness),
            scenario_raw=raw,
            cli_trigger_for_composition=cli_for_bootstrap_composition,
        )
    else:
        ids = [x.strip() for x in (args.chars or "ayame,celina").split(",") if x.strip()]
        if args.no_deep_simulation_turns and args.deep_simulation_turns:
            p.error("Use only one of --deep-simulation-turns and --no-deep-simulation-turns")
        deep_turns = bool(args.deep_simulation_turns)
        adhoc_tpl = str(args.scene_template_id or "").strip() or None
        try:
            adhoc_roles = parse_cli_scene_template_role_assignments(args.scene_template_roles)
        except ValueError as exc:
            p.error(str(exc))
        if adhoc_tpl and not adhoc_roles:
            p.error(
                "--scene-template-id requires --scene-template-roles in ad-hoc mode "
                "(Issue #80); e.g. harley_quinn=cell_resident,magpie=new_arrival"
            )
        if adhoc_roles and not adhoc_tpl:
            p.error("--scene-template-roles requires --scene-template-id")
        st = prepare_headless_session(
            character_card_ids=ids,
            opening_description=args.opening or default_opening,
            location=args.location or "corridor",
            user_name=args.user_name,
            seed_escalating_issue=not args.no_seed_issue,
            beat_shift_active=args.beat_shift,
            audit_enabled=args.audit,
            llm_audit_enabled=args.llm_audit,
            audit_session_owner="headless_adhoc",
            progression_enforcement_disabled=args.no_progression_enforcement,
            arch_quality_variant=args.arch_quality_variant,
            deep_simulation_turns=deep_turns,
            enable_episodic_memory=args.episodic_memory,
            scene_template_id=adhoc_tpl,
            scene_template_role_assignments=adhoc_roles if adhoc_roles else None,
            scenario_raw=None,
            cli_trigger_for_composition=cli_for_bootstrap_composition,
        )

    opening_for_trigger = str(
        st.session_state.get("simulation_opening_final") or ""
    ).strip()
    if get_effective_user_trigger is None:
        composed = str(
            st.session_state.get("first_round_user_line_composed") or ""
        ).strip()
        if composed:
            trigger_text = composed
        else:
            trigger_text = effective_round1_trigger_text_headless(
                scenario_raw=raw_scenario,
                simulation_opening_final=opening_for_trigger,
                adhoc_fallback_trigger=default_trigger,
                cli_trigger_provided=cli_trigger_provided,
                cli_trigger_value=cli_trigger_value,
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
                get_effective_user_trigger=get_effective_user_trigger,
            )
            print(format_simulation_audit_markdown(result))
            if args.metrics_out is not None and result.structured_eval is not None:
                args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
                args.metrics_out.write_text(
                    json.dumps(result.structured_eval, indent=2, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
            if args.fact_spec is not None:
                spec_file = args.fact_spec.resolve()
                if not spec_file.is_file():
                    print(f"--fact-spec not a file: {spec_file}", file=sys.stderr)
                    sys.exit(1)
                try:
                    loaded = json.loads(spec_file.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    print(f"--fact-spec: failed to read JSON: {exc}", file=sys.stderr)
                    sys.exit(1)
                if not isinstance(loaded, dict):
                    print("--fact-spec: root JSON value must be an object", file=sys.stderr)
                    sys.exit(1)
                summary_path = result.audit_summary_report_path
                if not summary_path:
                    print(
                        "--fact-spec requires an audit session with audit_summary_report_path "
                        "(enable --audit and ensure the run produced a summary).",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                session_dir = Path(summary_path).resolve().parent
                if args.fact_track_out is not None:
                    run_fact_track_postprocess(
                        session_dir,
                        loaded,
                        companion_path=args.fact_track_out,
                    )
                else:
                    run_fact_track_postprocess(session_dir, loaded)
        finally:
            mc = st.session_state.get("model_client")
            if mc is not None and hasattr(mc, "close"):
                await mc.close()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
