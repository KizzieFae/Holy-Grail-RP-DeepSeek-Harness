import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { runPlotCognitionPendingWorkLifecycle } from '../lib/plot-cognition-orchestration.mjs';
import { runPlotCognitionUpdateGeneration } from '../lib/plot-cognition-update-substrate.mjs';
import { CampaignLimits } from './campaign-limits.mjs';
import { loadTier2TruthFixture } from './fixture-truth.mjs';
import { analyzeHardBlockers } from './hard-blockers.mjs';
import { directorFor, NARRATOR_PROSE, VALID_CHARACTER_MOVE } from './inference-mocks.mjs';
import {
  assertInvalidationInPrepareContext,
  assertSemanticAuthorityInPrepare,
  buildPlotUpdateCertificationSubject,
  createPlotCognitionCapture,
  recordPlotInferenceCapture,
} from './production-capture.mjs';
import { createScenarioResult, finalizeScenarioResult, gate } from './scenario-result.mjs';
import { joinScenarioForensics, loadOverlayStore } from './forensic-query.mjs';
import { buildCampaignReport } from './campaign-report.mjs';
import { classifyReplanJudgment, summarizePhaseDMetrics } from './phase-d-analysis.mjs';
import {
  BOB_ANXIETY_CHARACTER_MOVE,
  TREATY_BREACH_CHARACTER_MOVE,
  TREATY_BREACH_NARRATOR_PROSE,
  campaignDataRoot,
  createFreshOverlaySession,
  durableEvidenceRef,
  evaluateAndFinalize,
  withLiveHarness,
} from './tier1-tranche2.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../../..');

export const PHASE_D_INFERENCE_CEILING = 40;

export const VAULT_SEALED_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'welds reinforced bars across the vault entrance, sealing it permanently' }],
  motivation: { goal: 'secure vault', tactic: 'permanent seal', emotional_driver: 'decisive', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export const EMPTY_PANEL_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'opens the north wall panel and finds the compartment completely empty' }],
  motivation: { goal: 'verify location', tactic: 'inspect panel', emotional_driver: 'frustrated', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export const DOOR_SLAM_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'startles at a distant slamming door but continues searching quietly' }],
  motivation: { goal: 'keep searching', tactic: 'ignore distraction', emotional_driver: 'focused', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export const GUARDS_PATROL_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'spots guards now patrolling the corridor near the workshop' }],
  motivation: { goal: 'assess risk', tactic: 'observe patrol', emotional_driver: 'wary', risk_level: 'medium' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export const GUARDS_DEPART_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'watches the guards leave the corridor for the night' }],
  motivation: { goal: 'note relief', tactic: 'observe departure', emotional_driver: 'cautious', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const SEED_LIBRARY = {
  treaty_breach: {
    character: 'Alice',
    move: TREATY_BREACH_CHARACTER_MOVE,
    prose: TREATY_BREACH_NARRATOR_PROSE,
  },
  vault_sealed: {
    character: 'Bob',
    move: VAULT_SEALED_CHARACTER_MOVE,
    prose: 'Bob welded reinforced bars across the vault entrance; the path inside was sealed for good.',
  },
  empty_panel: {
    character: 'Alice',
    move: EMPTY_PANEL_CHARACTER_MOVE,
    prose: 'Alice opened the north wall panel and found the compartment empty; the key was not there.',
  },
  door_slam: {
    character: 'Alice',
    move: DOOR_SLAM_CHARACTER_MOVE,
    prose: 'A distant door slammed through the workshop, but nothing blocked the quiet search.',
  },
  guards_patrol: {
    character: 'Alice',
    move: GUARDS_PATROL_CHARACTER_MOVE,
    prose: 'Guards began patrolling the corridor near the workshop, tightening the margin for error.',
  },
  guards_depart: {
    character: 'Alice',
    move: GUARDS_DEPART_CHARACTER_MOVE,
    prose: 'The guards left the corridor for the night, easing the immediate patrol pressure.',
  },
  bob_anxiety: {
    character: 'Bob',
    move: BOB_ANXIETY_CHARACTER_MOVE,
    prose: NARRATOR_PROSE,
  },
  alice_search: {
    character: 'Alice',
    move: VALID_CHARACTER_MOVE,
    prose: NARRATOR_PROSE,
  },
};

function findRawByKind(rawStore, kind) {
  return rawStore.find((entry) => entry.inference_kind === kind) ?? null;
}

function overlayPressuresFromTruth(truth) {
  return (truth.overlay_pressures ?? []).map((text) => ({
    pressure_text: text,
    dramatic_rationale: 'Persistent narrative pressure for characterization scenario.',
  }));
}

async function runSeedRound(ctx, ctxSession, seedKey) {
  const seed = SEED_LIBRARY[seedKey];
  if (!seed) throw new Error(`unknown_seed:${seedKey}`);
  const round = await ctx.orchestrator.runRound({
    domainApi: ctx.api,
    session: { mode: 'open', hg_session_id: ctxSession.session.hg_session_id },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [directorFor(seed.character)],
    mockCharacterTurnResponses: [[JSON.stringify(seed.move)]],
    mockNarratorTurnResponses: [[seed.prose]],
  });
  if (round.committed !== true) {
    throw new Error(`seed_round_not_committed:${seedKey}`);
  }
  return round;
}

function extractUpdateJudgment(updateResult) {
  const parsed = updateResult?.parsed?.result ?? {};
  const proposal = parsed.update_proposal ?? {};
  const evaluation = parsed.update_evaluation ?? {};
  return {
    replan_required: proposal.replan_required === true,
    overall_result: evaluation.overall_result ?? null,
    no_change_rationale: evaluation.no_change_rationale ?? null,
    finalize_code: updateResult?.finalizeResponse?.code ?? null,
    replan_committed: updateResult?.finalizeResponse?.code === 'replan_committed',
  };
}

async function runPlotUpdateCharacterization({
  caseId,
  truth,
  seedKey,
  campaignLimits,
  campaignDataDir,
  requireInvalidation = true,
}) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const pressures = overlayPressuresFromTruth(truth);
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      cast: truth.characters ?? ['Alice', 'Bob'],
      characterId: 'Alice',
      direction: truth.overlay_direction,
      pressures,
    });
    const overlayBefore = loadOverlayStore(ctx.sessionsDir, ctxSession.scopeId);
    capture.overlay_revision_before = overlayBefore?.store_revision ?? 0;

    const baselinePrepare = await ctx.api.preparePlotCognitionUpdate({
      hg_scene_id: ctxSession.hgSceneId,
      manifest_id: `manifest-${caseId}-baseline-${crypto.randomUUID()}`,
    });
    const baselineBody = baselinePrepare?.source_snapshot?.canonical_body ?? {};
    const baseline = {
      authority_source_fingerprint: baselinePrepare?.authority_source_fingerprint ?? null,
      committed_move_count: (baselineBody.committed_moves ?? []).length,
      public_event_count: (baselineBody.continuity?.public_events ?? []).length,
    };

    await runSeedRound(ctx, ctxSession, seedKey);

    const prepareAfter = await ctx.api.preparePlotCognitionUpdate({
      hg_scene_id: ctxSession.hgSceneId,
      manifest_id: `manifest-${caseId}-post-seed-${crypto.randomUUID()}`,
    });
    const invalidationProof = assertInvalidationInPrepareContext(prepareAfter, baseline);
    const semanticProof = assertSemanticAuthorityInPrepare(prepareAfter);
    capture.invalidation_proof = invalidationProof;
    capture.semantic_authority_proof = semanticProof;
    if (requireInvalidation && !invalidationProof.ok) {
      throw new Error(`${caseId.toLowerCase()}_invalidation_not_in_authority`);
    }
    if (!semanticProof.ok) {
      throw new Error(`${caseId.toLowerCase()}_semantic_authority_missing`);
    }

    const updateResult = await runPlotCognitionUpdateGeneration({
      domainApi: ctx.api,
      hgSceneId: ctxSession.hgSceneId,
      inferenceId: `inf-phase-d-${caseId}`,
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
    });

    const judgment = extractUpdateJudgment(updateResult);
    const semanticClassification = classifyReplanJudgment(truth, judgment);
    capture.model_judgment = judgment;
    capture.semantic_classification = semanticClassification;

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

    const structuralGates = {
      semantic_authority_present: gate('semantic_authority_present', semanticProof.ok === true),
      update_inference_ok: gate('update_inference_ok', updateResult.ok === true),
      invalidation_observed: gate('invalidation_observed', invalidationProof.ok === true || !requireInvalidation),
      durable_evidence: gate('durable_evidence', forensics.evidenceIds.length > 0),
      chronicle_present: gate('chronicle_present', forensics.chronicleKeys.length > 0),
    };

    const base = finalizeScenarioResult(createScenarioResult(truth.scenario_id, {
      fixtureId: truth.fixture_id,
      objectiveGates: structuralGates,
      operationSequence: ['seed_commit', 'live_plot_cognition_update', 'characterization'],
      overlayRevisions: [overlayBefore?.store_revision, overlayAfter?.store_revision],
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'phase_d_characterization',
      notes: [
        judgment.replan_required ? 'replan_required' : 'no_replan_required',
        judgment.overall_result ?? 'unknown',
        semanticClassification.label,
      ],
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    const finalized = await evaluateAndFinalize({
      caseId,
      scenarioId: truth.scenario_id,
      truth,
      baseResult: base,
      evaluationSubject: buildPlotUpdateCertificationSubject({
        capture,
        updateResult,
        truth,
        overlayBefore,
        overlayAfter,
      }),
      evaluationTarget: 'plot_cognition_update',
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
    finalized.result.characterization = {
      structural: structuralGates,
      semantic: semanticClassification,
      model_judgment: judgment,
    };
    if (finalized.result.campaign) {
      finalized.result.campaign.tranche = 'D';
      finalized.result.campaign.phase = 'characterization';
    }
    return finalized;
  });
}

export function runT2_R1(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-R1',
    truth: loadTier2TruthFixture('t2-r1-treaty-breach'),
    seedKey: 'treaty_breach',
    campaignLimits,
    campaignDataDir,
  });
}

export function runT2_R2(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-R2',
    truth: loadTier2TruthFixture('t2-r2-target-sealed'),
    seedKey: 'vault_sealed',
    campaignLimits,
    campaignDataDir,
  });
}

export function runT2_R3(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-R3',
    truth: loadTier2TruthFixture('t2-r3-premise-disproven'),
    seedKey: 'empty_panel',
    campaignLimits,
    campaignDataDir,
  });
}

export function runT2_R4(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-R4',
    truth: loadTier2TruthFixture('t2-r4-viable-control'),
    seedKey: 'door_slam',
    campaignLimits,
    campaignDataDir,
    requireInvalidation: false,
  });
}

export function runT2_U1(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-U1',
    truth: loadTier2TruthFixture('t2-u1-new-pressure'),
    seedKey: 'guards_patrol',
    campaignLimits,
    campaignDataDir,
    requireInvalidation: false,
  });
}

export function runT2_U2(campaignLimits, campaignDataDir) {
  return runPlotUpdateCharacterization({
    caseId: 'T2-U2',
    truth: loadTier2TruthFixture('t2-u2-pressure-resolved'),
    seedKey: 'guards_depart',
    campaignLimits,
    campaignDataDir,
    requireInvalidation: false,
  });
}

export async function runT2_L1(campaignLimits, campaignDataDir) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTier2TruthFixture('t2-l1-multi-commit');
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      cast: truth.characters ?? ['Alice', 'Bob'],
      direction: truth.overlay_direction,
      pressures: overlayPressuresFromTruth(truth),
    });

    await runSeedRound(ctx, ctxSession, 'bob_anxiety');
    const stale = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
    capture.freshness_after_first_commit = stale;

    await ctx.api.startRound({ hg_scene_id: ctxSession.hgSceneId });
    await runSeedRound(ctx, ctxSession, 'alice_search');
    const staleAfterSecond = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
    capture.freshness_after_second_commit = staleAfterSecond;

    const lifecycle = await runPlotCognitionPendingWorkLifecycle({
      domainApi: ctx.api,
      hgSceneId: ctxSession.hgSceneId,
      inferenceId: 'inf-phase-d-T2-L1',
      runEphemeralInference: ctx.instrumented.runEphemeralInference,
      modelProfile: ctx.roleProfiles.storyteller,
      evidenceContextBase: {
        hgSessionId: ctxSession.session.hg_session_id,
        hgSceneId: ctxSession.hgSceneId,
      },
    });
    capture.pending_lifecycle = {
      ok: lifecycle.ok === true,
      operation: lifecycle.operation ?? null,
      stage: lifecycle.stage ?? null,
      fresh_after: lifecycle.freshAfter === true,
    };
    const freshAfter = await ctx.api.assessPlotCognitionFreshness({ hg_scene_id: ctxSession.hgSceneId });
    capture.freshness_after_lifecycle = freshAfter;

    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });

    const structuralGates = {
      pending_after_commits: gate('pending_after_commits', staleAfterSecond.fresh === false),
      lifecycle_ok: gate('lifecycle_ok', lifecycle.ok === true),
      overlay_fresh_after_lifecycle: gate('overlay_fresh_after_lifecycle', freshAfter.fresh === true),
      chronicle_present: gate('chronicle_present', forensics.chronicleKeys.length > 0),
    };

    const base = finalizeScenarioResult(createScenarioResult(truth.scenario_id, {
      fixtureId: truth.fixture_id,
      objectiveGates: structuralGates,
      operationSequence: ['commit_1', 'commit_2', 'pending_lifecycle'],
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'phase_d_characterization',
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    const finalized = await evaluateAndFinalize({
      caseId: 'T2-L1',
      scenarioId: truth.scenario_id,
      truth,
      baseResult: base,
      evaluationSubject: {
        kind: 'plot_cognition_lifecycle',
        fixture_id: truth.fixture_id,
        pending_after_first: capture.freshness_after_first_commit,
        pending_after_second: capture.freshness_after_second_commit,
        lifecycle: capture.pending_lifecycle,
        freshness_after_lifecycle: capture.freshness_after_lifecycle,
      },
      evaluationTarget: 'plot_cognition_lifecycle',
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
    if (finalized.result.campaign) {
      finalized.result.campaign.tranche = 'D';
    }
    return finalized;
  });
}

export async function runT2_D1(campaignLimits, campaignDataDir) {
  campaignLimits.assertCanRun();
  campaignLimits.recordRun();
  const truth = loadTier2TruthFixture('t2-d1-director-projection');
  return withLiveHarness(campaignLimits, campaignDataDir, async (ctx) => {
    const started = Date.now();
    const capture = createPlotCognitionCapture();
    const ctxSession = await createFreshOverlaySession(ctx.api, ctx.sessionsDir, {
      cast: truth.characters ?? ['Alice', 'Bob'],
      direction: truth.overlay_direction,
      pressures: overlayPressuresFromTruth(truth),
    });

    const directorFresh = await ctx.api.prepareDirectorContext({
      hg_scene_id: ctxSession.hgSceneId,
      hg_round_id: ctxSession.hgRoundId,
      inference_id: 'inf-phase-d-T2-D1-director',
      manifest_id: `manifest-${crypto.randomUUID()}`,
    });
    capture.director_projection = {
      contribution_count: (directorFresh.contributions ?? []).length,
      texts: (directorFresh.contributions ?? []).map((c) => c.content),
    };

    const structuralGates = {
      director_projection_present: gate(
        'director_projection_present',
        (directorFresh.contributions ?? []).length > 0,
      ),
    };

    const forensics = joinScenarioForensics({
      forensicsDir: ctx.forensicsDir,
      dataDir: ctx.dataDir,
      scopeId: ctxSession.scopeId,
      hgSessionId: ctxSession.session.hg_session_id,
    });

    const base = finalizeScenarioResult(createScenarioResult(truth.scenario_id, {
      fixtureId: truth.fixture_id,
      objectiveGates: structuralGates,
      operationSequence: ['director_projection'],
      chronicleKeys: forensics.chronicleKeys,
      evidenceIds: forensics.evidenceIds,
      phaseDurationsMs: { total: Date.now() - started },
      certificationClass: 'phase_d_characterization',
      durableEvidence: durableEvidenceRef(ctx.dataDir, ctxSession.session.hg_session_id, forensics.evidenceIds),
    }));

    const finalized = await evaluateAndFinalize({
      caseId: 'T2-D1',
      scenarioId: truth.scenario_id,
      truth,
      baseResult: base,
      evaluationSubject: {
        kind: 'director_projection',
        fixture_id: truth.fixture_id,
        director_projection: capture.director_projection,
      },
      evaluationTarget: 'director',
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
    if (finalized.result.campaign) {
      finalized.result.campaign.tranche = 'D';
    }
    return finalized;
  });
}

export const PHASE_D_CASES = [
  { id: 'T2-R1', run: runT2_R1, estimated_calls: 3 },
  { id: 'T2-R2', run: runT2_R2, estimated_calls: 3 },
  { id: 'T2-R3', run: runT2_R3, estimated_calls: 3 },
  { id: 'T2-R4', run: runT2_R4, estimated_calls: 3 },
  { id: 'T2-U1', run: runT2_U1, estimated_calls: 3 },
  { id: 'T2-U2', run: runT2_U2, estimated_calls: 3 },
  { id: 'T2-L1', run: runT2_L1, estimated_calls: 2 },
  { id: 'T2-D1', run: runT2_D1, estimated_calls: 1 },
];

export const PHASE_D_ESTIMATED_CALLS = PHASE_D_CASES.reduce((sum, c) => sum + c.estimated_calls, 0);

export function phaseDCampaignDataRoot() {
  return path.join(REPO_ROOT, 'data', 'storyteller_tier1_campaign', 'phase_d');
}

export async function runPhaseDCampaign(options = {}) {
  const limits = options.limits ?? new CampaignLimits({
    maxRuns: PHASE_D_CASES.length,
    maxInferences: PHASE_D_INFERENCE_CEILING,
  });
  const campaignDataDir = options.campaignDataDir
    ?? path.join(phaseDCampaignDataRoot(), `run-${crypto.randomUUID()}`);
  const results = [];
  const hardBlockers = [];

  for (const entry of PHASE_D_CASES) {
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

  const report = {
    ...buildCampaignReport({
      results,
      limits,
      hardBlockers,
      tranche: 'D',
      schema: 'hg_storyteller_phase_d_report_v1',
    }),
    campaign_data_dir: campaignDataDir,
    phase_d_analysis: summarizePhaseDMetrics(results),
    historical_c3_baseline: {
      source: 'phase_c_tranche3',
      observation: 'structurally valid no_change despite treaty-breach semantics',
      counts_toward_new_sample: false,
    },
  };
  return report;
}

export function estimatePhaseDCallCeiling() {
  return {
    ceiling: PHASE_D_INFERENCE_CEILING,
    estimated: PHASE_D_ESTIMATED_CALLS,
    cases: PHASE_D_CASES.map((c) => ({ id: c.id, estimated_calls: c.estimated_calls })),
  };
}
