import { parseJsonObject } from './inference-utils.mjs';

export const SEMANTIC_QA_RESULT_SCHEMA = 'hg_semantic_qa_result_v1';

export const VALID_EVALUATION_TARGET_ROLES = new Set(['director', 'narrator', 'character']);
export const VALID_OVERALL_RESULTS = new Set(['pass', 'reject_soft', 'reject_hard']);
export const VALID_SEVERITIES = new Set(['hard', 'soft']);

export const CITATION_STATUS = {
  VALID: 'valid',
  UNKNOWN_REF: 'unknown_ref',
  MISSING_CITATION: 'missing_citation',
  ADVISORY_AUTHORITY_CLASS: 'advisory_authority_class',
  DERIVED_AUTHORITY_CLASS: 'derived_authority_class',
};

const SEMANTIC_QA_AUTHORITY_CLASSES = new Set(['authoritative', 'derived', 'advisory']);

export function normalizeAuthorityClass(value) {
  const text = String(value ?? '').trim().toLowerCase();
  return SEMANTIC_QA_AUTHORITY_CLASSES.has(text) ? text : null;
}

export function validateAuthorityReference(ref) {
  const errors = [];
  if (!ref || typeof ref !== 'object') {
    return ['authority reference must be an object'];
  }
  const refId = String(ref.ref_id ?? ref.authority_ref_id ?? '').trim();
  if (!refId) errors.push('ref_id is required');
  if (!String(ref.kind ?? '').trim()) errors.push('kind is required');
  if (!normalizeAuthorityClass(ref.authority_class)) {
    errors.push('authority_class must be authoritative, derived, or advisory');
  }
  if (!String(ref.label ?? '').trim()) errors.push('label is required');
  if (ref.text == null || String(ref.text).trim() === '') errors.push('text is required');
  return errors;
}

export function validateAuthorityReferences(refs) {
  if (!Array.isArray(refs)) {
    return { normalized: [], errors: ['authority_references must be a list'] };
  }
  const normalized = [];
  const errors = [];
  const seen = new Set();
  for (let index = 0; index < refs.length; index += 1) {
    const itemErrors = validateAuthorityReference(refs[index]);
    if (itemErrors.length) {
      errors.push(...itemErrors.map((msg) => `authority_references[${index}]: ${msg}`));
      continue;
    }
    const refId = String(refs[index].ref_id ?? refs[index].authority_ref_id ?? '').trim();
    if (seen.has(refId)) {
      errors.push(`authority_references[${index}]: duplicate ref_id ${refId}`);
      continue;
    }
    seen.add(refId);
    normalized.push({
      ref_id: refId,
      kind: String(refs[index].kind ?? '').trim(),
      authority_class: normalizeAuthorityClass(refs[index].authority_class),
      label: String(refs[index].label ?? '').trim(),
      text: String(refs[index].text ?? ''),
      ...(refs[index].provenance && typeof refs[index].provenance === 'object'
        ? { provenance: { ...refs[index].provenance } }
        : {}),
    });
  }
  return { normalized, errors };
}

export function authorityReferenceIndex(refs) {
  const index = new Map();
  for (const ref of refs ?? []) {
    const refId = String(ref?.ref_id ?? '').trim();
    if (refId) index.set(refId, ref);
  }
  return index;
}

export function validateFindingCitations(findings, authorityRefs) {
  const refIndex = authorityReferenceIndex(authorityRefs);
  const validations = [];
  for (let findingIndex = 0; findingIndex < (findings ?? []).length; findingIndex += 1) {
    const finding = findings[findingIndex];
    const severity = String(finding?.severity ?? '').trim();
    const citation = finding?.authoritative_citation;
    const refId = citation && typeof citation === 'object'
      ? String(citation.ref_id ?? citation.authority_ref_id ?? '').trim()
      : '';

    if (severity === 'hard' && !refId) {
      validations.push({
        finding_index: findingIndex,
        ref_id: null,
        status: CITATION_STATUS.MISSING_CITATION,
        resolved_authority_class: null,
      });
      continue;
    }
    if (!refId) continue;

    const resolved = refIndex.get(refId);
    if (!resolved) {
      validations.push({
        finding_index: findingIndex,
        ref_id: refId,
        status: CITATION_STATUS.UNKNOWN_REF,
        resolved_authority_class: null,
      });
      continue;
    }

    const resolvedClass = normalizeAuthorityClass(resolved.authority_class);
    let status = CITATION_STATUS.VALID;
    if (resolvedClass === 'advisory') status = CITATION_STATUS.ADVISORY_AUTHORITY_CLASS;
    else if (resolvedClass === 'derived') status = CITATION_STATUS.DERIVED_AUTHORITY_CLASS;

    validations.push({
      finding_index: findingIndex,
      ref_id: refId,
      status,
      resolved_authority_class: resolvedClass,
    });
  }
  return validations;
}

function normalizeFinding(raw, findingIndex) {
  const warnings = [];
  if (!raw || typeof raw !== 'object') {
    warnings.push(`findings[${findingIndex}] is not an object`);
    return { finding: null, warnings };
  }
  const dimension = String(raw.dimension ?? '').trim();
  if (!dimension) {
    warnings.push(`findings[${findingIndex}].dimension is required`);
    return { finding: null, warnings };
  }
  const severity = String(raw.severity ?? '').trim();
  if (!VALID_SEVERITIES.has(severity)) {
    warnings.push(`findings[${findingIndex}].severity must be hard or soft`);
    return { finding: null, warnings };
  }

  let normalizedCitation = null;
  if (raw.authoritative_citation && typeof raw.authoritative_citation === 'object') {
    const refId = String(
      raw.authoritative_citation.ref_id
      ?? raw.authoritative_citation.authority_ref_id
      ?? '',
    ).trim();
    if (refId) normalizedCitation = { ref_id: refId };
  } else if (severity === 'hard') {
    warnings.push(
      `findings[${findingIndex}] hard severity requires authoritative_citation.ref_id`,
    );
  }

  return {
    finding: {
      dimension,
      severity,
      finding: String(raw.finding ?? ''),
      rationale: String(raw.rationale ?? ''),
      candidate_evidence: raw.candidate_evidence ?? null,
      authoritative_citation: normalizedCitation,
    },
    warnings,
  };
}

export function parseSemanticQaResult(raw, authorityReferences = [], options = {}) {
  const {
    expectedEvaluationPassId = null,
    expectedEvaluationTargetRole = null,
  } = options;

  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return {
      ok: false,
      error: String(error),
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }
  if (!parsed || typeof parsed !== 'object') {
    return {
      ok: false,
      error: 'evaluator output not an object',
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }

  const parseWarnings = [];
  if (String(parsed.schema ?? '').trim() !== SEMANTIC_QA_RESULT_SCHEMA) {
    return {
      ok: false,
      error: `unsupported schema ${String(parsed.schema ?? '<missing>')}`,
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }

  const evaluationTargetRole = String(parsed.evaluation_target_role ?? '').trim();
  if (!VALID_EVALUATION_TARGET_ROLES.has(evaluationTargetRole)) {
    return {
      ok: false,
      error: 'evaluation_target_role must be director, narrator, or character',
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }
  if (expectedEvaluationTargetRole && evaluationTargetRole !== expectedEvaluationTargetRole) {
    parseWarnings.push('evaluation_target_role does not match expected evaluation target');
  }

  const evaluationPassId = String(parsed.evaluation_pass_id ?? '').trim();
  if (!evaluationPassId) {
    return {
      ok: false,
      error: 'evaluation_pass_id is required',
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }
  if (expectedEvaluationPassId && evaluationPassId !== expectedEvaluationPassId) {
    parseWarnings.push('evaluation_pass_id does not match expected correlation id');
  }

  const overallResult = String(parsed.overall_result ?? '').trim();
  if (!VALID_OVERALL_RESULTS.has(overallResult)) {
    return {
      ok: false,
      error: 'overall_result must be pass, reject_soft, or reject_hard',
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }

  const { normalized: refs, errors: refErrors } = validateAuthorityReferences(
    authorityReferences ?? [],
  );
  parseWarnings.push(...refErrors);

  const findingsRaw = Array.isArray(parsed.findings) ? parsed.findings : null;
  if (findingsRaw === null) {
    return {
      ok: false,
      error: 'findings must be an array',
      result: null,
      citationValidations: [],
      parseWarnings: [],
    };
  }

  const findings = [];
  for (let index = 0; index < findingsRaw.length; index += 1) {
    const { finding, warnings } = normalizeFinding(findingsRaw[index], index);
    parseWarnings.push(...warnings);
    if (finding) findings.push(finding);
  }

  const citationValidations = validateFindingCitations(findings, refs);
  const evaluatorSummary = parsed.evaluator_summary;
  if (evaluatorSummary != null && typeof evaluatorSummary !== 'string') {
    parseWarnings.push('evaluator_summary must be a string when present');
  }

  let residualSoftConcerns = [];
  if (Array.isArray(parsed.residual_soft_concerns)) {
    residualSoftConcerns = parsed.residual_soft_concerns.map((item) => String(item));
  } else if (parsed.residual_soft_concerns != null) {
    parseWarnings.push('residual_soft_concerns must be an array when present');
  }

  return {
    ok: true,
    error: null,
    result: {
      schema: SEMANTIC_QA_RESULT_SCHEMA,
      evaluation_target_role: evaluationTargetRole,
      evaluation_pass_id: evaluationPassId,
      overall_result: overallResult,
      findings,
      evaluator_summary: evaluatorSummary ? String(evaluatorSummary) : null,
      residual_soft_concerns: residualSoftConcerns,
    },
    citationValidations,
    parseWarnings,
  };
}
