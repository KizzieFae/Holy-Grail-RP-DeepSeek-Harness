import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH1B_SCHEMAS, LH1B_SCENARIO_FAMILIES } from './issue201-lh1b-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '../../../..');
export const LH1B_FIXTURE_ROOT = path.join(REPO_ROOT, 'governance/records/issue201-lh1b-fixtures');

const FIXTURE_FILES = {
  [LH1B_SCENARIO_FAMILIES.AYAME]: 'ayame_lh1b_fixture_v1.json',
};

export function loadLh1bFixtureManifest(scenarioKey = LH1B_SCENARIO_FAMILIES.AYAME) {
  const fileName = FIXTURE_FILES[scenarioKey];
  if (!fileName) throw new Error(`unknown LH-1B scenario: ${scenarioKey}`);
  const manifestPath = path.join(LH1B_FIXTURE_ROOT, fileName);
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (raw.schema !== LH1B_SCHEMAS.FIXTURE_MANIFEST) {
    throw new Error(`unexpected fixture schema: ${raw.schema}`);
  }
  return raw;
}

export function fixturePathForScenario(scenarioKey = LH1B_SCENARIO_FAMILIES.AYAME) {
  const fileName = FIXTURE_FILES[scenarioKey];
  return path.join(LH1B_FIXTURE_ROOT, fileName);
}

export function sceneForTurn(fixture, turnIndex) {
  return fixture.scenes.find(
    (s) => turnIndex >= s.turn_range[0] && turnIndex <= s.turn_range[1],
  ) ?? null;
}

export function listLh1bDecisionForks(fixture) {
  return fixture?.causal_design?.decision_forks ?? [];
}

export function forkForTurn(fixture, turnIndex, { consumer = null } = {}) {
  return listLh1bDecisionForks(fixture).filter((f) => {
    if (f.decision_turn !== turnIndex) return false;
    if (consumer && f.consumer !== consumer) return false;
    return true;
  });
}

export function obligationById(fixture, obligationId) {
  return fixture.obligations.find((o) => o.obligation_id === obligationId) ?? null;
}
