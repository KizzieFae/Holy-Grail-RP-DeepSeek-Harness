import {
  SEMANTIC_QA_RESULT_SCHEMA,
  parseSemanticQaResult,
} from './semantic-qa-envelope.mjs';

function manifestFromSemanticQaContext(contextResponse) {
  const contributions = (contextResponse.contributions ?? []).map((c) => ({
    contribution_id: c.contribution_id,
    source_kind: c.source_kind,
    authority_class: c.authority_class,
    priority: c.priority,
    content: c.content,
    knowledge_ids: c.knowledge_ids,
    provenance: c.provenance,
  }));
  return {
    manifest_id: contextResponse.manifest_id,
    inference_id: contextResponse.inference_id,
    hg_scene_id: contextResponse.hg_scene_id,
    hg_round_id: contextResponse.hg_round_id,
    role: 'semantic_evaluator',
    character_id: contextResponse.character_id ?? null,
    turn_index: contextResponse.turn_index,
    attempt_index: 0,
    contributions,
  };
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

  const prompt = buildEvaluatorPrompt({
    schema: SEMANTIC_QA_RESULT_SCHEMA,
    evaluationTargetRole,
    evaluationPassId,
  });

  const evalRun = await runEphemeralInference({
    inferenceId: evalInferenceId,
    prompt,
    manifest,
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
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
