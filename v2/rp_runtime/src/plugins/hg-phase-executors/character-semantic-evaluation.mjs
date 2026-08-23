import { parseJsonObject } from '../../lib/inference-utils.mjs';

export const SEMANTIC_EVAL_RESULT_SCHEMA = 'hg_semantic_evaluation_result_v1';
export const SEMANTIC_EVAL_CONFIG_ID = 'semantic_evaluator_v1';

const VALID_DIMENSIONS = new Set(['R02b', 'R11', 'R12', 'R14', 'R15']);
const VALID_SEVERITIES = new Set(['hard', 'soft']);

export const DEFAULT_PASS_RESULT = {
  schema: SEMANTIC_EVAL_RESULT_SCHEMA,
  overall_result: 'pass',
  findings: [],
  correction_request: null,
  residual_soft_concerns: [],
};

export function buildCorrectionContextFromEvaluation(evaluationResult, {
  evaluationPassId,
  priorCandidateSummary,
}) {
  return {
    evaluation_pass_id: evaluationPassId,
    schema: SEMANTIC_EVAL_RESULT_SCHEMA,
    findings: evaluationResult.findings ?? [],
    correction_request: evaluationResult.correction_request ?? null,
    overall_result: evaluationResult.overall_result,
    prior_candidate_summary: priorCandidateSummary ?? null,
    instruction:
      'Revise your Character move JSON. Address the semantic evaluation findings. '
      + 'Do not invent player-controlled behavior. Output replacement RP as JSON only.',
  };
}

export function summarizeCandidateForCorrection(proposed, rawModelOutput) {
  return {
    proposed_move: proposed,
    raw_model_output_excerpt: String(rawModelOutput ?? '').slice(0, 4000),
  };
}

function normalizeFinding(raw, authorityRefIds) {
  if (!raw || typeof raw !== 'object') return null;
  const dimension = String(raw.dimension ?? '').trim();
  const severity = String(raw.severity ?? '').trim();
  if (!VALID_DIMENSIONS.has(dimension) || !VALID_SEVERITIES.has(severity)) {
    return null;
  }
  const finding = {
    dimension,
    severity,
    finding: String(raw.finding ?? ''),
    rationale: String(raw.rationale ?? ''),
    candidate_evidence: raw.candidate_evidence ?? null,
    authoritative_citation: raw.authoritative_citation ?? null,
  };
  if (severity === 'hard') {
    const refId = String(
      finding.authoritative_citation?.ref_id
      ?? finding.authoritative_citation?.authority_ref_id
      ?? '',
    ).trim();
    if (!refId || !authorityRefIds.has(refId)) {
      return {
        ...finding,
        severity: 'soft',
        rationale: `${finding.rationale} [downgraded: unknown authority ref ${refId || '<missing>'}]`.trim(),
        authoritative_citation: null,
      };
    }
  }
  return finding;
}

export function parseSemanticEvaluationResult(raw, authorityReferences = []) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return {
      ok: false,
      error: String(error),
      result: null,
    };
  }
  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'evaluator output not an object', result: null };
  }
  const authorityRefIds = new Set(
    (authorityReferences ?? []).map((ref) => String(ref.ref_id ?? ref.authority_ref_id ?? '')),
  );
  const findingsRaw = Array.isArray(parsed.findings) ? parsed.findings : [];
  const findings = findingsRaw
    .map((item) => normalizeFinding(item, authorityRefIds))
    .filter(Boolean);
  const hasHard = findings.some((f) => f.severity === 'hard');
  const hasSoft = findings.some((f) => f.severity === 'soft');
  let overall = String(parsed.overall_result ?? '').trim();
  if (!overall) {
    if (hasHard) overall = 'reject_hard';
    else if (hasSoft) overall = 'reject_soft';
    else overall = 'pass';
  }
  if (hasHard) overall = 'reject_hard';
  const correctionRequest = parsed.correction_request ?? (
    findings.length
      ? {
        summary: findings.map((f) => f.finding).filter(Boolean).join('; '),
        dimensions: [...new Set(findings.map((f) => f.dimension))],
        must_not: 'Do not supply replacement RP prose; revise JSON only.',
      }
      : null
  );
  const result = {
    schema: SEMANTIC_EVAL_RESULT_SCHEMA,
    evaluation_pass_id: parsed.evaluation_pass_id ?? null,
    evaluator_config_id: parsed.evaluator_config_id ?? SEMANTIC_EVAL_CONFIG_ID,
    overall_result: overall,
    findings,
    correction_request: correctionRequest,
    residual_soft_concerns: Array.isArray(parsed.residual_soft_concerns)
      ? parsed.residual_soft_concerns
      : [],
  };
  return { ok: true, error: null, result };
}

function manifestFromSemanticContext(contextResponse) {
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
    character_id: contextResponse.character_id,
    turn_index: contextResponse.turn_index,
    attempt_index: 0,
    contributions,
  };
}

export async function runSemanticEvaluation({
  api,
  runEphemeralInference,
  recorder,
  scope,
  characterInferenceId,
  characterId,
  role,
  hgSceneId,
  hgRoundId,
  hgSessionId,
  turnIndex,
  evaluationPassId,
  candidateMove,
  rawModelOutput,
  semanticEvaluatorProfile,
  mockSemanticResponse,
  parentCharacterEvidenceId,
  infrastructureAttempt = 0,
}) {
  const contextResponse = await api.prepareSemanticEvaluationContext({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: characterInferenceId,
    character_id: characterId,
    role,
    turn_index: turnIndex,
    evaluation_pass_id: evaluationPassId,
    candidate_move: candidateMove,
    raw_model_output: rawModelOutput,
  });
  const manifest = manifestFromSemanticContext(contextResponse);
  const infraSuffix = infrastructureAttempt > 0 ? `-infra-retry-${infrastructureAttempt}` : '';
  const evalInferenceId = `${characterInferenceId}-semantic-${evaluationPassId}${infraSuffix}`;
  const evalRun = await runEphemeralInference({
    inferenceId: evalInferenceId,
    prompt: [
      'You are a bounded semantic evaluator for a Character move candidate.',
      'Return ONLY one JSON object (no markdown) with schema hg_semantic_evaluation_result_v1.',
      'Use overall_result pass|reject_soft|reject_hard and findings[] with dimension R02b|R11|R12|R14|R15.',
      'If no issues, return {"schema":"hg_semantic_evaluation_result_v1","overall_result":"pass","findings":[]}.',
    ].join(' '),
    manifest,
    mockResponses: mockSemanticResponse ? [mockSemanticResponse] : [],
    modelProfile: semanticEvaluatorProfile,
    evidenceContext: {
      hgSessionId,
      hgSceneId,
      hgRoundId,
      role: 'semantic_evaluator',
      characterId,
      inferenceId: characterInferenceId,
      attemptIndex: 0,
      priorAttemptId: parentCharacterEvidenceId,
      evaluationPassId,
    },
  });
  if (evalRun.failed) {
    return {
      ok: false,
      infrastructureFailure: true,
      evaluatorError: evalRun.failure ?? 'inference_failed',
      evidenceId: evalRun.evidenceId ?? null,
      contextResponse,
      raw: null,
      result: null,
    };
  }
  const parsed = parseSemanticEvaluationResult(
    evalRun.raw,
    contextResponse.authority_references,
  );
  if (!parsed.ok || !parsed.result) {
    return {
      ok: false,
      infrastructureFailure: true,
      evaluatorError: parsed.error ?? 'malformed_evaluator_output',
      evidenceId: evalRun.evidenceId ?? null,
      contextResponse,
      raw: evalRun.raw,
      result: null,
    };
  }
  const result = {
    ...parsed.result,
    evaluation_pass_id: evaluationPassId,
  };
  return {
    ok: true,
    infrastructureFailure: false,
    evaluatorError: null,
    evidenceId: evalRun.evidenceId ?? null,
    contextResponse,
    raw: evalRun.raw,
    result,
    inferenceSessionId: evalRun.inferenceSessionId,
    trace: evalRun.trace,
  };
}
