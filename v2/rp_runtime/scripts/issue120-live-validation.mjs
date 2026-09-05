/**
 * Bounded live validation for Issue #120 — seiza/Japan generalized internal regression.
 * Run from v2/rp_runtime: node scripts/issue120-live-validation.mjs
 *
 * Replay captured evidence (no paid inference):
 *   node scripts/issue120-live-validation.mjs --replay tests/fixtures/issue120-live-call-1-decomposition.json
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
import {
  analyzeSemantics,
  buildSemanticPass,
  evaluateAyameProjection,
  JAPAN_TOKEN,
  projectPlayerUserTurnForAyame,
  readProjectionFromRecordUserTurnMetadata,
} from './lib/issue120-projection.mjs';

const SEIZA_JAPAN_TURN =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you '
  + 'realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

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

function parseReplayArg(argv) {
  const index = argv.indexOf('--replay');
  if (index === -1) return null;
  const replayPath = argv[index + 1];
  if (!replayPath) {
    throw new Error('--replay requires a path to captured evidence JSON');
  }
  return path.resolve(replayPath);
}

async function buildCallReport({
  api,
  callIndex,
  content,
  decomposition,
  evidenceRoot = null,
  sessionId = null,
  attemptSummary = null,
  entrypoint = 'runPlayerDecompositionPhase',
}) {
  const resolvedSessionId = sessionId ?? `issue120-live-seiza-japan-${callIndex}`;
  const parsed = decomposition.failure_class
    ? { parseError: decomposition.failure_class }
    : parsePlayerDecompositionEnvelope(JSON.stringify({
      perceptual_visibility: decomposition.perceptual_visibility,
      source_accounting: decomposition.source_accounting,
    }));

  const units = decomposition.perceptual_visibility?.units ?? [];
  const domain = await projectPlayerUserTurnForAyame({
    api,
    sessionId: resolvedSessionId,
    content,
    decomposition,
    presentCharacters: CAST,
  });
  const semantics = analyzeSemantics(units);
  const projection = evaluateAyameProjection({
    semantics,
    assembly: domain.assembly,
  });
  const legacyProjection = readProjectionFromRecordUserTurnMetadata(domain.entry);
  const legacyJapanExcluded = semantics.japan_unit
    ? (legacyProjection.excluded_unit_ids ?? []).includes(semantics.japan_unit.unit_id)
    : null;

  return {
    call_index: callIndex,
    entrypoint,
    harness: 'issue120-live-validation.mjs',
    model_profile: entrypoint === 'replay' ? null : MODEL_PROFILE,
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
    projection,
    projection_path: 'assemble_player_user_entry_for_viewer',
    legacy_projection_bug: {
      japan_excluded_from_ayame: legacyJapanExcluded,
      metadata_projection_present: Object.keys(legacyProjection).length > 0,
    },
    semantic_pass: buildSemanticPass({ semantics, projection }),
    contract_pass: domain.validation_accepted === true,
    evidence_root: evidenceRoot,
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

  return buildCallReport({
    api,
    callIndex,
    content: SEIZA_JAPAN_TURN,
    decomposition,
    evidenceRoot,
    sessionId,
    attemptSummary,
  });
}

async function replayCapturedCall({ api, replayPath, callIndex = 1 }) {
  const fixture = JSON.parse(fs.readFileSync(replayPath, 'utf8'));
  const content = fixture.player_text ?? SEIZA_JAPAN_TURN;
  const decomposition = fixture.raw_decomposition;
  const sessionId = `issue120-replay-${callIndex}`;
  await api.createSession({ cast: CAST, hg_session_id: sessionId });
  return buildCallReport({
    api,
    callIndex,
    content,
    decomposition,
    sessionId,
    entrypoint: 'replay',
  });
}

async function main() {
  const replayPath = parseReplayArg(process.argv);
  const allowSecond = process.argv.includes('--second-call');
  const evidenceRoot = replayPath ? null : fs.mkdtempSync(path.join(os.tmpdir(), 'issue120-live-evidence-'));
  const port = 29820 + Math.floor(Math.random() * 100);
  const host = await startDomainApi(port, { withSession: true });
  const baseUrl = host.baseUrl;
  const api = createDomainApiClient(baseUrl);
  const { ctx, phaseExecutors } = replayPath
    ? { ctx: { fiber: { dispose: async () => {} } }, phaseExecutors: null }
    : await createHolyGrailRpContext({
      domainApi: { baseUrl },
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
        defaultProfile: MODEL_PROFILE,
      },
    });

  const report = {
    mode: replayPath ? 'replay' : 'live',
    replay_source: replayPath,
    calls: [],
  };
  try {
    if (replayPath) {
      report.calls.push(await replayCapturedCall({ api, replayPath, callIndex: 1 }));
    } else {
      const first = await runLiveCall({ api, phaseExecutors, evidenceRoot, callIndex: 1 });
      report.calls.push(first);
      const needsSecond = allowSecond
        || (!first.semantic_pass && first.parse_ok)
        || (first.semantic_pass && !first.contract_pass);
      if (needsSecond && report.calls.length < 2) {
        const second = await runLiveCall({ api, phaseExecutors, evidenceRoot, callIndex: 2 });
        report.calls.push(second);
      }
    }
  } finally {
    await ctx.fiber.dispose();
    await host.stop();
  }

  if (evidenceRoot) {
    report.evidence_root = evidenceRoot;
  }
  const reportPath = evidenceRoot
    ? path.join(evidenceRoot, 'issue120-live-report.json')
    : path.join(path.dirname(replayPath ?? '.'), 'issue120-replay-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ evidenceRoot, reportPath, report }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
