/**
 * Issue #201 LH-1B — live campaign runner (authoritative A2 turn path).
 * Live inference requires separate Governance authorization.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
} from '../../src/application/application-settings.mjs';
import { agentOptionsFromProfile, mockInferenceProfile } from '../../src/lib/inference-profile.mjs';
import { resolveApplicationRoleProfiles } from '../../src/application/application-settings.mjs';
import { runA2BeatRound } from '../../src/lib/a2-beat-orchestration.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import {
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  extractContinuityForensics,
  plotOffAbsenceProof,
  storytellerAbsenceProof,
} from './issue201-g3d-lib.mjs';
import { LH0_ARMS, buildLh0ArmConfig, resolveLh0BeatOptions } from './issue201-lh0-arms.mjs';
import { runPlayerPvrAndRecord } from './issue201-lh0-live-lib.mjs';
import {
  readLh0Store,
  writeLh0Store,
  classifyLh0ObligationStates,
  lh0StorePath,
} from './issue201-lh0-persistent-store.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import {
  LH1B_APPARATUS_CANDIDATE_SHA,
  LH1B_CHECKPOINTS,
  LH1B_FROZEN_HASHES,
  LH1B_SCHEMAS,
} from './issue201-lh1b-contract.mjs';
import { loadLh1bFixtureManifest, forkForTurn, sceneForTurn } from './issue201-lh1b-fixtures.mjs';
import { loadLh1bPolicy, sha256File } from './issue201-lh1b-player-policy.mjs';
import { fixturePathForScenario } from './issue201-lh1b-fixtures.mjs';
import { buildLh1bCampaignPlan } from './issue201-lh1b-orchestrator.mjs';
import {
  evaluateCharacterForkAtTurn,
  evaluateDirectorForkAtTurn,
} from './issue201-lh1b-causal-classifier.mjs';
import { buildLh1bArchaeologyDossier } from './issue201-lh1b-archaeology.mjs';
import { attemptsToInferenceEvents, buildLh1bCostRollup } from './issue201-lh1b-cost-accounting.mjs';
import { buildLhProvenanceAuditBlock, buildLh1bCausalTraceRow } from './issue201-lh1b-provenance.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { LH1B_LIVE_FAILURE_POLICY } from './issue201-lh1b-failure-policy.mjs';
import { runLh1bLivePreflight } from './issue201-lh1b-live-preflight-lib.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';

export const APPARATUS_CANDIDATE_SHA = LH1B_APPARATUS_CANDIDATE_SHA;
export const FROZEN_HASHES = LH1B_FROZEN_HASHES;
export { LH1B_LIVE_FAILURE_POLICY, runLh1bLivePreflight };

/** Authoritative per-turn ordering (LH-1B Director projection before Director when persistent). */
export const LH1B_TURN_ORDERING = Object.freeze([
  'player_stimulus',
  'pvr_preprocessing',
  'record_user_turn',
  'participation_eligibility',
  'lh0_projection_transport_before_director',
  'director_inference_or_deterministic_select',
  'indexed_retrieval_when_enabled',
  'character_move',
  'deterministic_move_validation_bounded_repair',
  'authoritative_commit',
  'narrator_presentation',
  'deterministic_presentation_validation',
  'lh0_post_commit_persistence',
  'execution_evidence_recording',
]);

const SCENARIO_MAP = {
  ayame_controlled: G3_SCENARIOS.ayame_controlled,
};

const VALID_MOVE_BASE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'considers the question carefully' }],
  motivation: { goal: 'respond', tactic: 'measured', emotional_driver: 'neutral', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_DIRECTOR_AYAME = {
  next_actor: 'Ayame',
  end_round: false,
  reason: 'Ayame continues the household evaluation.',
  environment_event: '',
  tension_shift: '',
};

const VALID_NARRATOR = 'Ayame regarded the applicant with measured attention.';

export function verifyLh1bFrozenHashes(sequencePlan) {
  const fixturePath = fixturePathForScenario(sequencePlan.scenario_key);
  const measured = {
    fixture_hash: sha256File(fixturePath),
    policy_hash: sequencePlan.policy_hash,
    causal_design_hash: crypto.createHash('sha256')
      .update(JSON.stringify(loadLh1bFixtureManifest(sequencePlan.scenario_key).causal_design))
      .digest('hex'),
  };
  const drift = Object.entries(FROZEN_HASHES).filter(([k, v]) => measured[k] !== v);
  return { pass: drift.length === 0, measured, drift };
}

export function loadFullAttemptsForRound(evidenceRoot, sessionId, hgRoundId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((attemptId) => {
    const attempt = JSON.parse(fs.readFileSync(
      path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`),
      'utf8',
    ));
    const corr = attempt.correlation ?? {};
    const roundId = corr.hg_round_id ?? corr.hgRoundId ?? null;
    if (hgRoundId && roundId !== hgRoundId) return null;
    return {
      ...attempt,
      inference_kind: corr.inference_kind ?? null,
      hg_round_id: roundId,
    };
  }).filter(Boolean);
}

export function extractAssembledRequestFromAttempts(attempts, inferenceKind) {
  const row = attempts.find((a) => a.inference_kind === inferenceKind)
    ?? attempts.find((a) => a.correlation?.inference_kind === inferenceKind);
  if (row?.request) return row.request;
  return null;
}

export function buildLh1bBeatOptions({
  armConfig,
  fixture,
  turnIndex,
  sessionsDir,
  scenario,
  mockOverrides = {},
}) {
  const inferenceOpts = mockOverrides.inferenceOpts ?? null;
  const beatBase = {
    ...resolveLh0BeatOptions(armConfig),
    scenarioKey: scenario.scenario_key,
    roleAssignments: scenario.roleAssignments,
    roleProfiles: mockOverrides.forceMockInferenceProfiles
      ? resolveApplicationRoleProfiles({ inferenceMode: 'mock' }, { inferenceMode: 'mock' })
      : inferenceOpts?.roleProfiles,
    liveMaxAttempts: inferenceOpts?.liveMaxAttempts ?? 3,
    uniformProjectionEligible: true,
    characterSemanticEvaluationEnabled: false,
    captureActorContextPackages: true,
    lhProvenanceAudit: true,
    lh0FixtureTurnIndex: turnIndex,
    lh0FixtureManifest: armConfig.persistent_cognition_enabled ? fixture : null,
    lh0SessionsDir: armConfig.persistent_cognition_enabled ? sessionsDir : null,
    lh1bForceDirectorInference: armConfig.arm === LH0_ARMS.LH_D && turnIndex === 15,
    presentationSpatialClaims: {
      schema: 'hg_presentation_spatial_claims_v1',
      claims: [],
    },
    mockCharacterResponses: [JSON.stringify(VALID_MOVE_BASE)],
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR_AYAME)],
    mockNarratorResponses: [VALID_NARRATOR],
    ...mockOverrides.beatOptions,
  };
  if (!armConfig.persistent_cognition_enabled) {
    delete beatBase.lh0Arm;
    delete beatBase.lh0SessionsDir;
    delete beatBase.lh0FixtureManifest;
  }
  return beatBase;
}

function verifyArmIsolation({ arm, turnIndex, roundResult, store, attempts }) {
  const transport = roundResult.lh0_transport;
  const projected = transport?.projected_finalized === true;
  const plotProof = plotOffAbsenceProof(attempts);
  const violations = [];
  if (arm === LH0_ARMS.LH_A) {
    if (projected) violations.push('lh_a_projected_persistence');
    if ((store?.obligations ?? []).length > 0) violations.push('lh_a_store_seeded');
    if (!plotProof.pass) {
      violations.push(`lh_a_plot_kinds:${plotProof.violations.map((v) => v.inference_kind).join(',')}`);
    }
    const charReceipt = roundResult.character_turn?.lh0ConsumerEvidence;
    if (charReceipt?.received_obligation_ids?.length) violations.push('lh_a_character_persistence_receipt');
    const dirProj = roundResult.lh0_director_projection_receipt;
    if (dirProj?.contributions?.length) violations.push('lh_a_director_persistence_receipt');
  }
  if (arm === LH0_ARMS.LH_B) {
    const postCommit = roundResult.lh0_post_commit;
    const postCommitActive = postCommit && postCommit.skipped !== true;
    if (!postCommitActive) violations.push('lh_b_missing_post_commit_persistence');
    const dirDue = transport?.director?.projected_obligation_ids ?? [];
    if (dirDue.includes('LH1B-AYA-DIR-TRAJECTORY')) violations.push('lh_b_director_trajectory_leak');
  }
  if (arm === LH0_ARMS.LH_D && turnIndex === 15) {
    if (!roundResult.topology_proof?.director_llm_invoked) {
      violations.push('lh_d_director_not_invoked_at_t15');
    }
  }
  return { pass: violations.length === 0, violations, turn_index: turnIndex, arm };
}

function extractCharacterConsumerBehaviorText(charAttempt, presentationText = '') {
  const raw = charAttempt?.response?.assistantText
    ?? charAttempt?.response?.assistant_text
    ?? '';
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      const speeches = (parsed.beats ?? [])
        .filter((b) => b.type === 'speech' && b.dialogue)
        .map((b) => b.dialogue);
      if (speeches.length) return speeches.join(' ');
      const actions = (parsed.beats ?? [])
        .filter((b) => b.type === 'action' && b.action)
        .map((b) => b.action);
      if (actions.length) return actions.join(' ');
    } catch {
      // fall through to raw text
    }
    if (String(raw).trim()) return String(raw);
  }
  return String(presentationText ?? '');
}

function evaluateTurnForks({
  fixture,
  arm,
  turnIndex,
  roundResult,
  store,
  playerStimulus,
  attempts,
}) {
  const charForks = forkForTurn(fixture, turnIndex, { consumer: 'character_move' });
  const dirForks = forkForTurn(fixture, turnIndex, { consumer: 'director_turn' });
  const presentationText = roundResult.presentation_text ?? '';
  const charRequest = extractAssembledRequestFromAttempts(attempts, 'character_move');
  const dirRequest = extractAssembledRequestFromAttempts(attempts, 'director_turn');
  const charManifest = roundResult.character_turn?.consumerManifest
    ?? (charRequest?.contributions
      ? { contributions: charRequest.contributions, manifest_id: charRequest.manifest_id }
      : null);
  const dirManifest = dirRequest?.contributions
    ? { contributions: dirRequest.contributions, manifest_id: dirRequest.manifest_id }
    : null;
  const charAttempt = attempts.find((a) => a.inference_kind === 'character_move');
  const moveText = extractCharacterConsumerBehaviorText(charAttempt, presentationText);
  const projection = roundResult.lh0_transport?.character?.finalized_projection
    ?? roundResult.character_turn?.lh0FinalizedProjection
    ?? null;
  const dirProjection = roundResult.lh0_director_projection_receipt ?? null;
  const continuity = extractContinuityForensics(roundResult.hgSessionId, roundResult.sessionsDir);

  const forkResults = [];
  if (charForks.length && charManifest) {
    forkResults.push(...evaluateCharacterForkAtTurn({
      fixture,
      turnIndex,
      manifest: charManifest,
      finalizedProjection: projection,
      moveText,
      presentationText,
      playerStimulus,
      storeSnapshot: store,
    }));
  }
  if (dirForks.length) {
    forkResults.push(...evaluateDirectorForkAtTurn({
      fixture,
      turnIndex,
      manifest: dirManifest,
      finalizedProjection: dirProjection,
      directorDecision: roundResult.directorPhase?.directorDecision ?? null,
      playerStimulus,
      storeSnapshot: store,
    }));
  }
  return buildLh1bCausalTraceRow({
    turnIndex,
    hgRoundId: roundResult.hg_round_id,
    arm,
    characterTrace: roundResult.lh0_transport?.character ?? null,
    directorTrace: roundResult.lh0_transport?.director ?? null,
    forkEvaluations: forkResults,
  });
}

async function createLh1bScenarioSession(client, scenarioKey) {
  const scenario = SCENARIO_MAP[scenarioKey];
  if (!scenario) throw new Error(`unknown LH-1B scenario: ${scenarioKey}`);
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = openers[0];
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

export async function runLh1bTurn({
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
  mockOverrides = {},
  stopOnFailure = true,
  frozenHashGate = null,
}) {
  const hashCheck = frozenHashGate ?? verifyLh1bFrozenHashes({
    scenario_key: scenario.scenario_key,
    policy_hash: loadLh1bPolicy(scenario.scenario_key).policy_hash,
  });
  if (!hashCheck.pass) {
    const err = new Error(`LH-1B frozen hash drift: ${hashCheck.drift.map(([k]) => k).join(',')}`);
    err.stop_condition = 'fixture_policy_hash_drift';
    throw err;
  }

  client._beginRoundOperation(`lh1b-${sequenceId}-t${turnIndex}`, 'user_turn');
  const started = Date.now();
  const { playerDecomposition } = await runPlayerPvrAndRecord(client, playerStimulus);
  const api = client._domainApi();
  const runtime = client.supervisor.runtime;
  const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const sceneSessionId = SessionId(`hg-lh1b-a2-${crypto.randomUUID()}`);
  const sceneAgent = runtime.ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const beatOptions = buildLh1bBeatOptions({
    armConfig,
    fixture,
    turnIndex,
    sessionsDir,
    scenario,
    mockOverrides: { ...mockOverrides, inferenceOpts },
  });
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
  roundResult.hgSessionId = client.activeSessionId;
  roundResult.sessionsDir = sessionsDir;
  roundResult.directorPhase = roundResult.directorPhase ?? {
    directorDecision: beatOptions.mockDirectorResponses?.[0]
      ? JSON.parse(beatOptions.mockDirectorResponses[0])
      : null,
  };

  const operationWallMs = Date.now() - started;
  const allAttempts = loadAttempts(evidenceRoot, client.activeSessionId);
  const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
  const fullRoundAttempts = loadFullAttemptsForRound(
    evidenceRoot,
    client.activeSessionId,
    roundResult.hg_round_id,
  );
  const store = armConfig.persistent_cognition_enabled
    ? readLh0Store(sessionsDir, client.activeSessionId)
    : { obligations: [], events: [] };
  if (armConfig.persistent_cognition_enabled) {
    classifyLh0ObligationStates(store, turnIndex);
    writeLh0Store(sessionsDir, client.activeSessionId, store);
  }

  const isolation = verifyArmIsolation({
    arm: armConfig.arm,
    turnIndex,
    roundResult,
    store,
    attempts: roundAttempts,
  });
  if (!isolation.pass && stopOnFailure) {
    const err = new Error(`LH-1B arm leakage: ${isolation.violations.join(';')}`);
    err.stop_condition = 'arm_leakage_detected';
    throw err;
  }

  const charRequest = extractAssembledRequestFromAttempts(fullRoundAttempts, 'character_move');
  const provenanceAudit = charRequest?.contributions?.some((c) => c?.provenance?.lh0_obligation_id)
    ? buildLhProvenanceAuditBlock({
      obligationIds: (store.obligations ?? []).map((o) => o.obligation_id),
      manifest: charRequest,
      hgRoundId: roundResult.hg_round_id,
      consumer: 'character_move',
    })
    : null;

  const causalTrace = evaluateTurnForks({
    fixture,
    arm: armConfig.arm,
    turnIndex,
    roundResult,
    store,
    playerStimulus,
    attempts: fullRoundAttempts,
  });

  const transportStep = roundResult.audit_steps?.find((s) => s.step === 'lh0_projection_transport');
  const charAttempt = fullRoundAttempts.find((a) => a.inference_kind === 'character_move');
  const moveText = extractCharacterConsumerBehaviorText(
    charAttempt,
    roundResult.presentation_text ?? '',
  );
  const continuitySnapshot = extractContinuityForensics(client.activeSessionId, sessionsDir);
  return {
    turn_index: turnIndex,
    scene_id: sceneId,
    exact_player_stimulus: playerStimulus,
    hg_round_id: roundResult.hg_round_id,
    domain_commit_id: roundResult.domain_commit_id,
    presentation_text: roundResult.presentation_text ?? '',
    move_text: moveText,
    lh0_post_commit: roundResult.lh0_post_commit ?? null,
    continuity_snapshot: continuitySnapshot,
    operation_wall_ms: operationWallMs,
    committed: roundResult.committed === true,
    player_decomposition_recorded: playerDecomposition != null,
    inference: summarizeAttempts(roundAttempts),
    turn_ordering: [...LH1B_TURN_ORDERING],
    lh1b_projection: {
      projected: transportStep?.projected_finalized === true,
      consumer_received: roundResult.lh0_transport?.character?.consumer_received === true,
      director_receipt: Boolean(roundResult.lh0_director_projection_receipt),
      director_llm_invoked: roundResult.topology_proof?.director_llm_invoked === true,
    },
    arm_isolation: isolation,
    provenance_audit: provenanceAudit,
    assembled_request_character: charRequest,
    assembled_request_director: extractAssembledRequestFromAttempts(fullRoundAttempts, 'director_turn'),
    causal_trace: causalTrace,
    checkpoint: Object.entries(LH1B_CHECKPOINTS).find(([, t]) => t === turnIndex)?.[0] ?? null,
    stop_triggered: !roundResult.committed && stopOnFailure,
  };
}

export async function executeLh1bLiveSequence({
  sequencePlan,
  evidenceRoot,
  outputDir,
  mockOverridesByTurn = {},
  turnRange = null,
  liveAuthorized = false,
}) {
  if (!liveAuthorized) {
    throw new Error('LH-1B live execution not authorized — use mock qualification mode');
  }
  const armConfig = buildLh0ArmConfig(sequencePlan.arm);
  const fixture = loadLh1bFixtureManifest(sequencePlan.scenario_key);
  const scenario = SCENARIO_MAP[sequencePlan.scenario_key];
  const hashCheck = verifyLh1bFrozenHashes(sequencePlan);
  if (!hashCheck.pass) {
    return {
      failed: true,
      error: `frozen hash drift: ${hashCheck.drift.map(([k]) => k).join(',')}`,
      stop_condition: 'fixture_policy_hash_drift',
    };
  }

  const sequenceId = `LH1B-LIVE-${sequencePlan.arm}-${sequencePlan.scenario_key}-${Date.now()}`;
  const sessionsDir = defaultSessionsDir();
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
      sessionsDir,
    },
  });
  const turns = [];
  const causalTraces = [];
  let failed = false;
  let error = null;
  let stopCondition = null;
  let hgSessionId = null;
  const inferenceEvents = [];

  await client.start();
  try {
    await createLh1bScenarioSession(client, sequencePlan.scenario_key);
    hgSessionId = client.activeSessionId;
    if (armConfig.persistent_cognition_enabled) {
      writeLh0Store(sessionsDir, hgSessionId, {
        schema: 'issue201_lh0_persistent_store_v1',
        campaign: 'lh1b',
        fixture_id: fixture.fixture_id,
        obligations: [],
        events: [],
      });
    }
    const planTurns = sequencePlan.turns.filter((t) => {
      if (!turnRange) return true;
      return t.turn_index >= turnRange.from && t.turn_index <= turnRange.to;
    });
    for (const planTurn of planTurns) {
      const turnRow = await runLh1bTurn({
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
        mockOverrides: mockOverridesByTurn[planTurn.turn_index] ?? {},
      });
      turns.push(turnRow);
      causalTraces.push(turnRow.causal_trace);
      for (const ev of turnRow.inference?.events ?? []) {
        inferenceEvents.push({ ...ev, turn_index: planTurn.turn_index });
      }
      if (!turnRow.committed) {
        failed = true;
        error = `turn ${planTurn.turn_index} not committed`;
        stopCondition = 'terminal_beat_failure_budget_exceeded';
        break;
      }
    }
  } catch (err) {
    failed = true;
    error = String(err?.message ?? err);
    stopCondition = err.stop_condition ?? 'projection_seam_failed';
  } finally {
    await client.stop();
  }

  const lh0Store = (hgSessionId && armConfig.persistent_cognition_enabled)
    ? readLh0Store(sessionsDir, hgSessionId)
    : { obligations: [], events: [] };
  const archaeology = buildLh1bArchaeologyDossier({
    sequencePlan: { ...sequencePlan, sequence_id: sequenceId },
    fixture,
    turnRecords: turns,
    forkResults: causalTraces.flatMap((t) => t.fork_evaluations ?? []),
  });
  const costRollup = buildLh1bCostRollup({
    arm: sequencePlan.arm,
    sequenceId,
    inferenceEvents: attemptsToInferenceEvents(inferenceEvents),
  });

  const sequence = {
    schema: LH1B_SCHEMAS.LIVE_SEQUENCE,
    sequence_id: sequenceId,
    blind_label: sequencePlan.blind_label,
    arm: sequencePlan.arm,
    scenario_key: sequencePlan.scenario_key,
    hg_session_id: hgSessionId,
    fixture_hash: sequencePlan.fixture_hash,
    policy_hash: sequencePlan.policy_hash,
    failed,
    error,
    stop_condition: stopCondition,
    turn_count_completed: turns.length,
    turn_count_target: sequencePlan.turn_count,
    turns,
    causal_traces: causalTraces,
    lh0_store_path: hgSessionId ? lh0StorePath(sessionsDir, hgSessionId) : null,
    lh0_store: lh0Store,
    archaeology_dossier: archaeology,
    cost_rollup: costRollup,
    failure_policy: LH1B_LIVE_FAILURE_POLICY,
    isolation: sequencePlan.isolation,
  };

  if (outputDir) {
    fs.mkdirSync(outputDir, { recursive: true });
    fs.writeFileSync(
      path.join(outputDir, `${sequenceId}-sequence.json`),
      `${JSON.stringify(sequence, null, 2)}\n`,
    );
  }
  return sequence;
}

export async function executeLh1bLiveCampaign({
  outputDir,
  preflightReport = null,
  liveAuthorized = false,
}) {
  if (!liveAuthorized) {
    throw new Error('LH-1B live S1–S6 not authorized');
  }
  fs.mkdirSync(outputDir, { recursive: true });
  const preflight = preflightReport ?? runLh1bLivePreflight();
  if (!preflight.all_pass) {
    throw new Error('LH-1B live preflight failed');
  }
  const campaignPlan = preflight.campaign_plan;
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh1b-campaign-plan-locked.json'),
    `${JSON.stringify(campaignPlan, null, 2)}\n`,
  );
  const sequences = [];
  for (const seqPlan of campaignPlan.sequences) {
    sequences.push(await executeLh1bLiveSequence({
      sequencePlan: seqPlan,
      evidenceRoot: outputDir,
      outputDir,
      liveAuthorized: true,
    }));
    if (sequences[sequences.length - 1].failed) break;
  }
  const report = {
    schema: LH1B_SCHEMAS.LIVE_CAMPAIGN_REPORT,
    campaign: 'lh1b_causal_replication',
    apparatus_candidate_sha: APPARATUS_CANDIDATE_SHA,
    execution_candidate_sha: gitSha(),
    preflight,
    frozen_hashes: FROZEN_HASHES,
    campaign_plan: campaignPlan,
    sequences,
    campaign_failed: sequences.some((s) => s.failed),
    failure_policy: LH1B_LIVE_FAILURE_POLICY,
    output_dir: outputDir,
  };
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh1b-live-campaign-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  return report;
}

export function describeLh1bLiveExecutionPlan() {
  const plan = buildLh1bCampaignPlan();
  return {
    authorized: false,
    entry_point: 'node v2/rp_runtime/scripts/issue201-lh1b-seam-verification.mjs --execute-campaign',
    sequences: plan.sequences.map((s) => ({
      blind_label: s.blind_label,
      arm: s.arm,
      turn_count: s.turn_count,
      fork_ids: s.fork_ids,
    })),
    failure_policy: LH1B_LIVE_FAILURE_POLICY,
    note: 'Requires Governance live authorization and passing runLh1bLivePreflight().',
  };
}
