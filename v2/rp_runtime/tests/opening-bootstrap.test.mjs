import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

test('application client: template opening persists authored prose', async (t) => {
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

  const openers = await client.listTemplateOpeners('celina_apartment_recovery_watch');
  assert.ok(openers.length > 0);

  await client.createSession({
    characters: ['kizzie', 'willow'],
    sceneTemplateId: 'celina_apartment_recovery_watch',
    roleAssignments: {
      kizzie: 'recovering_demi_human',
      willow: 'protector',
    },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
  });

  const transcript = client.getTranscript();
  assert.equal(transcript.length, 1);
  assert.equal(transcript[0].speaker, 'Narrator');
  assert.match(transcript[0].content, /Walking out of one of her boss's hotels/);
});

test('application client: generated opening uses mock inference and persists once', async (t) => {
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

  const session = await client.createSession({
    characters: ['kizzie'],
    opening: { mode: 'generated' },
    mockOpeningResponses: ['Generated opening prose for tests.'],
  });

  const transcript = client.getTranscript();
  assert.equal(transcript.length, 1);
  assert.equal(transcript[0].content, 'Generated opening prose for tests.');

  await client.openSession(session.hg_session_id);
  const reopenedTranscript = client.getTranscript();
  assert.equal(reopenedTranscript.length, 1);

  const retry = await client.generateOpening({
    mockOpeningResponses: ['Should not duplicate.'],
  });
  assert.equal(retry.skipped, true);
  assert.equal(client.getTranscript().length, 1);
});

test('application client: minimal opening has no transcript entry', async (t) => {
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

  await client.createSession({
    characters: ['kizzie', 'willow'],
    sceneTemplateId: 'celina_apartment_recovery_watch',
    roleAssignments: {
      kizzie: 'recovering_demi_human',
      willow: 'protector',
    },
    opening: { mode: 'minimal' },
  });

  assert.equal(client.getTranscript().length, 0);
});

test('application client: restart preserves template opening and allows user turn', async (t) => {
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

  const openers = await client.listTemplateOpeners('celina_apartment_recovery_watch');
  const created = await client.createSession({
    characters: ['kizzie', 'willow'],
    sceneTemplateId: 'celina_apartment_recovery_watch',
    roleAssignments: {
      kizzie: 'recovering_demi_human',
      willow: 'protector',
    },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
  });
  const sessionId = created.hg_session_id;
  const openingText = client.getTranscript()[0].content;

  const restarted = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await restarted.start();
  t.after(() => restarted.stop());
  await restarted.openSession(sessionId);
  assert.equal(restarted.getTranscript().length, 1);
  assert.equal(restarted.getTranscript()[0].content, openingText);

  const turn = await restarted.submitUserTurn({ userMessage: 'Hello?' });
  assert.ok(turn.transcript.length >= 2);
});
