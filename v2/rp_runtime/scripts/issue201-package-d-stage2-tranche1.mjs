/**
 * Issue #201 Package D Stage 2 — first causal ablation tranche (EXP-1..3).
 * Uses D0 controls from prior run; variants via orchestrator roundOptions.
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

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const CONTROL_SHA = 'c751ea666f0cae6524698005aa5859721c2e9738';
const D0_EVIDENCE_ROOT = path.join(
  REPO_ROOT,
  'data',
  'investigation_runs',
  'issue201-d0-baseline-2026-09-14T07-46-14-584Z',
);

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
    playerPost:
      'Magpie keeps her eyes on the guard\'s gold watch while she pushes food around her tray. '
      + 'When Harley\'s voice carries across the table, she murmurs just loud enough to be heard: '
      + '"Pretty things never stay pretty in here for long."',
  },
  ayame_controlled: {
    id: 'ayame_household_entry_evaluation',
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
    label: 'Skip Storyteller + Plot preamble cognition',
    roundOptions: {
      skipStorytellerCognition: true,
      skipPlotCognitionOrchestration: true,
    },
    info_preservation: {
      cognition_removed: ['storyteller_orientation', 'storyteller_assessment', 'librarian_mediation (storyteller)', 'plot_cognition_init', 'plot_cognition_update'],
      preserved: ['scenario premise', 'character cards', 'continuity', 'PVR', 'director', 'character orientation', 'narrator env'],
      disappears: ['storyteller advisory package', 'plot cognition resume summaries'],
      confound: 'low — skip flags are existing production hooks; downstream receives authoritative context without advisory overlays',
    },
  },
  {
    experiment_id: 'EXP-2',
    maps_to: 'D-06',
    label: 'Disable Director semantic QA',
    roundOptions: { directorSemanticQaEnabled: false },
    info_preservation: {
      cognition_removed: ['director_semantic_qa'],
      preserved: ['director_decision inference', 'structural director validation', 'character semantic evaluation'],
      disappears: ['director QA pass/fail gate on proposed designation'],
      confound: 'low — director decision content retained; only semantic QA checker bypassed',
    },
  },
  {
    experiment_id: 'EXP-3',
    maps_to: 'D-03',
    label: 'Skip Character knowledge cognition (orientation + orientation-mediated librarian bundle)',
    roundOptions: { skipCharacterKnowledgeCognition: true },
    info_preservation: {
      cognition_removed: ['character_orientation', 'character_orientation-mediated librarian_mediation'],
      preserved: ['prepareCharacterContext authoritative manifest (perceptual inventory, continuity, director decision)'],
      disappears: ['orientation information_gaps', 'KAR', 'orientation-mediated librarian bundle'],
      confound: 'moderate — librarian bundle from orientation is genuinely novel derived info; character move proceeds with authoritative manifest only (nullable librarian_bundle)',
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

function loadD0Controls() {
  const reportPath = path.join(D0_EVIDENCE_ROOT, 'issue201-d0-baseline-report.json');
  if (!fs.existsSync(reportPath)) throw new Error(`D0 report missing: ${reportPath}`);
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  return report.runs.map((run) => {
    const kinds = run.inference?.kinds ?? [];
    const kindCount = (name) => (kinds.find((k) => k.inference_kind === name)?.count ?? 0);
    const inference = {
      ...run.inference,
      librarian_mediation_count: kindCount('librarian_mediation'),
      character_orientation_count: kindCount('character_orientation'),
      director_semantic_qa_count: kindCount('director_semantic_qa'),
      storyteller_inference_count: kinds
        .filter((k) => String(k.inference_kind).startsWith('storyteller')
          || String(k.inference_kind).startsWith('plot_cognition'))
        .reduce((s, k) => s + k.count, 0),
    };
    return {
      case_id: run.case_id,
      scenario_key: run.scenario_key,
      scenario_id: run.scenario_id,
      repetition_index: run.repetition_index,
      architecture: 'A4_control_full',
      operation_wall_ms: run.operation_wall_ms,
      inference,
      objective: run.objective,
      hg_session_id: run.hg_session_id,
      presentation_path: run.presentation_path,
      presentation_text: fs.readFileSync(run.presentation_path, 'utf8'),
    };
  });
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
      attempt_index: corr.attempt_index ?? 0,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
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
  const llmKinds = Object.entries(byKind).filter(([k]) => k !== 'unknown' && k !== null);
  return {
    inference_count: attempts.length,
    librarian_mediation_count: (byKind.librarian_mediation ?? []).length,
    character_orientation_count: (byKind.character_orientation ?? []).length,
    director_semantic_qa_count: (byKind.director_semantic_qa ?? []).length,
    storyteller_inference_count: llmKinds
      .filter(([k]) => k.startsWith('storyteller') || k.startsWith('plot_cognition'))
      .reduce((s, [, rows]) => s + rows.length, 0),
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
    kinds: llmKinds.map(([kind, rows]) => ({
      inference_kind: kind,
      count: rows.length,
      wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    })),
  };
}

function parseLatencySummary(latencyText) {
  if (!latencyText || typeof latencyText !== 'string') return {};
  const out = {};
  const pvl = latencyText.match(/"player_visible_latency":\s*\{[^}]*"ms":\s*(\d+)/);
  const ccp = latencyText.match(/"character_turn_critical_path":\s*\{[^}]*"ms":\s*(\d+)/);
  const pc = latencyText.match(/"post_commit_section":\s*\{[^}]*"ms":\s*(\d+)/);
  if (pvl) out.player_visible_ms = Number(pvl[1]);
  if (ccp) out.character_turn_cp_ms = Number(ccp[1]);
  if (pc) out.post_commit_ms = Number(pc[1]);
  return out;
}

function runLatencyReconstruction(sessionId, operationId, roundId, commitId, evidenceRoot) {
  const script = path.join(REPO_ROOT, 'tools', 'investigation', 'reconstruct_round_latency.py');
  if (!fs.existsSync(script)) return null;
  try {
    return execFileSync(
      'python',
      [script, sessionId, '--operation', operationId ?? '', '--round', roundId ?? '', '--commit', commitId ?? '', '--attribution', '--evidence-root', evidenceRoot],
      { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 30 * 1024 * 1024 },
    );
  } catch (err) {
    return { error: String(err.stderr ?? err.message ?? err) };
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

function presentationFromRound(roundResult) {
  const lastTurn = roundResult.character_turns?.at(-1);
  return lastTurn?.presentation_text ?? '';
}

async function observeWorldState({ api, hgSceneId, history, userEntry, presentation, scenarioId }) {
  const observations = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  observations.push({
    type: 'player_pvr_recorded',
    validation_status: userPvr.validation_status ?? null,
    unit_count: Array.isArray(userPvr.units) ? userPvr.units.length : null,
  });
  observations.push({
    type: 'player_decomposition_present',
    present: Boolean(userEntry?.metadata?.player_decomposition ?? userEntry?.player_decomposition),
  });
  try {
    const sceneState = await api.getSceneState(hgSceneId);
    observations.push({
      type: 'scene_state_snapshot',
      turn_counter: sceneState.turn_counter ?? null,
      has_pressures: Boolean(sceneState.scene_pressures ?? sceneState.pressures),
    });
  } catch (err) {
    observations.push({ type: 'scene_state_read_failed', detail: String(err?.message ?? err) });
  }
  if (scenarioId === 'ayame_household_entry_evaluation') {
    const pres = String(presentation ?? '').toLowerCase();
    observations.push({
      type: 'portal_narrative_observation',
      door_open_in_presentation: /door.{0,40}(open|drew|drew back|inward)/i.test(pres),
      knock_acknowledged: /knock|prompt|door/i.test(pres),
    });
  }
  observations.push({
    type: 'history_entry_count',
    count: history?.entries?.length ?? 0,
  });
  return observations;
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
  const semanticRetries = (roundResult?.character_turns ?? [])
    .flatMap((t) => t.semantic_evaluation_retries ?? []);
  return {
    issue_count: issues.length,
    issues,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    pvr_validation_status: userPvr.validation_status ?? null,
    presentation_length: String(presentation ?? '').length,
    semantic_retry_signals: semanticRetries.length,
  };
}

async function runVariantCase({
  caseId, experimentId, scenarioKey, repIndex, roundOptions, evidenceRoot, outputsDir,
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
      ...roundOptions,
    });
    await client._recordRoundPresentations(api, roundResult);
    await client._refreshTranscript();
    const operationWallMs = Date.now() - started;
    const presentation = presentationFromRound(roundResult);
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
    const attempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const inference = summarizeAttempts(attempts);
    const latencyText = runLatencyReconstruction(
      created.hg_session_id, operationId,
      roundResult.hg_round_id, roundResult.domain_commit_id, evidenceRoot,
    );
    const latencyPath = path.join(outputsDir, `${caseId}-latency.txt`);
    if (typeof latencyText === 'string') fs.writeFileSync(latencyPath, latencyText, 'utf8');
    const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');
    const worldState = await observeWorldState({
      api,
      hgSceneId: created.hg_session_id,
      history,
      userEntry,
      presentation,
      scenarioId: scenario.id,
    });
    const result = {
      case_id: caseId,
      experiment_id: experimentId,
      scenario_key: scenarioKey,
      scenario_id: scenario.id,
      repetition_index: repIndex,
      architecture: 'A4_ablation',
      round_options: roundOptions,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      operation_wall_ms: operationWallMs,
      presentation_path: presentationPath,
      presentation_text: presentation,
      objective: objectiveChecks({ history, userEntry, roundResult, presentation }),
      inference,
      latency: parseLatencySummary(typeof latencyText === 'string' ? latencyText : ''),
      world_state_observations: worldState,
      storyteller_round_summary: roundResult.storyteller_round_summary ?? null,
      plot_cognition_resume_summary: roundResult.plot_cognition_resume_summary ?? null,
      player_decomposition_recorded: Boolean(playerDecomposition),
    };
    fs.writeFileSync(
      path.join(outputsDir, `${caseId}-meta.json`),
      `${JSON.stringify(result, null, 2)}\n`,
    );
    return result;
  } finally {
    await client.stop();
  }
}

function compareToControl(controlRuns, variantRun, experimentId) {
  const controls = controlRuns.filter((c) => c.scenario_key === variantRun.scenario_key);
  const ctrlInf = controls.map((c) => c.inference.inference_count);
  const ctrlWall = controls.map((c) => c.operation_wall_ms);
  const ctrlMed = controls.map((c) => c.inference.librarian_mediation_count ?? 0);
  return {
    control_case_ids: controls.map((c) => c.case_id),
    delta_inference_count: variantRun.inference.inference_count - (ctrlInf.reduce((a, b) => a + b, 0) / ctrlInf.length),
    delta_wall_ms: variantRun.operation_wall_ms - (ctrlWall.reduce((a, b) => a + b, 0) / ctrlWall.length),
    delta_librarian_mediation: variantRun.inference.librarian_mediation_count - (ctrlMed.reduce((a, b) => a + b, 0) / ctrlMed.length),
    removed_character_orientation: experimentId === 'EXP-3'
      ? variantRun.inference.character_orientation_count === 0
      : null,
    removed_director_qa: experimentId === 'EXP-2'
      ? variantRun.inference.director_semantic_qa_count === 0
      : null,
    removed_storyteller_plot: experimentId === 'EXP-1'
      ? variantRun.inference.storyteller_inference_count === 0
      : null,
  };
}

function buildHumanBlindPacket(allCases, outputsDir) {
  const samples = allCases.map((c, i) => ({
    blind_label: String.fromCharCode(65 + i),
    case_id: c.case_id,
    experiment_id: c.experiment_id ?? 'D0_control',
    scenario_id: c.scenario_id,
    presentation_text: c.presentation_text ?? fs.readFileSync(c.presentation_path, 'utf8'),
  }));
  for (let i = samples.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [samples[i], samples[j]] = [samples[j], samples[i]];
  }
  const packetPath = path.join(outputsDir, 'issue201-stage2-human-blind-eval-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-stage2-human-blind-eval-answer-key.json');
  const packet = {
    schema: 'issue201_blind_eval_packet_v1',
    purpose: 'Package D Stage 2 — human blind evaluation (control + EXP-1..3 variants)',
    instructions: 'Score presentation_text only. Do not request architecture, experiment, or latency data until after scoring.',
    samples: samples.map(({ blind_label, presentation_text }) => ({ blind_label, presentation_text })),
  };
  const answerKey = samples.map(({ blind_label, case_id, experiment_id, scenario_id }) => ({
    blind_label, case_id, experiment_id, scenario_id,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  return { packetPath, keyPath };
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
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const cli = parseArgs();
  const head = gitSha();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = cli.evidenceRoot
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-package-d-stage2-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });

  const d0Controls = loadD0Controls();
  const report = {
    schema: 'issue201_package_d_stage2_tranche1_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: head,
    control_substrate_sha: CONTROL_SHA,
    d0_evidence_root: D0_EVIDENCE_ROOT,
    evidence_root: evidenceRoot,
    d0_controls: d0Controls.map((c) => ({
      case_id: c.case_id,
      scenario_key: c.scenario_key,
      operation_wall_ms: c.operation_wall_ms,
      inference_count: c.inference.inference_count,
      librarian_mediation_count: c.inference.librarian_mediation_count,
    })),
    experiments: [],
  };

  const experimentsToRun = cli.only
    ? EXPERIMENTS.filter((e) => e.experiment_id === cli.only)
    : EXPERIMENTS;

  for (const exp of experimentsToRun) {
    const expReport = { ...exp, runs: [] };
    for (const scenarioKey of ['arkham_stress', 'ayame_controlled']) {
      for (let rep = 1; rep <= 2; rep += 1) {
        const caseId = `${exp.experiment_id}-${scenarioKey}-r${rep}`;
        const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
        if (cli.skipExisting && fs.existsSync(presentationPath) && fs.statSync(presentationPath).size > 0) {
          console.log(`Skipping ${caseId} (existing presentation)`);
          continue;
        }
        console.log(`Running ${caseId}...`);
        const result = await runVariantCase({
          caseId,
          experimentId: exp.experiment_id,
          scenarioKey,
          repIndex: rep,
          roundOptions: exp.roundOptions,
          evidenceRoot,
          outputsDir,
        });
        result.comparison_to_d0 = compareToControl(d0Controls, result, exp.experiment_id);
        expReport.runs.push(result);
        console.log(JSON.stringify({
          caseId,
          wall_ms: result.operation_wall_ms,
          inferences: result.inference.inference_count,
          lib_med: result.inference.librarian_mediation_count,
          committed: result.objective.committed,
        }));
      }
    }
    if (expReport.runs.length > 0) {
      report.experiments.push(expReport);
    }
  }

  // Rehydrate skipped/completed runs from meta sidecars for final report assembly.
  for (const exp of EXPERIMENTS) {
    let expReport = report.experiments.find((e) => e.experiment_id === exp.experiment_id);
    if (!expReport) {
      expReport = { ...exp, runs: [] };
      report.experiments.push(expReport);
    }
    for (const scenarioKey of ['arkham_stress', 'ayame_controlled']) {
      for (let rep = 1; rep <= 2; rep += 1) {
        const caseId = `${exp.experiment_id}-${scenarioKey}-r${rep}`;
        if (expReport.runs.some((r) => r.case_id === caseId)) continue;
        const metaPath = path.join(outputsDir, `${caseId}-meta.json`);
        if (!fs.existsSync(metaPath)) continue;
        const stub = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
        stub.comparison_to_d0 = compareToControl(d0Controls, stub, exp.experiment_id);
        expReport.runs.push(stub);
      }
    }
    expReport.runs.sort((a, b) => a.case_id.localeCompare(b.case_id));
  }

  const allForBlind = [
    ...d0Controls.map((c) => ({ ...c, experiment_id: 'D0_control' })),
    ...report.experiments.flatMap((e) => e.runs),
  ];
  report.human_blind_eval = buildHumanBlindPacket(allForBlind, outputsDir);
  report.human_blind_eval.status = 'prepared_for_governance_user_evaluation';

  const outPath = path.join(evidenceRoot, 'issue201-package-d-stage2-tranche1-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outPath, evidenceRoot, experiments: report.experiments.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
