/** Parse combined narrator/opening JSON envelopes with narrative_visibility (#81). */

export function parseNarratorVisibilityEnvelope(raw) {
  const text = String(raw ?? '').trim();
  if (!text) {
    return { presentationText: null, narrativeVisibility: null, parseError: 'empty output' };
  }

  let stripped = text;
  if (stripped.startsWith('```')) {
    stripped = stripped.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
  }

  if (!stripped.startsWith('{')) {
    return { presentationText: stripped, narrativeVisibility: null, parseError: null };
  }

  try {
    const payload = JSON.parse(stripped);
    if (!payload || typeof payload !== 'object') {
      return { presentationText: stripped, narrativeVisibility: null, parseError: 'envelope not an object' };
    }
    const presentationText = String(
      payload.presentation_text ?? payload.presentation ?? payload.text ?? '',
    ).trim() || null;
    const narrativeVisibility = payload.narrative_visibility;
    if (narrativeVisibility != null && typeof narrativeVisibility !== 'object') {
      return { presentationText, narrativeVisibility: null, parseError: 'narrative_visibility not an object' };
    }
    return { presentationText, narrativeVisibility: narrativeVisibility ?? null, parseError: null };
  } catch {
    return { presentationText: stripped, narrativeVisibility: null, parseError: null };
  }
}
