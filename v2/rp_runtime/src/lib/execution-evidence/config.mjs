import path from 'node:path';

import { defaultDataDir } from '../runtime-config.mjs';

const FALSE_VALUES = new Set(['0', 'false', 'off', 'no']);

/**
 * @returns {boolean} Whether durable execution evidence is enabled (default: on).
 */
export function isExecutionEvidenceEnabled(env = process.env) {
  const raw = String(env.HG_EXECUTION_EVIDENCE ?? 'on').trim().toLowerCase();
  return !FALSE_VALUES.has(raw);
}

/**
 * Root directory for session-scoped execution evidence trees.
 */
export function executionEvidenceRoot(env = process.env) {
  const explicit = String(env.HG_EXECUTION_EVIDENCE_DIR ?? '').trim();
  if (explicit) return path.resolve(explicit);
  return path.join(defaultDataDir(env), 'execution_evidence');
}

export const ATTEMPT_SCHEMA = 'hg_execution_evidence_attempt_v1';
export const INDEX_SCHEMA = 'hg_execution_evidence_index_v1';
export const NI_FORENSICS_CONTRACT = 'hg_ni_forensics_v1';
export const ASSEMBLED_REQUEST_SCHEMA = 'hg_assembled_request_v1';
export const MODEL_RESPONSE_SCHEMA = 'hg_model_response_v1';
