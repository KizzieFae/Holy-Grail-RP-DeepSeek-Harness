import { parseJsonObject } from './inference-utils.mjs';
import { bridgeManifestFromHostPrepare } from './bridge-manifest.mjs';

export const LIBRARIAN_PROPOSAL_RESULT_SCHEMA = 'hg_librarian_proposal_result_v1';
export const LIBRARIAN_PROPOSAL_CONFIG_ID = 'librarian_proposal_v1';

const VALID_CONFIDENCE = new Set(['confirmed', 'likely', 'speculative']);
const VALID_KINDS = new Set([
  'consequence_meaning',
  'information_salience',
  'knowledge_revelation_significance',
  'issue_tension_pressure',
]);

const CONSEQUENCE_TAGS = [
  'advancement',
  'complication',
  'revelation',
  'resolution_candidate',
  'relationship_shift',
  'tension_escalation',
  'tension_release',
];

const SALIENCE_LEVELS = ['minor', 'major', 'pivotal'];
const INTERPRETATION_SCOPES = ['utterance_occurrence', 'referenced_authoritative_proposition'];

const FORBIDDEN_PROPOSAL_FIELD_ALIASES = [
  'change_kind',
  'target',
  'type',
  'candidate_id',
  'info_kind',
];

function asStringArray(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? '').trim()).filter(Boolean);
}

/**
 * Canonical machine-readable Librarian proposal output contract (#72).
 * Single source for prompts and correction prompts.
 */
export function buildLibrarianProposalContractSpec({
  sampleAnchorId = 'committed_move:COMMIT_ID',
  domainCommitId = 'COMMIT_ID',
} = {}) {
  const anchorId = String(sampleAnchorId || `committed_move:${domainCommitId}`);
  const commitId = String(domainCommitId || 'COMMIT_ID');
  return {
    schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    top_level: {
      schema: `exact string "${LIBRARIAN_PROPOSAL_RESULT_SCHEMA}"`,
      proposals: 'array (required; may be empty when no grounded proposal exists)',
    },
    proposal_fields: {
      proposal_kind: [...VALID_KINDS].join(' | '),
      derivation_summary: 'non-empty string',
      confidence: [...VALID_CONFIDENCE].join(' | '),
      proposed_payload: 'object (per-kind shape below)',
      evidence_anchors: 'non-empty array of objects: { anchor_id, evidence_kind, anchor_commit_id?, anchor_path? }',
      proposal_id: 'optional string',
      affected_entities: 'optional string[]',
      affected_state_classes: 'optional string[]',
      source_bundle_id: 'optional string',
    },
    payload_by_kind: {
      consequence_meaning: `{ tags: non-empty string[] from ${CONSEQUENCE_TAGS.join('|')} }`,
      information_salience: `{ subject_ref: string, salience_level: ${SALIENCE_LEVELS.join('|')} }`,
      knowledge_revelation_significance: `{ event_ref, subject_character, revelation_significance_level: ${SALIENCE_LEVELS.join('|')}, interpretation_scope: ${INTERPRETATION_SCOPES.join('|')}, proposition_authority_refs?: string[] (required when interpretation_scope=referenced_authoritative_proposition; must cite world_truth_eligible catalog anchors) }`,
      issue_tension_pressure: '{ issue_ref, semantic_unmet_condition, stakes_summary? }',
    },
    forbidden: [
      `Do NOT use field aliases: ${FORBIDDEN_PROPOSAL_FIELD_ALIASES.join(', ')} — use proposal_kind and proposed_payload.`,
      'Do NOT use string entries in evidence_anchors — each anchor must be an object.',
      'Do NOT omit the top-level schema field.',
      'Do NOT use preservation_signal anchors.',
      'Do NOT invent anchor_id values outside the evidence catalog.',
    ],
    minimal_example: {
      schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
      proposals: [
        {
          proposal_id: 'prop-example-1',
          proposal_kind: 'information_salience',
          derivation_summary: 'Committed move advances scene salience.',
          confidence: 'likely',
          evidence_anchors: [
            {
              anchor_id: anchorId,
              evidence_kind: 'committed_move',
              anchor_commit_id: commitId,
            },
          ],
          proposed_payload: {
            subject_ref: `commit:${commitId}`,
            salience_level: 'major',
          },
        },
      ],
    },
  };
}

export function librarianProposalContractPromptLines(context = {}) {
  const spec = buildLibrarianProposalContractSpec(context);
  return [
    'Required top-level JSON object:',
    `- schema: "${spec.schema}"`,
    '- proposals: array',
    '',
    'Each proposal object MUST include:',
    `- proposal_kind: one of ${spec.proposal_fields.proposal_kind}`,
    '- derivation_summary: non-empty string',
    `- confidence: one of ${spec.proposal_fields.confidence}`,
    '- proposed_payload: object matching proposal_kind (see below)',
    '- evidence_anchors: non-empty array of objects with anchor_id and evidence_kind from the catalog only',
    '',
    'proposed_payload by proposal_kind:',
    `- consequence_meaning: ${spec.payload_by_kind.consequence_meaning}`,
    `- information_salience: ${spec.payload_by_kind.information_salience}`,
    `- knowledge_revelation_significance: ${spec.payload_by_kind.knowledge_revelation_significance}`,
    `- issue_tension_pressure: ${spec.payload_by_kind.issue_tension_pressure}`,
    '',
    'Forbidden:',
    ...spec.forbidden.map((line) => `- ${line}`),
    '',
    `Minimal example (replace anchor_id with a catalog value such as "${spec.minimal_example.proposals[0].evidence_anchors[0].anchor_id}"):`,
    JSON.stringify(spec.minimal_example, null, 2),
  ];
}

export function buildLibrarianProposalPrompt(context = {}) {
  return [
    'You are the Holy Grail Librarian post-commit semantic interpreter.',
    'Propose grounded information-level persistence/change candidates ONLY from evidence catalog anchor_id values.',
    'Do NOT invent facts, authority, or continuity commits.',
    'Do NOT use Storyteller PreservationSignal or attention refs as evidence.',
    'Occurrence truth ≠ proposition truth: public_event and committed_move anchors prove what occurred or was said; they do NOT establish objective world truth of claims inside dialogue.',
    'For knowledge_revelation_significance:',
    '- interpretation_scope utterance_occurrence: mark significance of what the Character said/claimed/expressed without endorsing the proposition as world truth. derivation_summary must frame significance of the utterance/claim, not objective ontology.',
    '- interpretation_scope referenced_authoritative_proposition: connect the occurrence to a proposition that already has independent world authority; cite proposition_authority_refs to catalog anchors with world_truth_eligible metadata (e.g. scenario_premise).',
    '- authored_role_private anchors support private epistemic alignment only; they cannot be the sole world-truth authority.',
    'Return ONLY one JSON object (no markdown fences, no commentary).',
    '',
    ...librarianProposalContractPromptLines(context),
  ].join('\n');
}

export function buildLibrarianProposalCorrectionPrompt({ priorRaw, structuralError, context }) {
  const prior = typeof priorRaw === 'string' ? priorRaw : JSON.stringify(priorRaw ?? {});
  const contractPrompt = buildLibrarianProposalPrompt(context ?? {});
  return [
    'CONTRACT CORRECTION: Your previous response did not satisfy the required Librarian proposal machine contract.',
    'Preserve the intended proposal meaning and cited evidence from that response unless satisfying the contract logically requires otherwise.',
    'Correct ONLY representation/serialization. Do NOT invent new evidence, anchors, or unrelated proposals.',
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
  return bridgeManifestFromHostPrepare(
    prepareResponse,
    prepareResponse.contributions ?? [],
  );
}
