"""Issue #29 deterministic machine analysis over audited sessions (harness-only).

Does not classify root cause. Reads scenario JSON + character *_full.json under session_NNN.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from audit_support_manifest import diff_support_manifests
from character_move_adapters import format_move_for_legacy_audit_view
from progression_simulation_scenarios import load_scenario


def _continuity_bundle(ctx: dict[str, Any] | None) -> str:
    if not isinstance(ctx, dict):
        ctx = {}
    payload = {
        "continuity_event": ctx.get("continuity_event"),
        "scene_state_after": ctx.get("scene_state_after"),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def load_character_audit_rows(session_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(session_dir.rglob("*_full.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(data.get("bot_type", "") or "") != "character":
            continue
        msgs = data.get("input_messages") or []
        content = ""
        if msgs and isinstance(msgs[0], dict):
            content = str(msgs[0].get("content", "") or "")
        md = data.get("metadata")
        if not isinstance(md, dict):
            md = {}
        po = data.get("parsed_output")
        if not isinstance(po, dict):
            po = {}
        ctx = data.get("context_snapshot")
        if not isinstance(ctx, dict):
            ctx = {}
        rows.append(
            {
                "_path": path,
                "round_number": int(data.get("round_number", 0) or 0),
                "turn_number": int(data.get("turn_number", 0) or 0),
                "bot_name": str(data.get("bot_name", "") or ""),
                "content": content,
                "metadata": md,
                "parsed_output": po,
                "context_snapshot": ctx,
                "effective_user_trigger": str(
                    data.get("effective_user_trigger", "") or ""
                ),
            }
        )

    def sort_key(r: dict[str, Any]) -> tuple:
        return (r["round_number"], r["turn_number"], str(r["_path"]))

    rows.sort(key=sort_key)
    return rows


def _combined_move(po: dict[str, Any]) -> str:
    return format_move_for_legacy_audit_view(po)


def _prompt_has(row: dict[str, Any], token: str) -> bool:
    return token in row["content"]


def _manifest(row: dict[str, Any]) -> dict[str, Any] | None:
    sm = row["metadata"].get("support_manifest")
    return sm if isinstance(sm, dict) else None


def _establishment_indices(
    rows: list[dict[str, Any]], inv: dict[str, Any]
) -> list[int]:
    turns = inv.get("establishment_turn_numbers")
    if not isinstance(turns, list) or not turns:
        turns = [1, 2, 3]
    turns_set = {int(x) for x in turns if str(x).isdigit() or isinstance(x, int)}
    out: list[int] = []
    for i, r in enumerate(rows):
        if r["round_number"] == 1 and r["turn_number"] in turns_set:
            out.append(i)
    return out


def _baseline_index(rows: list[dict[str, Any]], est_idx: list[int]) -> int | None:
    if not est_idx:
        return None
    return est_idx[-1]


def _all_tokens_in_prompt(row: dict[str, Any], tokens: list[str]) -> bool:
    return all(_prompt_has(row, t) for t in tokens)


def _manifest_diff_non_envelope_only(diff: dict[str, Any]) -> bool:
    """True if absent/changed/new involves any unit type other than prompt_envelope."""

    def _types(entries: list) -> set[str]:
        out: set[str] = set()
        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("type"), str):
                out.add(e["type"])
        return out

    for key in ("support_absent", "support_new"):
        for t in _types(diff.get(key) or []):
            if t != "prompt_envelope":
                return True
    for e in diff.get("support_changed") or []:
        if isinstance(e, dict) and e.get("type") != "prompt_envelope":
            return True
    return False


def compute_t_sup(
    rows: list[dict[str, Any]],
    b_idx: int,
    tokens: list[str],
) -> dict[str, Any] | None:
    """First index t > b_idx where support drops vs previous character row or manifest diffs."""
    if b_idx < 0 or b_idx >= len(rows):
        return None
    for t in range(b_idx + 1, len(rows)):
        prev = rows[t - 1]
        cur = rows[t]
        for tok in tokens:
            if tok in prev["content"] and tok not in cur["content"]:
                return {
                    "index": t,
                    "round_number": cur["round_number"],
                    "turn_number": cur["turn_number"],
                    "bot_name": cur["bot_name"],
                    "path": str(cur["_path"]),
                    "reason": "token_dropped_consecutive",
                    "token": tok,
                }
        mp = _manifest(prev)
        mc = _manifest(cur)
        if mp is None or mc is None:
            return {
                "index": t,
                "round_number": cur["round_number"],
                "turn_number": cur["turn_number"],
                "bot_name": cur["bot_name"],
                "path": str(cur["_path"]),
                "reason": "missing_support_manifest",
                "diff": None,
            }
        d = diff_support_manifests(mp, mc)
        if _manifest_diff_non_envelope_only(d):
            return {
                "index": t,
                "round_number": cur["round_number"],
                "turn_number": cur["turn_number"],
                "bot_name": cur["bot_name"],
                "path": str(cur["_path"]),
                "reason": "support_manifest_diff_non_envelope",
                "diff": d,
            }
    return None


def _behavior_fail_negotiation(row: dict[str, Any], tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return True
    c = _combined_move(row["parsed_output"])
    return not (tokens[0] in c and tokens[1] in c)


def _behavior_fail_transformation(row: dict[str, Any], tokens: list[str]) -> bool:
    if not tokens:
        return True
    c = _combined_move(row["parsed_output"])
    if "FORM_RELEASE_ISSUE29" in c:
        return True
    return tokens[0] not in c


def _behavior_fail_object(row: dict[str, Any], tokens: list[str]) -> bool:
    uid = tokens[0] if tokens else ""
    alt = "OBJECT_ISSUE29_ALTKEY"
    c = _combined_move(row["parsed_output"])
    if uid and alt in c and uid in c:
        return True
    return uid not in c


def _behavior_fail_instruction(row: dict[str, Any], tokens: list[str]) -> bool:
    trig = row["effective_user_trigger"]
    c = _combined_move(row["parsed_output"])
    p = row["content"]
    failed = False
    if "PROBE_RED_ISSUE29" in trig:
        if "NO_RED_ACCESS" not in c:
            failed = True
        if "RULE_ISSUE29_NO_RED" not in p:
            failed = True
    if "PAYMENT_ISSUE29" in trig:
        if "RULE_ISSUE29_CODA_Q9" not in c:
            failed = True
        elif "payment" in c.lower() and c.find("RULE_ISSUE29_CODA_Q9") > c.lower().find(
            "payment"
        ):
            failed = True
    return failed


def _behavior_fail_cross_scene(row: dict[str, Any], tokens: list[str]) -> bool:
    if len(tokens) < 2:
        return True
    c = _combined_move(row["parsed_output"])
    return not (tokens[0] in c and tokens[1] in c)


def _behavior_fail_multi_thread(row: dict[str, Any], tokens: list[str]) -> bool:
    c = _combined_move(row["parsed_output"])
    return not all(t in c for t in tokens)


def compute_t_beh(
    rows: list[dict[str, Any]],
    b_idx: int,
    scenario_id: str,
    inv: dict[str, Any],
    tokens: list[str],
) -> dict[str, Any] | None:
    recall_turns = inv.get("recall_turn_numbers")
    if not isinstance(recall_turns, list):
        recall_turns = []
    recall_set = {int(x) for x in recall_turns if isinstance(x, int) or str(x).isdigit()}
    kind = str(inv.get("behavior_kind", "") or "")

    for t in range(b_idx + 1, len(rows)):
        row = rows[t]
        if row["turn_number"] not in recall_set:
            continue
        fail = False
        if kind == "negotiation_dual_token_recall":
            fail = _behavior_fail_negotiation(row, tokens)
        elif kind == "transformation_form_token_recall":
            fail = _behavior_fail_transformation(row, tokens)
        elif kind == "object_uid_recall":
            fail = _behavior_fail_object(row, tokens)
        elif kind == "instruction_probe_recall":
            fail = _behavior_fail_instruction(row, tokens)
        elif kind == "cross_scene_carry_recall":
            fail = _behavior_fail_cross_scene(row, tokens)
        elif kind == "multi_thread_recall":
            fail = _behavior_fail_multi_thread(row, tokens)
        else:
            continue
        if fail:
            return {
                "index": t,
                "round_number": row["round_number"],
                "turn_number": row["turn_number"],
                "bot_name": row["bot_name"],
                "path": str(row["_path"]),
                "behavior_kind": kind,
            }
    return None


def analyze_issue29_session(
    session_dir: Path,
    scenario_id: str,
) -> dict[str, Any]:
    session_dir = session_dir.resolve()
    raw = load_scenario(scenario_id)
    inv = raw.get("investigation")
    if not isinstance(inv, dict):
        inv = {}
    tokens = raw.get("investigation_anchor_tokens") or []
    if not isinstance(tokens, list):
        tokens = []
    tokens = [str(t).strip() for t in tokens if str(t).strip()]

    min_turns = int(inv.get("min_character_rows", 25) or 25)
    rows = load_character_audit_rows(session_dir)
    est = _establishment_indices(rows, inv)
    b_idx = _baseline_index(rows, est)

    integrity_support_manifest = all(
        isinstance(r["metadata"].get("support_manifest"), dict) for r in rows
    )

    baseline_valid = False
    baseline_reason = "no_establishment_rows"
    if b_idx is not None and tokens:
        baseline_valid = _all_tokens_in_prompt(rows[b_idx], tokens)
        if baseline_valid:
            baseline_reason = "baseline_row_has_all_tokens"
        else:
            baseline_reason = "baseline_row_missing_token"
    elif not tokens:
        baseline_reason = "no_anchor_tokens_in_scenario"

    any_establishment_has_all = False
    if tokens and est:
        for i in est:
            if _all_tokens_in_prompt(rows[i], tokens):
                any_establishment_has_all = True
                break
    if tokens and est and not any_establishment_has_all:
        baseline_valid = False
        baseline_reason = "establishment_phase_missing_tokens"

    incomplete = len(rows) < min_turns or not baseline_valid or b_idx is None

    t_sup = None
    t_beh = None
    if b_idx is not None and baseline_valid:
        t_sup = compute_t_sup(rows, b_idx, tokens)
        t_beh = compute_t_beh(rows, b_idx, scenario_id, inv, tokens)

    continuity_summary = {
        "rows_with_all_tokens_in_bundle": sum(
            1
            for r in rows
            if tokens
            and all(t in _continuity_bundle(r["context_snapshot"]) for t in tokens)
        ),
        "first_row_all_tokens_in_bundle": None,
    }
    for i, r in enumerate(rows):
        if tokens and all(
            t in _continuity_bundle(r["context_snapshot"]) for t in tokens
        ):
            continuity_summary["first_row_all_tokens_in_bundle"] = {
                "index": i,
                "turn_number": r["turn_number"],
                "bot_name": r["bot_name"],
            }
            break

    return {
        "scenario_id": scenario_id,
        "session_dir": str(session_dir),
        "min_character_rows_expected": min_turns,
        "character_rows": len(rows),
        "integrity_support_manifest_all_rows": integrity_support_manifest,
        "establishment_indices": est,
        "baseline_index": b_idx,
        "baseline_valid": baseline_valid,
        "baseline_reason": baseline_reason,
        "incomplete_run": incomplete,
        "incomplete_flags": {
            "row_count_below_min": len(rows) < min_turns,
            "baseline_invalid": not baseline_valid,
            "no_baseline_index": b_idx is None,
        },
        "T_sup": t_sup,
        "T_beh": t_beh,
        "anchor_tokens": tokens,
        "audit_glob": str(session_dir / "**" / "*_full.json"),
        "continuity_pairing_summary": continuity_summary,
    }


def parse_audit_session_from_stdout(text: str) -> int | None:
    m = re.search(
        r"\*\*Audit session:\*\*\s*`?(\d+)`?",
        text,
    )
    if m:
        return int(m.group(1))
    m2 = re.search(r'"audit_session_number":\s*(\d+)', text)
    if m2:
        return int(m2.group(1))
    return None
