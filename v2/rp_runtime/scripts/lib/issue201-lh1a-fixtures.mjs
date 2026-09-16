import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH1A_SCHEMAS, LH1A_SCENARIO_FAMILIES } from './issue201-lh1a-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '../../../..');
export const LH1A_FIXTURE_ROOT = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-fixtures');

const FIXTURE_FILES = {
  [LH1A_SCENARIO_FAMILIES.AYAME]: 'ayame_lh1a_fixture_v1.json',
  [LH1A_SCENARIO_FAMILIES.ARKHAM]: 'arkham_lh1a_fixture_v1.json',
};

export function loadLh1aFixtureManifest(scenarioKey) {
  const fileName = FIXTURE_FILES[scenarioKey];
  if (!fileName) throw new Error(`unknown LH-1A scenario: ${scenarioKey}`);
  const manifestPath = path.join(LH1A_FIXTURE_ROOT, fileName);
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (raw.schema !== LH1A_SCHEMAS.FIXTURE_MANIFEST) {
    throw new Error(`unexpected fixture schema: ${raw.schema}`);
  }
  return raw;
}

export function loadAllLh1aFixtures() {
  return Object.values(LH1A_SCENARIO_FAMILIES).map((key) => loadLh1aFixtureManifest(key));
}

export function sceneForTurn(fixture, turnIndex) {
  return fixture.scenes.find(
    (s) => turnIndex >= s.turn_range[0] && turnIndex <= s.turn_range[1],
  ) ?? null;
}

export function obligationClassesPresent(fixture) {
  return new Set(fixture.obligations.map((o) => o.class));
}
