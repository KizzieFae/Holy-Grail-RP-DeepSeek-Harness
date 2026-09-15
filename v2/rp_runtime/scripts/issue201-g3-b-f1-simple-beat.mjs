#!/usr/bin/env node
/**
 * Issue #201 G3-B F1 — Simple-beat A2 vs lean-A4 (Ayame F06).
 * Produces blind packet + pre-decode evidence. STOP before answer-key decode.
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../src/application/application-settings.mjs';
import {
  agentOptionsFromProfile,
  mockInferenceProfile,
} from '../src/lib/inference-profile.mjs';
import { runA2BeatRound } from '../src/lib/a2-beat-orchestration.mjs';
import { G3_SCENARIOS } from './lib/issue201-g3-scenarios.mjs';
import {
  F06_PLAYER_STIMULUS,
  LEAN_A4_ROUND_OPTIONS,
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  prohibitedCognitionProof,
  ingressPvrObservations,
  buildBlindPacket,
} from './lib/issue201-g3-b-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const D07_EXPERIMENTAL_SHA = '921b127';
const D07_CONTROL_SHA = 'c751ea6';
const G3A_ACCEPT_SHA = 'b806c7d';

const SCENARIO_BRIEFING = {
  setting: 'Ayame household front door; Kizzie (applicant) has knocked for a live-in position interview.',
  player_character: 'Kizzie',
  judge: 'The presentation should reflect what the player sees/hears after the knock at the threshold.',
};

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function runComparabilityGate(head) {
  const narratorPhase = fs.readFileSync(
    path.join(REPO_ROOT, 'v2/rp_runtime/src/plugins/hg-phase-executors/narrator-phase.mjs'),
    'utf8',
  );
  const hasSkipFlag = narratorPhase.includes('skipNarratorEnvironmentCognition');
  const defaultFalse = /skipNarratorEnvironmentCognition\s*=\s*false/.test(narratorPhase)
    || (narratorPhase.includes('skipNarratorEnvironmentCognition') && !/skipNarratorEnvironmentCognition\s*\?\?\s*true/.test(narratorPhase));
  const diffSinceD07 = execFileSync(
    'git',
    ['diff', '--name-only', D07_EXPERIMENTAL_SHA, 'HEAD', '--',
      'v2/rp_runtime/src/plugins/hg-phase-executors/narrator-phase.mjs',
      'v2/domain/',
      'data/scene_templates/ayame_household_entry_evaluation.json',
      'v2/rp_runtime/scripts/lib/issue201-g3-scenarios.mjs'],
    { cwd: REPO_ROOT, encoding: 'utf8' },
  ).trim().split('\n').filter(Boolean);
  const materialDrift = diffSinceD07.some((f) => f.includes('ayame_household') || f.includes('issue201-g3-scenarios'));
  return {
    head_sha: head,
    d07_experimental_sha: D07_EXPERIMENTAL_SHA,
    d07_control_substrate_sha: D07_CONTROL_SHA,
    g3a_accept_sha: G3A_ACCEPT_SHA,
    skip_narrator_environment_cognition_present: hasSkipFlag,
    skip_narrator_environment_cognition_default_false: defaultFalse,
    lean_a4_preserves_env_cognition: defaultFalse,
    changed_paths_since_d07: diffSinceD07,
    material_drift_threatens_causal_comparability: materialDrift,
    decision: 'rerun_lean_a4_at_current_sha_for_exact_sha_pairing_with_a2',
    d07_ablated_evidence_reuse: false,
    rationale: 'Paired F1 comparison at current execution SHA. skipNarratorEnvironmentCognition default remains false; lean A4 does not pass skip flag.',
  };
}

async function createScenarioSession(client, scenario) {
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = scenario.openerPreference
    ? openers.find((o) => String(o.opener_id ?? '').includes(scenario.openerPreference)) ?? openers[0]
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

async function runPlayerPvrAndRecord(client, userMessage) {
  const api = client._domainApi();
  const phaseExecutors = client.supervisor.runtime?.phaseExecutors;
  const trace = client.supervisor.runtime?.traceEmitter;
  const inference = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const modelProfile = inference.roleProfiles.character;
  const sceneSessionId = SessionId(`hg-issue201-pvr-${crypto.randomUUID()}`);
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
    inferenceId: `issue201-triage-${crypto.randomUUID()}`,
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
      inferenceId: `issue201-pd-${crypto.randomUUID()}`,
      playerContent: userMessage,
      modelProfile: decompositionModelProfile,
    });
    playerDecomposition = decompositionResult.playerDecomposition;
  }
  await api.recordUserTurn({
    hg_session_id: client.activeSessionId,
    content: userMessage,
    speaker: client.userPersonaId ?? 'Player',
    player_decomposition: playerDecomposition,
  });
  return { playerDecomposition };
}

function presentationFromRound(roundResult) {
  return roundResult.presentation_text
    ?? roundResult.character_turns?.at(-1)?.presentation_text
    ?? '';
}

function parseLatencySummary(latencyText) {
  if (!latencyText || typeof latencyText !== 'string') return {};
  const out = {};
  const pvl = latencyText.match(/"player_visible_latency":\s*\{[^}]*"ms":\s*(\d+)/);
  if (pvl) out.player_visible_ms = Number(pvl[1]);
  return out;
}

function runLatencyReconstruction(sessionId, operationId, roundId, commitId, evidenceRoot) {
  const script = path.join(REPO_ROOT, 'tools', 'investigation', 'reconstruct_round_latency.py');
  if (!fs.existsSync(script)) return null;
  try {
    return execFileSync('python', [
      script, sessionId, '--operation', operationId ?? '', '--round', roundId ?? '',
      '--commit', commitId ?? '', '--attribution', '--evidence-root', evidenceRoot,
    ], { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 30 * 1024 * 1024 });
  } catch {
    return null;
  }
}

function objectiveChecksA2({
  roundResult, presentation, roundInference, topologyProof, prohibitedProof, spatial, playerDecomposition, ingressPvr,
}) {
  const issues = [];
  if (!roundResult?.committed) issues.push({ type: 'not_committed', detail: roundResult?.completion_reason });
  if (!String(presentation ?? '').trim()) issues.push({ type: 'empty_presentation' });
  if (!topologyProof?.two_call_contract) issues.push({ type: 'topology_proof_failed' });
  if (!prohibitedProof?.pass) issues.push({ type: 'prohibited_cognition', detail: prohibitedProof.violations });
  if (spatial?.accepted === false) issues.push({ type: 'spatial_contradiction' });
  if (roundInference.character_move_count < 1) issues.push({ type: 'missing_character_move' });
  if (roundInference.narrator_presentation_count < 1) issues.push({ type: 'missing_narrator_presentation' });
  if (ingressPvr?.uniform_path_violation) {
    issues.push({ type: 'ingress_uniform_path_violation', detail: 'player_decomposition when uniform eligible' });
  }
  const blocking = issues.filter((i) => ['not_committed', 'empty_presentation', 'topology_proof_failed', 'prohibited_cognition', 'spatial_contradiction'].includes(i.type));
  return {
    committed: Boolean(roundResult?.committed),
    presentation_nonempty: Boolean(String(presentation ?? '').trim()),
    uniform_projection_used: ingressPvr?.uniform_projection_eligible === true,
    player_decomposition_recorded: Boolean(playerDecomposition),
    ingress_pvr: ingressPvr,
    topology_proof: topologyProof,
    prohibited_cognition: prohibitedProof,
    spatial,
    issues,
    verdict: blocking.length > 0 ? 'blocking_failure' : issues.length > 0 ? 'degraded_non_blocking' : 'clean',
  };
}

function objectiveChecksLeanA4({ history, userEntry, roundResult, presentation, hookIsolation }) {
  const issues = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  if (userPvr.validation_status && userPvr.validation_status !== 'valid') {
    issues.push({ type: 'pvr_validation', detail: userPvr.validation_status });
  }
  if (!roundResult?.committed) issues.push({ type: 'not_committed', detail: roundResult?.completion_reason });
  if (!String(presentation ?? '').trim()) issues.push({ type: 'empty_presentation' });
  if (!hookIsolation?.isolation_ok) issues.push({ type: 'hook_isolation_failed' });
  const blocking = issues.filter((i) => ['not_committed', 'empty_presentation', 'hook_isolation_failed'].includes(i.type));
  return {
    committed: Boolean(roundResult?.committed),
    presentation_nonempty: Boolean(String(presentation ?? '').trim()),
    pvr_validation_status: userPvr.validation_status ?? null,
    hook_isolation: hookIsolation,
    issues,
    verdict: blocking.length > 0 ? 'blocking_failure' : issues.length > 0 ? 'degraded_non_blocking' : 'clean',
  };
}

function makeClient(evidenceRoot) {
  return new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
}

async function runA2Case({ caseId, repIndex, evidenceRoot, outputsDir, readinessOnly = false }) {
  const scenario = G3_SCENARIOS.ayame_controlled;
  const client = makeClient(evidenceRoot);
  await client.start();
  try {
    const created = await createScenarioSession(client, scenario);
    const operationId = `issue201-${caseId}-${crypto.randomUUID()}`;
    client._beginRoundOperation(operationId, 'user_turn');
    const started = Date.now();
    const { playerDecomposition } = await runPlayerPvrAndRecord(client, scenario.playerPost);
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const runtime = client.supervisor.runtime;
    const sceneSessionId = SessionId(`hg-g3b-a2-${crypto.randomUUID()}`);
    const sceneAgent = runtime.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );
    const roundResult = await runA2BeatRound({
      phaseExecutors: runtime.phaseExecutors,
      api,
      trace: runtime.traceEmitter,
      sceneAgent,
      sceneSessionId,
      hgSessionId: created.hg_session_id,
      hgSceneId: created.hg_session_id,
      options: {
        scenarioKey: scenario.scenario_key,
        roleAssignments: scenario.roleAssignments,
        roleProfiles: inferenceOpts.roleProfiles,
        liveMaxAttempts: inferenceOpts.liveMaxAttempts,
        uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
        characterSemanticEvaluationEnabled: false,
        skipPostCommitPlot: true,
      },
    });
    const operationWallMs = Date.now() - started;
    const presentation = roundResult.presentation_text ?? '';
    const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');
    const allAttempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
    const inference = summarizeAttempts(allAttempts);
    const roundInference = summarizeAttempts(roundAttempts);
    const topologyProof = roundResult.topology_proof ?? null;
    const prohibitedProof = prohibitedCognitionProof(roundInference, 'a2_prototype', { scope: 'a2_round' });
    const ingressPvr = ingressPvrObservations(allAttempts, playerDecomposition);
    const spatial = roundResult.spatial_validation ?? {
      skipped: true,
      reason: 'no_structured_spatial_claims_surface',
      contradiction_count: 0,
    };
    const objective = objectiveChecksA2({
      roundResult, presentation, roundInference, topologyProof, prohibitedProof, spatial, playerDecomposition, ingressPvr,
    });
    const latencyText = runLatencyReconstruction(
      created.hg_session_id, operationId, roundResult.hg_round_id, roundResult.domain_commit_id, evidenceRoot,
    );
    const result = {
      case_id: caseId,
      architecture_arm: 'a2_prototype',
      scenario_id: scenario.id,
      rep_index: repIndex,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      operation_wall_ms: operationWallMs,
      player_visible_wall_ms: parseLatencySummary(latencyText ?? '').player_visible_ms ?? roundResult.efficiency?.critical_path_wall_ms ?? null,
      presentation_path: presentationPath,
      presentation_text: presentation,
      objective,
      inference,
      round_inference: roundInference,
      ingress_pvr: ingressPvr,
      topology_proof: topologyProof,
      prohibited_cognition_proof: prohibitedProof,
      spatial_validation: spatial,
      character_semantic_eval_off: {
        enabled: false,
        inference_count: inference.character_semantic_evaluation_count,
        move_committed: Boolean(roundResult?.committed),
        character_validation: roundResult.character_turn?.validation ?? null,
        presentation_coherent: Boolean(String(presentation).trim()),
      },
      environment_cognition_off: {
        inference_count: inference.narrator_environment_cognition_count,
        d04r_classification: 'deferred_to_governance_blind_adjunct',
      },
      decision_value_records: roundResult.decision_value?.records ?? [],
      efficiency: roundResult.efficiency ?? null,
      readiness_only: readinessOnly,
    };
    fs.writeFileSync(path.join(outputsDir, `${caseId}-meta.json`), `${JSON.stringify(result, null, 2)}\n`);
    return result;
  } finally {
    await client.stop();
  }
}

async function runLeanA4Case({ caseId, repIndex, evidenceRoot, outputsDir }) {
  const scenario = G3_SCENARIOS.ayame_controlled;
  const client = makeClient(evidenceRoot);
  await client.start();
  try {
    const created = await createScenarioSession(client, scenario);
    const operationId = `issue201-${caseId}-${crypto.randomUUID()}`;
    client._beginRoundOperation(operationId, 'user_turn');
    const started = Date.now();
    const { playerDecomposition } = await runPlayerPvrAndRecord(client, scenario.playerPost);
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const roundResult = await client.orchestrator.runRound({
      session: { mode: 'open', hg_session_id: client.activeSessionId },
      roleProfiles: inferenceOpts.roleProfiles,
      liveMaxAttempts: inferenceOpts.liveMaxAttempts,
      clientOperationId: operationId,
      spanTracker: client.activeSpanTracker,
      ...LEAN_A4_ROUND_OPTIONS,
    });
    await client._recordRoundPresentations(api, roundResult);
    await client._refreshTranscript();
    const operationWallMs = Date.now() - started;
    const presentation = presentationFromRound(roundResult);
    const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
    const attempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const inference = summarizeAttempts(attempts);
    const hookIsolation = {
      narrator_semantic_qa_observed: inference.narrator_semantic_qa_count,
      director_semantic_qa_observed: inference.director_semantic_qa_count,
      storyteller_post_commit_observed: inference.storyteller_post_commit_count,
      isolation_ok: inference.narrator_semantic_qa_count === 0
        && inference.director_semantic_qa_count === 0
        && inference.storyteller_post_commit_count === 0,
    };
    const objective = objectiveChecksLeanA4({
      history, userEntry, roundResult, presentation, hookIsolation,
    });
    const latencyText = runLatencyReconstruction(
      created.hg_session_id, operationId, roundResult.hg_round_id, roundResult.domain_commit_id, evidenceRoot,
    );
    const result = {
      case_id: caseId,
      architecture_arm: 'lean_a4_ablated',
      scenario_id: scenario.id,
      rep_index: repIndex,
      round_options: LEAN_A4_ROUND_OPTIONS,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      operation_wall_ms: operationWallMs,
      player_visible_wall_ms: parseLatencySummary(latencyText ?? '').player_visible_ms ?? null,
      presentation_path: presentationPath,
      presentation_text: presentation,
      objective,
      inference,
      hook_isolation: hookIsolation,
      player_decomposition_recorded: Boolean(playerDecomposition),
    };
    fs.writeFileSync(path.join(outputsDir, `${caseId}-meta.json`), `${JSON.stringify(result, null, 2)}\n`);
    return result;
  } finally {
    await client.stop();
  }
}

function aggregateArm(runs, arm) {
  const armRuns = runs.filter((r) => r.architecture_arm === arm);
  return {
    architecture_arm: arm,
    completed_runs: armRuns.length,
    objective_clean: armRuns.filter((r) => r.objective.verdict === 'clean').length,
    total_inference_count: armRuns.reduce((s, r) => s + r.inference.inference_count, 0),
    synchronous_cognition_estimate: arm === 'a2_prototype'
      ? armRuns.reduce((s, r) => s + (r.inference.character_move_count + r.inference.narrator_presentation_count + r.inference.director_turn_count), 0)
      : armRuns.reduce((s, r) => s + r.inference.inference_count, 0),
    handoff_estimate: arm === 'a2_prototype' ? armRuns.length * 2 : armRuns.reduce((s, r) => s + r.inference.inference_count, 0),
    wall_ms_total: armRuns.reduce((s, r) => s + r.operation_wall_ms, 0),
    reasoning_tokens_total: armRuns.reduce((s, r) => s + r.inference.reasoning_tokens_total, 0),
    input_tokens_total: armRuns.reduce((s, r) => s + r.inference.input_tokens_total, 0),
    output_tokens_total: armRuns.reduce((s, r) => s + r.inference.output_tokens_total, 0),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const head = gitSha();
  const comparability = runComparabilityGate(head);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-g3b-f1-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceRoot, 'comparability_gate.json'), `${JSON.stringify(comparability, null, 2)}\n`);

  console.log('Ayame A2 readiness probe...');
  const readiness = await runA2Case({
    caseId: 'G3B-F1-readiness-r0',
    repIndex: 0,
    evidenceRoot,
    outputsDir,
    readinessOnly: true,
  });
  const readinessBlocking = readiness.objective.issues?.filter((i) => !['prohibited_cognition'].includes(i.type)) ?? [];
  if (!readiness.objective.committed || !readiness.objective.presentation_nonempty || readinessBlocking.length > 0) {
    const report = { stop: true, reason: 'ayame_a2_readiness_failed', readiness };
    fs.writeFileSync(path.join(evidenceRoot, 'issue201-g3b-f1-report.json'), `${JSON.stringify(report, null, 2)}\n`);
    throw new Error(`A2 Ayame readiness STOP: ${JSON.stringify(readiness.objective.issues)}`);
  }
  console.log('Readiness OK:', readiness.objective.verdict);

  const plan = [];
  for (let rep = 1; rep <= 2; rep += 1) {
    plan.push({ caseId: `G3B-F1-a2-ayame-r${rep}`, arm: 'a2', rep });
    plan.push({ caseId: `G3B-F1-a4-ayame-r${rep}`, arm: 'lean_a4', rep });
  }

  const runs = [];
  const failures = [];
  for (const item of plan) {
    console.log(`Running ${item.caseId}...`);
    try {
      const result = item.arm === 'a2'
        ? await runA2Case({ caseId: item.caseId, repIndex: item.rep, evidenceRoot, outputsDir })
        : await runLeanA4Case({ caseId: item.caseId, repIndex: item.rep, evidenceRoot, outputsDir });
      runs.push(result);
      console.log(JSON.stringify({
        caseId: item.caseId,
        verdict: result.objective.verdict,
        inferences: result.inference.inference_count,
        wall_ms: result.operation_wall_ms,
      }));
      if (result.objective.verdict === 'blocking_failure') {
        failures.push({ case_id: item.caseId, issues: result.objective.issues });
      }
    } catch (err) {
      failures.push({ case_id: item.caseId, error: String(err?.message ?? err) });
      console.error(`FAILED ${item.caseId}:`, err);
    }
  }

  const scoredRuns = runs.filter((r) => r.objective?.verdict !== 'blocking_failure'
    && String(r.presentation_text ?? '').trim().length > 0);
  const blind = buildBlindPacket({
    runs: scoredRuns,
    outputsDir,
    purpose: 'Issue #201 G3-B F1 — Simple-beat comparison (4 Ayame F06 presentations)',
    scenarioBriefing: SCENARIO_BRIEFING,
    playerStimulus: F06_PLAYER_STIMULUS,
  });

  const report = {
    schema: 'issue201_g3b_f1_pre_decode_v1',
    generated_at: new Date().toISOString(),
    execution_sha: head,
    g3a_accept_sha: G3A_ACCEPT_SHA,
    comparability_gate: comparability,
    scenario: G3_SCENARIOS.ayame_controlled,
    player_stimulus: F06_PLAYER_STIMULUS,
    arms: {
      a2_prototype: {
        topology: 'PVR → eligibility → Character move → validation → commit → Narrator presentation → presentation validation → audit',
        prohibited_sync: ['storyteller', 'director_qa', 'narrator_qa', 'env_cognition', 'orientation', 'librarian', 'sync_plot', 'plot_epistemic', 'character_semantic_eval'],
      },
      lean_a4_ablated: {
        topology: 'D-07 ablated lean orchestrator',
        round_options: LEAN_A4_ROUND_OPTIONS,
      },
    },
    ayame_a2_readiness: readiness,
    runs: [readiness, ...runs],
    scored_runs: scoredRuns,
    failures,
    arm_accounting: {
      a2_prototype: aggregateArm(scoredRuns, 'a2_prototype'),
      lean_a4_ablated: aggregateArm(scoredRuns, 'lean_a4_ablated'),
    },
    human_blind_eval: {
      ...blind,
      status: 'prepared_for_governance_blind_scoring',
      decode_authorized: false,
      answer_key_opened: false,
    },
    stop_condition_assessment: {
      triggered: failures.some((f) => f.error) || scoredRuns.length < 4,
      notes: failures.length ? failures : 'Blind packet prepared; awaiting Governance scoring.',
    },
    verdict_status: 'not_rendered_pending_governance_blind_lock',
  };
  const reportPath = path.join(evidenceRoot, 'issue201-g3b-f1-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ reportPath, blind_packet: blind.packetPath, scored: scoredRuns.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
