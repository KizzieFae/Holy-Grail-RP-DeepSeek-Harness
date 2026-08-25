import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
  parseLibrarianProposalResult,
} from '../src/lib/librarian-proposal-envelope.mjs';

test('parseLibrarianProposalResult accepts valid grounded proposal', () => {
  const catalog = new Set(['committed_move:commit-1']);
  const raw = JSON.stringify({
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    proposals: [
      {
        proposal_id: 'prop-1',
        proposal_kind: 'information_salience',
        derivation_summary: 'Committed move advances the scene.',
        confidence: 'likely',
        evidence_anchors: [
          {
            anchor_id: 'committed_move:commit-1',
            evidence_kind: 'committed_move',
            anchor_commit_id: 'commit-1',
          },
        ],
        proposed_payload: {
          subject_ref: 'commit:commit-1',
          salience_level: 'major',
        },
      },
    ],
  });
  const parsed = parseLibrarianProposalResult(raw, catalog);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.proposals[0].proposal_kind, 'information_salience');
});

test('parseLibrarianProposalResult rejects unknown anchor id', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals: [
        {
          proposal_kind: 'information_salience',
          derivation_summary: 'bad anchor',
          confidence: 'likely',
          evidence_anchors: [
            {
              anchor_id: 'committed_move:missing',
              evidence_kind: 'committed_move',
            },
          ],
          proposed_payload: {
            subject_ref: 'x',
            salience_level: 'minor',
          },
        },
      ],
    }),
    new Set(['committed_move:commit-1']),
  );
  assert.equal(parsed.ok, false);
  assert.match(String(parsed.error), /unknown_anchor/);
});

test('parseLibrarianProposalResult rejects preservation_signal evidence', () => {
  const parsed = parseLibrarianProposalResult(
    JSON.stringify({
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals: [
        {
          proposal_kind: 'information_salience',
          derivation_summary: 'storyteller hint',
          confidence: 'likely',
          evidence_anchors: [
            {
              anchor_id: 'preservation_signal:hint-1',
              evidence_kind: 'preservation_signal',
            },
          ],
          proposed_payload: {
            subject_ref: 'x',
            salience_level: 'minor',
          },
        },
      ],
    }),
    new Set(['preservation_signal:hint-1']),
  );
  assert.equal(parsed.ok, false);
  assert.match(String(parsed.error), /preservation_signal_not_evidence/);
});
