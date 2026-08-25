import { parseJsonObject } from './inference-utils.mjs';

export const CHARACTER_ORIENTATION_SCHEMA = 'hg_character_orientation_v1';

const PROHIBITED = new Set([
  'structured_move',
  'beats',
  'dialogue',
  'narration',
  'character_state',
  'continuity_mutation',
  'next_actor',
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

export function buildCharacterOrientationPrompt({
  schema = CHARACTER_ORIENTATION_SCHEMA,
} = {}) {
  return [
    'You are the Holy Grail Character knowledge-orientation phase.',
    'Given the upstream scene context, identify what additional knowledge you need to act.',
    'Populate information_gaps with focus questions for the Librarian.',
    'Do NOT output a character move, dialogue, narration, or continuity mutations.',
    'Do NOT reference retrieval backends, candidate ids, or relevance ranks.',
    `Return ONLY one JSON object matching schema ${schema}.`,
  ].join('\n');
}

export function manifestFromCharacterPrepareResponse(prepareResponse) {
  return {
    manifest_id: prepareResponse.manifest_id,
    contributions: prepareResponse.contributions ?? [],
  };
}

export function parseCharacterOrientation(raw) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_failed'), result: null };
  }
  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'not_object', result: null };
  }
  if (String(parsed.schema ?? '') !== CHARACTER_ORIENTATION_SCHEMA) {
    return { ok: false, error: 'schema_mismatch', result: null };
  }
  const prohibited = findProhibited(parsed);
  if (prohibited.length > 0) {
    return { ok: false, error: `prohibited_fields:${prohibited.slice(0, 5).join(',')}`, result: null };
  }
  const gaps = (parsed.information_gaps ?? [])
    .map((item) => String(item ?? '').trim())
    .filter(Boolean);
  if (gaps.length === 0) {
    return { ok: false, error: 'information_gaps_required', result: null };
  }
  if (!String(parsed.character_id ?? '').trim()) {
    return { ok: false, error: 'character_id_required', result: null };
  }
  return { ok: true, error: null, result: parsed };
}
