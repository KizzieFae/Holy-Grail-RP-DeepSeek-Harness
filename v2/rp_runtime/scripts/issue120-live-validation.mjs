/**
 * Bounded live validation for Issue #120 — seiza/Japan generalized internal regression.
 * Run from v2/rp_runtime: node scripts/issue120-live-validation.mjs
 *
 * Entrypoint: direct runPlayerDecompositionPhase (matches #112 repeatability harness).
 * Profile: deepseekInferenceProfile({ reasoningEffort: 'low' }) — no maxTokens override.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { parsePlayerDecompositionEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const SEIZA_JAPAN_TURN =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you '
  + 'realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

const JAPAN_TOKEN = 'they were not in Japan, but hold habits died hard.';
const CAST = ['Ayame', 'Kizzie', 'Harley', 'Celina'];
const MODEL_PROFILE = deepseekInferenceProfile({ reasoningEffort: 'low' });

function loadAttempt(evidenceRoot, sessionId, attemptId) {
  const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
  return JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
}

function summarizeAttempt(attempt) {
  const usage = attempt.response?.usage ?? {};
  return {
    evidence_id: attempt.evidence_id,
    provider: attempt.request?.provider ?? attempt.response?.provider ?? null,
    model: attempt.request?.model ?? attempt.response?.model ?? null,
    reasoning_effort: attempt.request?.reasoning_effort ?? null,
    thinking: attempt.request?.thinking ?? null,
    max_tokens: attempt.request?.max_tokens ?? null,
    wall_ms: attempt.timing?.wall_ms ?? attempt.timing?.duration_ms ?? null,
    input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
    output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
    reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
    total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
    finish: attempt.response?.finish?.kind ?? null,
    reasoning_trace: attempt.response?.reasoning_text ?? attempt.response?.reasoning ?? null,
  };
}

function analyzeSemantics(units) {
  const japanUnit = (units ?? []).find((unit) => String(unit.text ?? '').includes('not in Japan'));
  return {
    unit_count: Array.isArray(units) ? units.length : 0,
    units: (units ?? []).map((unit) => ({
      unit_id: unit.unit_id,
      kind: unit.kind,
      scope: unit.recipients?.scope ?? null,
      text_preview: String(unit.text ?? '').slice(0, 120),
    })),
    japan_unit: japanUnit
      ? {
        unit_id: japanUnit.unit_id,
        kind: japanUnit.kind,
        scope: japanUnit.recipients?.scope ?? null,
        text: japanUnit.text,
      }
      : null,
    japan_is_internal: japanUnit?.kind === 'internal',
    has_observable_seiza: (units ?? []).some(
      (unit) => unit.kind === 'observable_event' && /seiza|sieza|cushion/i.test(unit.text ?? ''),
    ),
    speech_units: (units ?? []).filter((unit) => unit.kind === 'speech').length,
  };
}

async function projectForAyame(api, sessionId, content, decomposition) {
  const entry = await api.recordUserTurn({
    hg_session_id: sessionId,
    content,
    speaker: 'Kizzie',
    player_decomposition: decomposition,
  });
  const metadata = entry.metadata ?? {};
  const pvr = metadata.perceptual_visibility ?? {};
  const audit = metadata.perceptual_visibility_validation ?? metadata.validation_audit ?? {};
  const projection = metadata.perceptual_visibility_projection ?? {};
  return {
    validation_accepted: Boolean(audit.accepted),
    validation_status: pvr.validation_status ?? null,
    failure_class: pvr.recovery?.failure_class ?? null,
    ayame_projection: projection,
    units: pvr.units ?? [],
  };
}

async function runLiveCall({ api, phaseExecutors, evidenceRoot, callIndex }) {
  const sessionId = `issue120-live-seiza-japan-${callIndex}`;
  await api.createSession({ cast: CAST, hg_session_id: sessionId });
  const inferenceId = `player-decomposition-issue120-${callIndex}`;
  const started = Date.now();
  const phaseResult = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: `issue120-live-round-${callIndex}`,
    inferenceId,
    playerContent: SEIZA_JAPAN_TURN,
    modelProfile: MODEL_PROFILE,
  });
  const wallMs = Date.now() - started;

  const decomposition = phaseResult.playerDecomposition ?? {};
  const parsed = decomposition.failure_class
    ? { parseError: decomposition.failure_class }
    : parsePlayerDecompositionEnvelope(JSON.stringify({
      perceptual_visibility: decomposition.perceptual_visibility,
      source_accounting: decomposition.source_accounting,
    }));

  const units = decomposition.perceptual_visibility?.units ?? [];
  const domain = await projectForAyame(api, sessionId, SEIZA_JAPAN_TURN, decomposition);

  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  let attemptSummary = null;
  if (fs.existsSync(indexPath)) {
    const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
    const attemptId = (index.attempt_ids ?? []).at(-1);
    if (attemptId) {
      const attempt = loadAttempt(evidenceRoot, sessionId, attemptId);
      attemptSummary = summarizeAttempt(attempt);
      if (!attemptSummary.wall_ms) attemptSummary.wall_ms = wallMs;
    }
  }

  const semantics = analyzeSemantics(units);
  const excluded = domain.ayame_projection?.excluded_unit_ids ?? [];
  const japanExcluded = semantics.japan_unit
    ? excluded.includes(semantics.japan_unit.unit_id)
    : null;

  return {
    call_index: callIndex,
    entrypoint: 'runPlayerDecompositionPhase',
    harness: 'issue120-live-validation.mjs',
    model_profile: MODEL_PROFILE,
    phase_failure_class: decomposition.failure_class ?? null,
    parse_ok: !parsed.parseError,
    raw_decomposition: decomposition,
    attempt: attemptSummary,
    semantics,
    contract: {
      validation_accepted: domain.validation_accepted,
      validation_status: domain.validation_status,
      failure_class: domain.failure_class,
    },
    projection: {
      japan_excluded_from_ayame: japanExcluded,
      japan_token_in_ayame_content: String(domain.ayame_projection?.content ?? '').includes(JAPAN_TOKEN),
      exclusion_reasons: domain.ayame_projection?.exclusion_reasons ?? {},
    },
    semantic_pass:
      semantics.japan_is_internal
      && semantics.has_observable_seiza
      && semantics.speech_units >= 2
      && japanExcluded === true,
    contract_pass: domain.validation_accepted === true,
  };
}

async function main() {
  const allowSecond = process.argv.includes('--second-call');
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue120-live-evidence-'));
  const port = 29820 + Math.floor(Math.random() * 100);
  const host = await startDomainApi(port, { withSession: true });
  const baseUrl = host.baseUrl;
  const api = createDomainApiClient(baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
      defaultProfile: MODEL_PROFILE,
    },
  });

  const report = { calls: [] };
  try {
    const first = await runLiveCall({ api, phaseExecutors, evidenceRoot, callIndex: 1 });
    report.calls.push(first);
    const needsSecond = allowSecond
      || (!first.semantic_pass && first.parse_ok)
      || (first.semantic_pass && !first.contract_pass);
    if (needsSecond && report.calls.length < 2) {
      const second = await runLiveCall({ api, phaseExecutors, evidenceRoot, callIndex: 2 });
      report.calls.push(second);
    }
  } finally {
    await ctx.fiber.dispose();
    await host.stop();
  }

  report.evidence_root = evidenceRoot;
  const reportPath = path.join(evidenceRoot, 'issue120-live-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ evidenceRoot, reportPath, report }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
