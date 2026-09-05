/** Deterministic uniform-projection synthesis envelope (#121). */

import { createHash } from 'node:crypto';

export const UNIFORM_PROJECTION_KIND = 'uniform_projection';
export const UNIFORM_PROJECTION_DERIVATION_PROFILE = 'uniform_projection';
export const UNIFORM_PROJECTION_SYNTHESIS_ROUTE = 'checker_uniform';
export const UNIFORM_PROJECTION_SYNTHESIS_SOURCE = 'player_uniform_synthesis';
export const SEMANTIC_DECOMPOSITION_NOT_PERFORMED = 'not_performed';
export const UNIFORM_PROJECTION_UNIT_ID = 'u_uniform';
export const UNIFORM_PROJECTION_SEGMENT_ID = 's_uniform';
export const SOURCE_ACCOUNTING_NORMALIZATION = 'nfc_crlf_to_lf';

function normalizeForIndexing(content) {
  return String(content ?? '').normalize('NFC').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

function normalizedSourceSha256(normalized) {
  return createHash('sha256').update(normalized, 'utf8').digest('hex');
}

export function buildUniformProjectionDecomposition(playerContent, { checkerAudit = {}, inferenceId = null } = {}) {
  const normalized = normalizeForIndexing(playerContent);
  const length = normalized.length;
  const checker = { ...checkerAudit };
  if (inferenceId) {
    checker.inference_id = checker.inference_id ?? inferenceId;
  }

  if (!length) {
    return {
      perceptual_visibility: { units: [] },
      source_accounting: {
        source_length: 0,
        source_sha256: normalizedSourceSha256(normalized),
        normalization: SOURCE_ACCOUNTING_NORMALIZATION,
        segments: [
          {
            segment_id: UNIFORM_PROJECTION_SEGMENT_ID,
            char_start: 0,
            char_end: 0,
            disposition: 'non_projects',
            unit_ids: [],
          },
        ],
      },
      generation: {
        derivation_profile: UNIFORM_PROJECTION_DERIVATION_PROFILE,
        semantic_decomposition: SEMANTIC_DECOMPOSITION_NOT_PERFORMED,
        synthesis_route: UNIFORM_PROJECTION_SYNTHESIS_ROUTE,
        checker,
      },
    };
  }

  return {
    perceptual_visibility: {
      units: [
        {
          unit_id: UNIFORM_PROJECTION_UNIT_ID,
          kind: UNIFORM_PROJECTION_KIND,
          text: normalized,
          recipients: { scope: 'present', characters: [], roles: [] },
          source_provenance: {
            segment_ids: [UNIFORM_PROJECTION_SEGMENT_ID],
            order_index: 0,
          },
          source: UNIFORM_PROJECTION_SYNTHESIS_SOURCE,
        },
      ],
    },
    source_accounting: {
      source_length: length,
      source_sha256: normalizedSourceSha256(normalized),
      normalization: SOURCE_ACCOUNTING_NORMALIZATION,
      segments: [
        {
          segment_id: UNIFORM_PROJECTION_SEGMENT_ID,
          char_start: 0,
          char_end: length,
          disposition: 'projects',
          unit_ids: [UNIFORM_PROJECTION_UNIT_ID],
        },
      ],
    },
    generation: {
      derivation_profile: UNIFORM_PROJECTION_DERIVATION_PROFILE,
      semantic_decomposition: SEMANTIC_DECOMPOSITION_NOT_PERFORMED,
      synthesis_route: UNIFORM_PROJECTION_SYNTHESIS_ROUTE,
      checker,
    },
  };
}
