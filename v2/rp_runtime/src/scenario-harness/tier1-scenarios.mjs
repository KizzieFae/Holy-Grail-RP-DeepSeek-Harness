import crypto from 'node:crypto';

import { createHolyGrailRpContext } from '../bootstrap.mjs';
import { runCharacterProjectionLifecycle } from '../plugins/hg-phase-executors/plot-cognition-character-projection.mjs';
import {
  runPlotCognitionPendingWorkLifecycle,
  buildNoChangeUpdateInference,
} from '../lib/plot-cognition-orchestration.mjs';
import { runPlotCognitionUpdateGeneration } from '../lib/plot-cognition-update-substrate.mjs';
import { attachCharacterCognitionApiStubs } from '../../tests/helpers/character-cognition-mock.mjs';
import {
  instrumentProjectionApi,
  seedCharacterOverlayGoal,
  seedEmptyOverlayStore,
} from '../../tests/helpers/plot-cognition-projection-fixtures.mjs';
import { startHarnessRuntime, createHarnessRpContext } from './harness-runtime.mjs';
import {
  buildInitProposal,
  buildReplanUpdateInference,
  createTrackingInference,
  directorFor,
  epistemicPass,
  epistemicRewriteRequired,
  epistemicWithhold,
  NARRATOR_PROSE,
  semanticPassCharacter,
  summarizeInferenceCounts,
  VALID_CHARACTER_MOVE,
} from './inference-mocks.mjs';
import {
  chronicleKeysForScope,
  evidenceIdsForSession,
  findEvidenceByKind,
  joinScenarioForensics,
  loadOverlayStore,
} from './forensic-query.mjs';
import { createScenarioResult, finalizeScenarioResult, gate } from './scenario-result.mjs';

async function withHarness(fn) {
  const runtime = await startHarnessRuntime();
  try {
    return await fn({ ...runtime, baseUrl: runtime.baseUrl });
  } finally {
    await runtime.dispose();
  }
}

async function createAbsentOverlaySession(api, cast = ['Alice', 'Bob']) {
  const scopeId = `scope-tier1-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  return { session, scopeId, hgSceneId: session.hg_scene_id };
}

async function createFreshOverlaySession(api, sessionsDir, {
  cast = ['Alice', 'Bob'],
  characterId = 'Alice',
  direction = 'Find the key quietly.',
} = {}) {
  const scopeId = `scope-tier1-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  seedCharacterOverlayGoal(sessionsDir, scopeId, { characterId, direction });
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

export async function runT1_01() {
  return withHarness(async ({ api, baseUrl, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const { session, scopeId, hgSceneId } = await createAbsentOverlaySession(api);
    const plan = await api.planPostCommitPlotCognitionWork({ hg_scene_id: hgSceneId });
    const { ctx: rpCtx, phaseExecutors } = await createHarnessRpContext({ baseUrl, dataDir });
    try {
      const lifecycle = await runPlotCognitionPendingWorkLifecycle({
        domainApi: api,
        hgSceneId,
        inferenceId: 'inf-tier1-init',
        runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
        mockInitResponse: (initPrepare) => buildInitProposal(initPrepare),
        evidenceContextBase: {
          hgSessionId: session.hg_session_id,
          hgSceneId,
        },
      });
      const freshness = await api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
      const overlay = loadOverlayStore(sessionsDir, scopeId);
      const forensics = joinScenarioForensics({
        forensicsDir,
        dataDir,
        scopeId,
        hgSessionId: session.hg_session_id,
      });
      const gates = {
        plan_initialization: gate('plan_initialization', plan.operation === 'initialization'),
        lifecycle_ok: gate(
          'lifecycle_ok',
          lifecycle.ok === true && lifecycle.operation === 'initialization',
        ),
        overlay_ready: gate('overlay_ready', overlay && Object.keys(overlay.pressures ?? {}).length > 0),
        freshness_fresh: gate('freshness_fresh', freshness.fresh === true),
        chronicle_present: gate('chronicle_present', forensics.chronicleKeys.some((k) => k.includes(':init:'))),
      };
      return finalizeScenarioResult(createScenarioResult('T1-01', {
        fixtureId: scopeId,
        objectiveGates: gates,
        operationSequence: ['plan_initialization', 'init_prepare', 'init_finalize'],
        overlayRevisions: [overlay?.store_revision ?? null],
        evidenceIds: forensics.evidenceIds,
        chronicleKeys: forensics.chronicleKeys,
        integrityGaps: forensics.chronicleKeys.some((k) => k.includes(':init:'))
          ? []
          : ['missing_chronicle_init'],
        phaseDurationsMs: { total: Date.now() - started },
        notes: [
          'Integrated path: pending-work plan → runPlotCognitionPendingWorkLifecycle initialization.',
          'Absent overlay fresh:true is non-stale for consumers; initialization routing is separate.',
        ],
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_02() {
  return withHarness(async ({ api, baseUrl, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const { ctx: rpCtx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
    try {
      const result = await orchestrator.runRound({
        domainApi: api,
        session: { mode: 'open', hg_session_id: ctx.session.hg_session_id },
        skipStorytellerCognition: true,
        mockDirectorResponses: [directorFor('Alice')],
        mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
        mockNarratorTurnResponses: [[NARRATOR_PROSE]],
        mockPlotCognitionUpdateResponses: (prepareResponse) => buildNoChangeUpdateInference(prepareResponse),
      });
      const freshness = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
      const forensics = joinScenarioForensics({
        forensicsDir,
        dataDir,
        scopeId: ctx.scopeId,
        hgSessionId: ctx.session.hg_session_id,
      });
      const gates = {
        round_committed: gate('round_committed', result.committed === true),
        update_no_replan: gate('update_no_replan', freshness.fresh === true && freshness.pending_work == null),
        no_pending_work: gate('no_pending_work', freshness.pending_work == null),
      };
      return finalizeScenarioResult(createScenarioResult('T1-02', {
        fixtureId: ctx.scopeId,
        objectiveGates: gates,
        operationSequence: ['semantic_update', 'no_change'],
        evidenceIds: forensics.evidenceIds,
        chronicleKeys: forensics.chronicleKeys,
        integrityGaps: [],
        phaseDurationsMs: { total: Date.now() - started },
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_03() {
  return withHarness(async ({ api, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const overlayBefore = loadOverlayStore(sessionsDir, ctx.scopeId);
    const oldGoalIds = Object.keys(overlayBefore?.goals ?? {});
    const { runEphemeralInference, calls } = createTrackingInference();
    const updateResult = await runPlotCognitionUpdateGeneration({
      domainApi: api,
      hgSceneId: ctx.hgSceneId,
      inferenceId: 'inf-tier1-replan',
      runEphemeralInference,
      mockResponse: (prepareResponse) => buildReplanUpdateInference(prepareResponse, {
        supersededGoalId: oldGoalIds[0] ?? 'hg-plot-goal-superseded',
      }),
    });
    const overlayAfter = loadOverlayStore(sessionsDir, ctx.scopeId);
    const forensics = joinScenarioForensics({
      forensicsDir,
      dataDir,
      scopeId: ctx.scopeId,
      hgSessionId: ctx.session.hg_session_id,
    });
    const replanKeys = forensics.chronicleKeys.filter((k) => k.includes(':replan:'));
    const gates = {
      update_ok: gate('update_ok', updateResult.ok === true),
      replan_recorded: gate(
        'replan_recorded',
        replanKeys.length > 0 || updateResult.finalizeResponse?.code === 'replan_committed',
      ),
      store_changed: gate('store_changed', (overlayAfter?.store_revision ?? 0) > (overlayBefore?.store_revision ?? 0)),
      distinct_from_update: gate(
        'distinct_from_update',
        replanKeys.length > 0 || updateResult.finalizeResponse?.code === 'replan_committed',
      ),
    };
    return finalizeScenarioResult(createScenarioResult('T1-03', {
      fixtureId: ctx.scopeId,
      objectiveGates: gates,
      operationSequence: ['semantic_update', 'replan'],
      overlayRevisions: [overlayBefore?.store_revision, overlayAfter?.store_revision],
      inferenceCounts: summarizeInferenceCounts(calls),
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      integrityGaps: [],
      phaseDurationsMs: { total: Date.now() - started },
    }));
  });
}

export async function runT1_04() {
  return withHarness(async ({ api, baseUrl, sessionsDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const freshDirector = await api.prepareDirectorContext({
      hg_scene_id: ctx.hgSceneId,
      hg_round_id: ctx.hgRoundId,
      inference_id: 'inf-tier1-dir-fresh',
      turn_index: ctx.turnIndex,
      attempt_index: 0,
    });
    const { ctx: rpCtx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
    try {
      await orchestrator.runRound({
        domainApi: api,
        session: { mode: 'open', hg_session_id: ctx.session.hg_session_id },
        skipStorytellerCognition: true,
        mockDirectorResponses: [directorFor('Alice')],
        mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
        mockNarratorTurnResponses: [[NARRATOR_PROSE]],
        mockPlotCognitionUpdateResponses: [JSON.stringify({ schema: 'invalid' })],
      });
      const stale = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
      const staleDirector = await api.prepareDirectorContext({
        hg_scene_id: ctx.hgSceneId,
        hg_round_id: ctx.hgRoundId,
        inference_id: 'inf-tier1-dir-stale',
        turn_index: ctx.turnIndex,
        attempt_index: 0,
      });
      const freshText = (freshDirector.contributions ?? []).map((c) => c.content).join('\n');
      const staleText = (staleDirector.contributions ?? []).map((c) => c.content).join('\n');
      const gates = {
        fresh_has_overlay: gate('fresh_has_overlay', freshText.includes('Find the key')),
        stale_withholds_overlay: gate('stale_withholds_overlay', !staleText.includes('Find the key')),
        freshness_barrier: gate('freshness_barrier', stale.fresh === false),
      };
      return finalizeScenarioResult(createScenarioResult('T1-04', {
        fixtureId: ctx.scopeId,
        objectiveGates: gates,
        operationSequence: ['director_projection_fresh', 'post_commit_stale', 'director_projection_stale'],
        consumerContributions: { director_fresh: freshText.length, director_stale: staleText.length },
        phaseDurationsMs: { total: Date.now() - started },
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_05() {
  return withHarness(async ({ api, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const instrumented = instrumentProjectionApi(attachCharacterCognitionApiStubs(api));
    const { runEphemeralInference, calls } = createTrackingInference([epistemicPass()]);
    const projection = await runCharacterProjectionLifecycle({
      api: instrumented,
      runEphemeralInference,
      scope: { hgSessionId: ctx.session.hg_session_id },
      hgSceneId: ctx.hgSceneId,
      hgRoundId: ctx.hgRoundId,
      characterId: 'Alice',
      inferenceId: 'inf-tier1-pass',
      turnIndex: ctx.turnIndex,
    });
    const context = projection.ok
      ? await instrumented.prepareCharacterContext({
        hg_scene_id: ctx.hgSceneId,
        hg_round_id: ctx.hgRoundId,
        inference_id: 'inf-tier1-pass',
        character_id: 'Alice',
        role: 'guest',
        turn_index: ctx.turnIndex,
        attempt_index: 0,
        plot_cognition_finalized_projection: {
          batch_id: projection.finalized.batch_id,
          binding_digest: projection.finalized.binding_digest,
          binding: projection.finalized.binding,
          contributions: projection.finalized.contributions,
        },
      })
      : null;
    const storyteller = (context?.contributions ?? []).filter((c) => (
      String(c.source_kind ?? '').startsWith('storyteller')
    ));
    const forensics = joinScenarioForensics({
      forensicsDir,
      dataDir,
      scopeId: ctx.scopeId,
      hgSessionId: ctx.session.hg_session_id,
      batchId: projection.finalized?.batch_id,
    });
    const gates = {
      projection_ok: gate('projection_ok', projection.ok === true),
      layer_b_once: gate('layer_b_once', calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval').length === 1),
      contribution_admitted: gate('contribution_admitted', storyteller.length > 0),
    };
    return finalizeScenarioResult(createScenarioResult('T1-05', {
      fixtureId: ctx.scopeId,
      objectiveGates: gates,
      operationSequence: ['projection_prepare', 'layer_b_eval', 'projection_finalize', 'character_context'],
      inferenceCounts: summarizeInferenceCounts(calls),
      consumerContributions: { character_storyteller: storyteller.length },
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      integrityGaps: [],
      phaseDurationsMs: { total: Date.now() - started },
    }));
  });
}

export async function runT1_06() {
  return withHarness(async ({ api, sessionsDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir, {
      cast: ['Alice', 'Bob'],
      characterId: 'Alice',
      direction: 'Use Bob secret vault code 9999.',
    });
    const instrumented = instrumentProjectionApi(attachCharacterCognitionApiStubs(api));
    const { runEphemeralInference, calls } = createTrackingInference([epistemicWithhold()]);
    const projection = await runCharacterProjectionLifecycle({
      api: instrumented,
      runEphemeralInference,
      scope: { hgSessionId: ctx.session.hg_session_id },
      hgSceneId: ctx.hgSceneId,
      hgRoundId: ctx.hgRoundId,
      characterId: 'Alice',
      inferenceId: 'inf-tier1-isolation',
      turnIndex: ctx.turnIndex,
    });
    const context = await instrumented.prepareCharacterContext({
      hg_scene_id: ctx.hgSceneId,
      hg_round_id: ctx.hgRoundId,
      inference_id: 'inf-tier1-isolation',
      character_id: 'Alice',
      role: 'guest',
      turn_index: ctx.turnIndex,
      attempt_index: 0,
      ...(projection.ok && projection.finalized ? {
        plot_cognition_finalized_projection: {
          batch_id: projection.finalized.batch_id,
          binding_digest: projection.finalized.binding_digest,
          binding: projection.finalized.binding,
          contributions: projection.finalized.contributions,
        },
      } : {}),
    });
    const storyteller = (context?.contributions ?? []).filter((c) => (
      String(c.source_kind ?? '').startsWith('storyteller')
    ));
    const gates = {
      layer_b_withhold: gate('layer_b_withhold', projection.ok === false || (projection.finalized?.contributions ?? []).length === 0),
      no_storyteller_in_context: gate('no_storyteller_in_context', storyteller.length === 0),
      no_hidden_leak: gate('no_hidden_leak', !(context?.contributions ?? []).some((c) => String(c.content).includes('9999'))),
    };
    return finalizeScenarioResult(createScenarioResult('T1-06', {
      fixtureId: ctx.scopeId,
      objectiveGates: gates,
      operationSequence: ['layer_b_withhold'],
      inferenceCounts: summarizeInferenceCounts(calls),
      withheld: [{ consumer: 'character', reason: 'layer_b_withhold' }],
      phaseDurationsMs: { total: Date.now() - started },
      notes: ['Cross-Character hidden-basis candidate withheld at Layer B.'],
    }));
  });
}

export async function runT1_07() {
  return withHarness(async ({ api, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir, {
      direction: 'Reveal hidden vault [[REWRITE]]',
    });
    const instrumented = instrumentProjectionApi(attachCharacterCognitionApiStubs(api));
    const { runEphemeralInference, calls } = createTrackingInference();
    const projection = await runCharacterProjectionLifecycle({
      api: instrumented,
      runEphemeralInference,
      scope: { hgSessionId: ctx.session.hg_session_id },
      hgSceneId: ctx.hgSceneId,
      hgRoundId: ctx.hgRoundId,
      characterId: 'Alice',
      inferenceId: 'inf-tier1-regen',
      turnIndex: ctx.turnIndex,
      mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
      mockRegenerationResponses: ['Revised advisory without hidden vault details.'],
    });
    const evalCount = calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval').length;
    const regenCount = calls.filter((c) => c.inferenceKind === 'character_advisory_generation').length;
    const forensics = joinScenarioForensics({
      forensicsDir,
      dataDir,
      scopeId: ctx.scopeId,
      hgSessionId: ctx.session.hg_session_id,
      batchId: projection.finalized?.batch_id,
    });
    const gates = {
      regen_bounded: gate('regen_bounded', regenCount <= 1),
      eval_bounded: gate('eval_bounded', evalCount <= 2),
      admitted_after_regen: gate('admitted_after_regen', projection.ok === true),
      two_evals_when_regen: gate('two_evals_when_regen', evalCount === 2 && regenCount === 1),
    };
    return finalizeScenarioResult(createScenarioResult('T1-07', {
      fixtureId: ctx.scopeId,
      objectiveGates: gates,
      operationSequence: ['layer_b_eval', 'regeneration', 'layer_b_eval_2', 'finalize'],
      inferenceCounts: summarizeInferenceCounts(calls),
      regenerationCount: regenCount,
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      integrityGaps: [],
      phaseDurationsMs: { total: Date.now() - started },
    }));
  });
}

export async function runT1_08() {
  return withHarness(async ({ api, baseUrl, sessionsDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const { ctx: rpCtx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
    try {
      await orchestrator.runRound({
        domainApi: api,
        session: { mode: 'open', hg_session_id: ctx.session.hg_session_id },
        skipStorytellerCognition: true,
        mockDirectorResponses: [directorFor('Alice')],
        mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
        mockNarratorTurnResponses: [[NARRATOR_PROSE]],
        mockPlotCognitionUpdateResponses: [JSON.stringify({ schema: 'invalid' })],
      });
      const stale = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
      const director = await api.prepareDirectorContext({
        hg_scene_id: ctx.hgSceneId,
        hg_round_id: ctx.hgRoundId,
        inference_id: 'inf-tier1-stale',
        turn_index: ctx.turnIndex,
        attempt_index: 0,
      });
      const directorText = (director.contributions ?? []).map((c) => c.content).join('\n');
      const gates = {
        stale_flag: gate('stale_flag', stale.fresh === false),
        pending_preserved: gate('pending_preserved', stale.pending_work != null),
        overlay_withheld: gate('overlay_withheld', !directorText.includes('Find the key')),
      };
      return finalizeScenarioResult(createScenarioResult('T1-08', {
        fixtureId: ctx.scopeId,
        objectiveGates: gates,
        operationSequence: ['post_commit_failure', 'freshness_barrier'],
        withheld: [{ consumer: 'director', reason: 'stale_overlay' }],
        phaseDurationsMs: { total: Date.now() - started },
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_09() {
  return withHarness(async ({ api, baseUrl, sessionsDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const { ctx: rpCtx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
    try {
      await orchestrator.runRound({
        domainApi: api,
        session: { mode: 'open', hg_session_id: ctx.session.hg_session_id },
        skipStorytellerCognition: true,
        mockDirectorResponses: [directorFor('Alice')],
        mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
        mockNarratorTurnResponses: [[NARRATOR_PROSE]],
        mockPlotCognitionUpdateResponses: [JSON.stringify({ schema: 'invalid' })],
      });
      const before = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
      const lifecycle = await runPlotCognitionPendingWorkLifecycle({
        domainApi: api,
        hgSceneId: ctx.hgSceneId,
        inferenceId: 'inf-tier1-resume',
        runEphemeralInference: async () => ({ failed: true, failure: 'timeout' }),
        mockUpdateResponse: null,
      });
      const after = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
      const gates = {
        pending_before: gate('pending_before', before.pending_work != null),
        pending_preserved_on_fail: gate('pending_preserved_on_fail', lifecycle.pendingPreserved === true),
        still_stale: gate('still_stale', after.fresh === false),
        rediscovered: gate('rediscovered', lifecycle.operation === 'semantic_update' || before.pending_work != null),
      };
      return finalizeScenarioResult(createScenarioResult('T1-09', {
        fixtureId: ctx.scopeId,
        objectiveGates: gates,
        operationSequence: ['pending_work', 'resume_attempt', 'pending_preserved'],
        phaseDurationsMs: { total: Date.now() - started },
        notes: ['Domain-owned pending work; not #66 transient projection batch.'],
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_10() {
  return withHarness(async ({ api, baseUrl, sessionsDir, forensicsDir, dataDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const instrumented = instrumentProjectionApi(attachCharacterCognitionApiStubs(api));
    const { ctx: rpCtx, phaseExecutors } = await createHarnessRpContext({ baseUrl, dataDir });
    try {
      const projection = await runCharacterProjectionLifecycle({
        api: instrumented,
        runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
        mockEpistemicResponses: [epistemicPass()],
        scope: {
          hgSessionId: ctx.session.hg_session_id,
          hgSceneId: ctx.hgSceneId,
          hgRoundId: ctx.hgRoundId,
        },
        hgSceneId: ctx.hgSceneId,
        hgRoundId: ctx.hgRoundId,
        characterId: 'Alice',
        inferenceId: 'inf-tier1-forensic-pass',
        turnIndex: ctx.turnIndex,
      });
      const passEvalEvidence = findEvidenceByKind(
        dataDir,
        ctx.session.hg_session_id,
        'plot_cognition_epistemic_eval',
      );
      const forensics = joinScenarioForensics({
        forensicsDir,
        dataDir,
        scopeId: ctx.scopeId,
        hgSessionId: ctx.session.hg_session_id,
        batchId: projection.finalized?.batch_id,
      });

      const ctxRegen = await createFreshOverlaySession(api, sessionsDir, {
        direction: 'Reveal hidden vault [[REWRITE]]',
      });
      const projectionRegen = await runCharacterProjectionLifecycle({
        api: instrumented,
        runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
        mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
        mockRegenerationResponses: ['Revised advisory without hidden vault details.'],
        scope: {
          hgSessionId: ctxRegen.session.hg_session_id,
          hgSceneId: ctxRegen.hgSceneId,
          hgRoundId: ctxRegen.hgRoundId,
        },
        hgSceneId: ctxRegen.hgSceneId,
        hgRoundId: ctxRegen.hgRoundId,
        characterId: 'Alice',
        inferenceId: 'inf-tier1-forensic-regen',
        turnIndex: ctxRegen.turnIndex,
      });
      const regenEvalEvidence = findEvidenceByKind(
        dataDir,
        ctxRegen.session.hg_session_id,
        'plot_cognition_epistemic_eval',
      );
      const regenGenEvidence = findEvidenceByKind(
        dataDir,
        ctxRegen.session.hg_session_id,
        'character_advisory_generation',
      );
      const regenForensics = joinScenarioForensics({
        forensicsDir,
        dataDir,
        scopeId: ctxRegen.scopeId,
        hgSessionId: ctxRegen.session.hg_session_id,
        batchId: projectionRegen.finalized?.batch_id,
      });

      const gates = {
        pass_projection_ok: gate('pass_projection_ok', projection.ok === true),
        pass_evidence_on_disk: gate('pass_evidence_on_disk', passEvalEvidence.length >= 1),
        pass_chronicle_linked: gate(
          'pass_chronicle_linked',
          forensics.chronicleKeys.some((k) => k.includes(':projection:')),
        ),
        regen_projection_ok: gate('regen_projection_ok', projectionRegen.ok === true),
        regen_eval_evidence_on_disk: gate('regen_eval_evidence_on_disk', regenEvalEvidence.length === 2),
        regen_generator_evidence_on_disk: gate(
          'regen_generator_evidence_on_disk',
          regenGenEvidence.length === 1,
        ),
        regen_chronicle_linked: gate(
          'regen_chronicle_linked',
          regenForensics.chronicleKeys.some((k) => k.includes(':projection:')),
        ),
      };
      const durableEvidence = {
        pass: {
          evidence_ids: passEvalEvidence.map((entry) => entry.evidence_id),
          chronicle_keys: forensics.chronicleKeys.filter((k) => k.includes(':projection:')),
        },
        regen: {
          eval_evidence_ids: regenEvalEvidence.map((entry) => entry.evidence_id),
          generator_evidence_ids: regenGenEvidence.map((entry) => entry.evidence_id),
          chronicle_keys: regenForensics.chronicleKeys.filter((k) => k.includes(':projection:')),
        },
      };
      return finalizeScenarioResult(createScenarioResult('T1-10', {
        fixtureId: ctx.scopeId,
        objectiveGates: gates,
        operationSequence: ['layer_b_pass', 'projection_finalize', 'layer_b_regen_chain'],
        evidenceIds: [
          ...passEvalEvidence.map((entry) => entry.evidence_id),
          ...regenEvalEvidence.map((entry) => entry.evidence_id),
          ...regenGenEvidence.map((entry) => entry.evidence_id),
        ],
        chronicleKeys: [...forensics.chronicleKeys, ...regenForensics.chronicleKeys],
        durableEvidence,
        integrityGaps: [],
        phaseDurationsMs: { total: Date.now() - started },
        notes: ['Durable execution-evidence recorder via production inference substrate.'],
      }));
    } finally {
      await rpCtx.fiber.dispose();
    }
  });
}

export async function runT1_11() {
  return withHarness(async ({ api, sessionsDir }) => {
    const started = Date.now();
    const ctx = await createFreshOverlaySession(api, sessionsDir);
    const instrumented = instrumentProjectionApi(attachCharacterCognitionApiStubs(api));
    const { runEphemeralInference, calls } = createTrackingInference();
    async function failingInference(args) {
      calls.push({ ...args, failed: true });
      return {
        failed: true,
        raw: '',
        evidenceId: `ev-fail-${args.inferenceId}`,
        inferenceSessionId: `sess-fail-${args.inferenceId}`,
        trace: {},
      };
    }
    const projection = await runCharacterProjectionLifecycle({
      api: instrumented,
      runEphemeralInference: failingInference,
      scope: { hgSessionId: ctx.session.hg_session_id },
      hgSceneId: ctx.hgSceneId,
      hgRoundId: ctx.hgRoundId,
      characterId: 'Alice',
      inferenceId: 'inf-tier1-degrade',
      turnIndex: ctx.turnIndex,
    });
    const gates = {
      fail_closed: gate(
        'fail_closed',
        (projection.finalized?.contributions ?? []).length === 0,
      ),
      lifecycle_completes: gate('lifecycle_completes', projection.ok === true),
      evaluator_called: gate('evaluator_called', calls.length > 0),
    };
    return finalizeScenarioResult(createScenarioResult('T1-11', {
      fixtureId: ctx.scopeId,
      objectiveGates: gates,
      operationSequence: ['evaluator_failure', 'withhold'],
      withheld: [{ consumer: 'character', reason: 'evaluator_unavailable' }],
      inferenceCounts: summarizeInferenceCounts(calls),
      phaseDurationsMs: { total: Date.now() - started },
    }));
  });
}

export const TIER1_SCENARIOS = [
  { id: 'T1-01', run: runT1_01, deterministic: true },
  { id: 'T1-02', run: runT1_02, deterministic: true },
  { id: 'T1-03', run: runT1_03, deterministic: true },
  { id: 'T1-04', run: runT1_04, deterministic: true },
  { id: 'T1-05', run: runT1_05, deterministic: true },
  { id: 'T1-06', run: runT1_06, deterministic: true },
  { id: 'T1-07', run: runT1_07, deterministic: true },
  { id: 'T1-08', run: runT1_08, deterministic: true },
  { id: 'T1-09', run: runT1_09, deterministic: true },
  { id: 'T1-10', run: runT1_10, deterministic: true },
  { id: 'T1-11', run: runT1_11, deterministic: true },
];

export async function runAllTier1Scenarios({ filter = null } = {}) {
  const selected = filter
    ? TIER1_SCENARIOS.filter((s) => filter.includes(s.id))
    : TIER1_SCENARIOS;
  const results = [];
  for (const scenario of selected) {
    results.push(await scenario.run());
  }
  return results;
}

export async function runTier1Scenario(scenarioId) {
  const scenario = TIER1_SCENARIOS.find((s) => s.id === scenarioId);
  if (!scenario) throw new Error(`unknown_tier1_scenario:${scenarioId}`);
  return scenario.run();
}
