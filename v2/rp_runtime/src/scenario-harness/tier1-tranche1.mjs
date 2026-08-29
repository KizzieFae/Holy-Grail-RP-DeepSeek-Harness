import crypto from 'node:crypto';

import { runCharacterProjectionLifecycle } from '../plugins/hg-phase-executors/plot-cognition-character-projection.mjs';
import {
  runPlotCognitionPendingWorkLifecycle,
  runPostCommitPlotCognitionLifecycle,
} from '../lib/plot-cognition-orchestration.mjs';
import { runPlotCognitionUpdateGeneration } from '../lib/plot-cognition-update-substrate.mjs';
import { attachCharacterCognitionApiStubs } from '../../tests/helpers/character-cognition-mock.mjs';
import {
  instrumentProjectionApi,
  seedCharacterOverlayGoal,
} from '../../tests/helpers/plot-cognition-projection-fixtures.mjs';
import { startHarnessRuntime } from './harness-runtime.mjs';
import { createLiveHarnessRpContext, createLiveRuntimeConfig, describeResolvedProfiles } from './live-config.mjs';
import { CampaignLimits } from './campaign-limits.mjs';
import { loadTruthFixture } from './fixture-truth.mjs';
import { createInstrumentedInference } from './instrumented-inference.mjs';
import { runCertificationEvaluator } from './certification-evaluator.mjs';
import { analyzeHardBlockers } from './hard-blockers.mjs';
import { attachSemanticCharacterization } from './semantic-characterization.mjs';
import { createScenarioResult, finalizeScenarioResult, gate } from './scenario-result.mjs';
import {
  directorFor,
  NARRATOR_PROSE,
  summarizeInferenceCounts,
  VALID_CHARACTER_MOVE,
} from './inference-mocks.mjs';
import {
  joinScenarioForensics,
  loadOverlayStore,
} from './forensic-query.mjs';

async function withLiveHarness(campaignLimits, fn) {
  const runtime = await startHarnessRuntime();
  const liveRuntimeConfig = createLiveRuntimeConfig();
  const { ctx: rpCtx, phaseExecutors, orchestrator } = await createLiveHarnessRpContext({
    baseUrl: runtime.baseUrl,
    dataDir: runtime.dataDir,
  });
  const instrumented = createInstrumentedInference({
    phaseExecutors,
    campaignLimits,
    runtimeConfig: liveRuntimeConfig,
  });
  try {
    return await fn({
      ...runtime,
      rpCtx,
      phaseExecutors,
      orchestrator,
      instrumented,
      liveRuntimeConfig,
      roleProfiles: liveRuntimeConfig.roleProfiles,
    });
  } finally {
    await rpCtx.fiber.dispose();
    await runtime.dispose();
  }
}

async function createAbsentOverlaySession(api, cast = ['Alice', 'Bob']) {
  const scopeId = `scope-live-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  return { session, scopeId, hgSceneId: session.hg_scene_id };
}

async function createFreshOverlaySession(api, sessionsDir, {
  cast = ['Alice', 'Bob'],
  characterId = 'Alice',
  direction = 'Find the key quietly.',
} = {}) {
  const scopeId = `scope-live-${crypto.randomUUID()}`;
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

function overlaySummary(overlay) {
  if (!overlay) return '';
  return JSON.stringify({
    goals: overlay.goals ?? {},
    pressures: overlay.pressures ?? {},
    frame: overlay.active_frame ?? null,
  });
}

function contributionTexts(contributions) {
  return (contributions ?? []).map((c) => String(c.content ?? ''));
}

async function evaluateAndFinalize({
  caseId,
  scenarioId,
  truth,
  baseResult,
  outputText,
  evaluationTarget,
  instrumented,
  roleProfiles,
  evidenceContextBase,
  consumerTexts = [],
  targetCharacter = null,
  requireChronicle = false,
}) {
  const evalResult = await runCertificationEvaluator({
    runEphemeralInference: instrumented.runEphemeralInference,
    truth,
    outputText,
    evaluationTarget,
    scenarioId,
    modelProfile: roleProfiles.semantic_evaluator,
    evidenceContextBase,
  });

  const liveCalls = instrumented.calls.filter((c) => c.live);
  const blockerAnalysis = analyzeHardBlockers({
    scenarioResult: baseResult,
    truth,
    consumerTexts,
    targetCharacter,
    liveCalls,
    requireChronicle,
  });

  const semantic = evalResult.characterization ?? {
    rubric_version: 'hg_storyteller_semantic_rubric_v1',
    fixture_id: truth.fixture_id,
    repetition_index: 0,
    dimensions: {},
    categorical_findings: evalResult.ok ? [] : ['evaluator_unavailable'],
    governance_flags: evalResult.ok ? [] : ['manual_review_recommended'],
    evaluator_evidence_id: evalResult.evidenceId,
    notes: [evalResult.error ?? ''],
  };

  const result = attachSemanticCharacterization({
    ...baseResult,
    certification_class: 'live_semantic',
    inference_counts: summarizeInferenceCounts(instrumented.calls),
    evidence_ids: [
      ...(baseResult.evidence_ids ?? []),
      ...(evalResult.evidenceId ? [evalResult.evidenceId] : []),
    ],
    campaign: {
      case_id: caseId,
      live_inference_summary: instrumented.summarize(),
      hard_blockers: blockerAnalysis,
      certification_evaluator: {
        ok: evalResult.ok,
        stage: evalResult.stage ?? null,
        evidence_id: evalResult.evidenceId ?? null,
      },
    },
  }, semantic);

  return { result, blockerAnalysis, evalResult };
}

export async function runC1_T1_01_live(campaignLimits) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-01-init');
  return withLiveHarness(campaignLimits, async (ctx) => {
    const started = Date.now();
    const { session, scopeId, hgSceneId } = await createAbsentOverlaySession(ctx.api);
    const plan = await ctx.api.planPostCommitPlotCognitionWork({ hg_scene_id: hgSceneId });
    const lifecycle = await runPlotCognitionPendingWorkLifecycle({
      domainApi: ctx.api,
      hgSceneId,
      inferenceId: 'inf-live-init',
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: { hgSessionId: session.hg_session_id, hgSceneId },
    });
    const overlay = loadOverlayStore(ctx.sessionsDir, scopeId);
    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId,
      hgSessionId: session.hg_session_id,
    });
    const gates = {
      plan_initialization: gate('plan_initialization', plan.operation === 'initialization'),
      lifecycle_ok: gate('lifecycle_ok', lifecycle.ok === true),
      overlay_ready: gate('overlay_ready', overlay && Object.keys(overlay.pressures ?? {}).length > 0),
      chronicle_present: gate('chronicle_present', forensics.chronicleKeys.some((k) => k.includes(':init:'))),
    };
    const base = finalizeScenarioResult(createScenarioResult('T1-01', {
      fixtureId: truth.fixture_id,
      objectiveGates: gates,
      operationSequence: ['plan_initialization', 'live_init_inference', 'init_finalize'],
      evidenceIds: forensics.evidenceIds,
      chronicleKeys: forensics.chronicleKeys,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
    }));
    return evaluateAndFinalize({
      caseId: 'C1',
      scenarioId: 'T1-01',
      truth,
      baseResult: base,
      outputText: overlaySummary(overlay),
      evaluationTarget: 'plot_cognition_init',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: { hgSessionId: session.hg_session_id, hgSceneId },
      requireChronicle: true,
    });
  });
}

export async function runC2_T1_02_live(campaignLimits) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-02-no-replan');
  return withLiveHarness(campaignLimits, async (ctx) => {
    const started = Date.now();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir);
    const round = await ctx.orchestrator.runRound({
      domainApi: ctx.api,
      session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
      skipStorytellerCognition: true,
      skipPlotCognitionOrchestration: true,
      mockDirectorResponses: [directorFor('Alice')],
      mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
      mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    });
    const postCommit = await runPostCommitPlotCognitionLifecycle({
      domainApi: ctx.api,
      hgSceneId: ctxSession.hgSceneId,
      inferenceId: 'inf-live-t1-02-update',
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
        hgRoundId: round.hg_round_id,
      },
    });
    const freshness = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
    const overlay = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });
    const gates = {
      round_committed: gate('round_committed', round.committed === true),
      post_commit_ok: gate('post_commit_ok', postCommit.ok === true),
      update_no_replan: gate('update_no_replan', freshness.fresh === true && freshness.pending_work == null),
      no_pending_work: gate('no_pending_work', freshness.pending_work == null),
    };
    const base = finalizeScenarioResult(createScenarioResult('T1-02', {
      fixtureId: truth.fixture_id,
      objectiveGates: gates,
      operationSequence: ['controlled_round', 'live_post_commit_plot_cognition'],
      evidenceIds: forensics.evidenceIds,
      chronicleKeys: forensics.chronicleKeys,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      notes: [postCommit.operation ?? postCommit.stage ?? 'post_commit'],
    }));
    return evaluateAndFinalize({
      caseId: 'C2',
      scenarioId: 'T1-02',
      truth,
      baseResult: base,
      outputText: overlaySummary(overlay),
      evaluationTarget: 'plot_cognition_update',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
    });
  });
}

export async function runC3_T1_03_live(campaignLimits) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-03-replan');
  return withLiveHarness(campaignLimits, async (ctx) => {
    const started = Date.now();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      direction: 'Pursue revenge against Bob for the broken treaty.',
    });
    const overlayBefore = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    const updateResult = await runPlotCognitionUpdateGeneration({
      domainApi: ctx.api,
      hgSceneId: ctxSession.hgSceneId,
      inferenceId: 'inf-live-replan',
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
    });
    const overlayAfter = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });
    const replanKeys = forensics.chronicleKeys.filter((k) => k.includes(':replan:'));
    const gates = {
      update_ok: gate('update_ok', updateResult.ok === true),
      replan_recorded: gate(
        'replan_recorded',
        replanKeys.length > 0 || updateResult.finalizeResponse?.code === 'replan_committed',
      ),
      store_changed: gate(
        'store_changed',
        (overlayAfter?.store_revision ?? 0) > (overlayBefore?.store_revision ?? 0),
      ),
    };
    const base = finalizeScenarioResult(createScenarioResult('T1-03', {
      fixtureId: truth.fixture_id,
      objectiveGates: gates,
      operationSequence: ['live_plot_cognition_update', 'replan_or_update'],
      overlayRevisions: [overlayBefore?.store_revision, overlayAfter?.store_revision],
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      notes: [updateResult.finalizeResponse?.code ?? updateResult.stage ?? 'unknown'],
    }));
    return evaluateAndFinalize({
      caseId: 'C3',
      scenarioId: 'T1-03',
      truth,
      baseResult: base,
      outputText: [
        updateResult.inferRun?.raw ?? '',
        overlaySummary(overlayAfter),
      ].join('\n'),
      evaluationTarget: 'plot_cognition_replan',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
      requireChronicle: true,
    });
  });
}

async function runCharacterLiveCase({
  caseId,
  truth,
  direction,
  campaignLimits,
  requireChronicle = false,
}) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  return withLiveHarness(campaignLimits, async (ctx) => {
    const started = Date.now();
    const targetCharacter = truth.target_character ?? 'Alice';
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      cast: truth.characters ?? ['Alice', 'Bob'],
      characterId: targetCharacter,
      direction,
    });
    const instrumentedApi = instrumentProjectionApi(attachCharacterCognitionApiStubs(ctx.api));
    const projection = await runCharacterProjectionLifecycle({
      api: instrumentedApi,
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      scope: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
        hgRoundId: ctxSession.hgRoundId,
      },
      hgSceneId: ctxSession.hgSceneId,
      hgRoundId: ctxSession.hgRoundId,
      characterId: targetCharacter,
      inferenceId: `inf-live-${caseId}`,
      turnIndex: ctxSession.turnIndex,
      modelProfile: ctx.roleProfiles.plot_cognition_epistemic_evaluator,
    });
    const context = projection.ok
      ? await instrumentedApi.prepareCharacterContext({
        hg_scene_id: ctxSession.hgSceneId,
        hg_round_id: ctxSession.hgRoundId,
        inference_id: `inf-live-${caseId}`,
        character_id: targetCharacter,
        role: 'guest',
        turn_index: ctxSession.turnIndex,
        attempt_index: 0,
        plot_cognition_finalized_projection: projection.finalized ? {
          batch_id: projection.finalized.batch_id,
          binding_digest: projection.finalized.binding_digest,
          binding: projection.finalized.binding,
          contributions: projection.finalized.contributions,
        } : undefined,
      })
      : null;
    const storyteller = (context?.contributions ?? []).filter((c) => (
      String(c.source_kind ?? '').startsWith('storyteller')
    ));
    const admittedTexts = contributionTexts(storyteller);
    const candidateTexts = contributionTexts(projection.finalized?.contributions ?? []);
    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
      batchId: projection.finalized?.batch_id,
    });
    const evalCount = ctx.instrumented.calls.filter(
      (c) => c.live && c.inference_kind === 'plot_cognition_epistemic_eval',
    ).length;
    const regenCount = ctx.instrumented.calls.filter(
      (c) => c.live && c.inference_kind === 'character_advisory_generation',
    ).length;
    const gates = {
      projection_completed: gate('projection_completed', projection.ok === true || projection.stage != null),
      eval_bounded: gate('eval_bounded', evalCount <= 2),
      regen_bounded: gate('regen_bounded', regenCount <= 1),
      layer_b_chain_bounded: gate('layer_b_chain_bounded', evalCount + regenCount <= 3),
    };
    const base = finalizeScenarioResult(createScenarioResult(truth.scenario_id, {
      fixtureId: truth.fixture_id,
      objectiveGates: gates,
      operationSequence: projection.callLog ?? ['layer_b_live'],
      regenerationCount: regenCount,
      consumerContributions: { character_storyteller: storyteller.length },
      withheld: storyteller.length === 0 ? [{ consumer: 'character', reason: 'withheld_or_failed' }] : [],
      evidenceIds: forensics.evidenceIds,
      chronicleKeys: forensics.chronicleKeys,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      notes: [
        `projection_ok=${projection.ok}`,
        `eval_count=${evalCount}`,
        `regen_count=${regenCount}`,
      ],
    }));
    return evaluateAndFinalize({
      caseId,
      scenarioId: truth.scenario_id,
      truth,
      baseResult: base,
      outputText: [...candidateTexts, ...admittedTexts].join('\n'),
      evaluationTarget: `character:${targetCharacter}`,
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
      consumerTexts: admittedTexts,
      targetCharacter,
      requireChronicle,
    });
  });
}

export function runC4_T1_05_live(campaignLimits) {
  const truth = loadTruthFixture('t1-05-known-basis');
  return runCharacterLiveCase({
    caseId: 'C4',
    truth,
    direction: 'Find the key quietly without drawing attention.',
    campaignLimits,
    requireChronicle: true,
  });
}

export function runC5_T1_06_unsafe_live(campaignLimits) {
  const truth = loadTruthFixture('t1-06-unsafe-hidden');
  return runCharacterLiveCase({
    caseId: 'C5',
    truth,
    direction: 'Use Bob secret vault code 9999 to open the vault.',
    campaignLimits,
    requireChronicle: true,
  });
}

export function runC6_T1_06_safe_live(campaignLimits) {
  const truth = loadTruthFixture('t1-06-safe-translation');
  return runCharacterLiveCase({
    caseId: 'C6',
    truth,
    direction: 'Bob is anxious about vault security; encourage Alice to check in discreetly without revealing secrets.',
    campaignLimits,
    requireChronicle: true,
  });
}

export function runC7_T1_07_live(campaignLimits) {
  const truth = loadTruthFixture('t1-07-regen');
  return runCharacterLiveCase({
    caseId: 'C7',
    truth,
    direction: 'Reveal the hidden vault location on the north wall panel to Alice.',
    campaignLimits,
    requireChronicle: true,
  });
}

export const TRANCHE1_CASES = [
  { id: 'C1', run: runC1_T1_01_live },
  { id: 'C2', run: runC2_T1_02_live },
  { id: 'C3', run: runC3_T1_03_live },
  { id: 'C4', run: runC4_T1_05_live },
  { id: 'C5', run: runC5_T1_06_unsafe_live },
  { id: 'C6', run: runC6_T1_06_safe_live },
  { id: 'C7', run: runC7_T1_07_live },
];

export async function runTranche1Campaign(options = {}) {
  const limits = options.limits ?? new CampaignLimits({
    maxRuns: 7,
    maxInferences: 25,
  });
  const results = [];
  const hardBlockers = [];
  for (const entry of TRANCHE1_CASES) {
    if (limits.stopped) break;
    try {
      const { result, blockerAnalysis } = await entry.run(limits);
      results.push({ case_id: entry.id, result, blockerAnalysis });
      if (blockerAnalysis.has_blocker) {
        hardBlockers.push(...blockerAnalysis.blockers.map((b) => ({ case_id: entry.id, ...b })));
        limits.stop(`hard_blocker:${entry.id}`);
        break;
      }
    } catch (error) {
      results.push({ case_id: entry.id, error: String(error?.message ?? error) });
      if (String(error?.message ?? error).includes('campaign_')) {
        limits.stop(String(error.message));
        break;
      }
      throw error;
    }
  }
  return buildCampaignReport({ results, limits, hardBlockers });
}

function buildCampaignReport({ results, limits, hardBlockers }) {
  const profiles = describeResolvedProfiles(createLiveRuntimeConfig());
  const allLiveCalls = [];
  let totalTokensIn = 0;
  let totalTokensOut = 0;
  for (const entry of results) {
    const summary = entry.result?.campaign?.live_inference_summary;
    if (summary?.calls) allLiveCalls.push(...summary.calls.filter((c) => c.live));
  }
  for (const call of allLiveCalls) {
    const usage = call.usage ?? {};
    const input = Number(usage.input_tokens ?? usage.inputTokens ?? 0);
    const output = Number(usage.output_tokens ?? usage.outputTokens ?? 0);
    if (input) totalTokensIn += input;
    if (output) totalTokensOut += output;
  }
  return {
    schema: 'hg_storyteller_tranche1_report_v1',
    tranche: 1,
    limits: limits.snapshot(),
    resolved_profiles: profiles,
    results,
    hard_blockers: hardBlockers,
    totals: {
      scenario_runs: results.length,
      live_inference_calls: allLiveCalls.length,
      by_kind: allLiveCalls.reduce((acc, call) => {
        const kind = call.inference_kind ?? 'unknown';
        acc[kind] = (acc[kind] ?? 0) + 1;
        return acc;
      }, {}),
      tokens: {
        input: totalTokensIn || null,
        output: totalTokensOut || null,
        total: (totalTokensIn || totalTokensOut) ? totalTokensIn + totalTokensOut : null,
        unavailable: totalTokensIn === 0 && totalTokensOut === 0,
      },
      latency_ms: {
        per_inference: allLiveCalls.map((c) => ({
          inference_id: c.inference_id,
          kind: c.inference_kind,
          duration_ms: c.duration_ms,
        })),
        per_scenario: results.map((r) => ({
          case_id: r.case_id,
          total_ms: r.result?.phase_durations_ms?.total ?? null,
        })),
      },
    },
  };
}
