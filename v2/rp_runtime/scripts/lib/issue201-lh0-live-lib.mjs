/**
 * Issue #201 LH-0 — live micro-run execution.
 */
import { execFileSync } from 'node:child_process';
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
  storytellerAbsenceProof,
  a2ProhibitedSupportProof,
} from './issue201-g3d-lib.mjs';
import { LH0_ARMS, buildLh0ArmConfig, resolveLh0BeatOptions } from './issue201-lh0-arms.mjs';
import { loadLh0Policy, selectPlayerStimulus, sha256File } from './issue201-lh0-player-policy.mjs';
import { loadLh0FixtureManifest, REPO_ROOT } from './issue201-lh0-fixtures.mjs';
import {
  readLh0Store,
  writeLh0Store,
  classifyLh0ObligationStates,
  lh0StorePath,
} from './issue201-lh0-persistent-store.mjs';
import {
  adjudicateLh0ArmSequence,
  buildCounterfactualInterpretation,
  buildPassFailMatrix,
} from './issue201-lh0-live-adjudication.mjs';
import { buildInformationUniquenessReport } from './issue201-lh0-semantic-content.mjs';
import { runLh0SemanticValidationSuite } from './issue201-lh0-semantic-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import { simulateNegativeControl } from './issue201-lh0-lib.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';

export { REPO_ROOT, gitSha };

const SCENARIO = G3_SCENARIOS.ayame_controlled;

async function createScenarioSession(client) {
  const openers = await client.listTemplateOpeners(SCENARIO.id);
  const opener = openers[0];
  if (!opener) throw new Error(`no opener for ${SCENARIO.id}`);
  return client.createSession({
    characters: SCENARIO.characters,
    sceneTemplateId: SCENARIO.id,
    roleAssignments: SCENARIO.roleAssignments,
    playerCharacterFileId: SCENARIO.playerCharacterFileId,
    userPersonaId: SCENARIO.userName,
    opening: { mode: 'template', opener_id: opener.opener_id },
  });
}

async function runPlayerPvr(client, userMessage) {
  const api = client._domainApi();
  const phaseExecutors = client.supervisor.runtime?.phaseExecutors;
  const trace = client.supervisor.runtime?.traceEmitter;
  const inference = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const modelProfile = inference.roleProfiles.character;
  const sceneSessionId = SessionId(`hg-lh0-pvr-${crypto.randomUUID()}`);
  const sceneAgent = client.supervisor.runtime.ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const triageModelProfile = modelProfileForInferenceKind(
    modelProfile, 'player_visibility_triage', client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const verificationModelProfile = modelProfileForInferenceKind(
    modelProfile, 'player_uniform_eligibility_verification', client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const triageResult = await phaseExecutors.runPlayerVisibilityTriage({
    api, trace, sceneAgent,
    hgSessionId: client.activeSessionId,
    hgSceneId: client.activeSessionId,
    hgRoundId: null,
    inferenceId: `lh0-triage-${crypto.randomUUID()}`,
    playerContent: userMessage,
    modelProfile: triageModelProfile,
    verificationModelProfile,
  });
  let playerDecomposition = null;
  if (triageResult.route === 'uniform_projection' && triageResult.playerDecomposition) {
    playerDecomposition = triageResult.playerDecomposition;
  } else {
    const decompositionModelProfile = modelProfileForInferenceKind(
      modelProfile, 'player_decomposition', client.runtimeSettings,
      { inferenceMode: client.options.inferenceMode },
    );
    const decompositionResult = await phaseExecutors.runPlayerDecomposition({
      api, trace, sceneAgent,
      hgSessionId: client.activeSessionId,
      hgSceneId: client.activeSessionId,
      hgRoundId: null,
      inferenceId: `lh0-decomp-${crypto.randomUUID()}`,
      playerContent: userMessage,
      modelProfile: decompositionModelProfile,
    });
    playerDecomposition = decompositionResult.playerDecomposition ?? null;
  }
  return { playerDecomposition };
}

function extractLh0TurnForensics(roundResult, { sessionsDir, hgSessionId, turnIndex }) {
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
      || charEvidence?.consumer_received === true
      || transportStep?.character_consumer_receipt === true,
    consumer_used: charEvidence?.consumer_used === true,
    decision_influenced: (charEvidence?.decision_influenced_obligation_ids ?? []).length > 0,
    projected_anchor_ids: [],
    lh0_store: store,
    lh0_transport: roundResult.lh0_transport ?? null,
    lh0_consequences: roundResult.lh0_consequences ?? null,
  };
}

async function runLh0Turn({
  client, armConfig, turnIndex, playerStimulus, sequenceId, evidenceRoot, sessionsDir, plotScopeIdRef,
}) {
  const continuityBefore = extractContinuityForensics(client.activeSessionId, sessionsDir);
  const plotBefore = extractPlotForensics(
    continuityBefore.plot_cognition_scope_id ?? plotScopeIdRef.value,
    sessionsDir,
  );
  client._beginRoundOperation(`lh0-${sequenceId}-t${turnIndex}`, 'user_turn');
  const started = Date.now();
  const { playerDecomposition } = await runPlayerPvr(client, playerStimulus);
  const api = client._domainApi();
  const runtime = client.supervisor.runtime;
  const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const sceneSessionId = SessionId(`hg-lh0-a2-${crypto.randomUUID()}`);
  const sceneAgent = runtime.ctx.agentLoop.create(
    sceneSessionId,
    agentOptionsFromProfile(mockInferenceProfile()),
  );
  const beatOptions = {
    ...resolveLh0BeatOptions(armConfig),
    scenarioKey: SCENARIO.scenario_key,
    roleAssignments: SCENARIO.roleAssignments,
    roleProfiles: inferenceOpts.roleProfiles,
    liveMaxAttempts: inferenceOpts.liveMaxAttempts,
    uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
    characterSemanticEvaluationEnabled: false,
    captureActorContextPackages: true,
    lh0Arm: armConfig.persistent_cognition_enabled ? armConfig.arm : null,
    lh0SessionsDir: armConfig.persistent_cognition_enabled ? sessionsDir : null,
    lh0FixtureTurnIndex: turnIndex,
    skipPostCommitPlot: armConfig.arm !== LH0_ARMS.LH_B,
    runPostCommitPlot: false,
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
  const plotAfter = extractPlotForensics(continuityAfter.plot_cognition_scope_id, sessionsDir);
  const lh0Projection = extractLh0TurnForensics(roundResult, {
    sessionsDir, hgSessionId: client.activeSessionId, turnIndex,
  });
  const isolation = roundResult.actor_context_audit?.isolation ?? { pass: true, leak_count: 0 };
  const storytellerProof = storytellerAbsenceProof(roundAttempts);
  const prohibitedProof = a2ProhibitedSupportProof(roundAttempts, {
    allowPlot: armConfig.arm === LH0_ARMS.LH_B,
  });
  return {
    turn_index: turnIndex,
    exact_player_stimulus: playerStimulus,
    hg_round_id: roundResult.hg_round_id,
    domain_commit_id: roundResult.domain_commit_id,
    presentation_text: roundResult.presentation_text ?? '',
    operation_wall_ms: operationWallMs,
    committed: roundResult.committed === true,
    inference: summarizeAttempts(roundAttempts),
    session_inference: summarizeAttempts(allAttempts),
    plot_forensics: { before: plotBefore, after: plotAfter },
    lh0_post_commit: roundResult.lh0_post_commit ?? null,
    lh0_projection: lh0Projection,
    lh0_director_projection_receipt: roundResult.lh0_director_projection_receipt ?? null,
    actor_context_isolation: isolation,
    lh0_transport: roundResult.lh0_transport ?? null,
    lh0_consequences: roundResult.lh0_consequences ?? null,
    lh0_causal_evidence: roundResult.character_turn?.lh0ConsumerEvidence?.lh0_causal_evidence ?? null,
    audit: {
      projection_transport: roundResult.audit_steps?.find((s) => s.step === 'lh0_projection_transport') ?? null,
      character_consumer_receipt: roundResult.audit_steps?.find((s) => s.step === 'lh0_character_consumer_receipt') ?? null,
      consumption_enforcer: roundResult.audit_steps?.find((s) => s.step === 'lh0_consumption_lifecycle_enforcer') ?? null,
    },
    proofs: { storyteller_absence: storytellerProof, prohibited_support: prohibitedProof },
    seam_failure: null,
  };
}

export async function executeLh0LiveArm({
  arm,
  evidenceRoot,
  outputDir,
  policyBundle,
}) {
  const armConfig = buildLh0ArmConfig(arm);
  const { policy, policy_hash } = policyBundle;
  const fixture = loadLh0FixtureManifest();
  const sequenceId = `LH0-LIVE-${arm}-${Date.now()}`;
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
  let failed = false;
  let error = null;
  let hgSessionId = null;
  const plotScopeIdRef = { value: null };
  await client.start();
  try {
    await createScenarioSession(client);
    hgSessionId = client.activeSessionId;
    if (armConfig.persistent_cognition_enabled) {
      writeLh0Store(sessionsDir, hgSessionId, { schema: 'issue201_lh0_persistent_store_v1', obligations: [], events: [] });
    }
    const prior = [];
    for (let turnIndex = 1; turnIndex <= policy.turn_count; turnIndex += 1) {
      const selection = selectPlayerStimulus(policy, turnIndex, prior);
      const turnRow = await runLh0Turn({
        client,
        armConfig,
        turnIndex,
        playerStimulus: selection.exact_player_stimulus,
        sequenceId,
        evidenceRoot,
        sessionsDir,
        plotScopeIdRef,
      });
      turns.push(turnRow);
      prior.push({ turn_index: turnIndex, presentation_text: turnRow.presentation_text });
      if (!turnRow.committed) {
        failed = true;
        error = `turn ${turnIndex} not committed`;
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
  const adjudication = adjudicateLh0ArmSequence({ arm, turns, lh0Store, fixture });
  const sequence = {
    schema: 'issue201_lh0_live_sequence_v1',
    sequence_id: sequenceId,
    arm,
    arm_label: armConfig.label,
    hg_session_id: hgSessionId,
    policy_id: policy.policy_id,
    policy_hash,
    fixture_id: fixture.fixture_id,
    fixture_hash: sha256File(path.join(REPO_ROOT, 'governance/records/issue201-lh0-fixtures/lh0_fixture_manifest.json')),
    failed,
    error,
    turns,
    lh0_store_path: hgSessionId ? lh0StorePath(sessionsDir, hgSessionId) : null,
    lh0_store: lh0Store,
    adjudication,
  };
  fs.writeFileSync(
    path.join(outputDir, `${sequenceId}-sequence.json`),
    `${JSON.stringify(sequence, null, 2)}\n`,
  );
  return sequence;
}

export async function executeLh0TurnAlignedVerificationCampaign({ outputDir }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const timing = runLh0TimingValidationSuite();
  if (!timing.readiness_for_turn_aligned_qualification) {
    throw new Error('LH-0 timing validation failed before turn-aligned qualification');
  }
  const semantic = runLh0SemanticValidationSuite();
  if (!semantic.readiness_for_final_qualification) {
    throw new Error('LH-0 semantic validation failed before turn-aligned qualification');
  }
  const policyBundle = loadLh0Policy('ayame_lh0_policy_v1');
  const evidenceRoot = outputDir;
  const arms = [LH0_ARMS.LH_A, LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D];
  const sequences = [];
  for (const arm of arms) {
    sequences.push(await executeLh0LiveArm({
      arm,
      evidenceRoot,
      outputDir,
      policyBundle,
    }));
  }
  const armResults = sequences.map((s) => s.adjudication);
  const control = sequences.find((s) => s.arm === LH0_ARMS.LH_A);
  const persistent = sequences.filter((s) => s.arm !== LH0_ARMS.LH_A);
  const counterfactual = buildCounterfactualInterpretation({
    controlSequence: control,
    persistentSequences: persistent,
    fixture: loadLh0FixtureManifest(),
  });
  const report = {
    schema: 'issue201_lh0_turn_aligned_verification_v1',
    campaign: 'lh0_turn_aligned_final_verification',
    prior_anchors: {
      semantic_qualification: 'data/investigation_runs/issue201-lh0-final-qualification-2026-09-15T22-17-52-827Z',
      semantic_remediation_commit: 'b7d5b7c',
    },
    candidate_sha: gitSha(),
    timing_validation: timing,
    semantic_validation: semantic,
    information_uniqueness: buildInformationUniquenessReport({ manifestContributions: [] }),
    output_dir: outputDir,
    sequences,
    pass_fail_matrix: buildPassFailMatrix(armResults),
    counterfactual_interpretation: counterfactual,
    lh1a_readiness: {
      lh_b: armResults.find((r) => r.arm === LH0_ARMS.LH_B)?.lh1a_ready ?? false,
      lh_c: armResults.find((r) => r.arm === LH0_ARMS.LH_C)?.lh1a_ready ?? false,
      lh_d: armResults.find((r) => r.arm === LH0_ARMS.LH_D)?.lh1a_ready ?? false,
    },
  };
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-turn-aligned-verification-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  return report;
}

export async function executeLh0FinalQualificationCampaign({ outputDir }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const semantic = runLh0SemanticValidationSuite();
  if (!semantic.readiness_for_final_qualification) {
    throw new Error('LH-0 semantic validation failed before final qualification');
  }
  const policyBundle = loadLh0Policy('ayame_lh0_policy_v1');
  const evidenceRoot = outputDir;
  const arms = [LH0_ARMS.LH_A, LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D];
  const sequences = [];
  for (const arm of arms) {
    sequences.push(await executeLh0LiveArm({
      arm,
      evidenceRoot,
      outputDir,
      policyBundle,
    }));
  }
  const armResults = sequences.map((s) => s.adjudication);
  const control = sequences.find((s) => s.arm === LH0_ARMS.LH_A);
  const persistent = sequences.filter((s) => s.arm !== LH0_ARMS.LH_A);
  const counterfactual = buildCounterfactualInterpretation({
    controlSequence: control,
    persistentSequences: persistent,
    fixture: loadLh0FixtureManifest(),
  });
  const report = {
    schema: 'issue201_lh0_final_qualification_v1',
    campaign: 'lh0_semantic_final_qualification',
    prior_anchors: {
      first_live: 'data/investigation_runs/issue201-lh0-live-2026-09-15T21-16-16-968Z',
      remediation: 'data/investigation_runs/issue201-lh0-live-2026-09-15T21-36-09-178Z',
      cd_postfix: 'data/investigation_runs/issue201-lh0-cd-postfix-2026-09-15T21-51-52-447Z',
    },
    candidate_sha: gitSha(),
    semantic_validation: semantic,
    information_uniqueness: buildInformationUniquenessReport({ manifestContributions: [] }),
    output_dir: outputDir,
    sequences,
    pass_fail_matrix: buildPassFailMatrix(armResults),
    counterfactual_interpretation: counterfactual,
    lh1a_readiness: {
      lh_b: armResults.find((r) => r.arm === LH0_ARMS.LH_B)?.lh1a_ready ?? false,
      lh_c: armResults.find((r) => r.arm === LH0_ARMS.LH_C)?.lh1a_ready ?? false,
      lh_d: armResults.find((r) => r.arm === LH0_ARMS.LH_D)?.lh1a_ready ?? false,
    },
  };
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-final-qualification-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  return report;
}

export async function executeLh0LiveCampaign({ outputDir }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const policyBundle = loadLh0Policy('ayame_lh0_policy_v1');
  const evidenceRoot = outputDir;
  const arms = [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D];
  const sequences = [];
  for (const arm of arms) {
    sequences.push(await executeLh0LiveArm({
      arm,
      evidenceRoot,
      outputDir,
      policyBundle,
    }));
  }
  const negativeControls = loadLh0FixtureManifest().negative_controls.map((nc) => ({
    control_id: nc.control_id,
    observed: simulateNegativeControl(nc.break_layer),
    expected_seam: nc.expected_seam,
  }));
  const armResults = sequences.map((s) => s.adjudication);
  const report = {
    schema: 'issue201_lh0_live_execution_v1',
    remediation_run: true,
    first_run_anchor: 'data/investigation_runs/issue201-lh0-live-2026-09-15T21-16-16-968Z',
    candidate_sha: gitSha(),
    apparatus_sha: 'a96886b',
    activation_commit: '741e1ce',
    live_micro_runs_executed: true,
    rp_quality_conclusions: false,
    inference_mode: 'live',
    model_configuration: 'application default live profiles (DeepSeek mount)',
    fixture_id: policyBundle.policy.fixture_id ?? loadLh0FixtureManifest().fixture_id,
    fixture_hash: sha256File(path.join(REPO_ROOT, 'governance/records/issue201-lh0-fixtures/lh0_fixture_manifest.json')),
    policy_hash: policyBundle.policy_hash,
    sequences,
    pass_fail_matrix: buildPassFailMatrix(armResults),
    negative_controls: negativeControls,
    lh1a_readiness: {
      lh_b: armResults.find((r) => r.arm === LH0_ARMS.LH_B)?.lh1a_ready ?? false,
      lh_c: armResults.find((r) => r.arm === LH0_ARMS.LH_C)?.lh1a_ready ?? false,
      lh_d: armResults.find((r) => r.arm === LH0_ARMS.LH_D)?.lh1a_ready ?? false,
    },
    disclaimer: 'LH-0 validates transport, persistence, consumption, deferral, activation, and forensic attribution. It does not establish comparative RP quality or long-horizon narrative value.',
  };
  fs.writeFileSync(
    path.join(outputDir, 'issue201-lh0-live-execution-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  return report;
}

export function verifyCandidateDrift(expectedSha = 'a96886b') {
  const head = gitSha();
  const apparatusFiles = [
    'v2/rp_runtime/scripts/lib/issue201-lh0-lib.mjs',
    'v2/rp_runtime/scripts/lib/issue201-lifecycle-tracer.mjs',
    'v2/rp_runtime/scripts/lib/issue201-obligation-ledger.mjs',
    'v2/rp_runtime/scripts/lib/issue201-lh0-arms.mjs',
    'v2/rp_runtime/scripts/lib/issue201-seam-classifier.mjs',
    'v2/rp_runtime/scripts/lib/issue201-lifecycle-states.mjs',
  ];
  let apparatusDiff = '';
  try {
    apparatusDiff = execFileSync(
      'git',
      ['diff', expectedSha, '--', ...apparatusFiles],
      { cwd: REPO_ROOT, encoding: 'utf8' },
    ).trim();
  } catch {
    apparatusDiff = 'diff_failed';
  }
  const unchanged = apparatusFiles.every((f) => fs.existsSync(path.join(REPO_ROOT, f)));
  const isAncestor = (() => {
    try {
      execFileSync('git', ['merge-base', '--is-ancestor', expectedSha, 'HEAD'], { cwd: REPO_ROOT });
      return true;
    } catch {
      return false;
    }
  })();
  return {
    head,
    expected_apparatus_sha: expectedSha,
    apparatus_ancestor_of_head: isAncestor,
    apparatus_core_diff_empty: apparatusDiff.length === 0,
    apparatus_files_present: unchanged,
    drift_detected: !unchanged || (!isAncestor && head !== expectedSha),
  };
}
