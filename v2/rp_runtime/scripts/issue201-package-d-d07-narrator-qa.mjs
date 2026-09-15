/**
 * Issue #201 Package D — D-07 Narrator semantic-QA marginal-value experiment.
 * Lean topology; only narratorSemanticQaEnabled differs between arms.
 *
 * Usage (from v2/rp_runtime): node scripts/issue201-package-d-d07-narrator-qa.mjs
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
const DESIGN_SHA = 'b88333b';
const D10_EVIDENCE_ROOT = path.join(
  REPO_ROOT,
  'data',
  'investigation_runs',
  'issue201-package-d-d10-2026-09-15T01-20-29-181Z',
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

const LEAN_BASE = {
  skipStorytellerCognition: true,
  skipLibrarianProposalGeneration: true,
  directorSemanticQaEnabled: false,
};

const ARMS = [
  {
    arm_id: 'control',
    maps_to: 'D-07-control',
    roundOptions: { ...LEAN_BASE, narratorSemanticQaEnabled: true },
  },
  {
    arm_id: 'ablated',
    maps_to: 'D-07-ablated',
    roundOptions: { ...LEAN_BASE, narratorSemanticQaEnabled: false },
  },
];

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function runPreflight() {
  const servicePath = path.join(
    REPO_ROOT, 'v2', 'rp_runtime', 'src', 'plugins', 'hg-round-orchestrator', 'service.mjs',
  );
  const narratorPhasePath = path.join(
    REPO_ROOT, 'v2', 'rp_runtime', 'src', 'plugins', 'hg-phase-executors', 'narrator-phase.mjs',
  );
  const serviceText = fs.readFileSync(servicePath, 'utf8');
  const narratorText = fs.readFileSync(narratorPhasePath, 'utf8');
  const checks = {
    narrator_qa_flag_wired: serviceText.includes('narratorSemanticQaEnabled'),
    narrator_qa_skip_gate: narratorText.includes('if (!narratorSemanticQaEnabled)'),
    director_qa_independent: serviceText.includes('directorSemanticQaEnabled'),
    storyteller_skip_independent: serviceText.includes('skipStorytellerCognition'),
    post_commit_skip_independent: serviceText.includes('skipLibrarianProposalGeneration'),
    plot_skip_independent: serviceText.includes('skipPlotCognitionOrchestration'),
  };
  checks.pass = Object.values(checks).every(Boolean);
  return {
    schema: 'issue201_d07_preflight_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: gitSha(),
    design_anchor_sha: DESIGN_SHA,
    checks,
    verdict: checks.pass ? 'PROCEED' : 'STOP_GOVERNANCE',
  };
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
    const decision = attempt.decision ?? {};
    return {
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: corr.inference_kind ?? null,
      role: corr.role ?? null,
      attempt_index: corr.attempt_index ?? 0,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
      decision,
      correlation: corr,
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
  const kindRows = (name) => byKind[name] ?? [];
  const narratorPresentation = kindRows('narrator_presentation');
  const narratorQa = kindRows('narrator_semantic_qa');
  const narratorEnv = kindRows('narrator_environment_cognition');
  const narratorRetries = narratorPresentation.filter((r) => (r.attempt_index ?? 0) > 0).length;
  return {
    inference_count: attempts.length,
    narrator_semantic_qa_count: narratorQa.length,
    narrator_environment_cognition_count: narratorEnv.length,
    narrator_presentation_count: narratorPresentation.length,
    narrator_regeneration_count: narratorRetries,
    director_semantic_qa_count: kindRows('director_semantic_qa').length,
    storyteller_post_commit_count: kindRows('storyteller_post_commit_issue_pressure').length,
    librarian_mediation_count: kindRows('librarian_mediation').length,
    character_orientation_count: kindRows('character_orientation').length,
    plot_cognition_count: kindRows('plot_cognition_init').length
      + kindRows('plot_cognition_update').length
      + kindRows('plot_cognition_epistemic_eval').length,
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    input_tokens_total: attempts.reduce((s, r) => s + (r.input_tokens ?? 0), 0),
    output_tokens_total: attempts.reduce((s, r) => s + (r.output_tokens ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
    kinds: Object.entries(byKind)
      .filter(([k]) => k !== 'unknown' && k !== null)
      .map(([kind, rows]) => ({
        inference_kind: kind,
        count: rows.length,
        wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
        reasoning_tokens_total: rows.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
      })),
  };
}

function classifyQaAction(action) {
  const a = String(action ?? 'unknown');
  if (a === 'pass') return 'pass';
  if (a === 'accept_with_residuals') return 'residual_accept';
  if (a === 'soft_regen') return 'soft_regen';
  if (a === 'hard_regen') return 'hard_regen';
  if (a === 'player_authorship_fail_closed') return 'authorship_fail_closed';
  if (a === 'exhausted_fallback' || a === 'infra_fail') return 'fail_closed_other';
  return 'other';
}

function extractQaForensics(evidenceRoot, sessionId) {
  const attempts = loadAttempts(evidenceRoot, sessionId);
  const events = [];
  for (const row of attempts) {
    if (row.inference_kind !== 'narrator_presentation') continue;
    const sq = row.decision?.semantic_qa ?? row.decision?.semanticQa ?? null;
    if (!sq) continue;
    const action = sq.policy_action ?? sq.policyAction ?? sq.result?.overall_result ?? 'unknown';
    const qaAttempt = attempts.find((a) => a.evidence_id === sq.evaluator_evidence_id
      || a.evidence_id === sq.evaluatorEvidenceId);
    events.push({
      presentation_evidence_id: row.evidence_id,
      attempt_index: row.attempt_index,
      policy_action: action,
      qa_category: classifyQaAction(action),
      findings: sq.result?.findings ?? [],
      evaluator_summary: sq.result?.evaluator_summary ?? null,
      pre_qa_candidate: row.decision?.candidate_presentation_text
        ?? row.decision?.candidatePresentationText
        ?? row.decision?.rejected_presentation_text
        ?? row.decision?.rejectedPresentationText
        ?? null,
      final_presentation: row.decision?.presentation_text ?? row.decision?.presentationText ?? null,
      validation_class: row.decision?.validation_class ?? row.decision?.validationClass ?? null,
      retry_decision: row.decision?.retry_decision ?? row.decision?.retryDecision ?? null,
      qa_wall_ms: qaAttempt?.wall_ms ?? null,
      qa_input_tokens: qaAttempt?.input_tokens ?? null,
      qa_output_tokens: qaAttempt?.output_tokens ?? null,
      qa_reasoning_tokens: qaAttempt?.reasoning_tokens ?? null,
    });
  }
  const qaAttempts = attempts.filter((a) => a.inference_kind === 'narrator_semantic_qa');
  const summary = {
    qa_invocations: qaAttempts.length,
    presentation_with_qa_metadata: events.length,
    pass: events.filter((e) => e.qa_category === 'pass').length,
    residual_accept: events.filter((e) => e.qa_category === 'residual_accept').length,
    soft_regen: events.filter((e) => e.qa_category === 'soft_regen').length,
    hard_regen: events.filter((e) => e.qa_category === 'hard_regen').length,
    authorship_fail_closed: events.filter((e) => e.qa_category === 'authorship_fail_closed').length,
    other_non_pass: events.filter((e) => !['pass', 'residual_accept'].includes(e.qa_category)).length,
    non_pass_total: events.filter((e) => !['pass'].includes(e.qa_category)).length,
    qa_wall_ms_total: qaAttempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    qa_reasoning_tokens_total: qaAttempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    events,
  };
  summary.category_note = 'non_pass_total counts all events where policy_action !== pass; '
    + 'residual_accept is a distinct accept-with-concerns outcome and is not counted in pass.';
  return summary;
}

function analyzeD10ArchiveSupplement() {
  const reportPath = path.join(D10_EVIDENCE_ROOT, 'issue201-package-d-d10-post-commit-report.json');
  if (!fs.existsSync(reportPath)) {
    return { available: false, reason: 'D-10 report missing' };
  }
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  const controlSequences = (report.sequences ?? []).filter((s) => s.arm_id === 'control' || String(s.sequence_id ?? '').includes('control'));
  const sessionIds = new Set();
  for (const seq of controlSequences) {
    for (const turn of seq.turns ?? []) {
      if (turn.hg_session_id) sessionIds.add(turn.hg_session_id);
    }
    if (seq.hg_session_id) sessionIds.add(seq.hg_session_id);
  }
  if (sessionIds.size === 0) {
    for (const seq of report.sequences ?? []) {
      if (String(seq.sequence_id ?? '').startsWith('D10-control') && seq.hg_session_id) {
        sessionIds.add(seq.hg_session_id);
      }
    }
  }
  const allEvents = [];
  for (const sid of sessionIds) {
    const forensics = extractQaForensics(D10_EVIDENCE_ROOT, sid);
    for (const ev of forensics.events) {
      allEvents.push({ hg_session_id: sid, ...ev });
    }
  }
  if (allEvents.length === 0) {
    const sessionsDir = D10_EVIDENCE_ROOT;
    for (const name of fs.readdirSync(sessionsDir)) {
      if (!name.startsWith('hg-session-')) continue;
      const forensics = extractQaForensics(D10_EVIDENCE_ROOT, name);
      if (forensics.qa_invocations > 0) {
        for (const ev of forensics.events) allEvents.push({ hg_session_id: name, ...ev });
      }
    }
  }
  const presentations = allEvents.length > 0
    ? allEvents
    : [];
  const byCategory = {};
  for (const ev of presentations) {
    byCategory[ev.qa_category] = (byCategory[ev.qa_category] ?? 0) + 1;
  }
  const presentationCount = presentations.length || 64;
  const nonPass = presentations.filter((e) => e.qa_category !== 'pass');
  return {
    available: true,
    evidence_root: D10_EVIDENCE_ROOT,
    control_sessions_scanned: sessionIds.size || 'all_hg-session dirs',
    presentations_with_qa_metadata: presentations.length,
    expected_presentations: 64,
    pass: byCategory.pass ?? (presentations.length - nonPass.length),
    residual_accept: byCategory.residual_accept ?? 0,
    soft_regen: byCategory.soft_regen ?? 0,
    hard_regen: byCategory.hard_regen ?? 0,
    authorship_fail_closed: byCategory.authorship_fail_closed ?? 0,
    non_pass_total: nonPass.length,
    category_overlap_note: 'Governance D-10 context: 9 non-pass events across 64 presentations '
      + '(3 hard_regen + 5 soft_regen + 1 authorship_fail_closed + 1 accept_with_residuals). '
      + 'accept_with_residuals maps to residual_accept; non_pass_total excludes pass only.',
    events: presentations,
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

function objectiveChecks({ history, userEntry, roundResult, presentation, qaForensics, armId }) {
  const issues = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  if (userPvr.validation_status && userPvr.validation_status !== 'valid') {
    issues.push({ type: 'pvr_validation', detail: userPvr.validation_status });
  }
  if (!roundResult?.committed) {
    issues.push({ type: 'round_not_committed', detail: roundResult?.completion_reason ?? null });
  }
  if (!presentation || String(presentation).trim().length === 0) {
    issues.push({ type: 'missing_presentation', detail: 'empty presentation text' });
  }
  for (const ev of qaForensics.events ?? []) {
    if (ev.qa_category === 'authorship_fail_closed') {
      issues.push({ type: 'player_authorship_defect', detail: ev.policy_action });
    }
    if (ev.validation_class && ev.validation_class !== 'accepted') {
      issues.push({ type: 'fidelity_validation_failure', detail: ev.validation_class });
    }
  }
  const blocking = issues.filter((i) => ['round_not_committed', 'missing_presentation', 'player_authorship_defect'].includes(i.type));
  const verdict = blocking.length > 0 ? 'blocking_failure' : issues.length > 0 ? 'degraded_non_blocking' : 'clean';
  return {
    verdict,
    issue_count: issues.length,
    issues,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    pvr_validation_status: userPvr.validation_status ?? null,
    presentation_length: String(presentation ?? '').length,
    arm_id: armId,
  };
}

async function runCase({
  caseId, armId, roundOptions, scenarioKey, repIndex, evidenceRoot, outputsDir,
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
    const qaForensics = extractQaForensics(evidenceRoot, created.hg_session_id);
    const latencyText = runLatencyReconstruction(
      created.hg_session_id, operationId,
      roundResult.hg_round_id, roundResult.domain_commit_id, evidenceRoot,
    );
    const latencyPath = path.join(outputsDir, `${caseId}-latency.txt`);
    if (typeof latencyText === 'string') fs.writeFileSync(latencyPath, latencyText, 'utf8');
    const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');
    const objective = objectiveChecks({
      history, userEntry, roundResult, presentation, qaForensics, armId,
    });
    const result = {
      case_id: caseId,
      arm_id: armId,
      scenario_key: scenarioKey,
      scenario_id: scenario.id,
      repetition_index: repIndex,
      round_options: roundOptions,
      hg_session_id: created.hg_session_id,
      client_operation_id: operationId,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      operation_wall_ms: operationWallMs,
      presentation_path: presentationPath,
      presentation_text: presentation,
      objective,
      inference,
      qa_forensics: qaForensics,
      latency: parseLatencySummary(typeof latencyText === 'string' ? latencyText : ''),
      player_decomposition_recorded: Boolean(playerDecomposition),
      hook_isolation: {
        narrator_semantic_qa_expected: armId === 'control' ? '>=1' : '0',
        narrator_semantic_qa_observed: inference.narrator_semantic_qa_count,
        director_semantic_qa_observed: inference.director_semantic_qa_count,
        storyteller_post_commit_observed: inference.storyteller_post_commit_count,
        isolation_ok: armId === 'control'
          ? inference.director_semantic_qa_count === 0 && inference.storyteller_post_commit_count === 0
          : inference.narrator_semantic_qa_count === 0
            && inference.director_semantic_qa_count === 0
            && inference.storyteller_post_commit_count === 0,
      },
    };
    fs.writeFileSync(path.join(outputsDir, `${caseId}-meta.json`), `${JSON.stringify(result, null, 2)}\n`);
    fs.writeFileSync(
      path.join(outputsDir, `${caseId}-qa-forensics.json`),
      `${JSON.stringify(qaForensics, null, 2)}\n`,
    );
    return result;
  } finally {
    await client.stop();
  }
}

function buildBlindPacket(runs, outputsDir) {
  const samples = runs.map((run, i) => ({
    blind_label: String.fromCharCode(65 + i),
    case_id: run.case_id,
    arm_id: run.arm_id,
    scenario_id: run.scenario_id,
    presentation_text: run.presentation_text ?? fs.readFileSync(run.presentation_path, 'utf8'),
  }));
  for (let i = samples.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [samples[i], samples[j]] = [samples[j], samples[i]];
  }
  const packetPath = path.join(outputsDir, 'issue201-d07-blind-eval-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-d07-blind-eval-answer-key.json');
  const transportPath = path.join(outputsDir, 'issue201-d07-blind-eval-transport.md');
  const packet = {
    schema: 'issue201_blind_eval_packet_v1',
    purpose: 'Package D D-07 — Narrator semantic-QA marginal value (8 presentations)',
    rubric: {
      primary: 'issue201-stage2-human-evaluator-worksheet.md (11 dimensions, 1-5 each)',
      adjunct_dimensions: ['environmental_grounding', 'overall_rp_usefulness'],
      adjunct_note: 'Score adjunct dimensions 1-5 for every sample if Governance retained them.',
    },
    instructions: 'Score presentation_text only. Do not request architecture, arm, QA state, session, latency, usage metadata, or intervention metadata.',
    samples: samples.map(({ blind_label, presentation_text }) => ({
      blind_label,
      presentation_text,
    })),
  };
  const answerKey = samples.map(({ blind_label, case_id, arm_id, scenario_id }) => ({
    blind_label, case_id, arm_id, scenario_id,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  const transport = `# Issue #201 D-07 Blind Evaluation Transport

Use \`governance/records/issue201-stage2-human-evaluator-worksheet.md\` for the 11-dimension rubric.

**Packet:** \`${packetPath}\`  
**Answer key:** \`${keyPath}\` — **concealed until Governance locks scores**

Optional adjunct (1-5 each): environmental_grounding, overall_rp_usefulness
`;
  fs.writeFileSync(transportPath, transport, 'utf8');
  const leakedFields = [];
  const packetStr = JSON.stringify(packet);
  for (const forbidden of ['hg-session', 'control', 'ablated', 'narrator_semantic', 'wall_ms', 'inference_kind', 'semantic_qa']) {
    if (packetStr.toLowerCase().includes(forbidden)) leakedFields.push(forbidden);
  }
  return {
    packetPath,
    keyPath,
    transportPath,
    sample_count: samples.length,
    blinding_integrity: {
      pass: leakedFields.length === 0,
      leaked_forbidden_substrings: leakedFields,
      randomized: true,
    },
  };
}

function aggregateArm(runs, armId) {
  const armRuns = runs.filter((r) => r.arm_id === armId);
  return {
    arm_id: armId,
    completed_runs: armRuns.length,
    objective_clean: armRuns.filter((r) => r.objective.verdict === 'clean').length,
    objective_degraded: armRuns.filter((r) => r.objective.verdict === 'degraded_non_blocking').length,
    objective_blocking: armRuns.filter((r) => r.objective.verdict === 'blocking_failure').length,
    total_inference_count: armRuns.reduce((s, r) => s + r.inference.inference_count, 0),
    narrator_qa_count: armRuns.reduce((s, r) => s + r.inference.narrator_semantic_qa_count, 0),
    narrator_env_count: armRuns.reduce((s, r) => s + r.inference.narrator_environment_cognition_count, 0),
    narrator_regen_count: armRuns.reduce((s, r) => s + r.inference.narrator_regeneration_count, 0),
    wall_ms_total: armRuns.reduce((s, r) => s + r.operation_wall_ms, 0),
    reasoning_tokens_total: armRuns.reduce((s, r) => s + r.inference.reasoning_tokens_total, 0),
    input_tokens_total: armRuns.reduce((s, r) => s + r.inference.input_tokens_total, 0),
    output_tokens_total: armRuns.reduce((s, r) => s + r.inference.output_tokens_total, 0),
    qa_non_pass: armRuns.reduce((s, r) => s + (r.qa_forensics?.non_pass_total ?? 0), 0),
  };
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { only: null, evidenceRoot: null, skipExisting: false, extraCases: [] };
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--only' && args[i + 1]) out.only = args[++i];
    if (args[i] === '--evidence-root' && args[i + 1]) out.evidenceRoot = args[++i];
    if (args[i] === '--skip-existing') out.skipExisting = true;
    if (args[i] === '--replacement-for' && args[i + 1]) {
      const failedCaseId = args[++i];
      const m = failedCaseId.match(/^D07-(control|ablated)-(\w+)-r(\d+)$/);
      if (!m) throw new Error(`invalid --replacement-for case id: ${failedCaseId}`);
      const arm = ARMS.find((a) => a.arm_id === m[1]);
      if (!arm) throw new Error(`unknown arm in ${failedCaseId}`);
      out.extraCases.push({
        caseId: `${failedCaseId}-a2`,
        armId: arm.arm_id,
        roundOptions: arm.roundOptions,
        scenarioKey: m[2],
        repIndex: Number(m[3]),
        replaces_case_id: failedCaseId,
        replacement_reason: 'generic_runtime_character_failure',
      });
      out.only = `${failedCaseId}-a2`;
      out.skipExisting = true;
    }
  }
  return out;
}

function rehydrateRunsFromMeta(plan, outputsDir, skipCaseIds = new Set()) {
  const runs = [];
  for (const item of plan) {
    if (skipCaseIds.has(item.caseId)) continue;
    const metaPath = path.join(outputsDir, `${item.caseId}-meta.json`);
    if (!fs.existsSync(metaPath)) continue;
    const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    if (meta.objective?.verdict === 'blocking_failure' && !item.replaces_case_id) continue;
    runs.push(meta);
  }
  return runs;
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) throw new Error('DEEPSEEK_API_KEY required');
  const cli = parseArgs();
  const preflight = runPreflight();
  if (!preflight.checks.pass) {
    console.error(JSON.stringify(preflight, null, 2));
    throw new Error('D-07 preflight STOP — hook blast radius changed');
  }
  const head = gitSha();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = cli.evidenceRoot
    ?? path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-package-d-d07-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceRoot, 'd07_preflight.json'), `${JSON.stringify(preflight, null, 2)}\n`);

  const plan = [];
  for (const arm of ARMS) {
    for (const scenarioKey of ['arkham_stress', 'ayame_controlled']) {
      for (let rep = 1; rep <= 2; rep += 1) {
        plan.push({
          caseId: `D07-${arm.arm_id}-${scenarioKey}-r${rep}`,
          armId: arm.arm_id,
          roundOptions: arm.roundOptions,
          scenarioKey,
          repIndex: rep,
        });
      }
    }
  }
  for (const extra of cli.extraCases ?? []) {
    plan.push(extra);
  }

  const replacedCaseIds = new Set(
    (cli.extraCases ?? []).map((c) => c.replaces_case_id).filter(Boolean),
  );
  let runs = rehydrateRunsFromMeta(plan, outputsDir, replacedCaseIds);
  const failures = [];
  for (const item of plan) {
    if (cli.only && item.caseId !== cli.only && !item.caseId.includes(cli.only)) continue;
    const presentationPath = path.join(outputsDir, `${item.caseId}-presentation.txt`);
    if (cli.skipExisting && fs.existsSync(presentationPath) && fs.statSync(presentationPath).size > 0) {
      const metaPath = path.join(outputsDir, `${item.caseId}-meta.json`);
      if (fs.existsSync(metaPath)) {
        if (!runs.some((r) => r.case_id === item.caseId)) {
          runs.push(JSON.parse(fs.readFileSync(metaPath, 'utf8')));
        }
        console.log(`Skipping ${item.caseId} (existing)`);
        continue;
      }
    }
    console.log(`Running ${item.caseId}...`);
    try {
      const result = await runCase({
        caseId: item.caseId,
        armId: item.armId,
        roundOptions: item.roundOptions,
        scenarioKey: item.scenarioKey,
        repIndex: item.repIndex,
        evidenceRoot,
        outputsDir,
      });
      if (item.replaces_case_id) {
        result.replaces_case_id = item.replaces_case_id;
        result.replacement_reason = item.replacement_reason ?? 'generic_runtime_failure';
      }
      runs = runs.filter((r) => r.case_id !== item.caseId);
      runs.push(result);
      if (!result.hook_isolation.isolation_ok) {
        failures.push({ case_id: item.caseId, type: 'hook_isolation_failure', detail: result.hook_isolation });
      }
      console.log(JSON.stringify({
        caseId: item.caseId,
        arm: item.armId,
        wall_ms: result.operation_wall_ms,
        inferences: result.inference.inference_count,
        narrator_qa: result.inference.narrator_semantic_qa_count,
        committed: result.objective.committed,
        objective: result.objective.verdict,
      }));
    } catch (err) {
      failures.push({ case_id: item.caseId, type: 'runtime_failure', detail: String(err?.message ?? err) });
      console.error(`FAILED ${item.caseId}:`, err);
    }
  }

  runs.sort((a, b) => a.case_id.localeCompare(b.case_id));
  const scoredRuns = runs.filter((r) => {
    if (r.replaces_case_id) return true;
    if (r.objective?.verdict === 'blocking_failure') return false;
    return String(r.presentation_text ?? '').trim().length > 0;
  });
  if (scoredRuns.length < 8) {
    console.warn(`WARNING: only ${scoredRuns.length}/8 scored runs available`);
  }

  const d10Archive = analyzeD10ArchiveSupplement();
  const blind = buildBlindPacket(scoredRuns, outputsDir);
  const report = {
    schema: 'issue201_package_d_d07_execution_v1',
    generated_at: new Date().toISOString(),
    experimental_sha: head,
    design_anchor_sha: DESIGN_SHA,
    control_substrate_sha: CONTROL_SHA,
    evidence_root: evidenceRoot,
    preflight,
    topology: {
      lean_base: LEAN_BASE,
      causal_difference: 'narratorSemanticQaEnabled control=true ablated=false',
    },
    runs,
    scored_runs: scoredRuns,
    replacements: runs.filter((r) => r.replaces_case_id).map((r) => ({
      replacement_case_id: r.case_id,
      replaces_case_id: r.replaces_case_id,
      reason: r.replacement_reason,
    })),
    excluded_from_blind: runs.filter((r) => !scoredRuns.some((s) => s.case_id === r.case_id)),
    failures,
    arm_accounting: {
      control: aggregateArm(scoredRuns, 'control'),
      ablated: aggregateArm(scoredRuns, 'ablated'),
    },
    d10_archive_qa_supplement: d10Archive,
    human_blind_eval: {
      ...blind,
      status: 'prepared_for_governance_blind_scoring',
      decode_authorized: false,
    },
    synthesis_status: 'paused_pending_governance_blind_scoring',
    verdict_status: 'not_rendered',
  };
  const outPath = path.join(evidenceRoot, 'issue201-package-d-d07-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outPath, evidenceRoot, runs: runs.length, blind: blind.packetPath }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
