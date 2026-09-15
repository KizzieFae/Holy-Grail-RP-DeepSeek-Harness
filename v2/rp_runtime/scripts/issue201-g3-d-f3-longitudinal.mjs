#!/usr/bin/env node
/**
 * Issue #201 G3-D F3 — Longitudinal A2 Plot/Scribe ON vs OFF.
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
import { defaultSessionsDir } from '../src/lib/runtime-config.mjs';
import { G3_SCENARIOS } from './lib/issue201-g3-scenarios.mjs';
import {
  buildPolicyManifest,
  loadPolicy,
  selectPlayerStimulus,
} from './lib/issue201-g3d-player-policy.mjs';
import {
  loadAttempts,
  filterAttemptsForRound,
  summarizeAttempts,
  createSpatialClaimsResolver,
  extractContinuityForensics,
  extractPlotForensics,
  storytellerAbsenceProof,
  plotOffAbsenceProof,
  a2ProhibitedSupportProof,
  buildCrossTurnConsumptionEvidence,
  classifyPlotDecisionValue,
  buildBlindSequencePacket,
} from './lib/issue201-g3d-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const G3C_DECODE_SHA = '08b46fa';

const SCENARIO_CONFIG = {
  arkham_stress: {
    ...G3_SCENARIOS.arkham_stress,
    policyId: 'arkham_g3d_policy_v1',
    sequencesPerArm: 2,
    requireSpatial: true,
  },
  ayame_controlled: {
    ...G3_SCENARIOS.ayame_controlled,
    policyId: 'ayame_d10_policy_v1',
    sequencesPerArm: 2,
    requireSpatial: false,
  },
};

const ARMS = [
  {
    arm_id: 'a2_plot_on',
    label: 'A2 Primary RP + post-commit Plot/Scribe',
    plot_on: true,
  },
  {
    arm_id: 'a2_plot_off',
    label: 'A2 Primary RP without Plot/Scribe',
    plot_on: false,
  },
];

const PLOT_INIT_CONTRACT = {
  initialization_trigger: 'first_post_commit_plot_lifecycle_after_turn_1_commit',
  initialization_timing: 'post_player_visible_presentation_outside_critical_path',
  initial_inputs: ['committed_events', 'continuity_state', 'scenario_authority'],
  plot_off_substrate: 'same_authoritative_continuity_and_scenario_paths_without_plot_overlay_updates',
  synchronous_plot: false,
  storyteller: 'absent',
};

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
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

function summarizePlotInference(attempts) {
  const plotKinds = attempts.filter((a) => String(a.inference_kind).startsWith('plot_cognition'));
  return {
    plot_inference_count: plotKinds.length,
    plot_kinds: plotKinds.map((a) => a.inference_kind),
  };
}

async function runA2SequenceTurn({
  client, arm, scenario, turnIndex, playerStimulus, sequenceId, evidenceRoot,
  sessionsDir, plotScopeIdRef, resolveSpatial,
}) {
  const continuityBefore = extractContinuityForensics(client.activeSessionId, sessionsDir);
  const plotBefore = extractPlotForensics(
    continuityBefore.plot_cognition_scope_id ?? plotScopeIdRef.value,
    sessionsDir,
  );
  const operationId = `issue201-${sequenceId}-t${turnIndex}-${crypto.randomUUID()}`;
  client._beginRoundOperation(operationId, 'user_turn');
  const started = Date.now();
  const { playerDecomposition } = await runPlayerPvrAndRecord(client, playerStimulus);
  const api = client._domainApi();
  const runtime = client.supervisor.runtime;
  const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
    inferenceMode: client.options.inferenceMode,
  });
  const sceneSessionId = SessionId(`hg-g3d-a2-${crypto.randomUUID()}`);
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
    hgSessionId: client.activeSessionId,
    hgSceneId: client.activeSessionId,
    options: {
      scenarioKey: scenario.scenario_key,
      roleAssignments: scenario.roleAssignments,
      roleProfiles: inferenceOpts.roleProfiles,
      liveMaxAttempts: inferenceOpts.liveMaxAttempts,
      uniformProjectionEligible: playerDecomposition?.uniform_projection_eligible !== false,
      characterSemanticEvaluationEnabled: false,
      skipPostCommitPlot: !arm.plot_on,
      runPostCommitPlot: arm.plot_on,
      requireStructuredSpatialClaims: scenario.requireSpatial === true,
      resolveSpatialClaimsFromEvidence: scenario.requireSpatial ? resolveSpatial : null,
      captureActorContextPackages: true,
    },
  });
  const operationWallMs = Date.now() - started;
  const presentation = roundResult.presentation_text ?? '';
  const allAttempts = loadAttempts(evidenceRoot, client.activeSessionId);
  const roundAttempts = filterAttemptsForRound(allAttempts, roundResult.hg_round_id);
  const sessionInference = summarizeAttempts(allAttempts);
  const roundInference = summarizeAttempts(roundAttempts);
  const continuityAfter = extractContinuityForensics(client.activeSessionId, sessionsDir);
  if (continuityAfter.plot_cognition_scope_id) plotScopeIdRef.value = continuityAfter.plot_cognition_scope_id;
  const plotAfter = extractPlotForensics(continuityAfter.plot_cognition_scope_id, sessionsDir);
  const eligStep = roundResult.audit_steps?.find((s) => s.step === 'actor_eligibility');
  const eligibleActors = eligStep?.snapshot?.eligible_actors ?? [];
  const directorInvoked = roundResult.topology_proof?.director_llm_invoked === true;
  const isolation = roundResult.actor_context_audit?.isolation ?? { pass: true, leak_count: 0 };
  const storytellerProof = storytellerAbsenceProof(roundAttempts);
  const plotOffProof = arm.plot_on ? { pass: true, count: 0 } : plotOffAbsenceProof(roundAttempts);
  const prohibitedProof = a2ProhibitedSupportProof(roundAttempts, { allowPlot: arm.plot_on });
  const plotInference = summarizePlotInference(roundAttempts);
  const issues = [];
  if (!roundResult.committed) issues.push({ type: 'not_committed' });
  if (!presentation.trim()) issues.push({ type: 'empty_presentation' });
  if (!isolation.pass) issues.push({ type: 'private_knowledge_leak' });
  if (!storytellerProof.pass) issues.push({ type: 'storyteller_present' });
  if (!plotOffProof.pass) issues.push({ type: 'plot_present_in_off_arm' });
  if (!prohibitedProof.pass) issues.push({ type: 'prohibited_cognition' });
  if (scenario.requireSpatial && !roundResult.structured_spatial_surface_present) {
    issues.push({ type: 'missing_spatial_surface' });
  }
  return {
    turn_index: turnIndex,
    exact_player_stimulus: playerStimulus,
    client_operation_id: operationId,
    hg_round_id: roundResult.hg_round_id,
    domain_commit_id: roundResult.domain_commit_id,
    operation_wall_ms: operationWallMs,
    presentation_text: presentation,
    eligible_actors: eligibleActors,
    director_llm_invoked: directorInvoked,
    selected_character_id: roundResult.selected_character_id,
    character_cognition_count: roundInference.character_move_count,
    objective: {
      committed: roundResult.committed === true && issues.length === 0,
      issues,
    },
    timing: {
      critical_path_wall_ms: roundResult.efficiency?.critical_path_wall_ms ?? null,
      plot_post_commit_wall_ms: roundResult.efficiency?.plot_post_commit_wall_ms ?? 0,
      total_operation_wall_ms: operationWallMs,
    },
    inference: {
      ...roundInference,
      plot_inference_count: plotInference.plot_inference_count,
    },
    session_inference_snapshot: sessionInference,
    plot_post_commit: roundResult.plot_post_commit ?? { skipped: true },
    plot_forensics: {
      before: plotBefore,
      after: plotAfter,
      inference: plotInference,
    },
    actor_context_isolation: isolation,
    spatial: scenario.requireSpatial ? {
      claims: roundResult.spatial_claims,
      validation: roundResult.spatial_validation,
      surface_present: roundResult.structured_spatial_surface_present,
    } : null,
    proofs: {
      storyteller_absence: storytellerProof,
      plot_off: plotOffProof,
      prohibited_support: prohibitedProof,
    },
  };
}

function mergeSequenceInference(turns) {
  const totals = {
    primary_rp_sync_llm: 0,
    plot_inference_count: 0,
    director_decision_count: 0,
    character_move_count: 0,
    narrator_presentation_count: 0,
    wall_ms_total: 0,
    critical_path_wall_ms_total: 0,
    plot_post_commit_wall_ms_total: 0,
    input_tokens_total: 0,
    output_tokens_total: 0,
    reasoning_tokens_total: 0,
  };
  for (const t of turns) {
    totals.primary_rp_sync_llm += t.inference?.synchronous_llm_count ?? 0;
    totals.plot_inference_count += t.inference?.plot_inference_count ?? 0;
    totals.director_decision_count += t.inference?.director_turn_count ?? 0;
    totals.character_move_count += t.inference?.character_move_count ?? 0;
    totals.narrator_presentation_count += t.inference?.narrator_presentation_count ?? 0;
    totals.wall_ms_total += t.operation_wall_ms ?? 0;
    totals.critical_path_wall_ms_total += t.timing?.critical_path_wall_ms ?? 0;
    totals.plot_post_commit_wall_ms_total += t.timing?.plot_post_commit_wall_ms ?? 0;
    totals.input_tokens_total += t.inference?.input_tokens_total ?? 0;
    totals.output_tokens_total += t.inference?.output_tokens_total ?? 0;
    totals.reasoning_tokens_total += t.inference?.reasoning_tokens_total ?? 0;
  }
  totals.total_llm_count = totals.primary_rp_sync_llm + totals.plot_inference_count;
  return totals;
}

async function runOneSequence({
  arm, scenarioKey, repIndex, policyBundle, evidenceRoot, outputsDir, sequenceAttempt, sessionsDir,
}) {
  const scenario = SCENARIO_CONFIG[scenarioKey];
  const { policy, policy_hash } = policyBundle;
  const sequenceId = `G3D-F3-${arm.arm_id}-${scenarioKey}-seq${repIndex}-a${sequenceAttempt}`;
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
  await client.start();
  const turns = [];
  const branchLogs = [];
  let failed = false;
  let error = null;
  let hgSessionId = null;
  const plotScopeIdRef = { value: null };
  let resolveSpatial = null;
  try {
    const created = await createScenarioSession(client, scenario);
    hgSessionId = created.hg_session_id ?? client.activeSessionId;
    if (scenario.requireSpatial) {
      resolveSpatial = createSpatialClaimsResolver(evidenceRoot, hgSessionId);
    }
    const priorForPolicy = [];
    for (let turnIndex = 1; turnIndex <= policy.turn_count; turnIndex += 1) {
      const selection = selectPlayerStimulus(policy, turnIndex, priorForPolicy);
      selection.policy_hash = policy_hash;
      branchLogs.push({
        turn: turnIndex,
        policy_hash,
        predicate_hits: selection.predicate_hits,
        winning_predicate: selection.winning_predicate,
        branch_id: selection.branch_id,
        exact_player_stimulus: selection.exact_player_stimulus,
      });
      const turnRow = await runA2SequenceTurn({
        client,
        arm,
        scenario,
        turnIndex,
        playerStimulus: selection.exact_player_stimulus,
        sequenceId,
        evidenceRoot,
        sessionsDir,
        plotScopeIdRef,
        resolveSpatial,
      });
      turnRow.branch_log = branchLogs[branchLogs.length - 1];
      turns.push(turnRow);
      priorForPolicy.push({
        turn_index: turnIndex,
        presentation_text: turnRow.presentation_text,
        winning_predicate: selection.winning_predicate,
      });
      if (!turnRow.objective.committed) {
        failed = true;
        error = `turn ${turnIndex} objective failed: ${JSON.stringify(turnRow.objective.issues)}`;
        break;
      }
    }
  } catch (err) {
    failed = true;
    error = String(err?.message ?? err);
  } finally {
    await client.stop();
  }
  const allCommitted = turns.length === policy.turn_count
    && turns.every((t) => t.objective.committed);
  const crossTurn = buildCrossTurnConsumptionEvidence(turns);
  const plotDecisionValues = turns.flatMap((t) => classifyPlotDecisionValue(t));
  const sequence = {
    sequence_id: sequenceId,
    arm_id: arm.arm_id,
    arm_label: arm.label,
    plot_on: arm.plot_on,
    scenario_key: scenarioKey,
    scenario_id: scenario.id,
    repetition_index: repIndex,
    sequence_attempt: sequenceAttempt,
    policy_id: policy.policy_id,
    policy_hash,
    hg_session_id: hgSessionId,
    turn_count_expected: policy.turn_count,
    turn_count_completed: turns.length,
    all_committed: allCommitted,
    failed,
    error,
    branch_trajectory: branchLogs,
    turns,
    cross_turn_plot_consumption: crossTurn,
    plot_decision_value_records: plotDecisionValues,
    sequence_inference: mergeSequenceInference(turns),
    plot_init_contract: PLOT_INIT_CONTRACT,
  };
  fs.writeFileSync(
    path.join(outputsDir, `${sequenceId}-sequence.json`),
    `${JSON.stringify(sequence, null, 2)}\n`,
  );
  return sequence;
}

async function runSequenceWithRetry(params) {
  const maxAttempts = 2;
  let last = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const seq = await runOneSequence({ ...params, sequenceAttempt: attempt });
    last = seq;
    if (seq.all_committed && !seq.failed) return seq;
    console.error(JSON.stringify({ retry: attempt, sequence_id: seq.sequence_id, error: seq.error }));
  }
  return last;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { only: null, evidenceRoot: null, skipExisting: true };
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--only' && args[i + 1]) out.only = args[++i];
    if (args[i] === '--evidence-root' && args[i + 1]) out.evidenceRoot = args[++i];
    if (args[i] === '--no-skip-existing') out.skipExisting = false;
  }
  return out;
}

async function main() {
  const args = parseArgs();
  const head = gitSha();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = args.evidenceRoot
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-g3d-f3-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  const sessionsDir = defaultSessionsDir();
  const policyManifest = buildPolicyManifest();
  const sequences = [];
  const failures = [];
  for (const arm of ARMS) {
    for (const [scenarioKey, cfg] of Object.entries(SCENARIO_CONFIG)) {
      const policyBundle = loadPolicy(cfg.policyId);
      for (let rep = 1; rep <= cfg.sequencesPerArm; rep += 1) {
        const seqKey = `${arm.arm_id}-${scenarioKey}-seq${rep}`;
        if (args.only && !seqKey.includes(args.only) && args.only !== arm.arm_id && args.only !== scenarioKey) continue;
        const outFile = path.join(outputsDir, `G3D-F3-${arm.arm_id}-${scenarioKey}-seq${rep}-a1-sequence.json`);
        if (args.skipExisting && fs.existsSync(outFile)) {
          sequences.push(JSON.parse(fs.readFileSync(outFile, 'utf8')));
          continue;
        }
        console.error(JSON.stringify({ status: 'starting', arm: arm.arm_id, scenarioKey, rep }));
        const seq = await runSequenceWithRetry({
          arm,
          scenarioKey,
          repIndex: rep,
          policyBundle,
          evidenceRoot,
          outputsDir,
          sessionsDir,
        });
        sequences.push(seq);
        if (!seq.all_committed || seq.failed) {
          failures.push({ sequence_id: seq.sequence_id, error: seq.error });
        }
      }
    }
  }
  const blind = buildBlindSequencePacket(sequences, outputsDir);
  const armAccounting = {};
  for (const arm of ARMS) {
    const armSeqs = sequences.filter((s) => s.arm_id === arm.arm_id && s.all_committed);
    armAccounting[arm.arm_id] = {
      sequences: armSeqs.length,
      primary_rp_sync_llm_total: armSeqs.reduce((s, x) => s + (x.sequence_inference?.primary_rp_sync_llm ?? 0), 0),
      plot_inference_total: armSeqs.reduce((s, x) => s + (x.sequence_inference?.plot_inference_count ?? 0), 0),
      critical_path_wall_ms_total: armSeqs.reduce((s, x) => s + (x.sequence_inference?.critical_path_wall_ms_total ?? 0), 0),
      plot_post_commit_wall_ms_total: armSeqs.reduce((s, x) => s + (x.sequence_inference?.plot_post_commit_wall_ms_total ?? 0), 0),
      operation_wall_ms_total: armSeqs.reduce((s, x) => s + (x.sequence_inference?.wall_ms_total ?? 0), 0),
    };
  }
  const report = {
    schema: 'issue201_g3d_f3_pre_decode_v1',
    generated_at: new Date().toISOString(),
    execution_sha: head,
    g3c_decode_sha: G3C_DECODE_SHA,
    plot_init_contract: PLOT_INIT_CONTRACT,
    carried_forward: {
      f1: 'strong_a2_support',
      f2: 'qualified_a2_support',
      sample_d_spatial_debt: 'bounded_narrator_deictic_claim_completeness',
      director_responsibility: 'retained_on_genuine_multi_actor_ambiguity',
    },
    arms: ARMS,
    policy_manifest: policyManifest,
    sequences,
    failures,
    arm_accounting: armAccounting,
    cross_turn_summary: sequences.map((s) => ({
      sequence_id: s.sequence_id,
      arm_id: s.arm_id,
      plot_on: s.plot_on,
      links: s.cross_turn_plot_consumption,
    })),
    human_blind_eval: blind,
    stop_condition_assessment: {
      triggered: failures.some((f) => f.error?.includes('private_knowledge'))
        || sequences.some((s) => s.turns?.some((t) => t.proofs?.storyteller_absence?.pass === false)),
      notes: failures.length ? 'see failures array' : 'blind packet prepared',
    },
    verdict_status: 'not_rendered_pending_governance_blind_lock',
  };
  const reportPath = path.join(evidenceRoot, 'issue201-g3d-f3-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    evidence_root: evidenceRoot,
    report_path: reportPath,
    sequences: sequences.length,
    all_committed: sequences.filter((s) => s.all_committed).length,
    blind_packet: blind.packetPath,
  }));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
