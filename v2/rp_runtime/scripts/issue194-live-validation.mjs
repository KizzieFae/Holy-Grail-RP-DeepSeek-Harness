/**
 * Formal validation live slice for Issue #194 — F06 efficiency interventions.
 * Run from v2/rp_runtime: node scripts/issue194-live-validation.mjs
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { modelProfileForInferenceKind, resolveApplicationRoleProfiles } from '../src/application/application-settings.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';
import { parseSemanticDecompositionEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

const F06_KNOCK_POST =
  'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.';

const COMPLEX_DENSE_SEIZA_JAPAN =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function loadAttempt(evidenceRoot, sessionId, attemptId) {
  const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
  return JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
}

function loadSessionAttempts(evidenceRoot, sessionId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((attemptId) => {
    const attempt = loadAttempt(evidenceRoot, sessionId, attemptId);
    const usage = attempt.response?.usage ?? {};
    const timing = attempt.inference_health?.timing ?? attempt.timing ?? {};
    const corr = attempt.correlation ?? {};
    return {
      evidence_id: attempt.evidence_id ?? attemptId,
      inference_kind: corr.inference_kind ?? null,
      role: corr.role ?? null,
      attempt_index: corr.attempt_index ?? null,
      inference_id: corr.inference_id ?? null,
      operation_id: corr.operation_id ?? null,
      hg_round_id: corr.hg_round_id ?? null,
      reasoning_effort: attempt.request?.reasoning_effort ?? null,
      effective_thinking: attempt.request?.effective_thinking ?? null,
      max_tokens: attempt.request?.max_tokens ?? null,
      wall_ms: timing.inference_wall_clock_ms ?? timing.wall_ms ?? timing.duration_ms ?? null,
      input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
      output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
      reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
      total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
      finish: attempt.response?.finish?.kind ?? null,
      assistant_prefix: String(attempt.response?.assistant_text ?? '').trim().slice(0, 160),
    };
  });
}

function filterAttempts(attempts, inferenceKind) {
  return attempts.filter((attempt) => attempt.inference_kind === inferenceKind);
}

function aggregateAttempts(attempts) {
  return {
    count: attempts.length,
    wall_ms_total: attempts.reduce((sum, item) => sum + (item.wall_ms ?? 0), 0),
    reasoning_tokens_total: attempts.reduce((sum, item) => sum + (item.reasoning_tokens ?? 0), 0),
    output_tokens_total: attempts.reduce((sum, item) => sum + (item.output_tokens ?? 0), 0),
    total_tokens_total: attempts.reduce((sum, item) => sum + (item.total_tokens ?? 0), 0),
    attempts,
  };
}

function summarizePvr(entry) {
  const pvr = entry?.metadata?.perceptual_visibility ?? {};
  const audit = entry?.metadata?.perceptual_visibility_validation
    ?? entry?.metadata?.validation_audit
    ?? {};
  const units = Array.isArray(pvr.units) ? pvr.units : [];
  return {
    validation_status: pvr.validation_status ?? null,
    accepted: Boolean(audit.accepted ?? pvr.validation_status === 'valid'),
    failure_class: pvr.recovery?.failure_class ?? null,
    semantic_decomposition: pvr.semantic_decomposition ?? null,
    unit_count: units.length,
    units: units.map((unit) => ({
      kind: unit.kind,
      scope: unit.recipients?.scope ?? null,
      text_preview: String(unit.text ?? '').slice(0, 100),
    })),
    normalization: pvr.normalization ?? entry?.metadata?.normalization_audit ?? null,
  };
}

function summarizeEnvAudit(audit) {
  if (!audit || typeof audit !== 'object') return null;
  const n1 = audit.n1 ?? {};
  const obligations = audit.environmental_response_obligations ?? [];
  return {
    cognition_status: audit.cognition_status ?? null,
    baseline_sufficient: n1.baseline_sufficient ?? audit.baseline_sufficient ?? null,
    need_count: Array.isArray(n1.information_needs) ? n1.information_needs.length : null,
    obligation_count: obligations.length,
    obligations: obligations.map((item) => ({
      render_behavior: item.render_behavior ?? null,
      resolution_category: item.resolution_category ?? null,
      property_key: item.property_key ?? null,
      value_preview: String(item.grounded_material?.[0] ?? item.rendering_question ?? '').slice(0, 80),
    })),
  };
}

async function runF06LiveTurn({ evidenceRoot }) {
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
    const openers = await client.listTemplateOpeners('ayame_household_entry_evaluation');
    const created = await client.createSession({
      characters: ['ayame', 'kizzie'],
      sceneTemplateId: 'ayame_household_entry_evaluation',
      roleAssignments: { ayame: 'host', kizzie: 'applicant' },
      opening: { mode: 'template', opener_id: openers[0].opener_id },
    });

    const operationStarted = Date.now();
    const turn = await client.submitUserTurn({
      userMessage: F06_KNOCK_POST,
      userName: 'Kizzie',
    });
    const operationWallMs = Date.now() - operationStarted;

    const api = createDomainApiClient(client.supervisor.domainHostUrl);
    const history = await api.getSessionHistory(created.hg_session_id);
    const userEntry = [...history.entries].reverse().find((entry) => entry.kind === 'user');
    const turnMeta = await api.getTurnMetadata?.(created.hg_session_id, turn.round.continuity_turn_index)
      .catch(() => null);
    const sessionFile = path.join(
      client.supervisor.domainHost?.sessionsDir ?? path.join(REPO_ROOT, 'data', 'sessions'),
      `${created.hg_session_id}.json`,
    );
    let narratorEnvAudit = null;
    if (fs.existsSync(sessionFile)) {
      const sessionJson = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
      const meta = sessionJson.turn_metadata_by_index?.[String(turn.round.continuity_turn_index)]
        ?? sessionJson.turn_metadata_by_index?.[turn.round.continuity_turn_index];
      narratorEnvAudit = meta?.narrator_environment_audit ?? null;
    }

    const attempts = loadSessionAttempts(evidenceRoot, created.hg_session_id);
    const decomposition = aggregateAttempts(filterAttempts(attempts, 'player_decomposition'));
    const triage = aggregateAttempts(filterAttempts(attempts, 'player_visibility_triage'));
    const envCog = aggregateAttempts(filterAttempts(attempts, 'narrator_environment_cognition'));

    const profiles = resolveApplicationRoleProfiles({
      inferenceMode: 'live',
      roleRouting: 'simple',
      model: HG_DEEPSEEK_DEFAULT_MODEL,
    });

    return {
      scenario_id: 'ayame_household_entry_evaluation',
      hg_session_id: created.hg_session_id,
      client_operation_id: turn.client_operation_id ?? null,
      hg_round_id: turn.round.hg_round_id ?? null,
      domain_commit_id: turn.round.domain_commit_id ?? null,
      continuity_turn_index: turn.round.continuity_turn_index ?? null,
      operation_wall_ms_observed: operationWallMs,
      presentation_preview: String(turn.presentation ?? '').slice(0, 500),
      transcript_preview: turn.transcript?.map((entry) => ({
        role: entry.role ?? entry.speaker ?? null,
        preview: String(entry.content ?? '').slice(0, 200),
      })) ?? [],
      pvr: summarizePvr(userEntry),
      narrator_environment_audit: summarizeEnvAudit(narratorEnvAudit),
      triage,
      decomposition,
      environmental_cognition: {
        ...envCog,
        inferred_profile: envCog.attempts[0]?.reasoning_effort === 'off' ? 'constrained' : 'deep',
        escalation_observed: envCog.attempts.some((item) => String(item.inference_id ?? '').includes('deep-escalation')),
        cognition_call_count: envCog.count,
      },
      role_profiles: {
        narrator: profiles.narrator,
        character: profiles.character,
        director: profiles.director,
      },
    };
  } finally {
    await client.stop();
  }
}

async function runComplexDecomposition({ evidenceRoot, api, runEphemeralInference }) {
  const sessionId = `issue194-complex-dense-${Date.now()}`;
  await api.createSession({ cast: ['Ayame', 'Kizzie', 'Harley', 'Celina'], hg_session_id: sessionId });
  const modelProfile = modelProfileForInferenceKind(
    resolveApplicationRoleProfiles({ inferenceMode: 'live', roleRouting: 'simple' }).character,
    'player_decomposition',
    {},
    { inferenceMode: 'live' },
  );
  const inferenceId = `issue194-pd-complex_dense_seiza_japan`;
  const phaseResult = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: `issue194-round-complex`,
    inferenceId,
    playerContent: COMPLEX_DENSE_SEIZA_JAPAN,
    modelProfile,
  });
  const decomposition = phaseResult.playerDecomposition ?? {};
  const attempts = loadSessionAttempts(evidenceRoot, sessionId);
  const parsed = decomposition.failure_class
    ? { parseError: decomposition.failure_class }
    : parseSemanticDecompositionEnvelope(JSON.stringify({
      semantic_decomposition: decomposition.generation?.semantic_decomposition ?? null,
    }));
  const units = decomposition.perceptual_visibility?.units ?? [];
  const kinds = new Set(units.map((unit) => unit.kind));
  return {
    case_id: 'complex_dense_seiza_japan',
    equivalent_to: '#112 complex_dense_repeat_1 (issue124 authoritative corpus)',
    attempt_count: attempts.filter((item) => item.inference_kind === 'player_decomposition').length,
    retry_used: attempts.filter((item) => item.inference_kind === 'player_decomposition').length > 1,
    accepted: Boolean(units.length && !decomposition.failure_class),
    unit_count: units.length,
    kinds: [...kinds],
    units: units.map((unit) => ({
      kind: unit.kind,
      scope: unit.recipients?.scope ?? null,
      text_preview: String(unit.text ?? '').slice(0, 90),
    })),
    parse_ok: !parsed.parseError,
    normalization_audit: phaseResult.normalizationAudit ?? null,
    attempts: attempts.filter((item) => item.inference_kind === 'player_decomposition'),
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
      { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 },
    );
    return out;
  } catch (err) {
    return { error: String(err.stderr ?? err.message ?? err) };
  }
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY required for Issue #194 live validation');
  }

  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue194-live-evidence-'));
  const candidateSha = gitSha();
  const report = {
    experiment: 'issue194_formal_validation_live',
    generated_at: new Date().toISOString(),
    candidate_sha: candidateSha,
    evidence_root: evidenceRoot,
    f06_baseline_reference: {
      session_id: 'hg-session-f06d7b72-1f3f-47d6-8ab9-c9a6ddd72a40',
      decomposition_attempts: 2,
      decomposition_wall_ms_approx: 41500,
      decomposition_reasoning_tokens_approx: 8555,
      environmental_cognition_wall_ms_approx: 55728,
      environmental_cognition_reasoning_tokens_approx: 11454,
      player_visible_latency_ms_approx: 224289,
    },
  };

  console.log('Running F06 live turn...');
  report.f06_live = await runF06LiveTurn({ evidenceRoot });
  report.latency_reconstruction = runLatencyReconstruction(
    report.f06_live.hg_session_id,
    report.f06_live.client_operation_id,
    report.f06_live.hg_round_id,
    report.f06_live.domain_commit_id,
    evidenceRoot,
  );

  const port = 29940 + Math.floor(Math.random() * 100);
  const domainApi = await startDomainApi(port, { withSession: true });
  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: domainApi.baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
    },
  });
  const api = createDomainApiClient(domainApi.baseUrl);
  console.log('Running complex decomposition guard...');
  report.complex_decomposition = await runComplexDecomposition({
    evidenceRoot,
    api,
    runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
  });
  await domainApi.close?.();

  const outPath = path.join(REPO_ROOT, 'governance', 'records', 'issue-194-live-validation-2026-09-14.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ outPath, candidateSha, f06: report.f06_live, complex: report.complex_decomposition }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
