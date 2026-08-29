import crypto from 'node:crypto';

import { parseJsonObject } from './inference-utils.mjs';

export const PLOT_COGNITION_INIT_PROPOSAL_SCHEMA = 'hg_plot_cognition_init_proposal_v1';

const FORBIDDEN_INIT_WRAPPERS = [
  'plot_cognition_initialize_proposal',
  'plot_cognition_init_proposal',
];

const FORBIDDEN_INIT_SCHEMA_NAMES = [
  'hg_plot_cognition_initialize_proposal_v1',
];

export function buildPlotCognitionInitPrompt(initPrepare) {
  const snapshot = initPrepare?.source_snapshot ?? {};
  const scopeId = snapshot.plot_cognition_scope_id ?? '';
  const fingerprint = initPrepare?.source_snapshot_fingerprint ?? snapshot.fingerprint ?? '';
  const snapshotId = snapshot.snapshot_id ?? '';

  return [
    'You are the Plot Cognition initialization semantic producer.',
    `Return ONLY one JSON object (no markdown fences, no commentary) with schema ${PLOT_COGNITION_INIT_PROPOSAL_SCHEMA}.`,
    'Required top-level fields:',
    `- schema: "${PLOT_COGNITION_INIT_PROPOSAL_SCHEMA}"`,
    '- proposal_id: new unique string',
    `- source_snapshot_id: copy "${snapshotId}" verbatim`,
    `- source_snapshot_fingerprint: copy "${fingerprint}" verbatim`,
    `- plot_cognition_scope_id: copy "${scopeId}" verbatim — do not invent or transform`,
    '- adoption_rationale: non-empty string explaining adoption',
    'Optional: goals[], pressures[], global_frame, per_item_rationale[].',
    'Do NOT use alternate wrapper keys such as plot_cognition_initialize_proposal.',
    `Do NOT use alternate schema names such as ${FORBIDDEN_INIT_SCHEMA_NAMES.join(' or ')}.`,
    'Do NOT return overlay/character_arcs shapes — use goals and pressures arrays.',
    `Minimal example: {"schema":"${PLOT_COGNITION_INIT_PROPOSAL_SCHEMA}","proposal_id":"hg-plot-init-proposal-example","source_snapshot_id":"${snapshotId}","source_snapshot_fingerprint":"${fingerprint}","plot_cognition_scope_id":"${scopeId}","adoption_rationale":"Adopt initial pressures from authoritative sources.","goals":[],"pressures":[]}`,
  ].join('\n');
}

export function buildPlotCognitionInitCorrectionPrompt({ priorRaw, structuralError, context }) {
  const initPrepare = context ?? {};
  const contractPrompt = buildPlotCognitionInitPrompt(initPrepare);
  const prior = typeof priorRaw === 'string' ? priorRaw : JSON.stringify(priorRaw ?? {});
  return [
    'CONTRACT CORRECTION: Your previous response did not satisfy the required machine contract.',
    'Preserve the semantic judgment from that response unless satisfying the contract logically requires otherwise.',
    'Correct only the representation/serialization. Output JSON only — no markdown, no commentary.',
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

function newId(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function extractInitProposalRoot(parsed) {
  if (!parsed || typeof parsed !== 'object') {
    return { root: null, error: 'invalid_json_object' };
  }
  for (const wrapper of FORBIDDEN_INIT_WRAPPERS) {
    if (Object.prototype.hasOwnProperty.call(parsed, wrapper)) {
      return { root: null, error: `forbidden_wrapper:${wrapper}` };
    }
  }
  if (parsed.proposal && typeof parsed.proposal === 'object') {
    return { root: parsed.proposal, error: null };
  }
  return { root: parsed, error: null };
}

export function parsePlotCognitionInitProposal(raw, initPrepare) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_error'), result: null };
  }

  const { root, error: wrapperError } = extractInitProposalRoot(parsed);
  if (wrapperError) {
    return { ok: false, error: wrapperError, result: null };
  }
  if (!root || typeof root !== 'object') {
    return { ok: false, error: 'missing_proposal', result: null };
  }

  const schema = String(root.schema ?? '').trim();
  if (schema !== PLOT_COGNITION_INIT_PROPOSAL_SCHEMA) {
    if (FORBIDDEN_INIT_SCHEMA_NAMES.includes(schema)) {
      return { ok: false, error: `forbidden_schema:${schema}`, result: null };
    }
    return { ok: false, error: 'schema_mismatch', result: null };
  }

  const snapshot = initPrepare?.source_snapshot ?? {};
  const authoritativeScope = String(snapshot.plot_cognition_scope_id ?? '').trim();
  const authoritativeFingerprint = String(
    initPrepare?.source_snapshot_fingerprint ?? snapshot.fingerprint ?? '',
  ).trim();

  const proposalId = String(root.proposal_id ?? '').trim();
  const scopeId = String(root.plot_cognition_scope_id ?? '').trim();
  const fingerprint = String(root.source_snapshot_fingerprint ?? '').trim();
  const adoptionRationale = String(root.adoption_rationale ?? '').trim();

  if (!proposalId) return { ok: false, error: 'proposal_id_required', result: null };
  if (!adoptionRationale) return { ok: false, error: 'adoption_rationale_required', result: null };
  if (!scopeId) return { ok: false, error: 'plot_cognition_scope_id_required', result: null };
  if (authoritativeScope && scopeId !== authoritativeScope) {
    return { ok: false, error: 'plot_cognition_scope_id_mismatch', result: null };
  }
  if (authoritativeFingerprint && fingerprint && fingerprint !== authoritativeFingerprint) {
    return { ok: false, error: 'source_snapshot_fingerprint_mismatch', result: null };
  }

  if (root.overlay || root.character_arcs) {
    return { ok: false, error: 'forbidden_shape:overlay', result: null };
  }

  const proposal = {
    schema: PLOT_COGNITION_INIT_PROPOSAL_SCHEMA,
    proposal_id: proposalId,
    source_snapshot_id: String(root.source_snapshot_id ?? snapshot.snapshot_id ?? ''),
    source_snapshot_fingerprint: fingerprint || authoritativeFingerprint,
    plot_cognition_scope_id: scopeId,
    adoption_rationale: adoptionRationale,
    goals: Array.isArray(root.goals) ? root.goals : [],
    pressures: Array.isArray(root.pressures) ? root.pressures : [],
    global_frame: root.global_frame ?? null,
    per_item_rationale: Array.isArray(root.per_item_rationale) ? root.per_item_rationale : [],
    revision_of_proposal_id: root.revision_of_proposal_id ?? null,
  };

  if (!proposal.source_snapshot_fingerprint) {
    return { ok: false, error: 'source_snapshot_fingerprint_required', result: null };
  }

  return { ok: true, error: null, result: proposal };
}

export function buildMinimalInitProposal(initPrepare) {
  const snapshot = initPrepare?.source_snapshot ?? {};
  return JSON.stringify({
    schema: PLOT_COGNITION_INIT_PROPOSAL_SCHEMA,
    proposal_id: newId('hg-plot-init-proposal'),
    source_snapshot_id: snapshot.snapshot_id ?? '',
    source_snapshot_fingerprint: initPrepare?.source_snapshot_fingerprint ?? snapshot.fingerprint ?? '',
    plot_cognition_scope_id: snapshot.plot_cognition_scope_id ?? '',
    adoption_rationale: 'Adopt initial narrative pressures from authoritative sources.',
    goals: [],
    pressures: [],
  });
}
