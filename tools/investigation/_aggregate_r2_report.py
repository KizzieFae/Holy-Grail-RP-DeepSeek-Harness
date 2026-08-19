from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE

import json
from pathlib import Path

root = REPO_ROOT  # patched M13.6 / "runs" / "arch_quality_r2"
rows: list[dict] = []
for comp in ("A1", "B", "C"):
    d = root / comp
    if not d.is_dir():
        continue
    for p in sorted(d.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        m = data.get("metrics") or {}
        sa = m.get("selection_attribution_summary") or {}
        stem = p.stem
        parts = stem.rsplit("_rep", 1)
        rep = int(parts[1]) if len(parts) == 2 else 0
        base = parts[0]
        scen, var = base, "?"
        for suffix in ("_baseline", "_a1", "_b", "_c"):
            if base.endswith(suffix):
                scen = base[: -len(suffix)]
                var = suffix[1:]
                break
        rows.append(
            {
                "comp": comp,
                "scen": scen,
                "var": var,
                "rep": rep,
                "accepted": m.get("accepted_character_turns"),
                "retries": m.get("progression_retries_triggered"),
                "fails": m.get("failed_progression_attempts"),
                "ov": sa.get("progression_override_applied_count"),
                "hard": sa.get("hard_route_events"),
                "fair": sa.get("fairness_rotation_count"),
                "chains": sa.get("attribution_chain_counts") or {},
            }
        )

turns_req = {"conflict_3char": 4, "arrival_setup": 3, "long_session": 8}

for comp in ("A1", "B", "C"):
    print("===", comp, "===")
    print(
        "scenario\tvariant\trep\tturns\taccepted\tretries\tfails\toverride\thard_route\tfairness\tchains"
    )
    for r in sorted(
        [x for x in rows if x["comp"] == comp],
        key=lambda x: (x["scen"], x["var"], x["rep"]),
    ):
        ch = "; ".join(f"{k}={v}" for k, v in sorted(r["chains"].items()))
        tr = turns_req.get(r["scen"], "?")
        print(
            f"{r['scen']}\t{r['var']}\t{r['rep']}\t{tr}\t{r['accepted']}\t{r['retries']}\t{r['fails']}\t{r['ov']}\t{r['hard']}\t{r['fair']}\t{ch}"
        )
    print()


def agg(comp: str, scen: str, var: str) -> dict:
    xs = [r for r in rows if r["comp"] == comp and r["scen"] == scen and r["var"] == var]
    if not xs:
        return {}
    return {
        "mean_acc": sum(r["accepted"] or 0 for r in xs) / len(xs),
        "sum_ov": sum(r["ov"] or 0 for r in xs),
        "sum_hard": sum(r["hard"] or 0 for r in xs),
        "sum_fair": sum(r["fair"] or 0 for r in xs),
        "sum_retries": sum(r["retries"] or 0 for r in xs),
        "n": len(xs),
    }


for comp in ("A1", "B", "C"):
    print("---", comp, "side aggregates (n=3 per side per scenario) ---")
    v1 = {"A1": "a1", "B": "b", "C": "c"}[comp]
    for scen in ("conflict_3char", "arrival_setup", "long_session"):
        a0, a1 = agg(comp, scen, "baseline"), agg(comp, scen, v1)
        print(f"  {scen} baseline: mean_acc={a0.get('mean_acc',0):.2f} sum_ov={a0.get('sum_ov')} sum_hard={a0.get('sum_hard')} sum_fair={a0.get('sum_fair')} sum_retries={a0.get('sum_retries')}")
        print(f"  {scen} {v1}:      mean_acc={a1.get('mean_acc',0):.2f} sum_ov={a1.get('sum_ov')} sum_hard={a1.get('sum_hard')} sum_fair={a1.get('sum_fair')} sum_retries={a1.get('sum_retries')}")
    print()
