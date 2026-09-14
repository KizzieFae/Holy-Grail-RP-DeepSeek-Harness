/**
 * Issue #201 Package D — D-01-L longitudinal synchronous-preamble Storyteller test.
 * Control: ST preamble ON / Plot ON. Ablated: skipStorytellerCognition / Plot ON.
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
import {
  buildPolicyManifest,
  loadPolicy,
  selectPlayerStimulus,
} from './lib/issue201-d01l-player-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CONTROL_SHA = 'c751ea666f0cae6524698005aa5859721c2e9738';

const SCENARIOS = {
  arkham_stress: {
    id: 'arkham_asylum_mess_hall_arena',
    characters: ['harley_quinn', 'poison_ivy', 'magpie'],
    roleAssignments: {
      harley_quinn: 'instigator',
      poison_ivy: 'instigator_accomplice',
      magpie: 'new_arrival',
    },
    playerCharacterFileId: 'magpie',
    userName: 'Magpie',
    openerPreference: 'mess_hall_magpie',
  },
  ayame_controlled: {
    id: 'ayame_household_entry_evaluation',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
  },
};

const ARMS = [
  { arm_id: 'control', label: 'Storyteller preamble ON', round_options: {} },
  {
    arm_id: 'ablated',
    label: 'Storyteller preamble OFF (skipStorytellerCognition)',
    round_options: { skipStorytellerCognition: true },
  },
];

const PREAMBLE_STORYTELLER_KINDS = new Set([
  'storyteller_orientation',
  'storyteller_assessment',
]);
const POST_COMMIT_STORYTELLER_KINDS = new Set([
  'storyteller_post_commit_issue_pressure',
  'storyteller_post_commit_issue_pressure_contract_correction',
]);

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function kindCount(kinds, name) {
  return kinds.find((k) => k.inference_kind === name)?.count ?? 0;
}

function summarizeInferenceKinds(kinds) {
  const list = kinds ?? [];
  const storytellerKinds = list.filter((k) => String(k.inference_kind).startsWith('storyteller'));
  const plotKinds = list.filter((k) => String(k.inference_kind).startsWith('plot_cognition'));
  let preambleSt = 0;
  let postCommitSt = 0;
  for (const k of storytellerKinds) {
    if (PREAMBLE_STORYTELLER_KINDS.has(k.inference_kind)) preambleSt += k.count;
    if (POST_COMMIT_STORYTELLER_KINDS.has(k.inference_kind)) postCommitSt += k.count;
  }
  return {
    inference_count: list.reduce((s, k) => s + k.count, 0),
    librarian_mediation_count: kindCount(list, 'librarian_mediation'),
    character_orientation_count: kindCount(list, 'character_orientation'),
    director_semantic_qa_count: kindCount(list, 'director_semantic_qa'),
    director_decision_count: kindCount(list, 'director_decision'),
    narrator_presentation_count: kindCount(list, 'narrator_presentation'),
    storyteller_inference_count: storytellerKinds.reduce((s, k) => s + k.count, 0),
    storyteller_preamble_inference_count: preambleSt,
    storyteller_post_commit_inference_count: postCommitSt,
    plot_inference_count: plotKinds.reduce((s, k) => s + k.count, 0),
    kinds: list,
  };
}

function loadAttemptsForOperation(evidenceRoot, sessionId, operationId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  const rows = [];
  for (const attemptId of index.attempt_ids ?? []) {
    const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
    const attempt = JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
    const op = attempt.correlation?.operation_id
      ?? attempt.associations?.operation_id
      ?? attempt.decision?.operation_id
      ?? null;
    if (String(op) !== String(operationId)) continue;
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    rows.push({
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: attempt.correlation?.inference_kind ?? null,
      attempt_index: attempt.correlation?.attempt_index ?? 0,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
    });
  }
  return rows;
}

function mergeTurnInference(turns) {
  const kindMap = new Map();
  for (const t of turns) {
    for (const k of t.inference.kinds ?? []) {
      const prev = kindMap.get(k.inference_kind) ?? { count: 0, wall_ms_total: 0 };
      kindMap.set(k.inference_kind, {
        inference_kind: k.inference_kind,
        count: prev.count + k.count,
        wall_ms_total: prev.wall_ms_total + (k.wall_ms_total ?? 0),
      });
    }
  }
  const merged = summarizeInferenceKinds([...kindMap.values()]);
  return {
    ...merged,
    wall_ms_total: turns.reduce((s, row) => s + (row.inference.wall_ms_total ?? 0), 0),
    reasoning_tokens_total: turns.reduce((s, row) => s + (row.inference.reasoning_tokens_total ?? 0), 0),
    retry_count: turns.reduce((s, row) => s + (row.inference.retry_count ?? 0), 0),
  };
}

function summarizeAttempts(attempts) {
  const byKind = {};
  for (const row of attempts) {
    const key = row.inference_kind ?? 'unknown';
    if (!byKind[key]) byKind[key] = [];
    byKind[key].push(row);
  }
  const kinds = Object.entries(byKind)
    .filter(([k]) => k !== 'unknown' && k !== null)
    .map(([kind, rows]) => ({
      inference_kind: kind,
      count: rows.length,
      wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    }));
  return {
    ...summarizeInferenceKinds(kinds),
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
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
  const lastTurn = roundResult.character_turns?.at(-1);
  return lastTurn?.presentation_text ?? '';
}

function objectiveChecks({ history, userEntry, roundResult, presentation }) {
  const issues = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  if (userPvr.validation_status && userPvr.validation_status !== 'valid') {
    issues.push({ type: 'pvr_validation', detail: userPvr.validation_status });
  }
  if (!roundResult?.committed) {
    issues.push({ type: 'round_not_committed', detail: roundResult?.completion_reason ?? null });
  }
  return {
    issue_count: issues.length,
    issues,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    pvr_validation_status: userPvr.validation_status ?? null,
    presentation_length: String(presentation ?? '').length,
  };
}

async function runSequenceTurn({
  client, api, inferenceOpts, roundOptions, turnIndex, playerStimulus,
  sequenceId, evidenceRoot, policyHash,
}) {
  const operationId = `issue201-${sequenceId}-t${turnIndex}-${crypto.randomUUID()}`;
  client._beginRoundOperation(operationId, 'user_turn');
  const started = Date.now();
  await runPlayerPvrAndRecord(client, playerStimulus);
  const roundResult = await client.orchestrator.runRound({
    session: { mode: 'open', hg_session_id: client.activeSessionId },
    roleProfiles: inferenceOpts.roleProfiles,
    liveMaxAttempts: inferenceOpts.liveMaxAttempts,
    clientOperationId: operationId,
    spanTracker: client.activeSpanTracker,
    ...roundOptions,
  });
  await client._recordRoundPresentations(api, roundResult);
  await client._refreshTranscript();
  const operation_wall_ms = Date.now() - started;
  const presentation = presentationFromRound(roundResult);
  const history = await api.getSessionHistory(client.activeSessionId);
  const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
  const attempts = loadAttemptsForOperation(evidenceRoot, client.activeSessionId, operationId);
  const inference = summarizeAttempts(attempts);
  return {
    turn_index: turnIndex,
    policy_hash: policyHash,
    branch_log: null,
    exact_player_stimulus: playerStimulus,
    client_operation_id: operationId,
    hg_round_id: roundResult.hg_round_id ?? null,
    domain_commit_id: roundResult.domain_commit_id ?? null,
    operation_wall_ms,
    presentation_text: presentation,
    objective: objectiveChecks({ history, userEntry, roundResult, presentation }),
    inference,
    storyteller_round_summary: roundResult.storyteller_round_summary ?? null,
    plot_cognition_resume_summary: roundResult.plot_cognition_resume_summary ?? null,
    continuity_turn_index: roundResult.continuity_turn_index ?? null,
  };
}

async function runOneSequence({
  arm, scenarioKey, repIndex, policyBundle, evidenceRoot, outputsDir, sequenceAttempt,
}) {
  const scenario = SCENARIOS[scenarioKey];
  const { policy, policy_hash } = policyBundle;
  const sequenceId = `D01L-${arm.arm_id}-${scenarioKey}-seq${repIndex}-a${sequenceAttempt}`;
  const caseId = sequenceId;
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
  try {
    const created = await createScenarioSession(client, scenario);
    hgSessionId = created.hg_session_id ?? client.activeSessionId;
    const api = client._domainApi();
    const inferenceOpts = buildInferenceOptions(client.runtimeSettings, {
      inferenceMode: client.options.inferenceMode,
    });
    const priorForPolicy = [];
    for (let turnIndex = 1; turnIndex <= policy.turn_count; turnIndex += 1) {
      const selection = selectPlayerStimulus(policy, turnIndex, priorForPolicy);
      selection.policy_hash = policy_hash;
      branchLogs.push({
        turn: turnIndex,
        policy_hash: policy_hash,
        predicate_hits: selection.predicate_hits,
        winning_predicate: selection.winning_predicate,
        branch_id: selection.branch_id,
        exact_player_stimulus: selection.exact_player_stimulus,
      });
      const turnRow = await runSequenceTurn({
        client,
        api,
        inferenceOpts,
        roundOptions: arm.round_options,
        turnIndex,
        playerStimulus: selection.exact_player_stimulus,
        sequenceId: caseId,
        evidenceRoot,
        policyHash: policy_hash,
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
        error = `turn ${turnIndex} not committed: ${turnRow.objective.completion_reason}`;
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
  const sequence = {
    sequence_id: caseId,
    arm_id: arm.arm_id,
    arm_label: arm.label,
    round_options: arm.round_options,
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
    sequence_wall_ms: turns.reduce((s, t) => s + t.operation_wall_ms, 0),
    sequence_inference: mergeTurnInference(turns),
  };
  const outBase = path.join(outputsDir, caseId);
  fs.writeFileSync(`${outBase}-sequence.json`, `${JSON.stringify(sequence, null, 2)}\n`);
  for (const t of turns) {
    fs.writeFileSync(
      path.join(outputsDir, `${caseId}-t${t.turn_index}-presentation.txt`),
      t.presentation_text,
      'utf8',
    );
  }
  return sequence;
}

function buildBlindSequencePacket(sequences, outputsDir) {
  const eligible = sequences.filter((s) => s.all_committed && !s.failed);
  const shuffled = [...eligible];
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  shuffled.forEach((s, i) => {
    s.blind_label = `SEQ-${String.fromCharCode(65 + i)}`;
  });
  const briefingKeys = {
    arkham_asylum_mess_hall_arena: 'arkham_mess_hall_stress',
    ayame_household_entry_evaluation: 'ayame_household_entry',
  };
  const packetPath = path.join(outputsDir, 'issue201-d01l-blind-sequence-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-d01l-blind-sequence-answer-key.json');
  const packet = {
    schema: 'issue201_blind_sequence_packet_v1',
    purpose: 'D-01-L longitudinal Storyteller preamble test — complete sequence bundles',
    causal_question: 'Does synchronous preamble Storyteller cognition add material multi-turn narrative value when Plot and post-commit Storyteller remain available?',
    instructions: 'Score each complete sequence using the 10 sequence-level dimensions (primary). Per-turn 11-dimension rubric is secondary. Do not request arm, session, inference, or latency data until after scoring is locked.',
    sequence_level_dimensions: [
      'thread persistence',
      'escalation coherence',
      'agenda persistence',
      'delayed consequences',
      'scene momentum',
      'cross-turn initiative',
      'reactive-loop avoidance',
      'premature-resolution avoidance',
      'plot-drift control',
      'cross-turn emotional/narrative continuity',
    ],
    sequences: shuffled.map((s) => ({
      blind_label: s.blind_label,
      scenario_briefing_key: briefingKeys[s.scenario_id] ?? s.scenario_id,
      turns: s.turns.map((t) => ({
        turn_index: t.turn_index,
        player_stimulus: t.exact_player_stimulus,
        presentation_text: t.presentation_text,
      })),
    })),
  };
  const answerKey = shuffled.map((s) => ({
    blind_label: s.blind_label,
    sequence_id: s.sequence_id,
    arm_id: s.arm_id,
    scenario_key: s.scenario_key,
    scenario_id: s.scenario_id,
    repetition_index: s.repetition_index,
    policy_id: s.policy_id,
    policy_hash: s.policy_hash,
    branch_trajectory: s.branch_trajectory,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  return { packetPath, keyPath, sequence_count: shuffled.length, excluded: sequences.length - eligible.length };
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

async function runSequenceWithRetry(params) {
  const maxAttempts = 2;
  let last = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const seq = await runOneSequence({ ...params, sequenceAttempt: attempt });
    last = seq;
    if (seq.all_committed && !seq.failed) return seq;
    console.error(JSON.stringify({
      sequence_id: seq.sequence_id,
      attempt,
      failed: true,
      error: seq.error,
    }));
  }
  return last;
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const cli = parseArgs();
  const manifest = buildPolicyManifest();
  const head = gitSha();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = cli.evidenceRoot
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-package-d-d01l-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  fs.writeFileSync(
    path.join(evidenceRoot, 'd01l_policy_manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );

  const policyBundles = {
    arkham_stress: loadPolicy('arkham_d01l_policy_v1'),
    ayame_controlled: loadPolicy('ayame_d01l_policy_v1'),
  };

  const plan = [];
  for (const scenarioKey of ['arkham_stress', 'ayame_controlled']) {
    for (let rep = 1; rep <= 2; rep += 1) {
      for (const arm of ARMS) {
        const sequenceId = `D01L-${arm.arm_id}-${scenarioKey}-seq${rep}`;
        plan.push({ arm, scenarioKey, rep, sequenceId });
      }
    }
  }

  const sequences = [];
  const failures = [];

  for (const item of plan) {
    if (cli.only && !item.sequenceId.includes(cli.only)) continue;
    if (cli.skipExisting) {
      const existingFiles = fs.readdirSync(outputsDir)
        .filter((f) => f.startsWith(`${item.sequenceId}-a`) && f.endsWith('-sequence.json'));
      const committed = existingFiles
        .map((f) => JSON.parse(fs.readFileSync(path.join(outputsDir, f), 'utf8')))
        .find((row) => row.all_committed && !row.failed);
      if (committed) {
        console.log(`Skipping ${item.sequenceId} (existing committed sequence)`);
        sequences.push(committed);
        continue;
      }
    }
    console.log(`Running ${item.sequenceId} (${item.arm.arm_id})...`);
    const seq = await runSequenceWithRetry({
      arm: item.arm,
      scenarioKey: item.scenarioKey,
      repIndex: item.rep,
      policyBundle: policyBundles[item.scenarioKey],
      evidenceRoot,
      outputsDir,
    });
    if (seq.all_committed && !seq.failed) {
      sequences.push(seq);
      console.log(JSON.stringify({
        sequence_id: seq.sequence_id,
        turns: seq.turn_count_completed,
        wall_ms: seq.sequence_wall_ms,
        st_preamble: seq.sequence_inference.storyteller_preamble_inference_count,
        st_post: seq.sequence_inference.storyteller_post_commit_inference_count,
        plot: seq.sequence_inference.plot_inference_count,
      }));
    } else {
      failures.push(seq);
      console.error(JSON.stringify({ sequence_id: seq.sequence_id, failed: true, error: seq.error }));
    }
  }

  const blind = buildBlindSequencePacket(sequences, outputsDir);
  const report = {
    schema: 'issue201_package_d_d01l_longitudinal_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: head,
    control_substrate_sha: CONTROL_SHA,
    consensus_anchor_sha: 'da70fc7',
    evidence_root: evidenceRoot,
    policy_manifest: manifest,
    causal_question: 'Does synchronous preamble Storyteller cognition add material multi-turn narrative value when Plot cognition and post-commit Storyteller cognition remain available?',
    arms: ARMS,
    sequences,
    failures,
    human_blind_eval: {
      ...blind,
      status: 'prepared_for_governance_blind_scoring',
    },
  };
  const reportPath = path.join(evidenceRoot, 'issue201-package-d-d01l-longitudinal-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    reportPath,
    evidenceRoot,
    sequences_committed: sequences.length,
    failures: failures.length,
    blind_sequences: blind.sequence_count,
  }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
