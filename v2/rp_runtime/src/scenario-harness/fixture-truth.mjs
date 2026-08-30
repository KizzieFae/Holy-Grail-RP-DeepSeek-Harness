import fs from 'node:fs';
import path from 'node:path';

import { repoRoot } from '../lib/runtime-config.mjs';

const TRUTH_DIR = path.join(repoRoot, 'data', 'fixtures', 'storyteller_tier1_truth');
const TIER2_TRUTH_DIR = path.join(repoRoot, 'data', 'fixtures', 'storyteller_tier2_truth');

export function truthFixturePath(fixtureId, tier = 1) {
  const base = tier === 2 ? TIER2_TRUTH_DIR : TRUTH_DIR;
  return path.join(base, `${fixtureId}.json`);
}

export function loadTruthFixture(fixtureId, tier = 1) {
  const filePath = truthFixturePath(fixtureId, tier);
  if (!fs.existsSync(filePath)) {
    throw new Error(`missing_truth_fixture:${fixtureId}:tier${tier}`);
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function loadTier2TruthFixture(fixtureId) {
  return loadTruthFixture(fixtureId, 2);
}

export function listTruthFixtures(tier = 1) {
  const dir = tier === 2 ? TIER2_TRUTH_DIR : TRUTH_DIR;
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith('.json'))
    .map((name) => name.replace(/\.json$/, ''));
}
