/**
 * Issue #201 Package D Stage 1 — fresh baseline + bounded ablation tranche.
 * Investigation-only harness; does not modify production runtime behavior.
 *
 * Usage (from v2/rp_runtime): node scripts/issue201-package-d-stage1.mjs
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { SessionId } from '@deepseek-ai/dsh-session';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import {
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../src/application/application-settings.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import {
  agentOptionsFromProfile,
  mockInferenceProfile,
} from '../src/lib/inference-profile.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const SCENARIOS = {
  arkham_stress: {
    id: 'arkham_asylum_mess_hall_arena',
    label: 'Arkham mess hall (3-char stress)',
    characters: ['harley_quinn', 'poison_ivy', 'magpie'],
    roleAssignments: {
      harley_quinn: 'instigator',
      poison_ivy: 'instigator_accomplice',
      magpie: 'new_arrival',
    },
    playerCharacterFileId: 'magpie',
    userName: 'Magpie',
    openerPreference: 'mess_hall_magpie',
    playerPost:
      'Magpie keeps her eyes on the guard\'s gold watch while she pushes food around her tray. '
      + 'When Harley\'s voice carries across the table, she murmurs just loud enough to be heard: '
      + '"Pretty things never stay pretty in here for long."',
  },
  ayame_controlled: {
    id: 'ayame_household_entry_evaluation',
    label: 'Ayame household entry (F06 controlled)',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
    playerPost:
      'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.',
  },
};

const EXPERIMENTS = [
  {
    experiment_id: 'EXP-1',
    maps_to: 'D-01',
    class: 'low_marginal_cognition',
    label: 'Skip Storyteller preamble + plot resume',
    roundOptions: {
      skipStorytellerCognition: true,
      skipPlotCognitionOrchestration: true,
    },
  },
  {
    experiment_id: 'EXP-2',
    maps_to: 'D-06',
    class: 'checker_validator',
    label: 'Disable Director semantic QA',
    roundOptions: {
      directorSemanticQaEnabled: false,
    },
  },
  {
    experiment_id: 'EXP-3',
    maps_to: 'D-01-partial / tiering',
    class: 'consolidation_tiering',
    label: 'Skip Storyteller preamble only (retain plot resume)',
    roundOptions: {
      skipStorytellerCognition: true,
    },
  },
];

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function loadAttempts(evidenceRoot, sessionId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((attemptId) => {
    const attempt = JSON.parse(fs.readFileSync(
      path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`),
      'utf8',
    ));
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    const corr = attempt.correlation ?? {};
    return {
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: corr.inference_kind ?? null,
      role: corr.role ?? null,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
    };
  });
}

function summarizeAttempts(attempts) {
  const byKind = {};
  for (const row of attempts) {
    const key = row.inference_kind ?? 'unknown';
    if (!byKind[key]) byKind[key] = [];
    byKind[key].push(row);
  }
  const kinds = Object.entries(byKind).map(([kind, rows]) => ({
    inference_kind: kind,
    count: rows.length,
    wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    reasoning_tokens_total: rows.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    total_tokens_total: rows.reduce((s, r) => s + (r.total_tokens ?? 0), 0),
  }));
  return {
    inference_count: attempts.length,
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    total_tokens_total: attempts.reduce((s, r) => s + (r.total_tokens ?? 0), 0),
    kinds,
    attempts,
  };
}

function runLatencyReconstruction(sessionId, operationId, roundId, commitId, evidenceRoot) {
  const script = path.join(REPO_ROOT, 'tools', 'investigation', 'reconstruct_round_latency.py');
  if (!fs.existsSync(script)) return null;
  try {
    const out = execFileSync(
      'python',
      [
        script,
        sessionId,
        '--operation', operationId ?? '',
        '--round', roundId ?? '',
        '--commit', commitId ?? '',
        '--attribution',
        '--evidence-root', evidenceRoot,
      ],
      { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 },
    );
    return out;
  } catch (err) {
    return { error: String(err.stderr ?? err.message ?? err) };
  }
}

function presentationFromRound(roundResult) {
  if (roundResult.presentation_text) return roundResult.presentation_text;
  const lastTurn = roundResult.character_turns?.at(-1);
  return lastTurn?.presentation_text ?? '';
}

function objectiveChecks({ history, userEntry, roundResult }) {
  const issues = [];
  const presentation = String(roundResult?.presentation ?? '');
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
    presentation_length: presentation.length,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    history_entry_count: history?.entries?.length ?? 0,
  };
}

async function createScenarioSession(client, scenario) {
  const openers = await client.listTemplateOpeners(scenario.id);
  const opener = scenario.openerPreference
    ? openers.find((o) => String(o.opener_id ?? '').includes(scenario.openerPreference)) ?? openers[0]
    : openers[0];
  if (!opener) {
    throw new Error(`no opener for ${scenario.id}`);
  }
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
    modelProfile,
    'player_visibility_triage',
    client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const verificationModelProfile = modelProfileForInferenceKind(
    modelProfile,
    'player_uniform_eligibility_verification',
    client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const triageResult = await phaseExecutors.runPlayerVisibilityTriage({
    api,
    trace,
    sceneAgent,
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
      modelProfile,
      'player_decomposition',
      client.runtimeSettings,
      { inferenceMode: client.options.inferenceMode },
    );
    const decompositionResult = await phaseExecutors.runPlayerDecomposition({
      api,
      trace,
      sceneAgent,
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

async function runProductionBaseline(client, scenario) {
  const started = Date.now();
  const turn = await client.submitUserTurn({
    userMessage: scenario.playerPost,
    userName: scenario.userName,
  });
  return {
    operation_wall_ms: Date.now() - started,
    turn,
    presentation_text: turn.presentation ?? '',
  };
}

async function runRoundVariant(client, roundOptions, operationId) {
  const api = client._domainApi();
  const inference = buildInferenceOptions(
    client.runtimeSettings,
    { inferenceMode: client.options.inferenceMode },
  );
  const started = Date.now();
  const roundResult = await client.orchestrator.runRound({
    session: { mode: 'open', hg_session_id: client.activeSessionId },
    roleProfiles: inference.roleProfiles,
    liveMaxAttempts: inference.liveMaxAttempts,
    clientOperationId: operationId,
    spanTracker: client.activeSpanTracker,
    ...roundOptions,
  });
  await client._recordRoundPresentations(api, roundResult);
  await client._refreshTranscript();
  const operationWallMs = Date.now() - started;
  const presentation = presentationFromRound(roundResult);
  return { roundResult, presentation, operationWallMs };
}

async function runCase({
  caseId,
  scenarioKey,
  variantLabel,
  roundOptions = {},
  evidenceRoot,
  useProductionSubmit = false,
}) {
  const scenario = SCENARIOS[scenarioKey];
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
  try {
    let created;
    let roundResult;
    let presentation;
    let operationWallMs;
    let totalWallMs;
    let resolvedOperationId = null;
    if (useProductionSubmit) {
      created = await createScenarioSession(client, scenario);
      const baseline = await runProductionBaseline(client, scenario);
      roundResult = baseline.turn.round;
      presentation = baseline.presentation_text;
      operationWallMs = baseline.operation_wall_ms;
      totalWallMs = baseline.operation_wall_ms;
      resolvedOperationId = baseline.turn.client_operation_id ?? null;
    } else {
      created = await createScenarioSession(client, scenario);
      resolvedOperationId = `issue201-${caseId}-${crypto.randomUUID()}`;
      client._beginRoundOperation(resolvedOperationId, 'user_turn');
      const operationStarted = Date.now();
      await runPlayerPvrAndRecord(client, scenario.playerPost);
      ({ roundResult, presentation, operationWallMs } = await runRoundVariant(
        client,
        roundOptions,
        resolvedOperationId,
      ));
      totalWallMs = Date.now() - operationStarted;
    }
    const api = client._domainApi();
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
    const attempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const inference = summarizeAttempts(attempts);
    const latencyText = runLatencyReconstruction(
      created.hg_session_id,
      resolvedOperationId,
      roundResult.hg_round_id,
      roundResult.domain_commit_id,
      evidenceRoot,
    );
    return {
      case_id: caseId,
      variant_label: variantLabel,
      scenario_key: scenarioKey,
      scenario_id: scenario.id,
      hg_session_id: created.hg_session_id,
      client_operation_id: resolvedOperationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      round_options: roundOptions,
      operation_wall_ms: totalWallMs,
      round_orchestration_wall_ms: operationWallMs,
      presentation_text: presentation,
      presentation_preview: String(presentation ?? '').slice(0, 1200),
      transcript_preview: client.getTranscript().slice(-6).map((e) => ({
        role: e.role ?? e.speaker ?? null,
        preview: String(e.content ?? '').slice(0, 300),
      })),
      objective: objectiveChecks({ history, userEntry, roundResult: { ...roundResult, presentation } }),
      inference,
      latency_reconstruction_excerpt: typeof latencyText === 'string'
        ? latencyText.split('\n').slice(0, 40).join('\n')
        : latencyText,
      storyteller_round_summary: roundResult.storyteller_round_summary ?? null,
      plot_cognition_resume_summary: roundResult.plot_cognition_resume_summary ?? null,
    };
  } finally {
    await client.stop();
  }
}

function buildBlindEvalPacket(cases) {
  const labels = cases.map((_, i) => String.fromCharCode(65 + i));
  const shuffled = [...cases].map((c, i) => ({ ...c, blind_label: labels[i] }));
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i].blind_label, shuffled[j].blind_label] = [shuffled[j].blind_label, shuffled[i].blind_label];
  }
  return {
    schema: 'issue201_blind_eval_packet_v1',
    instructions: 'Evaluate presentation_text only. Do not request architecture identity until after scoring.',
    samples: shuffled.map((c) => ({
      blind_label: c.blind_label,
      scenario_id: c.scenario_id,
      presentation_text: c.presentation_text,
    })),
    answer_key_path: 'issue201-blind-eval-answer-key.json (restricted; not for evaluators)',
    answer_key: shuffled.map((c) => ({
      blind_label: c.blind_label,
      case_id: c.case_id,
      variant_label: c.variant_label,
    })),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY required');
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-package-d-stage1-${stamp}`);
  fs.mkdirSync(evidenceRoot, { recursive: true });

  const report = {
    schema: 'issue201_package_d_stage1_v1',
    generated_at: new Date().toISOString(),
    candidate_sha: gitSha(),
    evidence_root: evidenceRoot,
    baselines: [],
    experiments: [],
    experiment_ranking: [
      { rank: 1, id: 'D-01', rationale: 'Highest uncertainty on preamble stack marginal value; isolates advisory layers without touching validators' },
      { rank: 2, id: 'D-06', rationale: 'Tests whether Director semantic QA provides unique safety beyond structural validation' },
      { rank: 3, id: 'D-01-partial', rationale: 'Distinguishes Storyteller vs plot cognition contribution within preamble' },
      { rank: 4, id: 'D-04', rationale: 'Env cognition cost/value — requires investigation hook; deferred' },
      { rank: 5, id: 'D-03', rationale: 'Character orientation — no production skip flag; deferred' },
      { rank: 6, id: 'D-10', rationale: 'Post-commit join slimming — skipLibrarianProposalGeneration candidate for tranche 2' },
    ],
    tranche_rationale: 'Three distinct classes on arkham_stress after dual-scenario baselines: preamble removal, checker removal, partial preamble tiering.',
  };

  console.log('D0 baseline — arkham stress...');
  report.baselines.push(await runCase({
    caseId: 'D0-arkham-control',
    scenarioKey: 'arkham_stress',
    variantLabel: 'control_full_architecture',
    roundOptions: {},
    evidenceRoot,
    useProductionSubmit: true,
  }));

  console.log('D0 baseline — ayame controlled...');
  report.baselines.push(await runCase({
    caseId: 'D0-ayame-control',
    scenarioKey: 'ayame_controlled',
    variantLabel: 'control_full_architecture',
    roundOptions: {},
    evidenceRoot,
    useProductionSubmit: true,
  }));

  for (const exp of EXPERIMENTS) {
    console.log(`Running ${exp.experiment_id} (${exp.label})...`);
    report.experiments.push({
      ...exp,
      result: await runCase({
        caseId: `${exp.experiment_id}-arkham`,
        scenarioKey: 'arkham_stress',
        variantLabel: exp.label,
        roundOptions: exp.roundOptions,
        evidenceRoot,
      }),
    });
  }

  const arkhamCases = [
    report.baselines.find((b) => b.case_id === 'D0-arkham-control'),
    ...report.experiments.map((e) => e.result),
  ];
  const blindPacket = buildBlindEvalPacket(arkhamCases);
  const blindPath = path.join(evidenceRoot, 'issue201-blind-eval-packet.json');
  const keyPath = path.join(evidenceRoot, 'issue201-blind-eval-answer-key.json');
  fs.writeFileSync(blindPath, `${JSON.stringify({ ...blindPacket, answer_key: undefined }, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(blindPacket.answer_key, null, 2)}\n`);

  const outJson = path.join(evidenceRoot, 'issue201-package-d-stage1-report.json');
  fs.writeFileSync(outJson, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outJson, evidenceRoot, baselines: report.baselines.length, experiments: report.experiments.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
