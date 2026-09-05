/**
 * Bounded live validation for Issue #124 — semantic-only PVR with uncapped tokens.
 * Run from v2/rp_runtime: node scripts/issue124-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { modelProfileForInferenceKind } from '../src/application/application-settings.mjs';
import { parseSemanticDecompositionEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const CAST = ['Ayame', 'Kizzie', 'Harley', 'Celina'];

const ORDINARY_PUBLIC = '"Good evening," she said with a small bow.';

const MIXED_ASYMMETRIC =
  'The player walks away from Harley toward the storeroom archway.'
  + ' Behind the closed door, the player works a concealed floor-panel latch with a tension-wrench rake technique.'
  + " The player steps back into Harley's view, brushing dust from their hands."
  + ' "Panel secured—the seam is hidden," the player says to the group.';

const COMPLEX_DENSE_SEIZA_JAPAN =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

const CASES = [
  {
    case_id: 'ordinary_public',
    description: 'straightforward ordinary public speech (issue109 public_speech)',
    content: ORDINARY_PUBLIC,
  },
  {
    case_id: 'mixed_asymmetric',
    description: 'mixed public/private perceptually asymmetric (#88-shaped mixed turn)',
    content: MIXED_ASYMMETRIC,
  },
  {
    case_id: 'complex_dense_seiza_japan',
    description: 'dense multi-span action+speech seiza/Japan (#120 regression input)',
    content: COMPLEX_DENSE_SEIZA_JAPAN,
  },
];

const MODEL_PROFILE = modelProfileForInferenceKind(
  deepseekInferenceProfile({ reasoningEffort: 'low' }),
  'player_decomposition',
  {},
  {},
);

function loadAttempt(evidenceRoot, sessionId, attemptId) {
  const attemptPath = path.join(evidenceRoot, sessionId, 'attempts', `${attemptId}.json`);
  return JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
}

function summarizeTokens(usage = {}) {
  return {
    input_tokens: usage.inputTokens ?? usage.input_tokens ?? null,
    output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
    reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
    total_tokens: usage.totalTokens ?? usage.total_tokens ?? null,
  };
}

function summarizeAttempt(attempt) {
  const usage = attempt.response?.usage ?? {};
  return {
    evidence_id: attempt.evidence_id,
    attempt_index: attempt.correlation?.attempt_index ?? null,
    prior_attempt_id: attempt.correlation?.prior_attempt_id ?? null,
    provider: attempt.request?.provider ?? attempt.response?.provider ?? null,
    model: attempt.request?.model ?? attempt.response?.model ?? null,
    reasoning_effort: attempt.request?.reasoning_effort ?? null,
    max_tokens: attempt.request?.max_tokens ?? null,
    wall_ms: attempt.timing?.wall_ms ?? attempt.timing?.duration_ms ?? null,
    ...summarizeTokens(usage),
    finish: attempt.response?.finish?.kind ?? null,
    failed: Boolean(attempt.response?.failed),
    assistant_prefix: String(attempt.response?.assistant_text ?? '').trim().slice(0, 120),
  };
}

function loadSessionAttempts(evidenceRoot, sessionId) {
  const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((attemptId) =>
    summarizeAttempt(loadAttempt(evidenceRoot, sessionId, attemptId)),
  );
}

async function validateWithDomain(api, sessionId, content, decomposition) {
  const entry = await api.recordUserTurn({
    hg_session_id: sessionId,
    content,
    speaker: 'Kizzie',
    player_decomposition: decomposition,
  });
  const metadata = entry.metadata ?? {};
  const pvr = metadata.perceptual_visibility ?? {};
  const audit = metadata.perceptual_visibility_validation ?? metadata.validation_audit ?? {};
  return {
    validation_status: pvr.validation_status ?? null,
    accepted: Boolean(audit.accepted),
    failure_class: pvr.recovery?.failure_class ?? null,
    unit_count: Array.isArray(pvr.units) ? pvr.units.length : 0,
  };
}

function semanticUnitsSummary(decomposition) {
  const units = decomposition.perceptual_visibility?.units ?? [];
  return units.map((unit) => ({
    unit_id: unit.unit_id ?? null,
    kind: unit.kind ?? null,
    scope: unit.recipients?.scope ?? null,
    characters: unit.recipients?.characters ?? [],
    text_len: (unit.text ?? '').length,
    text_preview: String(unit.text ?? '').slice(0, 80),
    order_index: unit.source_provenance?.order_index ?? null,
  }));
}

async function runCase({
  api,
  runEphemeralInference,
  evidenceRoot,
  caseDef,
}) {
  const sessionId = `issue124-live-${caseDef.case_id}`;
  await api.createSession({ cast: CAST, hg_session_id: sessionId });
  const inferenceId = `issue124-pd-${caseDef.case_id}`;
  const started = Date.now();
  const phaseResult = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: sessionId,
    hgSceneId: sessionId,
    hgRoundId: `issue124-live-round-${caseDef.case_id}`,
    inferenceId,
    playerContent: caseDef.content,
    modelProfile: MODEL_PROFILE,
  });
  const wallMs = Date.now() - started;
  const decomposition = phaseResult.playerDecomposition ?? {};
  const accepted = Boolean(
    decomposition.perceptual_visibility?.units?.length
    && !decomposition.failure_class,
  );
  const parsed = decomposition.failure_class
    ? { parseError: decomposition.failure_class }
    : parseSemanticDecompositionEnvelope(JSON.stringify({
      semantic_decomposition: decomposition.generation?.semantic_decomposition ?? null,
    }));
  const attempts = loadSessionAttempts(evidenceRoot, sessionId);
  if (attempts.length === 1 && !attempts[0].wall_ms) {
    attempts[0].wall_ms = wallMs;
  }

  let domainValidation = null;
  if (accepted) {
    domainValidation = await validateWithDomain(api, sessionId, caseDef.content, decomposition);
  }

  const generation = decomposition.generation ?? {};
  const normalizationAudit =
    phaseResult.normalizationAudit ?? generation.normalization ?? null;

  return {
    case_id: caseDef.case_id,
    description: caseDef.description,
    input_chars: caseDef.content.length,
    inference_id: inferenceId,
    wall_clock_ms: wallMs,
    max_tokens: MODEL_PROFILE.maxTokens ?? null,
    attempt_count: (generation.attempt_index ?? attempts.length - 1) + 1 || attempts.length,
    retry_used: attempts.length > 1,
    phase_failure_class: decomposition.failure_class ?? null,
    normalization_accepted: accepted,
    parse_ok: !parsed.parseError,
    unit_count: decomposition.perceptual_visibility?.units?.length ?? 0,
    units: semanticUnitsSummary(decomposition),
    normalization_audit: normalizationAudit,
    generation: {
      inference_id: generation.inference_id ?? null,
      attempt_index: generation.attempt_index ?? null,
      normalization_stage: generation.normalization_stage ?? null,
      has_raw_semantic_output: Boolean(generation.raw_semantic_output),
      has_semantic_decomposition: Boolean(generation.semantic_decomposition),
    },
    domain_validation: domainValidation,
    attempts,
    tokens_aggregate: attempts.reduce(
      (acc, attempt) => ({
        input_tokens: (acc.input_tokens ?? 0) + (attempt.input_tokens ?? 0),
        output_tokens: (acc.output_tokens ?? 0) + (attempt.output_tokens ?? 0),
        reasoning_tokens: (acc.reasoning_tokens ?? 0) + (attempt.reasoning_tokens ?? 0),
        total_tokens: (acc.total_tokens ?? 0) + (attempt.total_tokens ?? 0),
      }),
      {},
    ),
    evidence_id: phaseResult.evidenceId ?? null,
  };
}

async function main() {
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue124-live-'));
  const port = 29830 + Math.floor(Math.random() * 100);
  const domainApi = await startDomainApi(port, { withSession: true });
  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: domainApi.baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
      defaultProfile: MODEL_PROFILE,
    },
  });

  const api = createDomainApiClient(domainApi.baseUrl);
  const report = {
    experiment: 'issue124_live_semantic_validation',
    generated_at: new Date().toISOString(),
    validation_anchor: '0d2b3124e769f9a150fe1d6637e3413120c59be2',
    model_profile: MODEL_PROFILE,
    max_tokens_policy: 'uncapped',
    evidence_root: evidenceRoot,
    cases: [],
  };

  for (const caseDef of CASES) {
    const caseReport = await runCase({
      api,
      runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      evidenceRoot,
      caseDef,
    });
    report.cases.push(caseReport);
    console.log(JSON.stringify({ case_id: caseDef.case_id, ...caseReport }, null, 2));
  }

  const fixturePath = path.join('tests', 'fixtures', 'issue124-live-validation-report.json');
  fs.writeFileSync(fixturePath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`\nWrote ${fixturePath}`);
  await domainApi.close?.();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
