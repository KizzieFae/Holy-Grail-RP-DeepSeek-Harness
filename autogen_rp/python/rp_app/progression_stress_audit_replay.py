"""Offline replay for Progression Stress Audit (approved design).

Computes IS-1, IS-2, IS-3, FP-1, FP-2, beat-shift windows A/B, and E1–E5 from
existing character *_full.json audits, optional run.log, and structured_eval JSON.

Does not mutate runtime; deterministic given inputs.

Beat-shift **CTK_consume** (when not overridden): heuristic = ``CTK_first(R_arm)``
(first character row in the armed user round). Logs must still contain both arm and
consume lines for ``beat_shift.status == "ok"``. E4 uses ``progression_retry`` rows
from ``sim_progression_metrics_events`` when present (falls back to 0).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Match progression_enforcement (exact token match on normalized consequence string)
_PRESENCE_MARKERS = frozenset({"exit", "arrival"})
_ALLOWED_SCENE_STATE_KEYS = frozenset(
    {
        "sleeping_surface_assignment",
        "housing_call_outcome",
        "suppressant_formulation_outcome",
        "location_entry_outcome",
    }
)

IS1_TAU = 0.90
WINDOW_W = 3

_ARM_RE = re.compile(
    r"\[beat_shift\]\s+set active reason=progression_stall.*?source_turn_id=user_round_(\d+)",
    re.IGNORECASE | re.DOTALL,
)
_CONSUME_RE = re.compile(r"\[beat_shift\]\s+consumed and cleared", re.IGNORECASE)


def collapse_whitespace_only(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def normalize_for_similarity(s: str) -> str:
    """Lowercase, strip, non-alphanumeric -> space, collapse spaces (audit spec)."""
    raw = str(s or "").lower()
    out: list[str] = []
    prev_space = True
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            prev_space = False
        else:
            if not prev_space:
                out.append(" ")
            prev_space = True
    return " ".join("".join(out).split())


def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def similarity_sim(a: str, b: str) -> float:
    na, nb = normalize_for_similarity(a), normalize_for_similarity(b)
    if len(na) == 0 and len(nb) == 0:
        return 1.0
    lmax = max(len(na), len(nb))
    d = levenshtein_distance(na, nb)
    return 1.0 - (d / lmax)


def motivation_sig(motivation: Any) -> str:
    if isinstance(motivation, dict):
        return json.dumps(motivation, sort_keys=True, ensure_ascii=True)
    return ""


def normalized_consequences(meta: dict[str, Any]) -> list[str]:
    raw = meta.get("consequences", [])
    if not isinstance(raw, list):
        return []
    return [str(c).strip() for c in raw if str(c or "").strip()]


def q3_from_consequences(cons: list[str]) -> bool:
    for c in cons:
        if str(c).strip().lower() in _PRESENCE_MARKERS:
            return True
    return False


def q4_from_move(move: dict[str, Any]) -> bool:
    raw = move.get("scene_state_updates")
    if not isinstance(raw, dict):
        return False
    for key in raw.keys():
        k = str(key or "").strip()
        if k in _ALLOWED_SCENE_STATE_KEYS:
            return True
    return False


def find_prev_same_speaker_move(
    speaker: str,
    prior_moves: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    sp = str(speaker or "").strip()
    for spk, mv in reversed(prior_moves):
        if str(spk or "").strip() == sp:
            return mv
    return None


def compute_is1(
    *,
    speaker: str,
    move: dict[str, Any],
    prior_moves: list[tuple[str, dict[str, Any]]],
) -> bool:
    prev = find_prev_same_speaker_move(speaker, prior_moves)
    if prev is None:
        return False
    if motivation_sig(move.get("motivation")) != motivation_sig(prev.get("motivation")):
        return False
    sa = similarity_sim(str(move.get("action", "") or ""), str(prev.get("action", "") or ""))
    sd = similarity_sim(
        str(move.get("dialogue", "") or ""),
        str(prev.get("dialogue", "") or ""),
    )
    return sa >= IS1_TAU and sd >= IS1_TAU


def issue_semantic_tuple_from_before_issue(d: dict[str, Any]) -> tuple[str, str, tuple[str, ...], str]:
    """issue_id, status, participants sorted tuple, status_reason (excerpt field name in v1)."""
    iid = str(d.get("issue_id", "") or "").strip()
    st = str(d.get("status", "") or "").strip()
    parts = d.get("participants")
    if isinstance(parts, list):
        pt = tuple(sorted(str(p).strip() for p in parts if str(p).strip()))
    else:
        pt = tuple()
    sr = str(d.get("status_reason_excerpt", "") or d.get("status_reason", "") or "").strip()
    return (iid, st, pt, sr)


def issues_H_from_before_payload(payload: dict[str, Any] | None) -> list[tuple[str, str, tuple[str, ...], str]] | None:
    if not isinstance(payload, dict):
        return None
    obs = payload.get("observed")
    if not isinstance(obs, dict):
        return None
    ib = obs.get("issues_before")
    if not isinstance(ib, dict):
        return None
    issues = ib.get("issues")
    if not isinstance(issues, list):
        return None
    tuples: list[tuple[str, str, tuple[str, ...], str]] = []
    for item in issues:
        if not isinstance(item, dict):
            continue
        t = issue_semantic_tuple_from_before_issue(item)
        if t[0]:
            tuples.append(t)
    tuples.sort(key=lambda x: x[0])
    return tuples


def merge_issue_updates_into_H(
    base: list[tuple[str, str, tuple[str, ...], str]],
    updates: list[dict[str, Any]],
) -> list[tuple[str, str, tuple[str, ...], str]]:
    by_id: dict[str, tuple[str, str, tuple[str, ...], str]] = {t[0]: t for t in base}
    for u in updates:
        if not isinstance(u, dict):
            continue
        iid = str(u.get("issue_id", "") or "").strip()
        if not iid:
            continue
        st = str(u.get("status", "") or "").strip()
        parts = u.get("participants")
        if isinstance(parts, list):
            pt = tuple(sorted(str(p).strip() for p in parts if str(p).strip()))
        else:
            pt = tuple()
        sr = str(u.get("status_reason", "") or "").strip()
        by_id[iid] = (iid, st, pt, sr)
    out = sorted(by_id.values(), key=lambda x: x[0])
    return out


def post_turn_issue_H(
    rows: list[dict[str, Any]],
    ctk: int,
) -> list[tuple[str, str, tuple[str, ...], str]] | None:
    """H after successful character turn at index ctk (post-commit)."""
    if ctk + 1 < len(rows):
        nxt = rows[ctk + 1].get("character_audit_v1")
        return issues_H_from_before_payload(nxt if isinstance(nxt, dict) else None)
    cur = rows[ctk]
    pre = issues_H_from_before_payload(
        cur.get("character_audit_v1") if isinstance(cur.get("character_audit_v1"), dict) else None
    )
    if pre is None:
        return None
    meta = cur.get("metadata")
    if not isinstance(meta, dict):
        return None
    upd = meta.get("issue_updates")
    if not isinstance(upd, list):
        upd = []
    return merge_issue_updates_into_H(pre, upd)


def load_character_audit_rows(session_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(session_dir.rglob("*_full.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(data.get("bot_type", "") or "") != "character":
            continue
        md = data.get("metadata")
        if not isinstance(md, dict):
            md = {}
        po = data.get("parsed_output")
        if not isinstance(po, dict):
            po = {}
        ctx = data.get("context_snapshot")
        if not isinstance(ctx, dict):
            ctx = {}
        ssa = ctx.get("scene_state_after")
        if not isinstance(ssa, dict):
            ssa = {}
        cav1 = md.get("character_audit_v1")
        if cav1 is not None and not isinstance(cav1, dict):
            cav1 = None
        rows.append(
            {
                "_path": str(path),
                "round_number": int(data.get("round_number", 0) or 0),
                "turn_number": int(data.get("turn_number", 0) or 0),
                "timestamp": str(data.get("timestamp", "") or ""),
                "bot_name": str(data.get("bot_name", "") or ""),
                "parsed_output": po,
                "metadata": md,
                "scene_state_after": ssa,
                "character_audit_v1": cav1,
            }
        )

    def sort_key(r: dict[str, Any]) -> tuple[int, int, str, str]:
        return (
            r["round_number"],
            r["turn_number"],
            r["timestamp"],
            r["_path"],
        )

    rows.sort(key=sort_key)
    return rows


def parse_beat_shift_arm_round(log_text: str) -> int | None:
    m = _ARM_RE.search(log_text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def parse_beat_shift_consume_count(log_text: str) -> int:
    return len(_CONSUME_RE.findall(log_text))


def ctk_first_for_round(rows: list[dict[str, Any]], r: int) -> int | None:
    for i, row in enumerate(rows):
        if int(row["round_number"]) == r:
            return i
    return None


@dataclass
class ReplayResult:
    per_turn: list[dict[str, Any]] = field(default_factory=list)
    per_run_summary: dict[str, Any] = field(default_factory=dict)


def run_progression_stress_audit_replay(
    *,
    session_dir: Path,
    structured_eval_path: Path | None,
    log_path: Path | None,
    ctk_consume_override: int | None = None,
) -> ReplayResult:
    rows = load_character_audit_rows(session_dir)
    n = len(rows)

    prior_moves: list[tuple[str, dict[str, Any]]] = []
    per_turn: list[dict[str, Any]] = []

    # Join accepted_turn events by order
    events: list[dict[str, Any]] = []
    structured: dict[str, Any] = {}
    if structured_eval_path and structured_eval_path.is_file():
        structured = json.loads(structured_eval_path.read_text(encoding="utf-8"))
        events = structured.get("sim_progression_metrics_events")
        if not isinstance(events, list):
            events = []

    accepted = [e for e in events if e.get("kind") == "accepted_turn"]
    join_mismatch = len(accepted) != n

    for ctk, row in enumerate(rows):
        move = row["parsed_output"]
        speaker = str(row["bot_name"] or "").strip()
        meta = row["metadata"]
        cons = normalized_consequences(meta)
        ssa = row["scene_state_after"]
        scene_phase = str(ssa.get("phase", "") or "").strip()
        tension = str(ssa.get("current_tension_level", "") or "").strip().lower()
        pa = meta.get("progression_advisory")
        stall_score = None
        prog_pressure = None
        if isinstance(pa, dict):
            try:
                stall_score = float(pa.get("stall_score")) if pa.get("stall_score") is not None else None
            except (TypeError, ValueError):
                stall_score = None
            prog_pressure = str(pa.get("progression_pressure", "") or "").strip() or None

        te = meta.get("turn_execution")
        if not isinstance(te, dict):
            te = {}

        is1 = compute_is1(speaker=speaker, move=move, prior_moves=prior_moves)
        prior_moves.append((speaker, dict(move)))

        is2_na = ctk < 2
        is2 = False
        if not is2_na:
            h0 = post_turn_issue_H(rows, ctk)
            h1 = post_turn_issue_H(rows, ctk - 1)
            h2 = post_turn_issue_H(rows, ctk - 2)
            if h0 is None or h1 is None or h2 is None:
                is2_na = True
            else:
                is2 = h0 == h1 == h2

        is3 = False
        if ctk >= 1:
            prev = per_turn[ctk - 1]
            pphase = str(prev.get("scene_phase", "") or "").strip()
            ptens = str(prev.get("current_tension_level", "") or "").strip().lower()
            if (
                pphase
                and pphase == scene_phase
                and ptens in ("high", "extreme")
                and tension in ("high", "extreme")
            ):
                is3 = True

        stagnation = bool(is1 or (is2 and not is2_na) or is3)

        gate_effective: bool | None = None
        qualifies: bool | None = None
        continuity_turn_index: int | None = None
        if ctk < len(accepted):
            ev = accepted[ctk]
            gate_effective = bool(ev.get("enforcement_effective"))
            qualifies = bool(ev.get("qualifies"))
            cti = ev.get("continuity_turn_index")
            continuity_turn_index = int(cti) if isinstance(cti, int) else None

        q3 = q3_from_consequences(cons)
        q4 = q4_from_move(move)

        prev_cons = (
            list(per_turn[ctk - 1]["metadata_consequences"]) if ctk > 0 else []
        )

        issue_updates = meta.get("issue_updates")
        has_issue_touch = isinstance(issue_updates, list) and len(issue_updates) > 0

        fp1 = False
        if qualifies and is1 and cons == prev_cons and not q3 and not q4:
            fp1 = True

        # FP-2: Q1 single-tag repeat branch would be false; offline we require no Q3/Q4
        # and no issue_updates on this turn as a conservative proxy for Q2 false.
        fp2 = False
        if (
            qualifies
            and ctk > 0
            and len(cons) == 1
            and len(prev_cons) == 1
            and cons[0] == prev_cons[0]
            and not q3
            and not q4
            and not has_issue_touch
        ):
            fp2 = True

        per_turn.append(
            {
                "ctk": ctk,
                "round_number": row["round_number"],
                "turn_number": row["turn_number"],
                "actor": speaker,
                "action": move.get("action", ""),
                "dialogue": move.get("dialogue", ""),
                "motivation_json": json.dumps(move.get("motivation"), sort_keys=True)
                if isinstance(move.get("motivation"), dict)
                else "",
                "metadata_consequences": cons,
                "continuity_turn_index": continuity_turn_index,
                "scene_phase": scene_phase,
                "current_tension_level": tension,
                "stall_score": stall_score,
                "progression_pressure": prog_pressure,
                "gate_effective": gate_effective,
                "qualifies": qualifies,
                "is1": is1,
                "is2": is2 if not is2_na else False,
                "is2_na": is2_na,
                "is3": is3,
                "stagnation_turn": stagnation,
                "fp1": fp1,
                "fp2": fp2,
                "progression_retry_triggered": bool(te.get("progression_retry_triggered")),
                "issue_updates_non_empty": has_issue_touch,
                "join_mismatch_warning": join_mismatch,
            }
        )

    retries_total = sum(1 for e in events if e.get("kind") == "progression_retry")
    failures_total = sum(1 for e in events if e.get("kind") == "progression_failure")

    log_text = ""
    if log_path and log_path.is_file():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")

    r_arm = parse_beat_shift_arm_round(log_text)
    beat: dict[str, Any] = {
        "status": "BE-NA",
        "r_arm": r_arm,
        "ctk_first_r": None,
        "ctk_consume": None,
        "window_a_ctks": [],
        "window_b_ctks": [],
        "partial_a": False,
        "partial_b": False,
        "e1_a": None,
        "e1_b": None,
        "e2_a": None,
        "e2_b": None,
        "e3_a": None,
        "e3_b": None,
        "e4_a": None,
        "e4_b": None,
        "e5_a": None,
        "e5_b": None,
        "effect_observed": None,
    }

    rt_to_ctk = {(int(r["round_number"]), int(r["turn_number"])): i for i, r in enumerate(rows)}

    def _retry_count_for_ctk_indices(idxs: Iterable[int]) -> int:
        want = set(idxs)
        c = 0
        for e in events:
            if e.get("kind") != "progression_retry":
                continue
            r = e.get("round_number")
            t = e.get("orchestration_turn_number")
            if not isinstance(r, int) or not isinstance(t, int):
                continue
            idx = rt_to_ctk.get((r, t))
            if idx is not None and idx in want:
                c += 1
        return c

    if r_arm is not None and parse_beat_shift_consume_count(log_text) >= 1 and n > 0:
        ctk_fr = ctk_first_for_round(rows, r_arm)
        beat["ctk_first_r"] = ctk_fr
        if ctk_fr is not None:
            if ctk_consume_override is not None:
                ctk_c = ctk_consume_override
            else:
                # Heuristic: consuming turn is first character in armed round (see docstring).
                ctk_c = ctk_fr
            beat["ctk_consume"] = ctk_c
            w = WINDOW_W
            a_lo = max(0, ctk_fr - w)
            a_hi = ctk_fr - 1
            window_a = list(range(a_lo, a_hi + 1)) if a_hi >= a_lo else []
            beat["window_a_ctks"] = window_a
            beat["partial_a"] = len(window_a) < w
            b_lo = ctk_c + 1
            window_b = [i for i in range(b_lo, b_lo + w) if i < n]
            beat["window_b_ctks"] = window_b
            beat["partial_b"] = len(window_b) < w

            def _metric_e1(idxs: list[int]) -> float:
                if not idxs:
                    return 0.0
                return sum(1 for i in idxs if i < len(per_turn) and per_turn[i]["stagnation_turn"]) / len(
                    idxs
                )

            def _metric_e2(idxs: list[int]) -> float:
                if not idxs:
                    return 0.0
                return sum(1 for i in idxs if i < len(per_turn) and per_turn[i]["is1"]) / len(idxs)

            def _metric_e3(idxs: list[int]) -> float:
                if not idxs:
                    return 0.0
                s = 0
                for i in idxs:
                    if i >= len(per_turn):
                        continue
                    ge = per_turn[i].get("gate_effective")
                    if ge is True:
                        s += 1
                return s / len(idxs)

            def _metric_e4(idxs: list[int]) -> int:
                if events:
                    return _retry_count_for_ctk_indices(idxs)
                return sum(1 for i in idxs if i < len(per_turn) and per_turn[i]["progression_retry_triggered"])

            def _metric_e5(idxs: list[int]) -> float | None:
                acc = [i for i in idxs if i < len(per_turn) and per_turn[i].get("qualifies") is not None]
                if not acc:
                    return None
                return sum(1 for i in acc if per_turn[i].get("qualifies")) / len(acc)

            wa, wb = beat["window_a_ctks"], beat["window_b_ctks"]
            e1a, e1b = _metric_e1(wa), _metric_e1(wb)
            e2a, e2b = _metric_e2(wa), _metric_e2(wb)
            e3a, e3b = _metric_e3(wa), _metric_e3(wb)
            e4a, e4b = _metric_e4(wa), _metric_e4(wb)
            e5a, e5b = _metric_e5(wa), _metric_e5(wb)
            beat["e1_a"], beat["e1_b"] = e1a, e1b
            beat["e2_a"], beat["e2_b"] = e2a, e2b
            beat["e3_a"], beat["e3_b"] = e3a, e3b
            beat["e4_a"], beat["e4_b"] = e4a, e4b
            beat["e5_a"], beat["e5_b"] = e5a, e5b
            if e5a is not None and e5b is not None:
                eff = (e1b < e1a or e2b < e2a) and e4b <= e4a
                beat["effect_observed"] = eff
            beat["status"] = "ok"
    elif r_arm is None and not log_path:
        beat["status"] = "BE-NA"
    elif r_arm is None:
        beat["status"] = "BE-NA"

    mismatch_stall = {"both": 0, "stagnation_only": 0, "stall_only": 0}
    for pt in per_turn:
        ss = pt.get("stall_score")
        st = False
        if ss is not None:
            try:
                st = float(ss) >= 0.6
            except (TypeError, ValueError):
                st = False
        sg = bool(pt.get("stagnation_turn"))
        if st and sg:
            mismatch_stall["both"] += 1
        elif sg and not st:
            mismatch_stall["stagnation_only"] += 1
        elif st and not sg:
            mismatch_stall["stall_only"] += 1

    summary = {
        "session_dir": str(session_dir.resolve()),
        "n_ctk": n,
        "scenario_id": structured.get("scenario_id"),
        "metrics_from_structured_eval": structured.get("metrics"),
        "stall_score_ge_0_6_correlation": mismatch_stall,
        "stagnation_turn_count": sum(1 for p in per_turn if p["stagnation_turn"]),
        "fp1_count": sum(1 for p in per_turn if p["fp1"]),
        "fp2_count": sum(1 for p in per_turn if p["fp2"]),
        "progression_retries_total": retries_total,
        "progression_failures_total": failures_total,
        "join_accepted_turn_mismatch": join_mismatch,
        "beat_shift": beat,
        "completeness_flags": [],
    }
    if join_mismatch:
        summary["completeness_flags"].append("accepted_turn_event_count_mismatch_ctk")
    if any(p["is2_na"] for p in per_turn[: min(3, n)]):
        summary["completeness_flags"].append("is2_na_present_early_turns")

    return ReplayResult(per_turn=per_turn, per_run_summary=summary)


def write_replay_outputs(
    result: ReplayResult,
    out_dir: Path,
    *,
    basename: str = "progression_stress_replay",
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    p_turn = out_dir / f"{basename}_per_turn.json"
    p_sum = out_dir / f"{basename}_summary.json"
    p_turn.write_text(
        json.dumps(result.per_turn, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    p_sum.write_text(
        json.dumps(result.per_run_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return p_turn, p_sum
