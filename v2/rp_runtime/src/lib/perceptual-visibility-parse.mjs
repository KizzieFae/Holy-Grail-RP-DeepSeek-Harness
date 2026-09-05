/** Parse combined narrator/opening JSON envelopes with perceptual_visibility (#90). */

export function parsePerceptualVisibilityEnvelope(raw) {
  if (!raw || !String(raw).trim()) {
    return { presentationText: null, perceptualVisibility: null, parseError: 'empty output' };
  }

  let stripped = String(raw).trim();
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/, '');
    stripped = stripped.replace(/\s*```$/, '');
    stripped = stripped.trim();
  }

  if (!stripped.startsWith('{')) {
    return { presentationText: stripped, perceptualVisibility: null, parseError: null };
  }

  let payload;
  try {
    payload = JSON.parse(stripped);
  } catch {
    return { presentationText: stripped, perceptualVisibility: null, parseError: null };
  }

  if (!payload || typeof payload !== 'object') {
    return { presentationText: stripped, perceptualVisibility: null, parseError: 'envelope not an object' };
  }

  const presentation =
    payload.presentation_text ?? payload.presentation ?? (typeof payload.text === 'string' ? payload.text : null);
  const presentationText = presentation ? String(presentation).trim() || null : null;

  const perceptualVisibility = payload.perceptual_visibility;
  if (perceptualVisibility != null && typeof perceptualVisibility !== 'object') {
    return { presentationText, perceptualVisibility: null, parseError: 'perceptual_visibility not an object' };
  }

  const units = perceptualVisibility?.units;
  if (units != null && !Array.isArray(units)) {
    return { presentationText, perceptualVisibility: null, parseError: 'perceptual_visibility.units not a list' };
  }

  return {
    presentationText,
    perceptualVisibility: perceptualVisibility && typeof perceptualVisibility === 'object' ? perceptualVisibility : null,
    parseError: null,
  };
}

/** Parse player semantic decomposition envelopes (#124). */
export function parseSemanticDecompositionEnvelope(raw) {
  if (!raw || !String(raw).trim()) {
    return { semanticDecomposition: null, parseError: 'empty output' };
  }

  let stripped = String(raw).trim();
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/, '');
    stripped = stripped.replace(/\s*```$/, '');
    stripped = stripped.trim();
  }

  if (!stripped.startsWith('{')) {
    return { semanticDecomposition: null, parseError: 'not json object' };
  }

  let payload;
  try {
    payload = JSON.parse(stripped);
  } catch {
    return { semanticDecomposition: null, parseError: 'json parse failed' };
  }

  if (!payload || typeof payload !== 'object') {
    return { semanticDecomposition: null, parseError: 'envelope not an object' };
  }

  const semanticDecomposition = payload.semantic_decomposition;
  if (semanticDecomposition != null && typeof semanticDecomposition !== 'object') {
    return { semanticDecomposition: null, parseError: 'semantic_decomposition not an object' };
  }

  const units = semanticDecomposition?.units;
  if (units != null && !Array.isArray(units)) {
    return { semanticDecomposition: null, parseError: 'semantic_decomposition.units not a list' };
  }

  return {
    semanticDecomposition:
      semanticDecomposition && typeof semanticDecomposition === 'object'
        ? semanticDecomposition
        : null,
    parseError: null,
  };
}

/** Parse player decomposition envelopes (#91). Legacy pre-#124 canonical envelope. */
export function parsePlayerDecompositionEnvelope(raw) {
  if (!raw || !String(raw).trim()) {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'empty output' };
  }

  let stripped = String(raw).trim();
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/, '');
    stripped = stripped.replace(/\s*```$/, '');
    stripped = stripped.trim();
  }

  if (!stripped.startsWith('{')) {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'not json object' };
  }

  let payload;
  try {
    payload = JSON.parse(stripped);
  } catch {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'json parse failed' };
  }

  if (!payload || typeof payload !== 'object') {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'envelope not an object' };
  }

  const perceptualVisibility = payload.perceptual_visibility;
  if (perceptualVisibility != null && typeof perceptualVisibility !== 'object') {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'perceptual_visibility not an object' };
  }

  const sourceAccounting = payload.source_accounting;
  if (sourceAccounting != null && typeof sourceAccounting !== 'object') {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'source_accounting not an object' };
  }

  const units = perceptualVisibility?.units;
  if (units != null && !Array.isArray(units)) {
    return { perceptualVisibility: null, sourceAccounting: null, parseError: 'perceptual_visibility.units not a list' };
  }

  return {
    perceptualVisibility: perceptualVisibility && typeof perceptualVisibility === 'object' ? perceptualVisibility : null,
    sourceAccounting: sourceAccounting && typeof sourceAccounting === 'object' ? sourceAccounting : null,
    parseError: null,
  };
}

/** Parse player visibility triage checker envelopes (#121). */
export function parsePlayerVisibilityTriageEnvelope(raw) {
  if (!raw || !String(raw).trim()) {
    return {
      uniformProjectionSafe: null,
      reason: null,
      parseError: 'empty output',
    };
  }

  let stripped = String(raw).trim();
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/, '');
    stripped = stripped.replace(/\s*```$/, '');
    stripped = stripped.trim();
  }

  if (!stripped.startsWith('{')) {
    return {
      uniformProjectionSafe: null,
      reason: null,
      parseError: 'not json object',
    };
  }

  let payload;
  try {
    payload = JSON.parse(stripped);
  } catch {
    return {
      uniformProjectionSafe: null,
      reason: null,
      parseError: 'json parse failed',
    };
  }

  if (!payload || typeof payload !== 'object') {
    return {
      uniformProjectionSafe: null,
      reason: null,
      parseError: 'envelope not an object',
    };
  }

  const safeRaw = payload.uniform_projection_safe;
  if (typeof safeRaw !== 'boolean') {
    return {
      uniformProjectionSafe: null,
      reason: payload.reason ?? null,
      parseError: 'uniform_projection_safe missing or not boolean',
    };
  }

  return {
    uniformProjectionSafe: safeRaw,
    reason: payload.reason != null ? String(payload.reason) : null,
    parseError: null,
  };
}
