/**
 * Issue #201 LH-1A — live long-horizon campaign execution.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../../src/application/application-settings.mjs';
import { agentOptionsFromProfile, mockInferenceProfile } from '../../src/lib/inference-profile.mjs';
import { runA2BeatRound } from '../../src/lib/a2-beat-orchestration.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import {
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  extractContinuityForensics,
  extractPlotForensics,
} from './issue201-g3d-lib.mjs';
import { LH0_ARMS, buildLh0ArmConfig, resolveLh0BeatOptions } from './issue201-lh0-arms.mjs';
import { runPlayerPvrAndRecord } from './issue201-lh0-live-lib.mjs';
import {
  readLh0Store,
  writeLh0Store,
  classifyLh0ObligationStates,
  lh0StorePath,
} from './issue201-lh0-persistent-store.mjs';
import { gitSha, REPO_ROOT } from './issue201-lh0-lib.mjs';
import { LH1A_CHECKPOINTS, LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';
import { loadLh1aFixtureManifest, sceneForTurn } from './issue201-lh1a-fixtures.mjs';
import { loadLh1aPolicy } from './issue201-lh1a-player-policy.mjs';
import { buildLh1aLiveCampaignPlan } from './issue201-lh1a-orchestrator.mjs';
import { buildAllCheckpointSlices, buildCheckpointSlice } from './issue201-lh1a-checkpoint-exporter.mjs';
import {
  buildLh1aBlindPacket,
  buildLh1aAnswerKey,
  validateLh1aBlindPacketIntegrity,
  writeLh1aBlindArtifacts,
} from './issue201-lh1a-blind-packet.mjs';
import { buildArchaeologyDossier } from './issue201-lh1a-archaeology.mjs';
import { buildCostRollup } from './issue201-lh1a-cost-accounting.mjs';
import { ObligationLedger } from './issue201-obligation-ledger.mjs';
import { LifecycleTracer } from './issue201-lifecycle-tracer.mjs';
import { classifySeamFailure } from './issue201-seam-classifier.mjs';
import { runLh1aLivePreflight, FROZEN_HASHES, APPARATUS_CANDIDATE_SHA } from './issue201-lh1a-preflight-lib.mjs';

const SCENARIO_MAP = {
  ayame_controlled: G3_SCENARIOS.ayame_controlled,
  arkham_stress: G3_SCENARIOS.arkham_stress,
};

async function createLh1aScenarioSession(client, scenarioKey) {
  const scenario = SCENARIO_MAP[scenarioKey];
  if (!scenario) throw new Error(`unknown LH-1A scenario: ${scenarioKey}`);
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = scenario.openerPreference
    ? openers.find((o) => o.opener_id === scenario.openerPreference) ?? openers[0]
    : openers[0];
  if (!opener) throw new Error(`no opener for ${scenario.id}`);
  return client.createSession({
    characters: scenario.characters,
    sceneTemplateId: scenario.id,
    roleAssignments: scenario.roleAssignments,
    playerCharacterFileId: scenario.playerCharacterFileId,
    userPersonaId: scenario.userName,
    opening: { mode: 'template', opener_id: opener.opener_id },
  });
}

function extractLh1aTurnForensics(roundResult, { sessionsDir, hgSessionId, turnIndex }) {
  const store = readLh0Store(sessionsDir, hgSessionId);
  classifyLh0ObligationStates(store, turnIndex);
  writeLh0Store(sessionsDir, hgSessionId, store);
  const transportStep = roundResult.audit_steps?.find((s) => s.step === 'lh0_projection_transport');
  const receiptStep = roundResult.audit_steps?.find((s) => s.step === 'lh0_character_consumer_receipt');
  const charEvidence = roundResult.lh0_transport?.character
    ?? roundResult.character_turn?.lh0ConsumerEvidence
    ?? receiptStep
    ?? null;
  return {
    projected: transportStep?.projected_finalized === true,
    consumer_received: receiptStep?.consumer_received === true
      || charEvidence?.consumer_received === true,
    consumer_used: charEvidence?.consumer_used === true,
    decision_influenced: (charEvidence?.decision_influenced_obligation_ids ?? []).length > 0,
    lh0_store_snapshot: store,
    seam: classifySeamFailure({
      generated: true,
      persisted: store.obligations.length > 0,
      retrieved: store.obligations.length > 0,
      projected: transportStep?.projected_finalized === true,
      consumerReceived: receiptStep?.consumer_received === true,
      consumerUsed: charEvidence?.consumer_used === true,
    }),
  };
}

async function runLh1aTurn({
  client,
  armConfig,
  fixture,
  scenario,
  turnIndex,
  playerStimulus,
  sceneId,
  sequenceId,
  evidenceRoot,
  sessionsDir,
  plotScopeIdRef,
}) {
  const continuityBefore = extractContinuityForensics(client.activeSessionId, sessionsDir);
  client._beginRoundOperation(`lh1a-${sequenceId}-t${turnIndex}`, 'user_turn');
  const started = Date.now();
  const { playerDecomposition } = await runPlayerPvrAndRecord(client, playerStimulus);
  const api = client._domainApi();
  const runtime = client.supervisor.runtime;
  const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const sceneSessionId = SessionId(`hg-lh1a-a2-${crypto.randomUUID()}`);
  const sceneAgent = runtime.ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const beatOptions = {
    ...resolveLh0BeatOptions(armConfig),
    scenarioKey: scenario.scenario_key,
    roleAssignments: scenario.roleAssignments,
    roleProfiles: inferenceOpts.roleProfiles,
    liveMaxAttempts: inferenceOpts.liveMaxAttempts,
    uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
    characterSemanticEvaluationEnabled: false,
    captureActorContextPackages: true,
    lh0Arm: armConfig.persistent_cognition_enabled ? armConfig.arm : null,
    lh0SessionsDir: armConfig.persistent_cognition_enabled ? sessionsDir : null,
    lh0FixtureTurnIndex: turnIndex,
    lh0FixtureManifest: armConfig.persistent_cognition_enabled ? fixture : null,
  };
  const roundResult = await runA2BeatRound({
    phaseExecutors: runtime.phaseExecutors,
    api,
    trace: runtime.traceEmitter,
    sceneAgent,
    sceneSessionId,
    hgSessionId: client.activeSessionId,
    hgSceneId: client.activeSessionId,
    options: beatOptions,
  });
  const operationWallMs = Date.now() - started;
  const allAttempts = loadAttempts(evidenceRoot, client.activeSessionId);
  const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
  const continuityAfter = extractContinuityForensics(client.activeSessionId, sessionsDir);
  if (continuityAfter.plot_cognition_scope_id) plotScopeIdRef.value = continuityAfter.plot_cognition_scope_id;
  const lh1aProjection = extractLh1aTurnForensics(roundResult, {
    sessionsDir, hgSessionId: client.activeSessionId, turnIndex,
  });
  return {
    turn_index: turnIndex,
    scene_id: sceneId,
    exact_player_stimulus: playerStimulus,
    hg_round_id: roundResult.hg_round_id,
    domain_commit_id: roundResult.domain_commit_id,
    presentation_text: roundResult.presentation_text ?? '',
    operation_wall_ms: operationWallMs,
    committed: roundResult.committed === true,
    player_decomposition_recorded: playerDecomposition != null,
    inference: summarizeAttempts(roundAttempts),
    lh1a_projection: lh1aProjection,
    checkpoint: Object.entries(LH1A_CHECKPOINTS).find(([, t]) => t === turnIndex)?.[0] ?? null,
  };
}

export async function executeLh1aLiveSequence({
  sequencePlan,
  evidenceRoot,
  outputDir,
}) {
  const armConfig = buildLh0ArmConfig(sequencePlan.arm);
  const fixture = loadLh1aFixtureManifest(sequencePlan.scenario_key);
  const scenario = SCENARIO_MAP[sequencePlan.scenario_key];
  const sequenceId = `LH1A-LIVE-${sequencePlan.arm}-${sequencePlan.scenario_key}-${Date.now()}`;
  const sessionsDir = defaultSessionsDir();
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
  const turns = [];
  const checkpoints = {};
  let failed = false;
  let error = null;
  let hgSessionId = null;
  const plotScopeIdRef = { value: null };
  const inferenceEvents = [];

  await client.start();
  try {
    await createLh1aScenarioSession(client, sequencePlan.scenario_key);
    hgSessionId = client.activeSessionId;
    if (armConfig.persistent_cognition_enabled) {
      writeLh0Store(sessionsDir, hgSessionId, {
        schema: 'issue201_lh0_persistent_store_v1',
        campaign: 'lh1a',
        fixture_id: fixture.fixture_id,
        obligations: [],
        events: [],
      });
    }
    for (const planTurn of sequencePlan.turns) {
      const turnRow = await runLh1aTurn({
        client,
        armConfig,
        fixture,
        scenario,
        turnIndex: planTurn.turn_index,
        playerStimulus: planTurn.player_stimulus,
        sceneId: planTurn.scene_id,
        sequenceId,
        evidenceRoot,
        sessionsDir,
        plotScopeIdRef,
      });
      turns.push(turnRow);
      for (const ev of turnRow.inference?.events ?? []) {
        inferenceEvents.push({ ...ev, turn_index: planTurn.turn_index });
      }
      if (planTurn.checkpoint) {
        checkpoints[planTurn.checkpoint] = buildCheckpointSlice({
          sequencePlan: { ...sequencePlan, sequence_id: sequenceId },
          checkpointId: planTurn.checkpoint,
          turnRecords: turns,
          obligationLedger: null,
        });
      }
      if (!turnRow.committed) {
        failed = true;
        error = `turn ${planTurn.turn_index} not committed`;
        break;
      }
    }
  } catch (err) {
    failed = true;
    error = String(err?.message ?? err);
  } finally {
    await client.stop();
  }

  const lh0Store = (hgSessionId && armConfig.persistent_cognition_enabled)
    ? readLh0Store(sessionsDir, hgSessionId)
    : { obligations: [], events: [] };
  const ledger = new ObligationLedger({ fixtureManifest: fixture });
  for (const ob of lh0Store.obligations ?? []) {
    ledger.register({ ...ob, lifecycle_state: ob.lifecycle_state ?? 'GEN_UNUSED' });
  }
  const archaeology = buildArchaeologyDossier({
    sequencePlan: { ...sequencePlan, sequence_id: sequenceId },
    ledger,
  });
  const costRollup = buildCostRollup({
    arm: sequencePlan.arm,
    sequenceId,
    inferenceEvents,
    obligationLedger: ledger,
  });

  const sequence = {
    schema: 'issue201_lh1a_live_sequence_v1',
    sequence_id: sequenceId,
    blind_label: sequencePlan.blind_label,
    arm: sequencePlan.arm,
    arm_label: sequencePlan.arm_label,
    scenario_key: sequencePlan.scenario_key,
    scenario_id: sequencePlan.scenario_id,
    hg_session_id: hgSessionId,
    fixture_id: sequencePlan.fixture_id,
    fixture_hash: sequencePlan.fixture_hash,
    policy_id: sequencePlan.policy_id,
    policy_hash: sequencePlan.policy_hash,
    failed,
    error,
    turn_count_completed: turns.length,
    turn_count_target: sequencePlan.turn_count,
    turns,
    checkpoints,
    lh0_store_path: hgSessionId ? lh0StorePath(sessionsDir, hgSessionId) : null,
    lh0_store: lh0Store,
    archaeology_dossier: archaeology,
    cost_rollup: costRollup,
    isolation: {
      dedicated_session: true,
      session_id: hgSessionId,
      no_cross_sequence_store: true,
    },
  };

  fs.writeFileSync(
    path.join(outputDir, `${sequenceId}-sequence.json`),
    `${JSON.stringify(sequence, null, 2)}\n`,
  );
  return sequence;
}

function buildCampaignPlanWithPresentation(campaignPlan, sequences) {
  const enriched = { ...campaignPlan, sequences: campaignPlan.sequences.map((plan) => {
    const live = sequences.find((s) => s.arm === plan.arm && s.scenario_key === plan.scenario_key);
    if (!live) return plan;
    return {
      ...plan,
      sequence_id: live.sequence_id,
      turns: plan.turns.map((t) => {
        const liveTurn = live.turns.find((lt) => lt.turn_index === t.turn_index);
        return {
          ...t,
          presentation_text: liveTurn?.presentation_text ?? '',
        };
      }),
    };
  }) };
  return enriched;
}

export async function executeLh1aLiveCampaign({ outputDir, preflightReport = null }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const preflight = preflightReport ?? runLh1aLivePreflight();
  if (!preflight.all_pass) {
    throw new Error('LH-1A live preflight failed — aborting before inference');
  }

  const campaignPlan = preflight.campaign_plan;
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh1a-campaign-plan-locked.json'),
    `${JSON.stringify(campaignPlan, null, 2)}\n`,
  );

  const evidenceRoot = outputDir;
  const sequences = [];
  for (const seqPlan of campaignPlan.sequences) {
    sequences.push(await executeLh1aLiveSequence({
      sequencePlan: seqPlan,
      evidenceRoot,
      outputDir,
    }));
    if (sequences[sequences.length - 1].failed) {
      break;
    }
  }

  const rubricPath = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json');
  const rubric = JSON.parse(fs.readFileSync(rubricPath, 'utf8'));
  const enrichedPlan = buildCampaignPlanWithPresentation(campaignPlan, sequences);
  const blindPacket = buildLh1aBlindPacket({ campaignPlan: enrichedPlan, rubric });
  const answerKey = buildLh1aAnswerKey(enrichedPlan);
  const blindIntegrity = validateLh1aBlindPacketIntegrity(blindPacket);
  const blindPaths = writeLh1aBlindArtifacts({ outputDir, packet: blindPacket, answerKey });

  const report = {
    schema: 'issue201_lh1a_live_campaign_report_v1',
    campaign: 'lh1a_story_aging_screening_live',
    apparatus_candidate_sha: APPARATUS_CANDIDATE_SHA,
    execution_candidate_sha: gitSha(),
    preflight,
    frozen_hashes: FROZEN_HASHES,
    campaign_plan: campaignPlan,
    campaign_order: campaignPlan.sequences.map((s, i) => ({
      order_index: i + 1,
      blind_label: s.blind_label,
      arm: s.arm,
      scenario_key: s.scenario_key,
      planned_sequence_id: s.sequence_id,
    })),
    sequences,
    blind_packet: {
      integrity: blindIntegrity,
      paths: blindPaths,
      rubric_hash: FROZEN_HASHES.rubric_hash,
    },
    answer_key: answerKey,
    campaign_failed: sequences.some((s) => s.failed),
    partial_campaign: sequences.length < 8 || sequences.some((s) => s.failed),
    total_player_turns_completed: sequences.reduce((n, s) => n + s.turn_count_completed, 0),
    total_player_turns_target: 176,
    output_dir: outputDir,
  };

  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh1a-live-campaign-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  return report;
}

export { runLh1aLivePreflight, buildLh1aLiveCampaignPlan };
