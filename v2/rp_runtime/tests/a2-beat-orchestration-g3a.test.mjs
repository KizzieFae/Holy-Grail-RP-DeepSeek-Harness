import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { SessionId } from '@deepseek-ai/dsh-session';

import { runA2BeatRound, A2_TOPOLOGY_ABSENT } from '../src/lib/a2-beat-orchestration.mjs';
import { deriveObligationSignals } from '../src/lib/a2-obligation-dispatch.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { mockInferenceProfile, resolveRoleProfiles } from '../src/lib/inference-profile.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice responds.',
  environment_event: '',
  tension_shift: '',
};

test('isolation: production bootstrap does not import A2 orchestrator', async () => {
  const bootstrapPath = path.resolve('src/bootstrap.mjs');
  const mountPath = path.resolve('src/lib/mount-hg-services.mjs');
  const bootstrapText = fs.readFileSync(bootstrapPath, 'utf8');
  const mountText = fs.readFileSync(mountPath, 'utf8');
  assert.equal(bootstrapText.includes('a2-beat-orchestration'), false);
  assert.equal(mountText.includes('a2-beat-orchestration'), false);
});

test('obligation dispatch: simple beat does not authorize removed cognition', () => {
  const dispatch = deriveObligationSignals({
    scenarioKey: 'ayame_controlled',
    eligibleActors: ['ayame'],
    roleAssignments: { ayame: 'host' },
    uniformProjectionEligible: true,
  });
  assert.equal(dispatch.beat_class, 'simple');
  for (const blocked of [
    'storyteller_preamble',
    'narrator_semantic_qa',
    'llm_obligation_router',
  ]) {
    assert.ok(dispatch.not_authorized.includes(blocked));
  }
});

test('A2 simple path: character → commit → narrator with absent A4 cognition', async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-g3a-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const host = await startDomainApi(undefined, { sessionsDir, hostEnv: { HG_DATA_DIR: dataDir } });
  t.after(() => host.stop());

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { defaultProfile: mockInferenceProfile() },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const createRes = await fetch(`${host.baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  });
  const session = await createRes.json();
  const hgSessionId = session.hg_session_id;

  const apiMod = await import('../src/lib/domain-api-client.mjs');
  const api = apiMod.createDomainApiClient(host.baseUrl);
  await api.recordUserTurn({
    hg_session_id: hgSessionId,
    content: 'Knock.',
    speaker: 'Player',
  });

  const sceneSessionId = SessionId(`hg-a2-test-${Date.now()}`);
  const sceneAgent = ctx.agentLoop.create(sceneSessionId, { kind: 'mock' });
  const roleProfiles = resolveRoleProfiles({
    roleProfiles: {
      character: mockInferenceProfile(),
      narrator: mockInferenceProfile(),
      director: mockInferenceProfile(),
      semantic_evaluator: mockInferenceProfile(),
    },
  }, {});

  const result = await runA2BeatRound({
    phaseExecutors,
    api,
    trace: ctx.hgTraceEmitter,
    sceneAgent,
    sceneSessionId,
    hgSessionId,
    hgSceneId: hgSessionId,
    options: {
      scenarioKey: 'ayame_controlled',
      roleAssignments: { Alice: 'guest' },
      roleProfiles,
      uniformProjectionEligible: true,
      mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
      mockCharacterResponses: [JSON.stringify(VALID_MOVE)],
      mockNarratorResponses: ['Alice nodded, taking in the room.'],
      presentationSpatialClaims: {
        schema: 'hg_presentation_spatial_claims_v1',
        claims: [],
      },
    },
  });

  assert.equal(result.architecture_arm, 'a2_prototype');
  assert.equal(result.committed, true);
  assert.equal(result.topology_proof.two_call_contract, true);
  assert.equal(result.topology_proof.character_semantic_evaluation_enabled, false);
  assert.equal(result.topology_proof.director_llm_invoked, false);
  for (const absent of A2_TOPOLOGY_ABSENT) {
    assert.ok(result.topology_proof.absent.includes(absent));
  }

  const stepNames = result.audit_steps.map((s) => s.step);
  assert.ok(stepNames.indexOf('character_cognition') < stepNames.indexOf('authoritative_commit'));
  assert.ok(stepNames.indexOf('authoritative_commit') < stepNames.indexOf('narrator_cognition'));
  const kinds = result.decision_value.records.map((r) => r.inference_kind);
  assert.ok(kinds.includes('character_move'));
  assert.ok(kinds.includes('narrator_presentation'));
  assert.equal(kinds.includes('director_turn'), false);
});

test('entitlement: character manifest excludes director scratch', async (t) => {
  const port = 25765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { withSession: true });
  t.after(() => host.stop());

  const round = await fetch(`${host.baseUrl}/v1/rounds/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_scene_id: host.scene.hg_session_id }),
  }).then((r) => r.json());

  const character = await fetch(`${host.baseUrl}/v1/context/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_scene_id: host.scene.hg_session_id,
      hg_round_id: round.hg_round_id,
      inference_id: 'inf-char-ent',
      character_id: 'Alice',
      role: 'guest',
      turn_index: round.turn_index,
      attempt_index: 0,
    }),
  }).then((r) => r.json());

  const kinds = new Set(character.contributions.map((c) => c.source_kind));
  assert.equal(kinds.has('character_private'), true);
  assert.equal(kinds.has('director_scratch'), false);
});
