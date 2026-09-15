#!/usr/bin/env node
/**
 * Issue #201 G3-C F2 — Arkham complex-turn A2 vs lean-A4.
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
  LEAN_A4_ROUND_OPTIONS,
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  ingressPvrObservations,
  createSpatialClaimsResolver,
  runSampleERegression,
  buildBlindPacket,
  a2F2ProhibitedProof,
} from './lib/issue201-g3-c-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const D07_EXPERIMENTAL_SHA = '921b127';
const G3B_DECODE_SHA = 'aee6f98';

const SCENARIO = G3_SCENARIOS.arkham_stress;
const SCENARIO_BRIEFING = {
  setting: 'Arkham Asylum cafeteria. Harley Quinn and Poison Ivy at a table; Magpie (player) at another table. Guards on the margin; low privacy; institutional tension.',
  player_character: 'Magpie',
  judge: 'The presentation should reflect NPC response(s) visible to the player after this murmur, in mess-hall context.',
};

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function runComparabilityGate(head) {
  const diff = execFileSync(
    'git',
    ['diff', '--name-only', D07_EXPERIMENTAL_SHA, 'HEAD', '--',
      'data/scene_templates/arkham_asylum_mess_hall_arena.json',
      'v2/rp_runtime/scripts/lib/issue201-g3-scenarios.mjs',
      'v2/rp_runtime/src/plugins/hg-phase-executors/',
      'v2/domain/modules/scenario_spatial_validator.py'],
    { cwd: REPO_ROOT, encoding: 'utf8' },
  ).trim().split('\n').filter(Boolean);
  const arkhamSpatialFixtureChanged = diff.some((f) => f.includes('arkham_asylum'));
  return {
    head_sha: head,
    d07_experimental_sha: D07_EXPERIMENTAL_SHA,
    g3b_decode_sha: G3B_DECODE_SHA,
    changed_paths_since_d07: diff,
    arkham_spatial_fixture_changed: arkhamSpatialFixtureChanged,
    decision: 'rerun_lean_a4_at_current_sha_for_paired_f2_comparison',
    d07_arkham_evidence_reuse: false,
    rationale: 'Paired F2 at current SHA; Arkham spatial fixture present for Sample-E class validation.',
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

async function runA2Case({ caseId, repIndex, evidenceRoot, outputsDir }) {
  const client = makeClient(evidenceRoot);
  await client.start();
  try {
    const created = await createScenarioSession(client, SCENARIO);
    const operationId = `issue201-${caseId}-${crypto.randomUUID()}`;
    client._beginRoundOperation(operationId, 'user_turn');
    const started = Date.now();
    const { playerDecomposition } = await runPlayerPvrAndRecord(client, SCENARIO.playerPost);
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const runtime = client.supervisor.runtime;
    const sceneSessionId = SessionId(`hg-g3c-a2-${crypto.randomUUID()}`);
    const sceneAgent = runtime.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );
    const resolveSpatial = createSpatialClaimsResolver(evidenceRoot, created.hg_session_id);
    const roundResult = await runA2BeatRound({
      phaseExecutors: runtime.phaseExecutors,
      api,
      trace: runtime.traceEmitter,
      sceneAgent,
      sceneSessionId,
      hgSessionId: created.hg_session_id,
      hgSceneId: created.hg_session_id,
      options: {
        scenarioKey: SCENARIO.scenario_key,
        roleAssignments: SCENARIO.roleAssignments,
        roleProfiles: inferenceOpts.roleProfiles,
        liveMaxAttempts: inferenceOpts.liveMaxAttempts,
        uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
        characterSemanticEvaluationEnabled: false,
        skipPostCommitPlot: true,
        requireStructuredSpatialClaims: true,
        resolveSpatialClaimsFromEvidence: resolveSpatial,
        captureActorContextPackages: true,
      },
    });
    const eligStep = roundResult.audit_steps?.find((s) => s.step === 'actor_eligibility');
    const eligibleActors = eligStep?.snapshot?.eligible_actors ?? [];
    const isolationAudit = roundResult.actor_context_audit?.isolation ?? { pass: true, leak_count: 0, leaks: [] };
    if (roundResult.actor_context_audit) {
      fs.writeFileSync(
        path.join(outputsDir, `${caseId}-actor-context-packages.json`),
        `${JSON.stringify(roundResult.actor_context_audit, null, 2)}\n`,
      );
    }
    if (!roundResult.spatial_claims && roundResult.hg_round_id) {
      const claims = await resolveSpatial({ hgRoundId: roundResult.hg_round_id });
      if (claims) {
        roundResult.spatial_claims = claims;
        roundResult.spatial_validation = await api.validatePresentationSpatialClaims({
          hg_scene_id: created.hg_session_id,
          spatial_claims: claims,
        });
        roundResult.structured_spatial_surface_present = true;
      }
    }
    const operationWallMs = Date.now() - started;
    const presentation = roundResult.presentation_text ?? '';
    fs.writeFileSync(path.join(outputsDir, `${caseId}-presentation.txt`), presentation, 'utf8');
    if (roundResult.spatial_claims) {
      fs.writeFileSync(
        path.join(outputsDir, `${caseId}-spatial-claims.json`),
        `${JSON.stringify(roundResult.spatial_claims, null, 2)}\n`,
      );
    }
    const allAttempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
    const inference = summarizeAttempts(allAttempts);
    const roundInference = summarizeAttempts(roundAttempts);
    const prohibitedProof = a2F2ProhibitedProof(roundInference);
    const ingressPvr = ingressPvrObservations(allAttempts, playerDecomposition);
    const spatialOk = roundResult.structured_spatial_surface_present === true
      && roundResult.spatial_validation?.accepted !== false;
    const objectiveIssues = [];
    if (!roundResult.committed) objectiveIssues.push({ type: 'not_committed' });
    if (!presentation.trim()) objectiveIssues.push({ type: 'empty_presentation' });
    if (!isolationAudit.pass) objectiveIssues.push({ type: 'private_knowledge_leak', detail: isolationAudit.leaks });
    if (!spatialOk) objectiveIssues.push({ type: 'spatial_validation_failed' });
    if (!prohibitedProof.pass) objectiveIssues.push({ type: 'prohibited_cognition', detail: prohibitedProof.violations });
    const blocking = objectiveIssues.filter((i) => [
      'not_committed', 'empty_presentation', 'private_knowledge_leak', 'spatial_validation_failed', 'prohibited_cognition',
    ].includes(i.type));
    const result = {
      case_id: caseId,
      architecture_arm: 'a2_prototype',
      scenario_id: SCENARIO.id,
      rep_index: repIndex,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id,
      domain_commit_id: roundResult.domain_commit_id,
      operation_wall_ms: operationWallMs,
      presentation_text: presentation,
      eligible_actors: eligibleActors,
      director_llm_invoked: roundResult.topology_proof?.director_llm_invoked ?? false,
      character_cognition_count: roundInference.character_move_count,
      actor_context_isolation: isolationAudit,
      spatial_claims: roundResult.spatial_claims,
      spatial_validation: roundResult.spatial_validation,
      structured_spatial_surface_present: roundResult.structured_spatial_surface_present,
      objective: {
        verdict: blocking.length > 0 ? 'blocking_failure' : objectiveIssues.length > 0 ? 'degraded_non_blocking' : 'clean',
        issues: objectiveIssues,
      },
      inference,
      round_inference: roundInference,
      ingress_pvr: ingressPvr,
      prohibited_cognition_proof: prohibitedProof,
      topology_proof: roundResult.topology_proof,
      decision_value_records: roundResult.decision_value?.records ?? [],
      efficiency: roundResult.efficiency,
    };
    fs.writeFileSync(path.join(outputsDir, `${caseId}-meta.json`), `${JSON.stringify(result, null, 2)}\n`);
    return result;
  } finally {
    await client.stop();
  }
}

async function runLeanA4Case({ caseId, repIndex, evidenceRoot, outputsDir }) {
  const client = makeClient(evidenceRoot);
  await client.start();
  try {
    const created = await createScenarioSession(client, SCENARIO);
    const operationId = `issue201-${caseId}-${crypto.randomUUID()}`;
    client._beginRoundOperation(operationId, 'user_turn');
    const started = Date.now();
    const { playerDecomposition } = await runPlayerPvrAndRecord(client, SCENARIO.playerPost);
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
    fs.writeFileSync(path.join(outputsDir, `${caseId}-presentation.txt`), presentation, 'utf8');
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
    const allAttempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
    const inference = summarizeAttempts(allAttempts);
    const roundInference = summarizeAttempts(roundAttempts);
    const hookIsolation = {
      narrator_semantic_qa_observed: inference.narrator_semantic_qa_count,
      director_semantic_qa_observed: inference.director_semantic_qa_count,
      storyteller_post_commit_observed: inference.storyteller_post_commit_count,
      isolation_ok: inference.narrator_semantic_qa_count === 0
        && inference.director_semantic_qa_count === 0
        && inference.storyteller_post_commit_count === 0,
    };
    const issues = [];
    if (!roundResult?.committed) issues.push({ type: 'not_committed' });
    if (!presentation.trim()) issues.push({ type: 'empty_presentation' });
    if (!hookIsolation.isolation_ok) issues.push({ type: 'hook_isolation_failed' });
    const result = {
      case_id: caseId,
      architecture_arm: 'lean_a4_ablated',
      scenario_id: SCENARIO.id,
      rep_index: repIndex,
      round_options: LEAN_A4_ROUND_OPTIONS,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id,
      operation_wall_ms: operationWallMs,
      presentation_text: presentation,
      objective: {
        verdict: issues.some((i) => ['not_committed', 'empty_presentation'].includes(i.type)) ? 'blocking_failure' : issues.length ? 'degraded_non_blocking' : 'clean',
        issues,
        pvr_validation_status: userEntry?.metadata?.perceptual_visibility?.validation_status ?? null,
      },
      inference,
      round_inference: roundInference,
      hook_isolation: hookIsolation,
      ingress_pvr: ingressPvrObservations(allAttempts, playerDecomposition),
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
    round_sync_llm_total: arm === 'a2_prototype'
      ? armRuns.reduce((s, r) => s + (r.round_inference?.synchronous_llm_count ?? 0), 0)
      : armRuns.reduce((s, r) => s + (r.round_inference?.synchronous_llm_count ?? 0), 0),
    session_inference_records: armRuns.reduce((s, r) => s + r.inference.inference_count, 0),
    wall_ms_total: armRuns.reduce((s, r) => s + r.operation_wall_ms, 0),
    input_tokens_total: armRuns.reduce((s, r) => s + r.inference.input_tokens_total, 0),
    output_tokens_total: armRuns.reduce((s, r) => s + r.inference.output_tokens_total, 0),
    reasoning_tokens_total: armRuns.reduce((s, r) => s + r.inference.reasoning_tokens_total, 0),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const head = gitSha();
  const comparability = runComparabilityGate(head);
  const sampleE = runSampleERegression(REPO_ROOT);
  if (!sampleE.pass) throw new Error(`Sample-E regression STOP: ${sampleE.output}`);
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-g3c-f2-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceRoot, 'comparability_gate.json'), `${JSON.stringify(comparability, null, 2)}\n`);
  fs.writeFileSync(path.join(evidenceRoot, 'sample_e_regression.json'), `${JSON.stringify(sampleE, null, 2)}\n`);

  const plan = [];
  for (let rep = 1; rep <= 2; rep += 1) {
    plan.push({ caseId: `G3C-F2-a2-arkham-r${rep}`, arm: 'a2', rep });
    plan.push({ caseId: `G3C-F2-a4-arkham-r${rep}`, arm: 'lean_a4', rep });
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
        spatial: result.structured_spatial_surface_present,
        inferences: result.inference.inference_count,
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
    purpose: 'Issue #201 G3-C F2 — Arkham complex-turn comparison (4 presentations)',
    scenarioBriefing: SCENARIO_BRIEFING,
    playerStimulus: SCENARIO.playerPost,
  });

  const report = {
    schema: 'issue201_g3c_f2_pre_decode_v1',
    generated_at: new Date().toISOString(),
    execution_sha: head,
    g3b_decode_sha: G3B_DECODE_SHA,
    f1_classification_carried_forward: 'strong_a2_support',
    comparability_gate: comparability,
    sample_e_regression: sampleE,
    scenario: SCENARIO,
    arms: {
      a2_prototype: { topology: 'obligation-driven A2 complex path with mandatory spatial surface' },
      lean_a4_ablated: { round_options: LEAN_A4_ROUND_OPTIONS },
    },
    runs,
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
      notes: failures.length ? failures : 'Blind packet prepared.',
    },
    verdict_status: 'not_rendered_pending_governance_blind_lock',
  };
  const reportPath = path.join(evidenceRoot, 'issue201-g3c-f2-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ reportPath, blind_packet: blind.packetPath, scored: scoredRuns.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
