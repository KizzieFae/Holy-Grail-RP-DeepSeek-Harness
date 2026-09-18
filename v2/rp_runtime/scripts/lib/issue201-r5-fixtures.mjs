import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { R5_SCHEMAS } from './issue201-r5-contract.mjs';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const R5_FIXTURE_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-r5-fixtures');

const FIXTURE_FILE = 'ayame_r5_fixture_v1.json';

export function loadR5FixtureManifest() {
  const manifestPath = path.join(R5_FIXTURE_ROOT, FIXTURE_FILE);
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (raw.schema !== R5_SCHEMAS.FIXTURE_MANIFEST) {
    throw new Error(`unexpected R5 fixture schema: ${raw.schema}`);
  }
  return raw;
}

export function fixturePathForR5() {
  return path.join(R5_FIXTURE_ROOT, FIXTURE_FILE);
}

export function forkForTurn(fixture, turnIndex, opts = {}) {
  const forks = fixture?.causal_design?.decision_forks ?? [];
  return forks.filter((f) => {
    if (f.decision_turn !== turnIndex) return false;
    if (opts.consumer && f.consumer !== opts.consumer) return false;
    return true;
  });
}

export function primaryR5Fork(fixture) {
  const forks = fixture?.causal_design?.decision_forks ?? [];
  if (forks.length !== 1) throw new Error('R5 fixture must define exactly one primary fork');
  return forks[0];
}

export function obligationById(fixture, obligationId) {
  return fixture.obligations.find((o) => o.obligation_id === obligationId) ?? null;
}

export function buildLhBManifestFromQualification(fixture) {
  const q = fixture.qualification;
  const lhA = q.lh_a_lean_manifest;
  const contrib = [...lhA.contributions, q.lh_b_persistence_contribution];
  return { manifest_id: 'r5-qual-lh-b', contributions: contrib };
}

export function buildLhAManifestFromQualification(fixture) {
  const q = fixture.qualification;
  return { manifest_id: 'r5-qual-lh-a', contributions: [...q.lh_a_lean_manifest.contributions] };
}
