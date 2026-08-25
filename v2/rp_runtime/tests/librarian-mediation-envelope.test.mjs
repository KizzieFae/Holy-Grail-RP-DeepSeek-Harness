import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  parseLibrarianMediationResult,
} from '../src/lib/librarian-mediation-envelope.mjs';

test('parseLibrarianMediationResult accepts valid contextual selection', () => {
  const catalog = new Set(['lmi:cand:cause', 'lmi:cand:noise']);
  const raw = JSON.stringify({
    schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    selected_items: [
      {
        source_id: 'lmi:cand:cause',
        relevance_rank: 1,
        relevance_band: 'high',
        interpretive_status: 'likely',
        answers_focus_questions: ['Why is Alice reacting angrily now?'],
      },
    ],
  });
  const parsed = parseLibrarianMediationResult(raw, catalog);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.selected_items[0].source_id, 'lmi:cand:cause');
});

test('parseLibrarianMediationResult rejects unknown source id', () => {
  const parsed = parseLibrarianMediationResult(
    JSON.stringify({
      schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
      selected_items: [{ source_id: 'lmi:cand:missing', relevance_rank: 1 }],
    }),
    new Set(['lmi:cand:cause']),
  );
  assert.equal(parsed.ok, false);
  assert.match(String(parsed.error), /unknown_source/);
});
