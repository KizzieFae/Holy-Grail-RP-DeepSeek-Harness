import fs from 'node:fs';
import path from 'node:path';

import { repoRoot } from '../lib/runtime-config.mjs';

const TRUTH_DIR = path.join(repoRoot, 'data', 'fixtures', 'storyteller_tier1_truth');

export function truthFixturePath(fixtureId) {
  return path.join(TRUTH_DIR, `${fixtureId}.json`);
}

export function loadTruthFixture(fixtureId) {
  const filePath = truthFixturePath(fixtureId);
  if (!fs.existsSync(filePath)) {
    throw new Error(`missing_truth_fixture:${fixtureId}`);
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function listTruthFixtures() {
  if (!fs.existsSync(TRUTH_DIR)) return [];
  return fs.readdirSync(TRUTH_DIR)
    .filter((name) => name.endsWith('.json'))
    .map((name) => name.replace(/\.json$/, ''));
}
