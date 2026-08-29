import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import {
  PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
  buildNoChangeUpdateInference,
  parsePlotCognitionUpdateInference,
} from '../src/lib/plot-cognition-update-envelope.mjs';
import { runPlotCognitionPendingWorkLifecycle } from '../src/lib/plot-cognition-orchestration.mjs';
import { startDomainApi, makeTempSessionsDir } from './helpers/domain-api.mjs';

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'checks the latch carefully' }],
  motivation: {
    goal: 'inspect',
    tactic: 'slow check',
    emotional_driver: 'wary',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak next.`,
  environment_event: '',
  tension_shift: 'steady',
});

const NARRATOR_PROSE = 'Alice checked the latch with deliberate care.';

async function setupPlotCognitionSession(api, sessionsDir, cast = ['Alice']) {
  const scopeId = `scope-plot-orch-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  seedEmptyOverlayStore(sessionsDir, scopeId);
  return { session, scopeId, hgSceneId: session.hg_scene_id };
}

function seedEmptyOverlayStore(sessionsDir, scopeId) {
  const overlayDir = path.join(sessionsDir, '_plot_cognition_overlay');
  fs.mkdirSync(overlayDir, { recursive: true });
  const safe = scopeId.replace(/\//g, '_').replace(/\\/g, '_');
  const payload = {
    store_schema: 'hg_plot_cognition_overlay_store_v1',
    plot_cognition_scope_id: scopeId,
    store_revision: 1,
    assimilated_through_domain_commit_id: null,
    goals: {},
    pressures: {},
    active_frame: null,
  };
  fs.writeFileSync(path.join(overlayDir, `${safe}.json`), JSON.stringify(payload));
}

test('parsePlotCognitionUpdateInference accepts no_change payload', () => {
  const prepareResponse = {
    manifest_id: 'manifest-test',
    authority_source_fingerprint: 'fp-1',
    prior_store_revision: 1,
    source_snapshot: {
      snapshot_id: 'snap-1',
      plot_cognition_scope_id: 'scope-1',
      prior_store_revision: 1,
      authority_source_fingerprint: 'fp-1',
      canonical_body: { scene: 'hall' },
    },
  };
  const parsed = parsePlotCognitionUpdateInference(
    buildNoChangeUpdateInference(prepareResponse),
    prepareResponse,
  );
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.update_evaluation.overall_result, 'no_change');
  assert.equal(parsed.result.update_proposal.schema, 'hg_plot_cognition_update_proposal_v1');
});

test('plot cognition orchestration: reconciliation then pending work cleared on semantic no_change', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const port = 47765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const api = createDomainApiClient(baseUrl);
  const { session, hgSceneId } = await setupPlotCognitionSession(api, sessionsDir);

  const reconciliation = await api.finalizePlotCognitionReconciliation({ hg_scene_id: hgSceneId });
  assert.equal(reconciliation.accepted, true);

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: session.hg_session_id },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    mockPlotCognitionUpdateResponses: (prepareResponse) => buildNoChangeUpdateInference(prepareResponse),
  });

  assert.equal(result.committed, true);
  const freshness = await api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
  assert.equal(freshness.fresh, true);
  assert.equal(freshness.pending_work, null);

  const plotJoin = result.scene_events.find((event) => event.type === 'hg/plot-cognition-join');
  assert.ok(plotJoin);
  assert.equal(plotJoin.data.ok, true);
  assert.equal(plotJoin.data.fresh_after, true);
});

test('plot cognition orchestration: failure preserves pending work', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const port = 48765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const api = createDomainApiClient(baseUrl);
  const { session, hgSceneId } = await setupPlotCognitionSession(api, sessionsDir);

  await api.finalizePlotCognitionReconciliation({ hg_scene_id: hgSceneId });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: session.hg_session_id },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    mockPlotCognitionUpdateResponses: [JSON.stringify({ schema: 'invalid' })],
  });

  assert.equal(result.committed, true);
  const freshness = await api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
  assert.equal(freshness.fresh, false);
  assert.ok(freshness.pending_work);
});

test('plot cognition resume discovers pending work without commit callback', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const port = 49765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const api = createDomainApiClient(baseUrl);
  const { session, hgSceneId } = await setupPlotCognitionSession(api, sessionsDir);

  await api.finalizePlotCognitionReconciliation({ hg_scene_id: hgSceneId });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: session.hg_session_id },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    mockPlotCognitionUpdateResponses: [JSON.stringify({ schema: 'invalid' })],
  });

  const staleAfterCommit = await api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
  assert.equal(staleAfterCommit.fresh, false);
  assert.ok(staleAfterCommit.pending_work);

  const lifecycle = await runPlotCognitionPendingWorkLifecycle({
    domainApi: api,
    hgSceneId,
    inferenceId: 'inf-plot-cog-resume-test',
    runEphemeralInference: async () => ({ failed: true, failure: 'timeout' }),
    mockUpdateResponse: null,
  });
  assert.equal(lifecycle.pendingPreserved, true);
  const freshAfterFail = await api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
  assert.equal(freshAfterFail.fresh, false);
});
