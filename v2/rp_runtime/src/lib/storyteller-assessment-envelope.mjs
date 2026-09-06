import { parseJsonObject } from './inference-utils.mjs';
import { bridgeManifestFromHostPrepare } from './bridge-manifest.mjs';

export const STORYTELLER_ASSESSMENT_SCHEMA = 'hg_storyteller_assessment_v1';

const PROHIBITED = new Set([
  'next_actor',
  'next_actor_hint',
  'required_action',
  'mandated_beat',
  'required_beat',
  'dialogue',
  'narration',
  'structured_move',
  'character_state',
  'continuity_mutation',
  'plot_beat',
  'must_act',
  'must_say',
  'must_do',
]);

function findProhibited(value, path = '') {
  const hits = [];
  if (!value || typeof value !== 'object') return hits;
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      hits.push(...findProhibited(item, `${path}[${index}]`));
    });
    return hits;
  }
  for (const [key, nested] of Object.entries(value)) {
    const current = path ? `${path}.${key}` : key;
    if (PROHIBITED.has(key)) hits.push(current);
    hits.push(...findProhibited(nested, current));
  }
  return hits;
}

export function buildStorytellerAssessmentPrompt({
  schema = STORYTELLER_ASSESSMENT_SCHEMA,
} = {}) {
  return [
    'You are the Holy Grail Storyteller informed narrative assessment phase.',
    'Given the Librarian bundle digest, assess what is narratively significant now.',
    'Use opportunity framing — not mandates. Cite evidence_refs from bundle entries or authoritative refs.',
    'Do NOT prescribe actor selection, dialogue, narration, structured moves, or continuity mutations.',
    `Return ONLY one JSON object matching schema ${schema}.`,
  ].join('\n');
}

export function manifestFromStorytellerAssessmentPrepareResponse(prepareResponse) {
  return bridgeManifestFromHostPrepare(
    prepareResponse,
    prepareResponse.contributions ?? [],
  );
}

export function parseStorytellerAssessment(raw) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_failed'), result: null };
  }
  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'not_object', result: null };
  }
  if (String(parsed.schema ?? '') !== STORYTELLER_ASSESSMENT_SCHEMA) {
    return { ok: false, error: 'schema_mismatch', result: null };
  }
  const prohibited = findProhibited(parsed);
  if (prohibited.length > 0) {
    return { ok: false, error: `prohibited_fields:${prohibited.slice(0, 5).join(',')}`, result: null };
  }
  return { ok: true, error: null, result: parsed };
}
