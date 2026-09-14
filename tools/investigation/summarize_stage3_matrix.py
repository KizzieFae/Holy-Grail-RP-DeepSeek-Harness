import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[2]
STAGE3 = ROOT / 'data/investigation_runs/issue201-package-d-stage3-2026-09-14T18-16-06-752Z'
STAGE2_OUT = ROOT / 'data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/outputs'

report = json.loads((STAGE3 / 'issue201-package-d-stage3-preamble-decomposition-report.json').read_text(encoding='utf-8'))


def mean(vals):
    return statistics.mean(vals) if vals else None


def summarize_cases(cases, sk=None):
    cs = [c for c in cases if sk is None or c.get('scenario_key') == sk]
    if not cs:
        return {}
    return {
        'n': len(cs),
        'committed': sum(1 for c in cs if (c.get('objective') or {}).get('committed', True)),
        'wall_s': mean([c['operation_wall_ms'] / 1000 for c in cs]),
        'inf': mean([(c.get('inference') or {}).get('inference_count', c.get('inference_count')) for c in cs]),
        'st': mean([(c.get('inference') or {}).get('storyteller_inference_count', c.get('storyteller_inference_count', 0)) for c in cs]),
        'pl': mean([(c.get('inference') or {}).get('plot_inference_count', c.get('plot_inference_count', 0)) for c in cs]),
        'lib': mean([(c.get('inference') or {}).get('librarian_mediation_count', c.get('librarian_mediation_count', 0)) for c in cs]),
    }


d0 = report['d0_controls']
d01full = []
for r in report['d01_combined_reused_runs']:
    meta = json.loads((STAGE2_OUT / f"{r['case_id']}-meta.json").read_text(encoding='utf-8'))
    d01full.append(meta)

d01b = [r for e in report['experiments'] for r in e['runs'] if r.get('experiment_id') == 'D-01b' and not r.get('failed')]
d01a = [r for e in report['experiments'] for r in e['runs'] if r.get('experiment_id') == 'D-01a' and not r.get('failed')]

for name, cases in [('D0', d0), ('D-01', d01full), ('D-01b', d01b), ('D-01a', d01a)]:
    print(name)
    for sk in [None, 'arkham_stress', 'ayame_controlled']:
        label = sk or 'ALL'
        print(' ', label, summarize_cases(cases, sk))
