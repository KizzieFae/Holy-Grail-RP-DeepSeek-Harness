import fs from 'node:fs';
import path from 'node:path';

import {
  readForensicIndex,
  readExecutionAttempts,
} from '../../tests/helpers/plot-cognition-projection-fixtures.mjs';

export { readForensicIndex, readExecutionAttempts };

export function chronicleKeysForScope(forensicsDir, scopeId) {
  const index = readForensicIndex(forensicsDir, scopeId);
  if (!index?.by_idempotency_key) return [];
  return Object.keys(index.by_idempotency_key);
}

export function evidenceIdsForSession(dataDir, hgSessionId) {
  const attempts = readExecutionAttempts(dataDir, hgSessionId);
  return attempts.map((attempt) => attempt.evidence_id ?? attempt.attempt_id).filter(Boolean);
}

export function findChronicleOperationKeys(forensicsDir, scopeId, fragment) {
  return chronicleKeysForScope(forensicsDir, scopeId).filter((key) => key.includes(fragment));
}

export function joinScenarioForensics({
  forensicsDir,
  dataDir,
  scopeId,
  hgSessionId,
  batchId = null,
}) {
  const chronicleKeys = chronicleKeysForScope(forensicsDir, scopeId);
  const evidenceIds = hgSessionId ? evidenceIdsForSession(dataDir, hgSessionId) : [];
  const gaps = [];
  if (!chronicleKeys.length) gaps.push('missing_chronicle_index');
  if (hgSessionId && !evidenceIds.length) gaps.push('missing_execution_evidence');
  if (batchId && !chronicleKeys.some((key) => key.includes(batchId))) {
    gaps.push('batch_not_in_chronicle');
  }
  return { chronicleKeys, evidenceIds, integrityGaps: gaps };
}

export function loadOverlayStore(sessionsDir, scopeId) {
  const safe = scopeId.replace(/\//g, '_').replace(/\\/g, '_');
  const storePath = path.join(sessionsDir, '_plot_cognition_overlay', `${safe}.json`);
  if (!fs.existsSync(storePath)) return null;
  return JSON.parse(fs.readFileSync(storePath, 'utf8'));
}
