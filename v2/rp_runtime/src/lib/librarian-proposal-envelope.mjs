import { parseJsonObject } from './inference-utils.mjs';

export const LIBRARIAN_PROPOSAL_RESULT_SCHEMA = 'hg_librarian_proposal_result_v1';
export const LIBRARIAN_PROPOSAL_CONFIG_ID = 'librarian_proposal_v1';

const VALID_CONFIDENCE = new Set(['confirmed', 'likely', 'speculative']);
const VALID_KINDS = new Set(['consequence_meaning', 'information_salience']);

function asStringArray(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? '').trim()).filter(Boolean);
}

export function buildLibrarianProposalPrompt({ schema = LIBRARIAN_PROPOSAL_RESULT_SCHEMA } = {}) {
  return [
    'You are the Holy Grail Librarian post-commit semantic interpreter.',
    'Propose grounded information-level persistence/change candidates ONLY from evidence catalog anchor_id values.',
    'Do NOT invent facts, authority, or continuity commits.',
    'Do NOT use Storyteller PreservationSignal or attention refs as evidence.',
    'Each proposal must include non-empty evidence_anchors and a derivation_summary.',
    `Return ONLY one JSON object matching schema ${schema}.`,
  ].join('\n');
}

export function parseLibrarianProposalResult(raw, catalogAnchorIds = new Set()) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_failed'), result: null };
  }
  if (!parsed || typeof parsed !== 'object') {
    return { ok: false, error: 'not_object', result: null };
  }
  if (String(parsed.schema ?? '') !== LIBRARIAN_PROPOSAL_RESULT_SCHEMA) {
    return { ok: false, error: 'schema_mismatch', result: null };
  }

  const proposals = [];
  for (const [index, item] of (parsed.proposals ?? []).entries()) {
    if (!item || typeof item !== 'object') {
      return { ok: false, error: `proposals[${index}]`, result: null };
    }
    const proposalKind = String(item.proposal_kind ?? '').trim();
    const derivationSummary = String(item.derivation_summary ?? '').trim();
    const confidence = String(item.confidence ?? '').trim();
    if (!proposalKind || !derivationSummary || !VALID_CONFIDENCE.has(confidence)) {
      return { ok: false, error: `proposals[${index}].required_fields`, result: null };
    }
    if (!VALID_KINDS.has(proposalKind)) {
      return { ok: false, error: `proposals[${index}].proposal_kind`, result: null };
    }
    const anchors = [];
    for (const [aIndex, anchor] of (item.evidence_anchors ?? []).entries()) {
      if (!anchor || typeof anchor !== 'object') {
        return { ok: false, error: `proposals[${index}].evidence_anchors[${aIndex}]`, result: null };
      }
      const anchorId = String(anchor.anchor_id ?? '').trim();
      const evidenceKind = String(anchor.evidence_kind ?? '').trim();
      if (!anchorId || !evidenceKind) {
        return { ok: false, error: `proposals[${index}].evidence_anchors[${aIndex}]`, result: null };
      }
      if (catalogAnchorIds.size > 0 && !catalogAnchorIds.has(anchorId)) {
        return { ok: false, error: `unknown_anchor:${anchorId}`, result: null };
      }
      if (evidenceKind === 'preservation_signal' || anchorId.startsWith('preservation_signal')) {
        return { ok: false, error: 'preservation_signal_not_evidence', result: null };
      }
      anchors.push({
        anchor_id: anchorId,
        evidence_kind: evidenceKind,
        anchor_path: String(anchor.anchor_path ?? '').trim() || null,
        anchor_commit_id: String(anchor.anchor_commit_id ?? '').trim() || null,
      });
    }
    if (!anchors.length) {
      return { ok: false, error: `proposals[${index}].evidence_anchors_empty`, result: null };
    }
    if (!item.proposed_payload || typeof item.proposed_payload !== 'object') {
      return { ok: false, error: `proposals[${index}].proposed_payload`, result: null };
    }
    proposals.push({
      proposal_id: String(item.proposal_id ?? '').trim() || null,
      proposal_kind: proposalKind,
      derivation_summary: derivationSummary,
      confidence,
      evidence_anchors: anchors,
      proposed_payload: item.proposed_payload,
      affected_entities: asStringArray(item.affected_entities),
      affected_state_classes: asStringArray(item.affected_state_classes),
      source_bundle_id: String(item.source_bundle_id ?? '').trim() || null,
    });
  }

  return {
    ok: true,
    error: null,
    result: {
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals,
    },
  };
}

export function manifestFromLibrarianProposalPrepareResponse(prepareResponse) {
  return {
    manifest_id: prepareResponse.manifest_id,
    inference_id: prepareResponse.inference_id,
    contributions: prepareResponse.contributions ?? [],
  };
}
