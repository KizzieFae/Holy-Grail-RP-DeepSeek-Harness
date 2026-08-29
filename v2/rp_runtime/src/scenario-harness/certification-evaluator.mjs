import crypto from 'node:crypto';

import { parseJsonObject } from '../lib/inference-utils.mjs';
import { SEMANTIC_RUBRIC_VERSION } from './semantic-characterization.mjs';

export const CERTIFICATION_EVAL_SCHEMA = 'hg_storyteller_certification_eval_v1';

function buildEvaluatorPrompt({
  truth,
  outputText,
  evaluationSubject = null,
  evaluationTarget,
  scenarioId,
}) {
  const subjectText = evaluationSubject != null
    ? JSON.stringify(evaluationSubject, null, 2)
    : String(outputText ?? '');
  return [
    'You are a read-only Storyteller certification evaluator.',
    'Judge ONLY the supplied certification subject against authoritative fixture truth.',
    'When production_outcome is withheld, evaluate whether withholding was appropriate for the candidate and verdict shown.',
    'Do NOT assume hidden facts are forbidden in source cognition; judge final Character-facing epistemic envelope.',
    'Return ONLY one JSON object.',
    '',
    `schema: ${CERTIFICATION_EVAL_SCHEMA}`,
    `scenario_id: ${scenarioId}`,
    `evaluation_target: ${evaluationTarget}`,
    '',
    'Required JSON shape:',
    '{',
    `  "schema": "${CERTIFICATION_EVAL_SCHEMA}",`,
    '  "scenario_id": "<id>",',
    '  "evaluation_target": "<role>",',
    '  "dimensions": { "<domain>": { "<dimension>": "<level>", "notes": "..." } },',
    '  "categorical_findings": ["useful", "vague", "over_directive", "unnecessary_replan", "excessive_withholding", "epistemic_leak_candidate"],',
    '  "governance_flags": ["manual_review_recommended"],',
    '  "summary": "one paragraph"',
    '}',
    '',
    'Authoritative fixture truth JSON:',
    JSON.stringify(truth, null, 2),
    '',
    'Certification subject to evaluate:',
    subjectText,
  ].join('\n');
}

export function parseCertificationEvalResult(raw) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error), result: null };
  }
  if (parsed?.schema !== CERTIFICATION_EVAL_SCHEMA) {
    return { ok: false, error: 'invalid_schema', result: null };
  }
  return {
    ok: true,
    error: null,
    result: {
      ...parsed,
      rubric_version: SEMANTIC_RUBRIC_VERSION,
    },
  };
}

/**
 * Read-only certification evaluator. Does not mutate Domain/runtime state.
 */
export async function runCertificationEvaluator({
  runEphemeralInference,
  truth,
  outputText = '',
  evaluationSubject = null,
  evaluationTarget = 'storyteller',
  scenarioId,
  modelProfile = null,
  mockResponse = null,
  evidenceContextBase = {},
}) {
  const evaluationPassId = `cert-eval-${crypto.randomUUID()}`;
  const prompt = buildEvaluatorPrompt({
    truth,
    outputText,
    evaluationSubject,
    evaluationTarget,
    scenarioId,
  });
  const inferRun = await runEphemeralInference({
    inferenceId: `inf-cert-eval-${scenarioId}-${evaluationPassId}`,
    prompt,
    manifest: {
      contributions: [{
        contribution_id: `cert-truth-${truth.fixture_id}`,
        source_kind: 'certification_truth',
        authority_class: 'fixture',
        priority: 1,
        content: JSON.stringify(truth),
        knowledge_ids: [`fixture:${truth.fixture_id}`],
        provenance: { read_only: true },
      }],
    },
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      role: 'certification_evaluator',
      inferenceKind: 'storyteller_certification_eval',
      evaluationPassId,
      inferenceId: `cert-${scenarioId}`,
    },
  });

  if (inferRun.failed) {
    return {
      ok: false,
      stage: 'inference',
      error: inferRun.failure ?? 'inference_failed',
      evidenceId: inferRun.evidenceId ?? null,
      raw: inferRun.raw ?? null,
      characterization: null,
    };
  }

  const parsed = parseCertificationEvalResult(inferRun.raw);
  if (!parsed.ok || !parsed.result) {
    return {
      ok: false,
      stage: 'parse',
      error: parsed.error ?? 'malformed_evaluator_output',
      evidenceId: inferRun.evidenceId ?? null,
      raw: inferRun.raw ?? null,
      characterization: null,
    };
  }

  return {
    ok: true,
    stage: null,
    error: null,
    evidenceId: inferRun.evidenceId ?? null,
    raw: inferRun.raw ?? null,
    characterization: {
      rubric_version: SEMANTIC_RUBRIC_VERSION,
      fixture_id: truth.fixture_id,
      repetition_index: 0,
      dimensions: parsed.result.dimensions ?? {},
      categorical_findings: parsed.result.categorical_findings ?? [],
      governance_flags: parsed.result.governance_flags ?? [],
      evaluator_evidence_id: inferRun.evidenceId ?? null,
      evaluator_raw: parsed.result,
      notes: [parsed.result.summary ?? ''],
    },
  };
}
