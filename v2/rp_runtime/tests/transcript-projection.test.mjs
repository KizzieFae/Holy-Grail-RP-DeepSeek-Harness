import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { projectHistoryToTranscript } from '../src/lib/project-history.mjs';
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

test('application client: durable transcript survives restart', async (t) => {
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
  const turnA = await client1.submitUserTurn({
    userMessage: 'Alice, please respond.',
    ...MOCK_ROUND,
  });
  assert.equal(turnA.transcript.length, 2);
  const sessionId = created.hg_session_id;
  await client1.stop();

  const client2 = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client2.start();
  t.after(() => client2.stop());

  await client2.openSession(sessionId);
  assert.equal(client2.getTranscript().length, 2);
  assert.equal(client2.getTranscript()[0].content, 'Alice, please respond.');
  assert.match(client2.getTranscript()[1].content, /nodded thoughtfully/i);

  const turnB = await client2.submitUserTurn({
    userMessage: 'Continue the scene.',
    ...MOCK_ROUND,
  });
  assert.equal(turnB.transcript.length, 4);
  assert.equal(turnB.transcript.filter((e) => e.role === 'user').length, 2);
});

test('projectHistoryToTranscript: prefers presentation over committed_turn', () => {
  const entries = [
    { entry_id: '1', sequence_index: 0, kind: 'user', content: 'Hi', actor_id: 'Player', metadata: {} },
    {
      entry_id: '2',
      sequence_index: 1,
      kind: 'committed_turn',
      content: 'nods',
      domain_commit_id: 'c1',
      actor_id: 'Alice',
      metadata: {},
    },
    {
      entry_id: '3',
      sequence_index: 2,
      kind: 'presentation',
      content: 'Alice nodded.',
      domain_commit_id: 'c1',
      actor_id: 'Alice',
      presentation_status: 'rendered',
      metadata: {},
    },
  ];
  const transcript = projectHistoryToTranscript(entries);
  assert.equal(transcript.length, 2);
  assert.equal(transcript[1].content, 'Alice nodded.');
});
