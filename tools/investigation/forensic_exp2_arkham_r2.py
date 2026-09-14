#!/usr/bin/env python3
"""Read-only forensic trace for Issue #201 EXP-2 arkham r2 failure."""
import json
import pathlib
import sys

STAGE2 = pathlib.Path(__file__).resolve().parents[2] / 'data' / 'investigation_runs' / 'issue201-package-d-stage2-2026-09-14T08-09-42-791Z'

SESSIONS = {
    'EXP-2-arkham-r2-fail': 'hg-session-a92735ee-709d-4d00-a79a-7b41f0ee8652',
    'EXP-2-arkham-r1-ok': 'hg-session-a1718072-886b-4fd3-8b44-1aa8d9551883',
    'D0-arkham-r1': 'hg-session-fca85cb2-ab17-41f8-9a70-4fd05f8b38ff',
}


def load_session(root: pathlib.Path, session_id: str):
    base = root / session_id
    index = json.loads((base / 'index.json').read_text(encoding='utf-8'))
    attempts = []
    for aid in index.get('attempt_ids', []):
        p = base / 'attempts' / f'{aid}.json'
        if not p.exists():
            continue
        a = json.loads(p.read_text(encoding='utf-8'))
        corr = a.get('correlation') or {}
        dec = a.get('decision') or {}
        resp = a.get('response') or {}
        fin = (resp.get('finish') or {})
        attempts.append({
            'evidence_id': a.get('evidence_id', aid),
            'role': corr.get('role'),
            'inference_kind': corr.get('inference_kind'),
            'attempt_index': corr.get('attempt_index'),
            'finish': fin.get('kind'),
            'error': resp.get('error') or a.get('error'),
            'decision_keys': list(dec.keys()) if isinstance(dec, dict) else [],
            'decision': dec,
            'timing_ms': (a.get('inference_health') or {}).get('timing', {}).get('inference_wall_clock_ms'),
            'created_at': a.get('created_at'),
        })
    return {'session_id': session_id, 'index': index, 'attempts': attempts}


def summarize(label, data):
    kinds = {}
    for a in data['attempts']:
        k = a['inference_kind'] or a['role'] or 'unknown'
        kinds.setdefault(k, []).append(a)
    print(f'\n=== {label} ({data["session_id"]}) attempts={len(data["attempts"])} ===')
    for k, rows in sorted(kinds.items(), key=lambda x: -len(x[1])):
        finishes = [r['finish'] for r in rows]
        print(f'  {k}: n={len(rows)} finishes={set(finishes)}')
    # decision-bearing attempts
    for a in data['attempts']:
        if a['decision_keys']:
            dk = {k: a['decision'].get(k) for k in a['decision_keys'] if k in (
                'outcome', 'committed', 'completion_reason', 'selected_character_id',
                'director', 'character', 'semantic', 'qa', 'validation', 'stage',
                'proposed', 'accepted', 'reason', 'disposition'
            ) or 'reason' in k or 'outcome' in k}
            if dk:
                print(f"  DECISION {a['inference_kind'] or a['role']}: {json.dumps(dk, default=str)[:500]}")


def main():
    root = STAGE2
    if len(sys.argv) > 1:
        root = pathlib.Path(sys.argv[1])
    for label, sid in SESSIONS.items():
        if not (root / sid).exists():
            print(f'MISSING {label} {sid}')
            continue
        summarize(label, load_session(root, sid))

    fail = load_session(root, SESSIONS['EXP-2-arkham-r2-fail'])
    print('\n=== FAIL timeline (inference_kind order) ===')
    for a in fail['attempts']:
        if a['inference_kind'] or a['role'] in ('director', 'character', 'narrator', 'execution_span'):
            print(json.dumps({
                'kind': a['inference_kind'],
                'role': a['role'],
                'finish': a['finish'],
                'attempt_index': a['attempt_index'],
                'timing_ms': a['timing_ms'],
                'decision': {k: a['decision'].get(k) for k in a['decision_keys'][:8]} if a['decision_keys'] else None,
                'error': a['error'],
            }, default=str))


if __name__ == '__main__':
    main()
