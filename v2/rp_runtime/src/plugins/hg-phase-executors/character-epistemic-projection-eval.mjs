/** DSH Character epistemic projection evaluation (#63) — contract elicitation (#65). */

import { parseJsonObject } from '../../lib/inference-utils.mjs';

export const EPISTEMIC_PROJECTION_EVAL_SCHEMA = 'hg_epistemic_projection_eval_v1';
export const REGENERATION_GUIDANCE_SCHEMA = 'hg_regeneration_guidance_v1';

const VALID_VERDICTS = new Set(['pass', 'withhold', 'rewrite_required', 'evaluator_unavailable']);

const FORBIDDEN_SYNONYM_FIELDS = [
  'allowed',
  'permitted',
  'leakage',
  'epistemic_leakage',
];

const VIOLATION_CLASSES = [
  'third_party_private_knowledge',
  'withheld_basis_exposure',
  'global_cognition_leak',
  'over_specific_prospective',
  'relationship_boundary',
  'other',
];

export function buildEpistemicProjectionEvalPrompt() {
  return [
    'You are the Layer-B Character epistemic projection evaluator.',
    `Return ONLY one JSON object (no markdown fences, no commentary) with schema ${EPISTEMIC_PROJECTION_EVAL_SCHEMA}.`,
    'Required field: verdict — exactly one of: pass, withhold, rewrite_required, evaluator_unavailable.',
    'Include rationale and/or forensic_rationale (string).',
    'Optional: leak_indicators (array of strings).',
    'When verdict is rewrite_required, include regeneration_guidance object with:',
    `  schema: "${REGENERATION_GUIDANCE_SCHEMA}"`,
    '  safe_constraints: non-empty string array',
    `  violation_class: one of ${VIOLATION_CLASSES.join(', ')}`,
    'Do NOT use alternate fields such as allowed, permitted, leakage, or epistemic_leakage.',
    'Do NOT wrap the verdict in alternate JSON shapes.',
    `Minimal pass example: {"schema":"${EPISTEMIC_PROJECTION_EVAL_SCHEMA}","verdict":"pass","rationale":"Candidate stays within permitted envelope."}`,
    `Minimal withhold example: {"schema":"${EPISTEMIC_PROJECTION_EVAL_SCHEMA}","verdict":"withhold","rationale":"Candidate leaks private knowledge."}`,
  ].join('\n');
}

export function buildEpistemicProjectionEvalCorrectionPrompt({ priorRaw, structuralError }) {
  const prior = typeof priorRaw === 'string' ? priorRaw : JSON.stringify(priorRaw ?? {});
  const contractPrompt = buildEpistemicProjectionEvalPrompt();
  return [
    'CONTRACT CORRECTION: Your previous response did not satisfy the required machine contract.',
    'Preserve the semantic judgment from that response unless satisfying the contract logically requires otherwise.',
    'Correct only the representation/serialization. Output JSON only — no markdown, no commentary.',
    '',
    `Previous response:\n${prior}`,
    '',
    `Structural validation error: ${structuralError}`,
    '',
    'Required contract:',
    contractPrompt,
    '',
    'Re-emit the result using exactly the required JSON contract.',
  ].join('\n');
}

function detectForbiddenSynonymFields(parsed) {
  for (const field of FORBIDDEN_SYNONYM_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(parsed, field)) {
      return `forbidden_synonym_field:${field}`;
    }
  }
  return null;
}

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

  const synonymError = detectForbiddenSynonymFields(parsed);
  if (synonymError) {
    return { ok: false, error: synonymError, result: null };
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
    prompt: buildEpistemicProjectionEvalPrompt(),
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
