import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  runPlotCognitionPendingWorkLifecycle,
  runPostCommitPlotCognitionLifecycle,
} from '../lib/plot-cognition-orchestration.mjs';
import { runPlotCognitionUpdateGeneration } from '../lib/plot-cognition-update-substrate.mjs';
import { manifestFromPlotCognitionUpdatePrepare } from '../lib/plot-cognition-update-envelope.mjs';
import { attachCharacterCognitionApiStubs } from '../../tests/helpers/character-cognition-mock.mjs';
import {
  instrumentProjectionApi,
  seedCharacterOverlayGoal,
} from '../../tests/helpers/plot-cognition-projection-fixtures.mjs';
import { startHarnessRuntime } from './harness-runtime.mjs';
import { createLiveHarnessRpContext, createLiveRuntimeConfig } from './live-config.mjs';
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
  readExecutionAttempts,
} from './forensic-query.mjs';
import { buildCampaignReport } from './campaign-report.mjs';
import { runCharacterProjectionLifecycleCaptured } from './character-projection-capture.mjs';
import {
  assertInvalidationInPrepareContext,
  assertObservableAnxietySupportInPrepare,
  assertSemanticAuthorityInPrepare,
  buildCharacterCertificationSubject,
  buildCharacterSemanticGates,
  buildInitializationObjectiveGates,
  buildPlotInitCertificationSubject,
  buildPlotUpdateCertificationSubject,
  createCharacterProjectionCapture,
  createPlotCognitionCapture,
  overlayHasPressureText,
  proveUnsafeCandidate,
  recordPlotInferenceCapture,
} from './production-capture.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../../..');

export const TREATY_BREACH_NARRATOR_PROSE = 'Before the gathered witnesses, Bob publicly renounced the reconciliation treaty; the accord was broken and could not be restored.';

export const TREATY_BREACH_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{
    type: 'action',
    action: 'publicly renounces the reconciliation treaty before the gathered witnesses',
  }],
  motivation: {
    goal: 'acknowledge breach',
    tactic: 'public statement',
    emotional_driver: 'resolved',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export const BOB_ANXIETY_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{
    type: 'action',
    action: 'fidgets nervously and admits he cannot stop thinking about the vault',
  }],
  motivation: {
    goal: 'express anxiety',
    tactic: 'visible tension',
    emotional_driver: 'anxious',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export function campaignDataRoot(tranche = 2) {
  return path.join(REPO_ROOT, 'data', 'storyteller_tier1_campaign', `tranche${tranche}`);
}

export function verifyDurableEvidence(dataDir, hgSessionId) {
  const attempts = readExecutionAttempts(dataDir, hgSessionId);
  return {
    queryable: attempts.length > 0,
    count: attempts.length,
    evidence_ids: attempts.map((a) => a.evidence_id ?? a.attempt_id).filter(Boolean),
  };
}

async function withLiveHarness(campaignLimits, campaignDataDir, fn) {
  const runtime = await startHarnessRuntime({
    dataDir: campaignDataDir,
    sessionsDir: path.join(campaignDataDir, 'sessions'),
    forensicsDir: path.join(campaignDataDir, 'plot_cognition_forensics'),
    executionEvidence: true,
  });
  const liveRuntimeConfig = createLiveRuntimeConfig();
  const rawStore = [];
  const { ctx: rpCtx, phaseExecutors, orchestrator } = await createLiveHarnessRpContext({
    baseUrl: runtime.baseUrl,
    dataDir: runtime.dataDir,
  });
  const instrumented = createInstrumentedInference({
    phaseExecutors,
    campaignLimits,
    runtimeConfig: liveRuntimeConfig,
    rawStore,
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
      rawStore,
      campaignDataDir,
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
  pressures = [],
} = {}) {
  const scopeId = `scope-live-${crypto.randomUUID()}`;
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  seedCharacterOverlayGoal(sessionsDir, scopeId, { characterId, direction, pressures });
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

function contributionTexts(contributions) {
  return (contributions ?? []).map((c) => String(c.content ?? ''));
}

function findRawByKind(rawStore, kind) {
  return rawStore.find((entry) => entry.inference_kind === kind) ?? null;
}

function durableEvidenceRef(dataDir, hgSessionId, evidenceIds) {
  return {
    data_dir: dataDir,
    hg_session_id: hgSessionId,
    evidence_ids: evidenceIds,
    store: 'execution_evidence',
  };
}

async function evaluateAndFinalize({
  caseId,
  scenarioId,
  truth,
  baseResult,
  evaluationSubject,
  evaluationTarget,
  instrumented,
  roleProfiles,
  evidenceContextBase,
  consumerTexts = [],
  targetCharacter = null,
  requireChronicle = false,
  productionCapture = null,
  dataDir = null,
  hgSessionId = null,
}) {
  const evalResult = await runCertificationEvaluator({
    runEphemeralInference: instrumented.runEphemeralInference,
    truth,
    evaluationSubject,
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
    requireEvidence: true,
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

  let durableCheck = null;
  if (dataDir && hgSessionId) {
    durableCheck = verifyDurableEvidence(dataDir, hgSessionId);
  }

  const result = attachSemanticCharacterization({
    ...baseResult,
    production_capture: productionCapture,
    durable_evidence: {
      ...(baseResult.durable_evidence ?? {}),
      post_teardown_query: durableCheck,
    },
    certification_class: 'live_semantic',
    inference_counts: summarizeInferenceCounts(instrumented.calls),
    evidence_ids: [
      ...(baseResult.evidence_ids ?? []),
      ...(evalResult.evidenceId ? [evalResult.evidenceId] : []),
    ],
    campaign: {
      case_id: caseId,
      tranche: 2,
      live_inference_summary: instrumented.summarize(),
      hard_blockers: blockerAnalysis,
      certification_evaluator: {
        ok: evalResult.ok,
        stage: evalResult.stage ?? null,
        evidence_id: evalResult.evidenceId ?? null,
        subject_kind: evaluationSubject?.kind ?? null,
      },
    },
  }, semantic);

  return { result, blockerAnalysis, evalResult, durableCheck };
}

export async function runC1_T1_01_live(campaignLimits, campaignDataDir) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-01-init');
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const { session, scopeId, hgSceneId } = await createAbsentOverlaySession(ctx.api);
    const plan = await ctx.api.planPostCommitPlotCognitionWork({ hg_scene_id: hgSceneId });
    capture.planner = { operation: plan.operation ?? null, reason: plan.reason ?? null };
    capture.operation = plan.operation ?? null;
    const overlayBefore = loadOverlayStore(ctx.sessionsDir, scopeId);
    capture.overlay_revision_before = overlayBefore?.store_revision ?? 0;
    const pendingBefore = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    capture.pending_before = pendingBefore?.pending_work ?? null;

    const lifecycle = await runPlotCognitionPendingWorkLifecycle({
      domainApi: ctx.api,
      hgSceneId,
      inferenceId: 'inf-live-init',
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: { hgSessionId: session.hg_session_id, hgSceneId },
    });

    const initRaw = findRawByKind(ctx.rawStore, 'plot_cognition_init');
    recordPlotInferenceCapture(capture, {
      inferRun: initRaw,
      stage: lifecycle.ok ? 'initialization' : lifecycle.stage,
      finalizeResponse: lifecycle.initFinalize,
    });
    capture.finalize_result = {
      accepted: lifecycle.initFinalize?.accepted === true,
      code: lifecycle.initFinalize?.code ?? null,
      message: lifecycle.initFinalize?.message ?? null,
    };

    const overlay = loadOverlayStore(ctx.sessionsDir, scopeId);
    capture.overlay_revision_after = overlay?.store_revision ?? 0;
    const pendingAfter = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: hgSceneId });
    capture.pending_after = pendingAfter?.pending_work ?? null;

    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId,
      hgSessionId: session.hg_session_id,
    });
    capture.chronicle_keys = forensics.chronicleKeys;
    capture.evidence_ids = forensics.evidenceIds;

    const gates = buildInitializationObjectiveGates({
      truth,
      plan,
      lifecycle,
      overlay,
      overlayRevisionBefore: capture.overlay_revision_before,
      scopeId,
      forensics,
      initRaw,
    });
    const objectiveGates = Object.fromEntries(
      Object.values(gates).map((entry) => [entry.name, gate(entry.name, entry.pass, entry.detail)]),
    );
    const base = finalizeScenarioResult(createScenarioResult('T1-01', {
      fixtureId: truth.fixture_id,
      objectiveGates,
      operationSequence: ['plan_initialization', 'live_init_inference', 'init_finalize'],
      evidenceIds: forensics.evidenceIds,
      chronicleKeys: forensics.chronicleKeys,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      durableEvidence: durableEvidenceRef(ctx.dataDir, session.hg_session_id, forensics.evidenceIds),
    }));

    return evaluateAndFinalize({
      caseId: 'C1',
      scenarioId: 'T1-01',
      truth,
      baseResult: base,
      evaluationSubject: buildPlotInitCertificationSubject({ capture, lifecycle, truth }),
      evaluationTarget: 'plot_cognition_init',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: { hgSessionId: session.hg_session_id, hgSceneId },
      requireChronicle: true,
      productionCapture: capture,
      dataDir: ctx.dataDir,
      hgSessionId: session.hg_session_id,
    });
  });
}

export async function runC2_T1_02_live(campaignLimits, campaignDataDir) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-02-no-replan');
  const pressureText = truth.unresolved_pressures?.[0] ?? 'Locate the key without alerting others.';
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      direction: 'Find the key quietly.',
      pressures: [{
        pressure_text: pressureText,
        dramatic_rationale: 'The search must stay discreet.',
      }],
    });
    const overlayPre = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    const pressureProof = overlayHasPressureText(overlayPre, pressureText);
    if (!pressureProof) {
      throw new Error('c2_pressure_missing_from_overlay');
    }

    const round = await ctx.orchestrator.runRound({
      domainApi: ctx.api,
      session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
      skipStorytellerCognition: true,
      skipPlotCognitionOrchestration: true,
      mockDirectorResponses: [directorFor('Alice')],
      mockCharacterTurnResponses: [[JSON.stringify(VALID_CHARACTER_MOVE)]],
      mockNarratorTurnResponses: [[NARRATOR_PROSE]],
    });

    capture.overlay_revision_before = overlayPre?.store_revision ?? 0;
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

    const updateRaw = findRawByKind(ctx.rawStore, 'plot_cognition_update');
    const updateResult = postCommit.updateResult ?? null;
    recordPlotInferenceCapture(capture, {
      inferRun: updateRaw,
      parsed: updateResult?.parsed,
      stage: updateResult?.stage ?? postCommit.stage,
      prepareResponse: updateResult?.prepareResponse,
      finalizeResponse: updateResult?.finalizeResponse,
    });
    capture.operation = postCommit.operation ?? postCommit.stage ?? null;

    const freshness = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
    const overlay = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    capture.overlay_revision_after = overlay?.store_revision ?? 0;
    capture.pending_after = freshness.pending_work ?? null;

    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });
    capture.chronicle_keys = forensics.chronicleKeys;
    capture.evidence_ids = forensics.evidenceIds;

    const gates = {
      pressure_in_overlay: gate('pressure_in_overlay', pressureProof),
      round_committed: gate('round_committed', round.committed === true),
      post_commit_ok: gate('post_commit_ok', postCommit.ok === true),
      update_no_replan: gate('update_no_replan', freshness.fresh === true && freshness.pending_work == null),
      no_pending_work: gate('no_pending_work', freshness.pending_work == null),
      update_raw_captured: gate('update_raw_captured', Boolean(updateRaw?.raw)),
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
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    return evaluateAndFinalize({
      caseId: 'C2',
      scenarioId: 'T1-02',
      truth,
      baseResult: base,
      evaluationSubject: buildPlotUpdateCertificationSubject({
        capture,
        updateResult,
        truth,
        overlayBefore: overlayPre,
        overlayAfter: overlay,
      }),
      evaluationTarget: 'plot_cognition_update',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
      productionCapture: capture,
      dataDir: ctx.dataDir,
      hgSessionId: ctxSession.session.hg_session_id,
    });
  });
}

export async function runC3_T1_03_live(campaignLimits, campaignDataDir) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTruthFixture('t1-03-replan');
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      direction: 'Pursue revenge against Bob for the broken treaty.',
    });
    const overlayBefore = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    capture.overlay_revision_before = overlayBefore?.store_revision ?? 0;

    const baselinePrepare = await ctx.api.preparePlotCognitionUpdate({
      hg_scene_id: ctxSession.hgSceneId,
      manifest_id: `manifest-pre-breach-${crypto.randomUUID()}`,
    });
    const baselineBody = baselinePrepare?.source_snapshot?.canonical_body ?? {};
    const baseline = {
      authority_source_fingerprint: baselinePrepare?.authority_source_fingerprint ?? null,
      committed_move_count: (baselineBody.committed_moves ?? []).length,
      public_event_count: (baselineBody.continuity?.public_events ?? []).length,
    };

    const breachRound = await ctx.orchestrator.runRound({
      domainApi: ctx.api,
      session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
      skipStorytellerCognition: true,
      skipPlotCognitionOrchestration: true,
      mockDirectorResponses: [directorFor('Alice')],
      mockCharacterTurnResponses: [[JSON.stringify(TREATY_BREACH_CHARACTER_MOVE)]],
      mockNarratorTurnResponses: [[TREATY_BREACH_NARRATOR_PROSE]],
    });
    if (breachRound.committed !== true) {
      throw new Error(`c3_breach_round_not_committed:${JSON.stringify({
        committed: breachRound.committed,
        stage: breachRound.stage ?? null,
        reason: breachRound.reason ?? null,
      })}`);
    }

    const prepareAfterBreach = await ctx.api.preparePlotCognitionUpdate({
      hg_scene_id: ctxSession.hgSceneId,
      manifest_id: `manifest-post-breach-${crypto.randomUUID()}`,
    });
    const invalidationProof = assertInvalidationInPrepareContext(prepareAfterBreach, baseline);
    const semanticProof = assertSemanticAuthorityInPrepare(prepareAfterBreach);
    capture.invalidation_proof = invalidationProof;
    capture.semantic_authority_proof = semanticProof;
    if (!invalidationProof.ok) {
      throw new Error('c3_invalidation_not_in_authority');
    }
    if (!semanticProof.ok) {
      throw new Error('c3_semantic_authority_missing_from_prepare');
    }
    capture.manifest_material = semanticProof.manifest_material;

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

    const updateRaw = findRawByKind(ctx.rawStore, 'plot_cognition_update');
    recordPlotInferenceCapture(capture, {
      inferRun: updateRaw ?? { raw: updateResult.inferRun?.raw },
      parsed: updateResult.parsed,
      stage: updateResult.stage,
      prepareResponse: updateResult.prepareResponse,
      finalizeResponse: updateResult.finalizeResponse,
    });

    const overlayAfter = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    capture.overlay_revision_after = overlayAfter?.store_revision ?? 0;
    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });
    capture.chronicle_keys = forensics.chronicleKeys;
    capture.evidence_ids = forensics.evidenceIds;

    const replanKeys = forensics.chronicleKeys.filter((k) => k.includes(':replan:'));
    const gates = {
      invalidation_in_authority: gate('invalidation_in_authority', invalidationProof.ok === true),
      semantic_authority_present: gate('semantic_authority_present', semanticProof.ok === true),
      update_ok: gate('update_ok', updateResult.ok === true),
      replan_recorded: gate(
        'replan_recorded',
        replanKeys.length > 0 || updateResult.finalizeResponse?.code === 'replan_committed',
      ),
      store_changed: gate(
        'store_changed',
        (overlayAfter?.store_revision ?? 0) > (overlayBefore?.store_revision ?? 0),
      ),
      update_raw_captured: gate('update_raw_captured', Boolean(updateRaw?.raw || updateResult.inferRun?.raw)),
    };
    const base = finalizeScenarioResult(createScenarioResult('T1-03', {
      fixtureId: truth.fixture_id,
      objectiveGates: gates,
      operationSequence: ['commit_treaty_breach', 'live_plot_cognition_update', 'replan_or_update'],
      overlayRevisions: [overlayBefore?.store_revision, overlayAfter?.store_revision],
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      notes: [updateResult.finalizeResponse?.code ?? updateResult.stage ?? 'unknown'],
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    return evaluateAndFinalize({
      caseId: 'C3',
      scenarioId: 'T1-03',
      truth,
      baseResult: base,
      evaluationSubject: buildPlotUpdateCertificationSubject({
        capture,
        updateResult,
        truth,
        overlayBefore,
        overlayAfter,
      }),
      evaluationTarget: 'plot_cognition_replan',
      instrumented: ctx.instrumented,
      roleProfiles: ctx.roleProfiles,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
      requireChronicle: true,
      productionCapture: capture,
      dataDir: ctx.dataDir,
      hgSessionId: ctxSession.session.hg_session_id,
    });
  });
}

async function runCharacterLiveCase({
  caseId,
  truth,
  direction,
  campaignLimits,
  campaignDataDir,
  requireChronicle = false,
  requireUnsafeProof = false,
  beforeProjection = null,
}) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const targetCharacter = truth.target_character ?? 'Alice';
    const capture = createCharacterProjectionCapture();
    capture.candidate_text = direction;
    capture.unsafe_proof = proveUnsafeCandidate(direction, truth, targetCharacter);
    if (requireUnsafeProof && !capture.unsafe_proof.unsafe) {
      throw new Error(`${caseId.toLowerCase()}_candidate_not_unsafe`);
    }

    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      cast: truth.characters ?? ['Alice', 'Bob'],
      characterId: targetCharacter,
      direction,
    });
    if (beforeProjection) {
      await beforeProjection(ctx, ctxSession, capture);
    }
    const instrumentedApi = instrumentProjectionApi(attachCharacterCognitionApiStubs(ctx.api));
    const { projection, capture: filledCapture } = await runCharacterProjectionLifecycleCaptured({
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
      capture,
      candidateText: direction,
    });
    Object.assign(capture, filledCapture);

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
    capture.character_storyteller_contributions = storyteller;
    capture.delivery_observed = storyteller.length > 0;
    const admittedTexts = contributionTexts(storyteller);

    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
      batchId: projection.finalized?.batch_id,
    });
    capture.evidence_ids = forensics.evidenceIds;
    capture.chronicle_keys = forensics.chronicleKeys;

    const evalCount = ctx.instrumented.calls.filter(
      (c) => c.live && c.inference_kind === 'plot_cognition_epistemic_eval',
    ).length;
    const regenCount = ctx.instrumented.calls.filter(
      (c) => c.live && c.inference_kind === 'character_advisory_generation',
    ).length;
    const chainGates = {
      projection_completed: gate('projection_completed', projection.ok === true || projection.stage != null),
      eval_bounded: gate('eval_bounded', evalCount <= 2),
      regen_bounded: gate('regen_bounded', regenCount <= 1),
      layer_b_chain_bounded: gate('layer_b_chain_bounded', evalCount + regenCount <= 3),
    };
    const semanticGates = buildCharacterSemanticGates({
      truth,
      capture,
      storytellerCount: storyteller.length,
      chainGates,
      admittedTexts: admittedTexts,
      targetCharacter,
      evalCount,
      regenCount,
    });
    const objectiveGates = Object.fromEntries(
      Object.values(semanticGates).map((entry) => [entry.name, gate(entry.name, entry.pass, entry.detail)]),
    );

    const base = finalizeScenarioResult(createScenarioResult(truth.scenario_id, {
      fixtureId: truth.fixture_id,
      objectiveGates,
      operationSequence: projection.callLog ?? ['layer_b_live'],
      regenerationCount: regenCount,
      consumerContributions: { character_storyteller: storyteller.length },
      withheld: storyteller.length === 0 ? [{ consumer: 'character', reason: capture.withheld_reason ?? 'withheld_or_failed' }] : [],
      evidenceIds: forensics.evidenceIds,
      chronicleKeys: forensics.chronicleKeys,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'live_semantic',
      notes: [
        `projection_ok=${projection.ok}`,
        `eval_count=${evalCount}`,
        `regen_count=${regenCount}`,
        `layer_b_verdict=${capture.layer_b.first?.verdict ?? 'none'}`,
      ],
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    return evaluateAndFinalize({
      caseId,
      scenarioId: truth.scenario_id,
      truth,
      baseResult: base,
      evaluationSubject: buildCharacterCertificationSubject({
        capture,
        truth,
        targetCharacter,
      }),
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
      productionCapture: capture,
      dataDir: ctx.dataDir,
      hgSessionId: ctxSession.session.hg_session_id,
    });
  });
}

export function runC4_T1_05_live(campaignLimits, campaignDataDir) {
  const truth = loadTruthFixture('t1-05-known-basis');
  return runCharacterLiveCase({
    caseId: 'C4',
    truth,
    direction: 'Find the key quietly without drawing attention.',
    campaignLimits,
    campaignDataDir,
    requireChronicle: true,
  });
}

export function runC5_T1_06_unsafe_live(campaignLimits, campaignDataDir) {
  const truth = loadTruthFixture('t1-06-unsafe-hidden');
  return runCharacterLiveCase({
    caseId: 'C5',
    truth,
    direction: 'Use Bob secret vault code 9999 to open the vault.',
    campaignLimits,
    campaignDataDir,
    requireChronicle: true,
  });
}

export async function seedC6ObservableContext({
  ctx,
  ctxSession,
  capture,
  inferenceId = 'inf-live-c6-pending',
  mockUpdateResponse = null,
}) {
  capture.observable_context_seed = {
    committed: false,
    character_id: 'Bob',
    hg_round_id: null,
  };

  const baselineUpdatePrepare = await ctx.api.preparePlotCognitionUpdate({
    hg_scene_id: ctxSession.hgSceneId,
    manifest_id: `manifest-c6-baseline-${inferenceId}`,
  });
  const baselineMoveCount = (
    baselineUpdatePrepare?.source_snapshot?.canonical_body?.committed_moves ?? []
  ).length;
  capture.observable_context_baseline = {
    committed_move_count: baselineMoveCount,
    manifest_id: baselineUpdatePrepare?.manifest_id ?? null,
  };

  const seedRound = await ctx.orchestrator.runRound({
    domainApi: ctx.api,
    session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [directorFor('Bob')],
    mockCharacterTurnResponses: [[JSON.stringify(BOB_ANXIETY_CHARACTER_MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });
  capture.observable_context_seed = {
    committed: seedRound.committed === true,
    character_id: 'Bob',
    hg_round_id: seedRound.hg_round_id ?? null,
  };
  if (seedRound.committed !== true) {
    throw new Error('c6_observable_context_seed_failed');
  }

  const freshnessBeforeLifecycle = await ctx.api.assessPlotCognitionFreshness({
    hg_scene_id: ctxSession.hgSceneId,
  });
  capture.plot_cognition_freshness_before = freshnessBeforeLifecycle;
  capture.plot_cognition_pending_before = freshnessBeforeLifecycle?.pending_work ?? null;
  if (freshnessBeforeLifecycle?.fresh !== false || !freshnessBeforeLifecycle?.pending_work) {
    throw new Error('c6_pending_work_missing_after_seed');
  }

  const lifecycle = await runPlotCognitionPendingWorkLifecycle({
    domainApi: ctx.api,
    hgSceneId: ctxSession.hgSceneId,
    inferenceId,
    runEphemeralInference: ctx.instrumented.runEphemeralInference,
    modelProfile: ctx.roleProfiles.storyteller,
    mockUpdateResponse,
    evidenceContextBase: {
      hgSessionId: ctxSession.session.hg_session_id,
      hgSceneId: ctxSession.hgSceneId,
      hgRoundId: ctxSession.hgRoundId,
    },
  });
  capture.plot_cognition_pending_lifecycle = {
    ok: lifecycle.ok === true,
    operation: lifecycle.operation ?? null,
    stage: lifecycle.stage ?? null,
    fresh_after: lifecycle.freshAfter === true,
    pending_preserved: lifecycle.pendingPreserved === true,
  };

  const freshnessAfterLifecycle = await ctx.api.assessPlotCognitionFreshness({
    hg_scene_id: ctxSession.hgSceneId,
  });
  capture.plot_cognition_freshness_after = freshnessAfterLifecycle;
  if (freshnessAfterLifecycle?.fresh !== true || freshnessAfterLifecycle?.pending_work != null) {
    throw new Error('c6_pending_work_not_cleared_before_projection');
  }

  const supportPrepare = await ctx.api.preparePlotCognitionUpdate({
    hg_scene_id: ctxSession.hgSceneId,
    manifest_id: `manifest-c6-support-${inferenceId}`,
  });
  const anxietySupport = assertObservableAnxietySupportInPrepare(supportPrepare, {
    baselineCommittedMoveCount: baselineMoveCount,
  });
  capture.observable_anxiety_support = anxietySupport;
  if (!anxietySupport.ok) {
    throw new Error('c6_observable_anxiety_support_lost_after_pending_lifecycle');
  }

  const nextRound = await ctx.api.startRound({ hg_scene_id: ctxSession.hgSceneId });
  ctxSession.hgRoundId = nextRound.hg_round_id;
  ctxSession.turnIndex = Number(nextRound.turn_index ?? ctxSession.turnIndex + 1);

  return {
    seedRound,
    lifecycle,
    freshnessBeforeLifecycle,
    freshnessAfterLifecycle,
    anxietySupport,
    nextRound,
  };
}

export function runC6_T1_06_safe_live(campaignLimits, campaignDataDir) {
  const truth = loadTruthFixture('t1-06-safe-translation');
  return runCharacterLiveCase({
    caseId: 'C6',
    truth,
    direction: 'Bob is anxious about vault security; encourage Alice to check in discreetly without revealing secrets.',
    campaignLimits,
    campaignDataDir,
    requireChronicle: true,
    beforeProjection: async (ctx, ctxSession, capture) => {
      await seedC6ObservableContext({ ctx, ctxSession, capture });
    },
  });
}

export function runC7_T1_07_live(campaignLimits, campaignDataDir) {
  const truth = loadTruthFixture('t1-07-regen');
  return runCharacterLiveCase({
    caseId: 'C7',
    truth,
    direction: 'Reveal the hidden vault location on the north wall panel to Alice.',
    campaignLimits,
    campaignDataDir,
    requireChronicle: true,
    requireUnsafeProof: true,
  });
}

export const TRANCHE2_CASES = [
  { id: 'C1', run: runC1_T1_01_live },
  { id: 'C2', run: runC2_T1_02_live },
  { id: 'C3', run: runC3_T1_03_live },
  { id: 'C4', run: runC4_T1_05_live },
  { id: 'C5', run: runC5_T1_06_unsafe_live },
  { id: 'C6', run: runC6_T1_06_safe_live },
  { id: 'C7', run: runC7_T1_07_live },
];

/**
 * Tranche-3 live-call ceiling (#65).
 * C1–C3 plot: primary + correction + cert = 3 each (9)
 * C4/C6 character safe path: eval + correction + cert = 3 each (6)
 * C5/C7 character regen path: 5 Layer-B chain + cert = 6 each (12)
 * Total = 27
 */
export const TRANCHE3_INFERENCE_CEILING = 27;

/**
 * Targeted C6-only revalidation (#65 remediation).
 * C1/C3 not rerun; C6 only.
 */
export const TARGETED_REVALIDATION_CASES = [
  { id: 'C6', run: runC6_T1_06_safe_live },
];

/**
 * C6 live-call ceiling (#65 final C6 revalidation):
 * pending Plot Cognition lifecycle: update + optional correction (2)
 * Character projection regen path: eval + correction + regen + eval + correction (5)
 * certification evaluator (1)
 */
export const TARGETED_REVALIDATION_CEILING = 8;

export async function runTargetedRevalidationCampaign(options = {}) {
  const limits = options.limits ?? new CampaignLimits({
    maxRuns: TARGETED_REVALIDATION_CASES.length,
    maxInferences: TARGETED_REVALIDATION_CEILING,
  });
  const trancheNumber = options.tranche ?? 4;
  const campaignDataDir = options.campaignDataDir
    ?? path.join(campaignDataRoot(trancheNumber), `run-${crypto.randomUUID()}`);
  const results = [];
  const hardBlockers = [];
  for (const entry of TARGETED_REVALIDATION_CASES) {
    if (limits.stopped) break;
    try {
      const { result, blockerAnalysis, durableCheck } = await entry.run(limits, campaignDataDir);
      results.push({
        case_id: entry.id,
        result,
        blockerAnalysis,
        durable_check: durableCheck,
      });
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
  return {
    ...buildCampaignReport({
      results,
      limits,
      hardBlockers,
      tranche: trancheNumber,
      schema: options.reportSchema ?? 'hg_storyteller_targeted_revalidation_report_v1',
    }),
    campaign_data_dir: campaignDataDir,
  };
}

export async function runTranche3Campaign(options = {}) {
  return runTranche2Campaign({
    ...options,
    limits: options.limits ?? new CampaignLimits({
      maxRuns: 7,
      maxInferences: TRANCHE3_INFERENCE_CEILING,
    }),
    tranche: 3,
    reportSchema: 'hg_storyteller_tranche3_report_v1',
  });
}

export async function runTranche2Campaign(options = {}) {
  const limits = options.limits ?? new CampaignLimits({
    maxRuns: 7,
    maxInferences: 18,
  });
  const trancheNumber = options.tranche ?? 2;
  const campaignDataDir = options.campaignDataDir
    ?? path.join(campaignDataRoot(trancheNumber), `run-${crypto.randomUUID()}`);
  const results = [];
  const hardBlockers = [];
  for (const entry of TRANCHE2_CASES) {
    if (limits.stopped) break;
    try {
      const { result, blockerAnalysis, durableCheck } = await entry.run(limits, campaignDataDir);
      results.push({
        case_id: entry.id,
        result,
        blockerAnalysis,
        durable_check: durableCheck,
      });
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
  return {
    ...buildCampaignReport({
      results,
      limits,
      hardBlockers,
      tranche: options.tranche ?? 2,
      schema: options.reportSchema ?? 'hg_storyteller_tranche2_report_v1',
    }),
    campaign_data_dir: campaignDataDir,
  };
}

// Exported helpers for deterministic gate tests
export function buildC2OverlayWithPressure(sessionsDir, scopeId, truth) {
  const pressureText = truth.unresolved_pressures?.[0] ?? 'Locate the key without alerting others.';
  seedCharacterOverlayGoal(sessionsDir, scopeId, {
    direction: 'Find the key quietly.',
    pressures: [{ pressure_text: pressureText }],
  });
  const overlay = loadOverlayStore(sessionsDir, scopeId);
  return { overlay, pressureText, hasPressure: overlayHasPressureText(overlay, pressureText) };
}

export function buildC3InvalidationProofFromPrepare(baselinePrepare, afterPrepare) {
  const baselineBody = baselinePrepare?.source_snapshot?.canonical_body ?? {};
  return assertInvalidationInPrepareContext(afterPrepare, {
    authority_source_fingerprint: baselinePrepare?.authority_source_fingerprint ?? null,
    committed_move_count: (baselineBody.committed_moves ?? []).length,
  });
}

export function buildCertificationSubjectForCase(caseId, fixtures = {}) {
  switch (caseId) {
    case 'C1':
      return buildPlotInitCertificationSubject(fixtures);
    case 'C2':
    case 'C3':
      return buildPlotUpdateCertificationSubject(fixtures);
    default:
      return buildCharacterCertificationSubject(fixtures);
  }
}

export function manifestMaterialFromPrepare(prepareResponse) {
  const manifest = manifestFromPlotCognitionUpdatePrepare(prepareResponse);
  return manifest.contributions?.[0]?.content ?? null;
}
