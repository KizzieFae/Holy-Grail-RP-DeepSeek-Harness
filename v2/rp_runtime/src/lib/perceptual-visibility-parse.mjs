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

/** Parse player decomposition envelopes (#91). */
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
