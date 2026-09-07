import {
  SEMANTIC_QA_RESULT_SCHEMA,
  parseSemanticQaResult,
} from './semantic-qa-envelope.mjs';
import {
  bridgeManifestFromHostPrepare,
  normalizeBridgeContributions,
} from './bridge-manifest.mjs';

function manifestFromSemanticQaContext(contextResponse) {
  return bridgeManifestFromHostPrepare(
    contextResponse,
    normalizeBridgeContributions(contextResponse.contributions),
  );
}

/**
 * Shared semantic-QA runtime substrate (#25).
 * Invokes evaluator inference and returns parsed evidence for role integration.
 */
export async function runSemanticQaEvaluation({
  runEphemeralInference,
  prepareContext,
  buildEvaluatorPrompt,
  evidenceContextBase,
  evaluationPassId,
  evaluationTargetRole,
  parentCandidateEvidenceId = null,
  mockResponse = null,
  modelProfile = null,
  infrastructureAttempt = 0,
  parseResult = parseSemanticQaResult,
}) {
  let contextResponse;
  try {
    contextResponse = await prepareContext();
  } catch (error) {
    return {
      ok: false,
      infrastructureFailure: true,
      stage: 'context_prepare',
      evaluatorError: String(error?.message ?? error ?? 'context_prepare_failed'),
      evidenceId: null,
      contextResponse: null,
      raw: null,
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }

  const manifest = manifestFromSemanticQaContext(contextResponse);
  const inferenceId = String(contextResponse.inference_id ?? evidenceContextBase?.inferenceId ?? 'semantic-qa');
  const infraSuffix = infrastructureAttempt > 0 ? `-infra-retry-${infrastructureAttempt}` : '';
  const evalInferenceId = `${inferenceId}-semantic-qa-${evaluationPassId}${infraSuffix}`;

  let prompt = buildEvaluatorPrompt({
    schema: SEMANTIC_QA_RESULT_SCHEMA,
    evaluationTargetRole,
    evaluationPassId,
  });

  if (infrastructureAttempt > 0) {
    prompt = [
      prompt,
      '',
      'INFRASTRUCTURE RETRY: Your prior evaluator response was empty or malformed.',
      'Return ONLY one JSON object matching the required schema. No markdown, no prose.',
      `evaluation_pass_id must be "${evaluationPassId}".`,
    ].join('\n');
  }

  const evalRun = await runEphemeralInference({
    inferenceId: evalInferenceId,
    prompt,
    manifest,
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
        evidenceContext: {
      ...evidenceContextBase,
      inferenceKind: contextResponse.inference_kind ?? evidenceContextBase?.inferenceKind ?? null,
      role: 'semantic_evaluator',
      priorAttemptId: parentCandidateEvidenceId,
      evaluationPassId,
      evaluationTargetRole,
    },
  });

  if (evalRun.failed) {
    return {
      ok: false,
      infrastructureFailure: true,
      stage: 'inference',
      evaluatorError: evalRun.failure ?? 'inference_failed',
      evidenceId: evalRun.evidenceId ?? null,
      contextResponse,
      raw: null,
      result: null,
      citationValidations: [],
      parseWarnings: [],
      inferenceSessionId: evalRun.inferenceSessionId ?? null,
      trace: evalRun.trace ?? null,
    };
  }

  const rawText = String(evalRun.raw ?? '').trim();
  if (!rawText) {
    return {
      ok: false,
      infrastructureFailure: true,
      stage: 'empty_output',
      evaluatorError: 'evaluator produced empty structured output',
      evidenceId: evalRun.evidenceId ?? null,
      contextResponse,
      raw: evalRun.raw,
      result: null,
      citationValidations: [],
      parseWarnings: [],
      inferenceSessionId: evalRun.inferenceSessionId ?? null,
      trace: evalRun.trace ?? null,
    };
  }

  const parsed = parseResult(
    evalRun.raw,
    contextResponse.authority_references ?? [],
    {
      expectedEvaluationPassId: evaluationPassId,
      expectedEvaluationTargetRole: evaluationTargetRole,
    },
  );

  if (!parsed.ok || !parsed.result) {
    return {
      ok: false,
      infrastructureFailure: true,
      stage: 'parse',
      evaluatorError: parsed.error ?? 'malformed_evaluator_output',
      evidenceId: evalRun.evidenceId ?? null,
      contextResponse,
      raw: evalRun.raw,
      result: null,
      citationValidations: parsed.citationValidations ?? [],
      parseWarnings: parsed.parseWarnings ?? [],
      inferenceSessionId: evalRun.inferenceSessionId ?? null,
      trace: evalRun.trace ?? null,
    };
  }

  return {
    ok: true,
    infrastructureFailure: false,
    stage: null,
    evaluatorError: null,
    evidenceId: evalRun.evidenceId ?? null,
    contextResponse,
    raw: evalRun.raw,
    result: parsed.result,
    citationValidations: parsed.citationValidations ?? [],
    parseWarnings: parsed.parseWarnings ?? [],
    inferenceSessionId: evalRun.inferenceSessionId ?? null,
    trace: evalRun.trace ?? null,
  };
}
