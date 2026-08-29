"""DSH Character epistemic projection evaluation (#63)."""

import { parseJsonObject } from '../../lib/inference-utils.mjs';

export const EPISTEMIC_PROJECTION_EVAL_SCHEMA = 'hg_epistemic_projection_eval_v1';

const VALID_VERDICTS = new Set(['pass', 'withhold', 'rewrite_required', 'evaluator_unavailable']);

export function parseEpistemicProjectionEvalResult(raw) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return {
      ok: false,
      error: String(error?.message ?? error ?? 'parse_error'),
      result: null,
    };
  }
  const verdict = String(parsed?.verdict ?? '').trim();
  if (!VALID_VERDICTS.has(verdict)) {
    return { ok: false, error: `invalid_verdict:${verdict}`, result: null };
  }
  const rationale = String(parsed?.forensic_rationale ?? parsed?.rationale ?? '');
  let regenerationGuidance = null;
  if (verdict === 'rewrite_required') {
    const guidance = parsed?.regeneration_guidance;
    if (!guidance || typeof guidance !== 'object' || !Array.isArray(guidance.safe_constraints)) {
      return { ok: false, error: 'rewrite_required_missing_guidance', result: null };
    }
    regenerationGuidance = guidance;
  }
  return {
    ok: true,
    error: null,
    result: {
      schema: EPISTEMIC_PROJECTION_EVAL_SCHEMA,
      verdict,
      rationale: String(parsed?.rationale ?? rationale),
      forensic_rationale: rationale,
      regeneration_guidance: regenerationGuidance,
      leak_indicators: Array.isArray(parsed?.leak_indicators) ? parsed.leak_indicators : [],
    },
  };
}

export async function runCharacterEpistemicProjectionEval({
  api,
  runEphemeralInference,
  scope,
  preparePayload,
  modelProfile = null,
  mockResponse = null,
}) {
  const prepare = await api.preparePlotCognitionProjection(preparePayload);
  if (!prepare?.accepted) {
    return { ok: false, stage: 'prepare', prepare, inferRun: null, parsed: null };
  }
  const evaluationPassId = preparePayload.evaluation_pass_id;
  const manifest = prepare.evaluator_manifests?.[evaluationPassId] ?? [];
  const inferenceId = `${preparePayload.inference_id}-epistemic-${evaluationPassId}`;
  const inferRun = await runEphemeralInference({
    inferenceId,
    prompt: 'Evaluate Character advisory text for epistemic leakage. Output JSON only.',
    manifest: { contributions: manifest },
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...scope,
      inferenceId,
      inferenceKind: 'plot_cognition_epistemic_eval',
      evaluationPassId,
    },
  });
  if (inferRun.failed) {
    return {
      ok: false,
      stage: 'inference',
      prepare,
      inferRun,
      parsed: {
        ok: true,
        result: {
          schema: EPISTEMIC_PROJECTION_EVAL_SCHEMA,
          verdict: 'evaluator_unavailable',
          rationale: 'inference_failed',
          forensic_rationale: 'inference_failed',
          regeneration_guidance: null,
          leak_indicators: [],
        },
      },
    };
  }
  const parsed = parseEpistemicProjectionEvalResult(inferRun.raw);
  return { ok: parsed.ok, stage: 'parsed', prepare, inferRun, parsed };
}
