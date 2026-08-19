"""One-off: apply mandatory sampling + prompt integrity checks on validation audit sessions."""
from __future__ import annotations

import json
import re
from pathlib import Path

_AUDIT_ROOT = Path(__file__).resolve().parents[2] / "rp_app" / "data" / "rp_audits"

# session -> scenario label for reporting
SESSIONS: dict[int, str] = {
    388: "willow_dorm_binding_stress",
    389: "conflict_3char",
    390: "emotional_loop_2char_run1",
    391: "emotional_loop_2char_run2",
    392: "arkham_multi_character_stress_long",
    393: "long_session",
}


def _char_full_paths(session: int) -> list[tuple[int, str, Path]]:
    rnd = _AUDIT_ROOT / f"session_{session:03d}" / "round_001"
    out: list[tuple[int, str, Path]] = []
    for p in sorted(rnd.glob("*_full.json")):
        name = p.name.lower()
        if "director" in name or "narrator" in name:
            continue
        m = re.search(r"_turn(\d+)_", p.name)
        if not m:
            continue
        turn = int(m.group(1))
        # slug between turn##_ and _full
        rest = p.name[m.end() :]
        bot = rest.replace("_full.json", "")
        out.append((turn, bot, p))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def _system_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    msgs = data.get("input_messages") or data.get("messages") or []
    for m in msgs:
        if m.get("role") == "system":
            c = m.get("content")
            return c if isinstance(c, str) else ""
    return ""


def _actor_key_from_slug(slug: str) -> str:
    return slug.replace("_", " ").strip()


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).casefold()


def _same_character(a: str, b: str) -> bool:
    """Id vs display: slug with underscores vs spaced display."""
    if _norm_name(a) == _norm_name(b):
        return True
    a0 = _norm_name(a.replace("_", " "))
    b0 = _norm_name(b.replace("_", " "))
    return a0 == b0


def _check_prompt_integrity(text: str, actor_slug: str, bot_display_name: str) -> tuple[bool, bool, str]:
    """Returns (other_present_ok, cast_map_ok, notes)."""
    notes: list[str] = []

    # OTHER PRESENT CHARACTERS — single-line list after heading (audit format)
    op_m = re.search(
        r"OTHER PRESENT CHARACTERS:\s*([^\n]+)",
        text,
        re.IGNORECASE,
    )
    other_present_ok = True
    if op_m:
        raw = op_m.group(1)
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for p in parts:
            if _same_character(p, bot_display_name) or _same_character(p, actor_slug):
                other_present_ok = False
                notes.append(f"self_in_other_present:{p}")
    else:
        notes.append("no_other_present_line")

    # CAST ROLE MAP — JSON array after "CAST ROLE MAP:\n"
    cast_map_ok = True
    cm_m = re.search(r"CAST ROLE MAP:\s*\n(\[[\s\S]*?\])\s*\n\n", text)
    if cm_m:
        try:
            arr = json.loads(cm_m.group(1))
            names: list[str] = []
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict) and item.get("character"):
                        names.append(str(item["character"]))
            # duplicate if same logical character twice (id/display)
            for i, n1 in enumerate(names):
                for n2 in names[i + 1 :]:
                    if _same_character(n1, n2):
                        cast_map_ok = False
                        notes.append(f"dup_cast_map:{n1!r}|{n2!r}")
        except json.JSONDecodeError as e:
            cast_map_ok = False
            notes.append(f"cast_map_json_error:{e}")
    else:
        notes.append("no_cast_role_map_json")

    return other_present_ok, cast_map_ok, "; ".join(notes) if notes else "ok"


def _sample_turns(turns: list[int], actors: list[str]) -> list[int]:
    """Mandatory rule: first, last, actor-switch (cap 6 switches), min 3 total."""
    if not turns:
        return []
    unique_order: list[int] = []
    last_t = None
    for t, a in zip(turns, actors):
        if last_t is None or t != last_t:
            unique_order.append(t)
            last_t = t
    # sequence of (turn, actor) per character turn
    seq = list(zip(turns, actors))
    first_t = seq[0][0]
    last_t_end = seq[-1][0]
    switches: list[int] = []
    prev_a = None
    for t, a in seq:
        if prev_a is not None and a != prev_a:
            switches.append(t)
        prev_a = a
    switch_pick = switches[:6]
    sampled = {first_t, last_t_end, *switch_pick}
    if len(sampled) < 3:
        # add mid indices from sorted unique turns
        ut = sorted(set(turns))
        for t in ut:
            sampled.add(t)
            if len(sampled) >= 3:
                break
    return sorted(sampled)


def main() -> None:
    for session, scen in SESSIONS.items():
        rows = _char_full_paths(session)
        turns = [t for t, _, _ in rows]
        actors = [a for _, a, _ in rows]
        sample_ts = _sample_turns(turns, actors)
        print(f"\n=== {scen} session_{session:03d} ===")
        print(f"character_turns={len(rows)} sampled_turns={sample_ts}")
        pi_fail = False
        for t in sample_ts:
            matches = [(b, p) for tt, b, p in rows if tt == t]
            if not matches:
                print(f"  turn {t}: MISSING")
                continue
            for bot, path in matches:
                data = json.loads(path.read_text(encoding="utf-8"))
                display = str(data.get("bot_name") or bot)
                txt = _system_text(path)
                ok_o, ok_c, note = _check_prompt_integrity(txt, bot, display)
                if not ok_o or not ok_c:
                    pi_fail = True
                status = "FAIL" if (not ok_o or not ok_c) else "ok"
                print(f"  turn {t} {bot}: pi={status} ({note})")
        print(f"  scenario_pi_summary={'REGRESSION' if pi_fail else 'pass'}")


if __name__ == "__main__":
    main()
