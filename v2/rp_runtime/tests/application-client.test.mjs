import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'subtle gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_DIRECTOR_ALICE = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should respond.',
  environment_event: '',
  tension_shift: '',
};

const VALID_DIRECTOR_END = {
  next_actor: 'Alice',
  end_round: true,
  reason: 'Round complete.',
  environment_event: '',
  tension_shift: '',
};

const MOCK_ROUND = {
  mockDirectorResponses: [
    JSON.stringify(VALID_DIRECTOR_ALICE),
    JSON.stringify(VALID_DIRECTOR_END),
  ],
  mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  mockNarratorTurnResponses: [['Alice nodded thoughtfully in the workshop.']],
};

test('application client: create session, submit turn, persist across restart', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client1 = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client1.start();
  t.after(() => client1.stop());

  const created = await client1.createSession({ cast: ['Alice'] });
  assert.ok(created.hg_session_id);

  const turn = await client1.submitUserTurn({
    userMessage: 'Alice, please respond.',
    ...MOCK_ROUND,
    mockNarratorTurnResponses: [['Alice nodded thoughtfully in the workshop.']],
  });
  assert.equal(turn.round.committed, true);
  assert.equal(turn.round.continuity_turn_index, 1);
  assert.ok(turn.presentation);
  assert.equal(turn.transcript.length, 2);
  assert.ok(fs.existsSync(`${sessionsDir}/${created.hg_session_id}.json`));

  const sessionId = created.hg_session_id;
  await client1.stop();

  const client2 = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client2.start();
  t.after(() => client2.stop());

  const reopened = await client2.openSession(sessionId);
  assert.equal(reopened.turn_counter, 1);
  assert.equal(reopened.committed_move_count, 1);

  const secondTurn = await client2.submitUserTurn({
    userMessage: 'Continue.',
    ...MOCK_ROUND,
  });
  assert.equal(secondTurn.round.continuity_turn_index, 2);
});

test('application client: submit skip turn advances one round without user message', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  await client.createSession({ cast: ['Alice'] });
  const skip = await client.submitSkipTurn({ ...MOCK_ROUND });
  assert.equal(skip.round.committed, true);
  assert.equal(skip.round.continuity_turn_index, 1);
  assert.ok(skip.transcript.some((entry) => entry.player_skip));
  assert.ok(!skip.transcript.some((entry) => entry.role === 'user'));
});

test('application client: surfaces runtime-not-ready error', async () => {
  const client = new HolyGrailApplicationClient({ inferenceMode: 'mock' });
  await assert.rejects(
    () => client.createSession({ cast: ['Alice'] }),
    /not ready/,
  );
});
