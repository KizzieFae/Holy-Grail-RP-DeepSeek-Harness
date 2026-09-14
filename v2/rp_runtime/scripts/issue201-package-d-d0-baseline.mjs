/**
 * Issue #201 Package D — D0 baseline characterization only (no ablations).
 * Production submitUserTurn path; post-#206 control substrate.
 *
 * Usage (from v2/rp_runtime): node scripts/issue201-package-d-d0-baseline.mjs
 */
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const CONTROL_SHA = 'c751ea666f0cae6524698005aa5859721c2e9738';

const SCENARIOS = {
  arkham_stress: {
    id: 'arkham_asylum_mess_hall_arena',
    repetitions: 2,
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
    repetitions: 2,
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
    playerPost:
      'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.',
  },
};

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
      attempt_index: corr.attempt_index ?? null,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
      finish: attempt.response?.finish?.kind ?? null,
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
  return {
    inference_count: attempts.length,
    wall_ms_total: attempts.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    total_tokens_total: attempts.reduce((s, r) => s + (r.total_tokens ?? 0), 0),
    retry_count: attempts.filter((r) => (r.attempt_index ?? 0) > 0).length,
    kinds: Object.entries(byKind).map(([kind, rows]) => ({
      inference_kind: kind,
      count: rows.length,
      wall_ms_total: rows.reduce((s, r) => s + (r.wall_ms ?? 0), 0),
      reasoning_tokens_total: rows.reduce((s, r) => s + (r.reasoning_tokens ?? 0), 0),
    })),
    attempts,
  };
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

function parseLatencySegments(latencyText) {
  if (!latencyText || typeof latencyText !== 'string') return [];
  const segments = [];
  for (const line of latencyText.split('\n')) {
    const m = line.match(/^\s*([a-z0-9_]+)\s+\|\s+(\d+)\s*ms/i)
      || line.match(/^\|\s*([^|]+)\s*\|\s*(\d+)/);
    if (m) segments.push({ segment: m[1].trim(), wall_ms: Number(m[2]) });
  }
  return segments;
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

function objectiveChecks({ history, userEntry, roundResult, presentation, sessionsDir }) {
  const issues = [];
  const userPvr = userEntry?.metadata?.perceptual_visibility ?? {};
  if (userPvr.validation_status && userPvr.validation_status !== 'valid') {
    issues.push({ type: 'pvr_validation', detail: userPvr.validation_status });
  }
  if (!roundResult?.committed) {
    issues.push({ type: 'round_not_committed', detail: roundResult?.completion_reason ?? null });
  }
  let worldStateNotes = [];
  const sessionPath = sessionsDir
    ? path.join(sessionsDir, `${history?.hg_session_id ?? ''}.json`)
    : null;
  if (sessionPath && fs.existsSync(sessionPath)) {
    try {
      const sessionJson = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
      const turnIdx = roundResult?.continuity_turn_index;
      const meta = sessionJson.turn_metadata_by_index?.[String(turnIdx)]
        ?? sessionJson.turn_metadata_by_index?.[turnIdx];
      if (meta?.narrator_environment_audit) {
        worldStateNotes.push({ type: 'narrator_environment_audit_present', keys: Object.keys(meta.narrator_environment_audit) });
      }
    } catch {
      worldStateNotes.push({ type: 'session_parse_skipped' });
    }
  }
  return {
    issue_count: issues.length,
    issues,
    committed: Boolean(roundResult?.committed),
    completion_reason: roundResult?.completion_reason ?? null,
    selected_character_id: roundResult?.selected_character_id ?? null,
    pvr_validation_status: userPvr.validation_status ?? null,
    pvr_unit_count: Array.isArray(userPvr.units) ? userPvr.units.length : null,
    presentation_length: String(presentation ?? '').length,
    world_state_observations: worldStateNotes,
  };
}

async function runD0Baseline({ caseId, scenarioKey, repIndex, evidenceRoot, outputsDir }) {
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
    const started = Date.now();
    const turn = await client.submitUserTurn({
      userMessage: scenario.playerPost,
      userName: scenario.userName,
    });
    const operationWallMs = Date.now() - started;
    const roundResult = turn.round;
    const presentation = turn.presentation ?? '';
    const api = client._domainApi();
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((e) => e.kind === 'user');
    const attempts = loadAttempts(evidenceRoot, created.hg_session_id);
    const inference = summarizeAttempts(attempts);
    const latencyText = runLatencyReconstruction(
      created.hg_session_id,
      turn.client_operation_id,
      roundResult.hg_round_id,
      roundResult.domain_commit_id,
      evidenceRoot,
    );
    const presentationPath = path.join(outputsDir, `${caseId}-presentation.txt`);
    fs.writeFileSync(presentationPath, presentation, 'utf8');
    const sessionsDir = client.supervisor.domainHost?.sessionsDir ?? path.join(REPO_ROOT, 'data', 'sessions');
    return {
      case_id: caseId,
      scenario_key: scenarioKey,
      scenario_id: scenario.id,
      repetition_index: repIndex,
      architecture: 'A4_control_full',
      hg_session_id: created.hg_session_id,
      client_operation_id: turn.client_operation_id ?? null,
      hg_round_id: roundResult.hg_round_id ?? null,
      domain_commit_id: roundResult.domain_commit_id ?? null,
      operation_wall_ms: operationWallMs,
      presentation_path: presentationPath,
      presentation_preview: String(presentation).slice(0, 800),
      objective: objectiveChecks({
        history: { ...history, hg_session_id: created.hg_session_id },
        userEntry,
        roundResult,
        presentation,
        sessionsDir,
      }),
      inference,
      latency_segments: parseLatencySegments(latencyText),
      latency_reconstruction_path: path.join(outputsDir, `${caseId}-latency.txt`),
      storyteller_round_summary: roundResult.storyteller_round_summary ?? null,
      plot_cognition_resume_summary: roundResult.plot_cognition_resume_summary ?? null,
      character_orientation_evidence: attempts.some((a) => a.inference_kind === 'character_orientation'),
    };
  } finally {
    await client.stop();
  }
}

function buildBlindEvalPacket(runs, outputsDir) {
  const samples = runs.map((run, i) => ({
    blind_label: String.fromCharCode(65 + i),
    case_id: run.case_id,
    scenario_id: run.scenario_id,
    presentation_text: fs.readFileSync(run.presentation_path, 'utf8'),
  }));
  for (let i = samples.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [samples[i], samples[j]] = [samples[j], samples[i]];
  }
  const packetPath = path.join(outputsDir, 'issue201-d0-blind-eval-packet.json');
  const keyPath = path.join(outputsDir, 'issue201-d0-blind-eval-answer-key.json');
  const packet = {
    schema: 'issue201_blind_eval_packet_v1',
    purpose: 'D0 A4 control baseline quality characterization',
    samples: samples.map(({ blind_label, presentation_text }) => ({
      blind_label,
      presentation_text,
    })),
  };
  const answerKey = samples.map(({ blind_label, case_id, scenario_id }) => ({
    blind_label,
    case_id,
    scenario_id,
  }));
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  return { packetPath, keyPath, samples };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY required');
  }
  const head = gitSha();
  if (head !== CONTROL_SHA) {
    console.warn(`WARNING: HEAD ${head} != expected control ${CONTROL_SHA}`);
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const evidenceRoot = path.join(REPO_ROOT, 'data', 'investigation_runs', `issue201-d0-baseline-${stamp}`);
  const outputsDir = path.join(evidenceRoot, 'outputs');
  fs.mkdirSync(outputsDir, { recursive: true });

  const report = {
    schema: 'issue201_package_d_d0_baseline_v1',
    generated_at: new Date().toISOString(),
    control_substrate_sha: head,
    expected_control_sha: CONTROL_SHA,
    blocker_206_resolved: head === CONTROL_SHA,
    evidence_root: evidenceRoot,
    runs: [],
  };

  for (const [scenarioKey, scenario] of Object.entries(SCENARIOS)) {
    for (let rep = 1; rep <= scenario.repetitions; rep += 1) {
      const caseId = `D0-${scenarioKey}-r${rep}`;
      console.log(`Running ${caseId}...`);
      const result = await runD0Baseline({ caseId, scenarioKey, repIndex: rep, evidenceRoot, outputsDir });
      if (result.latency_reconstruction_path) {
        const lat = runLatencyReconstruction(
          result.hg_session_id,
          result.client_operation_id,
          result.hg_round_id,
          result.domain_commit_id,
          evidenceRoot,
        );
        if (typeof lat === 'string') {
          fs.writeFileSync(result.latency_reconstruction_path, lat, 'utf8');
        }
      }
      report.runs.push(result);
      console.log(JSON.stringify({
        caseId,
        wall_ms: result.operation_wall_ms,
        inferences: result.inference.inference_count,
        committed: result.objective.committed,
      }));
    }
  }

  const blind = buildBlindEvalPacket(report.runs, outputsDir);
  report.blind_eval = { packet_path: blind.packetPath, answer_key_path: blind.keyPath };

  const outPath = path.join(evidenceRoot, 'issue201-d0-baseline-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outPath, evidenceRoot, runs: report.runs.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
