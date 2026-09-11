import { parseJsonObject } from './inference-utils.mjs';
import {
  bridgeManifestFromHostPrepare,
  normalizeBridgeContributions,
} from './bridge-manifest.mjs';
import {
  librarianMediationContractPromptLines,
} from './librarian-mediation-inference-contract.mjs';

export const LIBRARIAN_MEDIATION_RESULT_SCHEMA = 'hg_librarian_mediation_result_v1';
export const LIBRARIAN_MEDIATION_CONFIG_ID = 'librarian_mediator_v1';
export const LIBRARIAN_MEDIATION_CORRECTION_KIND = 'librarian_mediation_contract_correction';

const VALID_EDGE = new Set(['supports', 'contradicts', 'same_entity', 'causal_candidate']);
const VALID_SYNTH = new Set(['summary', 'connection_bridge', 'consolidated_fact_view']);
const VALID_BAND = new Set(['high', 'medium', 'low']);
const VALID_STATUS = new Set(['confirmed', 'likely', 'speculative']);

function asStringArray(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? '').trim()).filter(Boolean);
}

export function buildLibrarianMediationPrompt({
  schema = LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  sampleSourceId = 'lmi:cand:example-source',
} = {}) {
  return [
    'You are the Holy Grail Librarian information mediator.',
    'Select and rank ONLY catalog source_id values that contextually help answer the focus questions.',
    'Do NOT choose narrative direction, dramatic theme, or plot prescription.',
    'Do NOT invent new source identities or authoritative facts.',
    'Indirect causal relevance, cross-relationship explanation, and late-emerging significance are in scope.',
    'Lexical overlap alone is insufficient when another supplied item better explains the need.',
    `Return ONLY one JSON object matching schema ${schema}.`,
    '',
    ...librarianMediationContractPromptLines({ sampleSourceId }),
  ].join('\n');
}

export function buildLibrarianMediationCorrectionPrompt({ priorRaw, structuralError, context }) {
  const prior = typeof priorRaw === 'string' ? priorRaw : JSON.stringify(priorRaw ?? {});
  const sampleSourceId = context?.sampleSourceId ?? [...(context?.catalogIds ?? [])][0] ?? 'lmi:cand:example-source';
  const contractPrompt = buildLibrarianMediationPrompt({
    sampleSourceId,
  });
  return [
    'CONTRACT CORRECTION: Your previous Librarian mediation response did not satisfy the required machine contract.',
    'Preserve the intended semantic selections and synthesis meaning from that response unless satisfying the contract logically requires otherwise.',
    'Correct ONLY representation/serialization. Do NOT independently redo knowledge selection.',
    'Do NOT invent new source_id values outside the mediation catalog.',
    'Output JSON only — no markdown, no commentary.',
    '',
    `Previous response:\n${prior}`,
    '',
    `Structural validation error: ${structuralError}`,
    '',
    'Required contract:',
    contractPrompt,
    '',
    'Re-emit the result using exactly the required JSON contract.',
  ].join('\n');
}

export function parseLibrarianMediationResult(raw, catalogSourceIds = new Set()) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_failed'), result: null };
  }
  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'not_object', result: null };
  }
  if (String(parsed.schema ?? '') !== LIBRARIAN_MEDIATION_RESULT_SCHEMA) {
    return { ok: false, error: 'schema_mismatch', result: null };
  }

  const selectedItems = [];
  for (const [index, item] of (parsed.selected_items ?? []).entries()) {
    if (!item || typeof item !== 'object') {
      return { ok: false, error: `selected_items[${index}]`, result: null };
    }
    const sourceId = String(item.source_id ?? '').trim();
    if (!sourceId) {
      return { ok: false, error: `selected_items[${index}].source_id`, result: null };
    }
    if (catalogSourceIds.size > 0 && !catalogSourceIds.has(sourceId)) {
      return { ok: false, error: `unknown_source:${sourceId}`, result: null };
    }
    const rank = Number(item.relevance_rank);
    if (!Number.isFinite(rank) || rank <= 0) {
      return { ok: false, error: `selected_items[${index}].relevance_rank`, result: null };
    }
    const band = item.relevance_band == null ? null : String(item.relevance_band);
    if (band != null && !VALID_BAND.has(band)) {
      return { ok: false, error: `selected_items[${index}].relevance_band`, result: null };
    }
    const status = item.interpretive_status == null ? null : String(item.interpretive_status);
    if (status != null && !VALID_STATUS.has(status)) {
      return { ok: false, error: `selected_items[${index}].interpretive_status`, result: null };
    }
    selectedItems.push({
      source_id: sourceId,
      relevance_rank: rank,
      relevance_band: band,
      salience_note: String(item.salience_note ?? '').trim() || null,
      interpretive_status: status,
      answers_focus_questions: asStringArray(item.answers_focus_questions),
    });
  }

  const synthesisEntries = [];
  for (const [index, item] of (parsed.synthesis_entries ?? []).entries()) {
    if (!item || typeof item !== 'object') {
      return { ok: false, error: `synthesis_entries[${index}]`, result: null };
    }
    const kind = String(item.synthesis_kind ?? '').trim();
    if (!VALID_SYNTH.has(kind)) {
      return { ok: false, error: `synthesis_entries[${index}].synthesis_kind`, result: null };
    }
    const content = String(item.content ?? '').trim();
    const sourceIds = asStringArray(item.source_ids);
    if (!content || sourceIds.length === 0) {
      return { ok: false, error: `synthesis_entries[${index}]`, result: null };
    }
    for (const sourceId of sourceIds) {
      if (catalogSourceIds.size > 0 && !catalogSourceIds.has(sourceId)) {
        return { ok: false, error: `synthesis_unknown_source:${sourceId}`, result: null };
      }
    }
    synthesisEntries.push({
      synthesis_id: String(item.synthesis_id ?? `synth-${index}`),
      synthesis_kind: kind,
      content,
      source_ids: sourceIds,
      interpretive_status: VALID_STATUS.has(String(item.interpretive_status ?? ''))
        ? String(item.interpretive_status)
        : 'likely',
    });
  }

  const connections = [];
  for (const [index, item] of (parsed.connections ?? []).entries()) {
    if (!item || typeof item !== 'object') continue;
    const edge = String(item.edge_kind ?? '').trim();
    const fromId = String(item.from_source_id ?? '').trim();
    const toId = String(item.to_source_id ?? '').trim();
    if (!VALID_EDGE.has(edge) || !fromId || !toId) continue;
    connections.push({
      connection_id: String(item.connection_id ?? `conn-${index}`),
      edge_kind: edge,
      from_source_id: fromId,
      to_source_id: toId,
      note: String(item.note ?? '').trim() || null,
    });
  }

  return {
    ok: true,
    error: null,
    result: {
      schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
      selected_items: selectedItems,
      synthesis_entries: synthesisEntries,
      connections,
      focus_question_outcomes: Array.isArray(parsed.focus_question_outcomes)
        ? parsed.focus_question_outcomes
        : [],
    },
  };
}

export function manifestFromLibrarianPrepareResponse(prepareResponse) {
  return bridgeManifestFromHostPrepare(
    prepareResponse,
    normalizeBridgeContributions(prepareResponse.contributions),
  );
}
