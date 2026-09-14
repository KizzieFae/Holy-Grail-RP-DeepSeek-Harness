import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
packet = json.loads(
    (ROOT / 'data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/outputs/issue201-stage2-human-blind-eval-packet.json').read_text(encoding='utf-8')
)
dims = [
    'Character fidelity', 'Distinctiveness', 'Initiative', 'Responsiveness',
    'Dramatic progression', 'Coherence', 'Prose quality',
    'Repetitiveness (5=low)', 'Stiffness (5=natural)',
    'Unnecessary exposition (5=lean)', 'Emotional/narrative continuity',
]
lines = [
    '# Issue #201 Stage 2 — Human Blind Scoring Sheet (refreshed)',
    '',
    'See `issue201-stage2-human-evaluator-worksheet.md` for rubric and scenario briefings.',
    '',
]
for s in packet['samples']:
    lines += [f'## Sample {s["blind_label"]}', '', s['presentation_text'], '', '| Dimension | Score |', '|---|---|']
    for d in dims:
        lines.append(f'| {d} | |')
    lines.append('')
out = ROOT / 'governance/records/issue201-stage2-human-evaluator-scoring-sheet.md'
out.write_text('\n'.join(lines), encoding='utf-8')
print('wrote', out, 'samples', len(packet['samples']))
