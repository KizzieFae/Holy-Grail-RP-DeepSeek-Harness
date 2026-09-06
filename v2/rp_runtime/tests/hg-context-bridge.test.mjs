import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { extractInferenceTrace } from '../src/lib/inference-trace.mjs';
import { waitForIdle } from '../src/lib/inference-utils.mjs';
import { HgMockLlmAdapter } from '../src/mock-llm-adapter.mjs';


async function postJson(baseUrl, pathName, body) {
  const res = await fetch(`${baseUrl}${pathName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  assert.equal(res.ok, true);
  return res.json();
}

test('HgContextBridge: manifest contributions correlate to DSH inference trace', async (t) => {
  const port = 29765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { withSession: true });
  const { baseUrl, scene } = host;
  t.after(() => host.stop());

  const round = await postJson(baseUrl, '/v1/rounds/start', { hg_scene_id: scene.hg_scene_id });
  const manifest = await postJson(baseUrl, '/v1/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-bridge-trace',
    character_id: 'Alice',
    role: 'guest',
    turn_index: round.turn_index,
    attempt_index: 0,
  });

  const { ctx, contextBridge } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const disposeAdapter = ctx.llm.registerAdapter(['mock'], new HgMockLlmAdapter(['{"ok":true}']));
  t.after(() => disposeAdapter());

  const agent = ctx.agentLoop.create(SessionId('hg-inf-bridge-trace'));
  const registration = contextBridge.registerManifest({ agent, manifest });
  t.after(() => registration.dispose());

  assert.equal(registration.manifestId, manifest.manifest_id);
  assert.deepEqual(
    registration.contributionIds,
    manifest.contributions.map((entry) => String(entry.contribution_id)),
  );
  assert.equal(registration.correlation.inference_id, 'inf-bridge-trace');
  assert.equal(registration.correlation.role, 'character');
  assert.equal(registration.correlation.character_id, 'Alice');

  agent.followup(
    createUserMessage({
      content: [{ type: 'text', text: 'Respond with JSON only.' }],
      source: { kind: 'user' },
    }),
  );
  await waitForIdle(ctx, agent);

  const trace = extractInferenceTrace(agent.session.events, {
    provider: 'mock',
    model: 'mock',
    manifestId: registration.manifestId,
    contributionIds: registration.contributionIds,
  });
  assert.equal(trace.manifest_id, manifest.manifest_id);
  assert.deepEqual(trace.contribution_ids, registration.contributionIds);
});

test('HgContextBridge: scoped registrations do not leak across inference agents', async (t) => {
  const port = 30765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { withSession: true });
  const { baseUrl, scene } = host;
  t.after(() => host.stop());

  const round = await postJson(baseUrl, '/v1/rounds/start', { hg_scene_id: scene.hg_scene_id });
  const directorManifest = await postJson(baseUrl, '/v1/director/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-bridge-director',
    turn_index: round.turn_index,
    attempt_index: 0,
  });
  const characterManifest = await postJson(baseUrl, '/v1/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-bridge-character',
    character_id: 'Alice',
    role: 'guest',
    turn_index: round.turn_index,
    attempt_index: 0,
  });

  const { ctx, contextBridge } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const disposeAdapter = ctx.llm.registerAdapter(['mock'], new HgMockLlmAdapter(['{}', '{}']));
  t.after(() => disposeAdapter());

  const directorAgent = ctx.agentLoop.create(SessionId('hg-inf-bridge-director'));
  const characterAgent = ctx.agentLoop.create(SessionId('hg-inf-bridge-character'));
  const directorRegistration = contextBridge.registerManifest({
    agent: directorAgent,
    manifest: directorManifest,
  });
  const characterRegistration = contextBridge.registerManifest({
    agent: characterAgent,
    manifest: characterManifest,
  });
  t.after(() => {
    directorRegistration.dispose();
    characterRegistration.dispose();
  });

  const directorPrivateKinds = new Set(
    directorManifest.contributions.map((entry) => entry.source_kind),
  );
  const characterPrivateKinds = new Set(
    characterManifest.contributions.map((entry) => entry.source_kind),
  );
  assert.equal(directorPrivateKinds.has('character_private'), false);
  assert.equal(characterPrivateKinds.has('director_scratch'), false);
  assert.equal(characterPrivateKinds.has('character_private'), true);

  const overlap = directorRegistration.contributionIds.filter((id) =>
    characterRegistration.contributionIds.includes(id),
  );
  assert.deepEqual(overlap, []);

  for (const agent of [directorAgent, characterAgent]) {
    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: 'Respond with JSON only.' }],
        source: { kind: 'user' },
      }),
    );
  }
  await Promise.all([waitForIdle(ctx, directorAgent), waitForIdle(ctx, characterAgent)]);

  const directorTrace = extractInferenceTrace(directorAgent.session.events, {
    manifestId: directorRegistration.manifestId,
    contributionIds: directorRegistration.contributionIds,
  });
  const characterTrace = extractInferenceTrace(characterAgent.session.events, {
    manifestId: characterRegistration.manifestId,
    contributionIds: characterRegistration.contributionIds,
  });
  assert.equal(directorTrace.manifest_id, directorManifest.manifest_id);
  assert.equal(characterTrace.manifest_id, characterManifest.manifest_id);
  assert.ok(
    directorTrace.contribution_ids.every((id) => id.includes('manifest-director')),
  );
  assert.ok(
    characterTrace.contribution_ids.some((id) => id.includes('character-private')),
  );
  assert.equal(
    directorTrace.contribution_ids.some((id) => id.includes('character-private')),
    false,
  );
});

test('HgContextBridge: rejects invalid model-context package before registration', async (t) => {
  const { ctx, contextBridge } = await createHolyGrailRpContext();
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const agent = ctx.agentLoop.create(SessionId('hg-inf-bridge-reject'));
  const invalidManifest = {
    manifest_id: 'manifest-invalid',
    inference_id: 'inf-invalid',
    inference_kind: 'narrator_presentation',
    hg_scene_id: 'scene-1',
    hg_round_id: 'round-1',
    role: 'narrator',
    character_id: 'Alice',
    turn_index: 1,
    attempt_index: 0,
    contributions: [
      {
        contribution_id: 'bad-env-cog',
        source_kind: 'narrator_environment_cognition',
        authority_class: 'derived',
        knowledge_ids: ['audit-1'],
        priority: 28,
        content: '{"forensic":"audit"}',
        provenance: {},
      },
    ],
  };

  assert.throws(
    () => contextBridge.registerManifest({ agent, manifest: invalidManifest }),
    /model-context package rejected/,
  );
});
