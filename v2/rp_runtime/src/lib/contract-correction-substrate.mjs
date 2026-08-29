/**
 * Bounded response-aware contract correction (#65).
 * One correction max per primary semantic inference; no recursive correction.
 */

export async function runInferenceWithContractCorrection({
  runEphemeralInference,
  primaryInferenceId,
  primaryInferenceKind,
  correctionInferenceKind,
  buildPrimaryPrompt,
  buildCorrectionPrompt,
  parseFn,
  parseContext = null,
  manifest,
  mockResponses = [],
  modelProfile = null,
  evidenceContextBase = null,
  maxCorrections = 1,
}) {
  const primaryPrompt = typeof buildPrimaryPrompt === 'function'
    ? buildPrimaryPrompt(parseContext)
    : buildPrimaryPrompt;

  const resolvedMocks = Array.isArray(mockResponses) ? mockResponses : [];
  const primaryMock = resolvedMocks[0] ?? null;

  const primaryRun = await runEphemeralInference({
    inferenceId: primaryInferenceId,
    prompt: primaryPrompt,
    manifest,
    mockResponses: primaryMock ? [primaryMock] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      inferenceId: primaryInferenceId,
      inferenceKind: primaryInferenceKind,
    },
  });

  const lineage = {
    primary: {
      inference_id: primaryInferenceId,
      inference_kind: primaryInferenceKind,
      evidence_id: primaryRun.evidenceId ?? null,
      raw: primaryRun.raw ?? null,
      failed: primaryRun.failed === true,
    },
    correction: null,
    correction_used: false,
  };

  if (primaryRun.failed) {
    return {
      ok: false,
      stage: 'inference',
      inferRun: primaryRun,
      inferRuns: [primaryRun],
      parsed: null,
      lineage,
      correctionUsed: false,
    };
  }

  let parsed = parseFn(primaryRun.raw, parseContext);
  if (parsed.ok && parsed.result) {
    return {
      ok: true,
      stage: 'parsed',
      inferRun: primaryRun,
      inferRuns: [primaryRun],
      parsed,
      lineage,
      correctionUsed: false,
    };
  }

  const structuralError = parsed.error ?? 'structural_validation_failed';
  lineage.primary.parse_error = structuralError;

  if (maxCorrections < 1) {
    return {
      ok: false,
      stage: 'parsed',
      inferRun: primaryRun,
      inferRuns: [primaryRun],
      parsed,
      lineage,
      correctionUsed: false,
      structuralError,
    };
  }

  const correctionInferenceId = `${primaryInferenceId}-contract-correction`;
  const correctionPrompt = buildCorrectionPrompt({
    priorRaw: primaryRun.raw,
    structuralError,
    context: parseContext,
  });
  const correctionMock = resolvedMocks[1] ?? null;

  const correctionRun = await runEphemeralInference({
    inferenceId: correctionInferenceId,
    prompt: correctionPrompt,
    manifest,
    mockResponses: correctionMock ? [correctionMock] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      inferenceId: correctionInferenceId,
      inferenceKind: correctionInferenceKind,
      parentInferenceId: primaryInferenceId,
      primaryEvidenceId: primaryRun.evidenceId ?? null,
      structuralError,
    },
  });

  lineage.correction = {
    inference_id: correctionInferenceId,
    inference_kind: correctionInferenceKind,
    evidence_id: correctionRun.evidenceId ?? null,
    raw: correctionRun.raw ?? null,
    failed: correctionRun.failed === true,
    parent_inference_id: primaryInferenceId,
    structural_error: structuralError,
  };
  lineage.correction_used = true;

  if (correctionRun.failed) {
    return {
      ok: false,
      stage: 'correction_inference',
      inferRun: correctionRun,
      inferRuns: [primaryRun, correctionRun],
      parsed: null,
      lineage,
      correctionUsed: true,
      structuralError,
    };
  }

  parsed = parseFn(correctionRun.raw, parseContext);
  lineage.correction.parse_error = parsed.ok ? null : (parsed.error ?? 'structural_validation_failed');

  if (parsed.ok && parsed.result) {
    return {
      ok: true,
      stage: 'corrected',
      inferRun: correctionRun,
      inferRuns: [primaryRun, correctionRun],
      parsed,
      lineage,
      correctionUsed: true,
      structuralError,
    };
  }

  return {
    ok: false,
    stage: 'correction_parsed',
    inferRun: correctionRun,
    inferRuns: [primaryRun, correctionRun],
    parsed,
    lineage,
    correctionUsed: true,
    structuralError,
  };
}
