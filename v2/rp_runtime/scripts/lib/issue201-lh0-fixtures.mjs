import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '../../../..');
export const LH0_FIXTURE_ROOT = path.join(REPO_ROOT, 'governance/records/issue201-lh0-fixtures');

export function loadLh0FixtureManifest() {
  const manifestPath = path.join(LH0_FIXTURE_ROOT, 'lh0_fixture_manifest.json');
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (raw.schema !== 'issue201_lh0_fixture_manifest_v1') {
    throw new Error(`unexpected fixture manifest schema: ${raw.schema}`);
  }
  return raw;
}
