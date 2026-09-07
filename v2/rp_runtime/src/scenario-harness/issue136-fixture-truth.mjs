import fs from 'node:fs';
import path from 'node:path';

import { repoRoot } from '../lib/runtime-config.mjs';

export const ISSUE136_TRUTH_SCHEMA = 'issue136_tier2_truth_v1';

const FIXTURE_ROOT = path.join(repoRoot, 'data', 'fixtures', 'issue136_tier2_fidelity');
const TRUTH_DIR = path.join(FIXTURE_ROOT, 'truth');
const CARDS_DIR = path.join(FIXTURE_ROOT, 'cards');

export const ISSUE136_FIXTURE_IDS = [
  '136-T2-A-STABILITY',
  '136-T2-B-POS-CHANGE',
  '136-T2-C-NEG-CHANGE',
  '136-T2-D-INACTION',
  '136-T2-E-ENTITLEMENT',
  '136-T2-F-ACTION-REQUIRED',
];

const TRUTH_FILE_BY_ID = {
  '136-T2-A-STABILITY': '136-t2-a-stability.json',
  '136-T2-B-POS-CHANGE': '136-t2-b-pos-change.json',
  '136-T2-C-NEG-CHANGE': '136-t2-c-neg-change.json',
  '136-T2-D-INACTION': '136-t2-d-inaction.json',
  '136-T2-E-ENTITLEMENT': '136-t2-e-entitlement.json',
  '136-T2-F-ACTION-REQUIRED': '136-t2-f-action-required.json',
};

const REQUIRED_TRUTH_FIELDS = [
  'schema_version',
  'fixture_id',
  'character_id',
  'cast',
  'character_cards',
  'turn_structure',
  'committed_facts',
  'character_knowledge',
  'scene_stimulus',
  'supported_envelope',
  'ambiguous_envelope',
  'unsupported_envelope',
  'adjudication_dimensions',
];

const ADJUDICATOR_ONLY_KEYS = new Set([
  'supported_envelope',
  'ambiguous_envelope',
  'unsupported_envelope',
  'forbidden_leaks',
  'storyteller_advisory_notes',
  'adjudication_dimensions',
  'truth_file',
]);

export function issue136FixtureRoot() {
  return FIXTURE_ROOT;
}

export function issue136TruthDir() {
  return TRUTH_DIR;
}

export function issue136CardsDir() {
  return CARDS_DIR;
}

export function issue136TruthPath(fixtureId) {
  const file = TRUTH_FILE_BY_ID[fixtureId];
  if (!file) {
    throw new Error(`unknown_issue136_fixture:${fixtureId}`);
  }
  return path.join(TRUTH_DIR, file);
}

export function listIssue136TruthFixtures() {
  return ISSUE136_FIXTURE_IDS.map((fixtureId) => ({
    fixture_id: fixtureId,
    path: issue136TruthPath(fixtureId),
  }));
}

export function loadIssue136TruthFixture(fixtureId) {
  const filePath = issue136TruthPath(fixtureId);
  if (!fs.existsSync(filePath)) {
    throw new Error(`missing_issue136_truth:${fixtureId}`);
  }
  const truth = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  validateIssue136TruthSchema(truth, fixtureId);
  return truth;
}

export function validateIssue136TruthSchema(truth, expectedFixtureId = null) {
  if (!truth || typeof truth !== 'object') {
    throw new Error('issue136_truth_invalid: not an object');
  }
  if (truth.schema_version !== ISSUE136_TRUTH_SCHEMA) {
    throw new Error(`issue136_truth_invalid schema:${truth.schema_version}`);
  }
  if (expectedFixtureId && truth.fixture_id !== expectedFixtureId) {
    throw new Error(`issue136_truth_fixture_mismatch:${truth.fixture_id}`);
  }
  for (const field of REQUIRED_TRUTH_FIELDS) {
    if (truth[field] === undefined || truth[field] === null) {
      throw new Error(`issue136_truth_missing:${field}`);
    }
  }
  if (truth.turn_zero_perception === true) {
    const prose = String(truth.turn_zero_observable_stimulus ?? truth.scene_stimulus ?? '').trim();
    if (!prose) {
      throw new Error(`issue136_truth_missing_turn_zero_stimulus:${truth.fixture_id}`);
    }
  }
  if (!Array.isArray(truth.cast) || truth.cast.length < 1) {
    throw new Error('issue136_truth_invalid: cast');
  }
  if (!truth.turn_structure || typeof truth.turn_structure !== 'object') {
    throw new Error('issue136_truth_invalid: turn_structure');
  }
  if (!Array.isArray(truth.turn_structure.live_character_turns)) {
    throw new Error('issue136_truth_invalid: live_character_turns');
  }
  for (const envelopeKey of ['supported_envelope', 'ambiguous_envelope', 'unsupported_envelope']) {
    const envelope = truth[envelopeKey];
    if (!envelope || typeof envelope !== 'object' || !envelope.summary) {
      throw new Error(`issue136_truth_invalid:${envelopeKey}`);
    }
  }
  return truth;
}

export function truthAdjudicatorPayload(truth) {
  const payload = {};
  for (const key of ADJUDICATOR_ONLY_KEYS) {
    if (truth[key] !== undefined) payload[key] = truth[key];
  }
  return payload;
}

/**
 * Guardrail: adjudicator-only truth must not appear in model/session-facing payloads.
 */
export function assertTruthNotInModelPayload(payload, truth = null) {
  const serialized = JSON.stringify(payload ?? {}).toLowerCase();
  const needles = [
    'unsupported_envelope',
    'ambiguous_envelope',
    'adjudication_dimensions',
    'examples_not_requirements',
    'forbidden_leaks',
    'storyteller_advisory_notes',
    'issue136_tier2_truth_v1',
  ];
  for (const needle of needles) {
    if (serialized.includes(needle)) {
      throw new Error(`truth_contamination:${needle}`);
    }
  }
  if (truth?.forbidden_leaks?.length) {
    for (const token of truth.forbidden_leaks) {
      const normalized = String(token).toLowerCase();
      if (normalized && serialized.includes(normalized)) {
        throw new Error(`truth_contamination:forbidden_leak:${token}`);
      }
    }
  }
}

export function detectIssue136ForbiddenLeaks(text, truth, targetCharacter = null) {
  const haystack = String(text ?? '').toLowerCase();
  const leaks = [];
  const globalForbidden = truth?.forbidden_leaks ?? [];
  for (const token of globalForbidden) {
    const normalized = String(token).toLowerCase();
    if (normalized && haystack.includes(normalized)) {
      leaks.push({ token, scope: 'global' });
    }
  }
  const perCharacter = truth?.forbidden_leaks_to?.[targetCharacter] ?? [];
  for (const token of perCharacter) {
    const normalized = String(token).toLowerCase();
    if (normalized && haystack.includes(normalized)) {
      leaks.push({ token, scope: 'character', target_character: targetCharacter });
    }
  }
  return leaks;
}

export function installIssue136ValidationCards(dataDir) {
  const dest = path.join(dataDir, 'characters');
  fs.mkdirSync(dest, { recursive: true });
  const installed = [];
  for (const name of fs.readdirSync(CARDS_DIR)) {
    if (!name.endsWith('.json')) continue;
    fs.copyFileSync(path.join(CARDS_DIR, name), path.join(dest, name));
    installed.push(name.replace(/\.json$/, ''));
  }
  return installed;
}

export function loadIssue136ValidationCard(cardId) {
  const cardPath = path.join(CARDS_DIR, `${cardId}.json`);
  if (!fs.existsSync(cardPath)) {
    throw new Error(`missing_issue136_card:${cardId}`);
  }
  return JSON.parse(fs.readFileSync(cardPath, 'utf8'));
}
