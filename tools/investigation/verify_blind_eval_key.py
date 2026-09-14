import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
STAGE2 = ROOT / 'data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z'

packet = json.loads((STAGE2 / 'outputs/issue201-stage2-human-blind-eval-packet.json').read_text(encoding='utf-8'))
key = json.loads((STAGE2 / 'outputs/issue201-stage2-human-blind-eval-answer-key.json').read_text(encoding='utf-8'))
report = json.loads((STAGE2 / 'issue201-package-d-stage2-tranche1-report.json').read_text(encoding='utf-8'))

FAILED_SESSION = 'hg-session-a92735ee-709d-4d00-a79a-7b41f0ee8652'

def norm(s: str) -> str:
    s = s.replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'")
    s = re.sub(r'[^\x00-\x7F]+', '?', s)
    return ' '.join(s.split())

case_pres = {}
case_meta = {}
for exp in report['experiments']:
    for run in exp.get('runs', []):
        case_pres[run['case_id']] = run.get('presentation_text', '')
        case_meta[run['case_id']] = run

d0_root = pathlib.Path(report['d0_evidence_root'])
for name in ['issue201-package-d-d0-baseline-report.json', 'issue201-d0-baseline-report.json']:
    p = d0_root / name
    if p.exists():
        d0_report = json.loads(p.read_text(encoding='utf-8'))
        break
else:
    raise SystemExit('D0 report not found')

for run in d0_report.get('runs', d0_report.get('cases', [])):
    cid = run.get('case_id') or run.get('id')
    case_pres[cid] = run.get('presentation_text', '')
    case_meta[cid] = run

labels_packet = {s['blind_label']: s['presentation_text'] for s in packet['samples']}
expected = {chr(ord('A') + i) for i in range(16)}

print('integrity:')
print('  packet_count', len(packet['samples']))
print('  key_count', len(key))
print('  labels_complete', set(labels_packet) == expected)
print('  key_labels_match_packet', {e['blind_label'] for e in key} == set(labels_packet))

mismatches = []
for e in key:
    bl, cid = e['blind_label'], e['case_id']
    pt_packet = labels_packet.get(bl, '')
    pt_case = case_pres.get(cid, '')
    if not pt_case:
        mismatches.append(f'{bl}/{cid}: missing case presentation')
    elif norm(pt_packet)[:120] != norm(pt_case)[:120]:
        mismatches.append(f'{bl}/{cid}: presentation prefix mismatch')

print('  presentation_mismatches', len(mismatches))
for m in mismatches:
    print('   ', m)

failed_in_packet = []
for e in key:
    cid = e['case_id']
    meta = case_meta.get(cid, {})
    sid = meta.get('hg_session_id', '')
    if sid == FAILED_SESSION:
        failed_in_packet.append(e['blind_label'])

print('  failed_session_in_packet', failed_in_packet or 'NONE')
print('  packet_purpose', packet.get('purpose'))

print('\nfull_mapping:')
for e in sorted(key, key=lambda x: x['blind_label']):
    meta = case_meta.get(e['case_id'], {})
    print(json.dumps({
        'blind_label': e['blind_label'],
        'case_id': e['case_id'],
        'experiment_id': e['experiment_id'],
        'scenario_id': e['scenario_id'],
        'hg_session_id': meta.get('hg_session_id'),
        'domain_commit_id': meta.get('domain_commit_id'),
        'committed': (meta.get('objective') or {}).get('committed'),
        'presentation_path': meta.get('presentation_path'),
    }))
