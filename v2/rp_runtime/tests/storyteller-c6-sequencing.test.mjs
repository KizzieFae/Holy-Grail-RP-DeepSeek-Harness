import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { buildNoChangeUpdateInference } from '../src/lib/plot-cognition-update-envelope.mjs';
import { runPlotCognitionPendingWorkLifecycle } from '../src/lib/plot-cognition-orchestration.mjs';
import {
  assertObservableAnxietySupportInPrepare,
  createCharacterProjectionCapture,
} from '../src/scenario-harness/production-capture.mjs';
import {
  BOB_ANXIETY_CHARACTER_MOVE,
  seedC6ObservableContext,
} from '../src/scenario-harness/tier1-tranche2.mjs';
import { directorFor, NARRATOR_PROSE } from '../src/scenario-harness/inference-mocks.mjs';
import { seedCharacterOverlayGoal } from './helpers/plot-cognition-projection-fixtures.mjs';
import { startDomainApi, makeTempSessionsDir } from './helpers/domain-api.mjs';

async function mockRunEphemeralInference({ mockResponses = [], inferenceId = 'inf-mock' }) {
  return {
    failed: false,
    raw: mockResponses[0] ?? '{}',
    evidenceId: `ev-${inferenceId}`,
    inferenceSessionId: `sess-${inferenceId}`,
    trace: {},
  };
}

async function setupC6Session(api, sessionsDir) {
  const scopeId = `scope-c6-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast: ['Alice', 'Bob'], memory_scope_id: scopeId });
  seedCharacterOverlayGoal(sessionsDir, scopeId, { characterId: 'Alice' });
  await api.finalizePlotCognitionReconciliation({ hg_scene_id: session.hg_scene_id });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  return {
    session,
    scopeId,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    turnIndex: Number(round.turn_index ?? 0),
  };
}

test('C6 sequencing: Bob seed records pending work then lifecycle restores freshness', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const host = await startDomainApi(undefined, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const api = createDomainApiClient(baseUrl);
  const ctxSession = await setupC6Session(api, sessionsDir);
  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const seedRound = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [directorFor('Bob')],
    mockCharacterTurnResponses: [[JSON.stringify(BOB_ANXIETY_CHARACTER_MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });
  assert.equal(seedRound.committed, true);

  const stale = await api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
  assert.equal(stale.fresh, false);
  assert.ok(stale.pending_work);

  const lifecycle = await runPlotCognitionPendingWorkLifecycle({
    domainApi: api,
    hgSceneId: ctxSession.hgSceneId,
    inferenceId: 'inf-c6-pending-seq',
    runEphemeralInference: mockRunEphemeralInference,
    mockUpdateResponse: (prepareResponse) => buildNoChangeUpdateInference(prepareResponse),
  });
  assert.equal(lifecycle.ok, true);
  assert.equal(lifecycle.freshAfter, true);

  const fresh = await api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
  assert.equal(fresh.fresh, true);
  assert.equal(fresh.pending_work, null);

  const supportPrepare = await api.preparePlotCognitionUpdate({
    hg_scene_id: ctxSession.hgSceneId,
    manifest_id: 'manifest-c6-seq-support',
  });
  const support = assertObservableAnxietySupportInPrepare(supportPrepare);
  assert.equal(support.ok, true, JSON.stringify(support));
});

test('assertObservableAnxietySupportInPrepare detects Bob vault anxiety move', () => {
  const proof = assertObservableAnxietySupportInPrepare({
    source_snapshot: {
      canonical_body: {
        committed_moves: [{
          character_id: 'Bob',
          beats: [{ action: BOB_ANXIETY_CHARACTER_MOVE.beats[0].action }],
        }],
      },
    },
  });
  assert.equal(proof.ok, true);
  assert.equal(proof.bob_move_observed, true);
});

test('seedC6ObservableContext helper enforces pending clearance and support retention', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const dataDir = path.join(path.dirname(sessionsDir), 'c6-data');
  const forensicsDir = path.join(dataDir, 'plot_cognition_forensics');
  fs.mkdirSync(forensicsDir, { recursive: true });
  const host = await startDomainApi(undefined, {
    sessionsDir,
    hostEnv: {
      HG_DATA_DIR: dataDir,
      HG_SESSIONS_DIR: sessionsDir,
      HG_PLOT_COGNITION_FORENSICS_DIR: forensicsDir,
    },
  });
  t.after(() => host.stop());

  const api = createDomainApiClient(host.baseUrl);
  const ctxSession = await setupC6Session(api, sessionsDir);
  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const capture = createCharacterProjectionCapture();
  const result = await seedC6ObservableContext({
    ctx: {
      api,
      orchestrator,
      instrumented: {
        runEphemeralInference: mockRunEphemeralInference,
      },
      roleProfiles: { storyteller: { provider: 'mock', model: 'mock' } },
    },
    ctxSession,
    capture,
    inferenceId: 'inf-c6-helper',
    mockUpdateResponse: (prepareResponse) => buildNoChangeUpdateInference(prepareResponse),
  });

  assert.equal(result.freshnessBeforeLifecycle.fresh, false);
  assert.ok(result.freshnessBeforeLifecycle.pending_work);
  assert.equal(result.freshnessAfterLifecycle.fresh, true);
  assert.equal(result.anxietySupport.ok, true);
  assert.equal(capture.plot_cognition_pending_lifecycle.ok, true);
  assert.equal(capture.observable_anxiety_support.ok, true);
});
