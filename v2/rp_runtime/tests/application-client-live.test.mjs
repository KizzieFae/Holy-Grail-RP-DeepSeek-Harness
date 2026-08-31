import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

test('application client: live DeepSeek user turn', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 180_000,
}, async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  await client.createSession({ cast: ['Alice'] });
  const turn = await client.submitUserTurn({
    userMessage: 'Alice, acknowledge the workshop quietly.',
  });

  assert.equal(turn.round.committed, true);
  assert.ok(turn.presentation);
  const traces = turn.round.role_inference_traces ?? {};
  const roleProfiles = turn.round.role_profiles ?? {};
  const usedLive = ['director', 'character', 'narrator']
    .some((role) => traces[role]?.provider === 'deepseek-official');
  assert.equal(usedLive, true);
  assert.equal(roleProfiles.storyteller?.kind, 'dsh');
  assert.equal(roleProfiles.storyteller?.provider, 'deepseek-official');
  assert.notEqual(roleProfiles.storyteller?.provider, 'hg-mock');
});
