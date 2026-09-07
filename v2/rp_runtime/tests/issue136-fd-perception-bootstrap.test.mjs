import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { directorFor } from '../src/scenario-harness/inference-mocks.mjs';
import {
  attachIssue136TurnZeroPerception,
  buildTurnZeroPerceptualVisibility,
  fixtureRequiresTurnZeroPerception,
  prepareIssue136CharacterManifestGate,
  turnZeroOpeningProse,
} from '../src/scenario-harness/issue136-fixture-bootstrap.mjs';
import {
  buildSessionCreateBody,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';
import {
  installIssue136ValidationCards,
  loadIssue136TruthFixture,
} from '../src/scenario-harness/issue136-fixture-truth.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

async function bootstrapSession(host, api, dataDir, fixtureId) {
  installIssue136ValidationCards(dataDir);
  const truth = loadIssue136TruthFixture(fixtureId);
  const created = await api.createSession(buildSessionCreateBody(truth));
  await attachIssue136TurnZeroPerception(api, created.hg_session_id, truth);
  return { created, truth };
}

function startIssue136DomainHost(sessionsDir, dataDir, t) {
  return startDomainApi(undefined, {
    sessionsDir,
    hostEnv: { HG_DATA_DIR: dataDir },
    t,
  });
}

test('issue136 F/D fixtures declare turn_zero_perception', () => {
  for (const fixtureId of ['136-T2-F-ACTION-REQUIRED', '136-T2-D-INACTION']) {
    const truth = loadIssue136TruthFixture(fixtureId);
    assert.equal(truth.turn_zero_perception, true);
    assert.ok(fixtureRequiresTurnZeroPerception(fixtureId));
    assert.ok(turnZeroOpeningProse(truth).length > 0);
  }
});

test('issue136 turn-zero PVR validates observable_scene units', async () => {
  const pvr = buildTurnZeroPerceptualVisibility({
    prose: 'A support bracket cracked visibly above a colleague\'s station.',
    unitIdPrefix: 'test_f',
  });
  assert.equal(pvr.units.length, 1);
  assert.equal(pvr.units[0].kind, 'observable_scene');
  assert.equal(pvr.units[0].recipients.scope, 'public');
});

test('issue136 F manifest gate: bracket hazard reaches Mara via recent_scene_transcript', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startIssue136DomainHost(sessionsDir, dataDir, t);
  const api = createDomainApiClient(host.baseUrl);
  const { created, truth } = await bootstrapSession(host, api, dataDir, '136-T2-F-ACTION-REQUIRED');
  const gate = await prepareIssue136CharacterManifestGate({
    api,
    hgSessionId: created.hg_session_id,
    truth,
    directorDecision: JSON.parse(directorFor('Mara')),
  });

  assert.ok(gate.opening);
  assert.ok(gate.opening.metadata?.perceptual_visibility?.units?.length > 0);
  assert.ok(gate.analysis.recentSceneTranscript);
  const transcript = gate.analysis.recentSceneTranscript.content;
  assert.match(transcript, /bracket/i);
  assert.match(transcript, /colleague/i);
  assert.match(transcript, /crack/i);
  assert.equal(gate.analysis.sceneSetup, null);
  assert.ok(gate.analysis.sceneContext);
  assert.doesNotMatch(gate.analysis.sceneContext.content, /Persistent scenario premise/i);
  assert.ok(gate.analysis.directorContext);
  assert.doesNotMatch(
    gate.analysis.sceneContext.content,
    /support bracket cracked visibly above a colleague's station/i,
  );
});

test('issue136 D manifest gate: scraping condition reaches Mara via recent_scene_transcript', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startIssue136DomainHost(sessionsDir, dataDir, t);
  const api = createDomainApiClient(host.baseUrl);
  const { created, truth } = await bootstrapSession(host, api, dataDir, '136-T2-D-INACTION');
  const gate = await prepareIssue136CharacterManifestGate({
    api,
    hgSessionId: created.hg_session_id,
    truth,
    directorDecision: JSON.parse(directorFor('Mara')),
  });

  assert.ok(gate.analysis.recentSceneTranscript);
  const transcript = gate.analysis.recentSceneTranscript.content;
  assert.match(transcript, /scraping/i);
  assert.match(transcript, /panel/i);
  assert.equal(gate.analysis.sceneSetup, null);
});

test('issue136 turn-zero PVR excludes viewer-ineligible internal units', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startIssue136DomainHost(sessionsDir, dataDir, t);
  const api = createDomainApiClient(host.baseUrl);
  const truth = loadIssue136TruthFixture('136-T2-F-ACTION-REQUIRED');
  installIssue136ValidationCards(dataDir);
  const created = await api.createSession(buildSessionCreateBody(truth));

  const prose = turnZeroOpeningProse(truth);
  const perceptual_visibility = buildTurnZeroPerceptualVisibility({
    prose,
    unitIdPrefix: 'f_entitlement',
    extraUnits: [{
      unit_id: 'f_colleague_private',
      kind: 'internal',
      text: 'Colleague private thought that Mara must not see.',
      recipients: { scope: 'private', characters: ['Colleague'] },
    }],
  });
  const validated = await api.validatePerceptualVisibility({
    hg_session_id: created.hg_session_id,
    perceptual_visibility,
  });
  assert.equal(validated.accepted, true);
  await api.attachOpeningPerceptualVisibility({
    hg_session_id: created.hg_session_id,
    perceptual_visibility: validated.record,
  });

  const gate = await prepareIssue136CharacterManifestGate({
    api,
    hgSessionId: created.hg_session_id,
    truth,
  });
  const transcript = gate.analysis.recentSceneTranscript?.content ?? '';
  assert.match(transcript, /bracket/i);
  assert.doesNotMatch(transcript, /Colleague private thought/i);
});

test('issue136 Director manifest retains scene_setup separation while Character gets PVR transcript', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startIssue136DomainHost(sessionsDir, dataDir, t);
  const api = createDomainApiClient(host.baseUrl);
  const { created, truth } = await bootstrapSession(host, api, dataDir, '136-T2-F-ACTION-REQUIRED');
  const gate = await prepareIssue136CharacterManifestGate({
    api,
    hgSessionId: created.hg_session_id,
    truth,
    directorDecision: {
      next_actor: 'Mara',
      end_round: false,
      reason: 'advisory test cue',
      environment_event: 'A loose bolt clattered across the floor.',
      tension_shift: 'steady',
    },
  });

  assert.ok(gate.analysis.recentSceneTranscript);
  assert.match(gate.analysis.recentSceneTranscript.content, /bracket/i);
  assert.ok(gate.analysis.directorContext);
  assert.match(gate.analysis.directorContext.content, /loose bolt/i);
  assert.equal(gate.directorKinds.has('scene_setup'), false);
});

test('issue136 bootstrap attaches opening PVR to session history', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startIssue136DomainHost(sessionsDir, dataDir, t);
  const api = createDomainApiClient(host.baseUrl);
  const { created } = await bootstrapSession(host, api, dataDir, '136-T2-D-INACTION');
  const history = await api.getSessionHistory(created.hg_session_id);
  const opening = (history.entries ?? []).find((entry) => entry.kind === 'opening');
  assert.ok(opening);
  assert.ok(opening.metadata?.perceptual_visibility?.units?.length > 0);
  assert.equal(opening.metadata.perceptual_visibility.units[0].kind, 'observable_scene');
});
