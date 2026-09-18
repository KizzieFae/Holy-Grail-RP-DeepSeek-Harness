import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { AGING_SCHEMAS, AGING_STATES, ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const AGING_FIXTURE_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-aging-fixtures');
export const AGING_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-aging-policies');

const FIXTURE_FILE = 'ayame_aging_fixture_v1.json';
const POLICY_FILE = 'ayame_aging_policy_v1.json';

export function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

export function semanticFingerprint(proposition) {
  return crypto.createHash('sha256')
    .update(String(proposition ?? '').toLowerCase().replace(/\s+/g, ' ').trim())
    .digest('hex');
}

export function loadAgingFixtureManifest() {
  const manifestPath = path.join(AGING_FIXTURE_ROOT, FIXTURE_FILE);
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (raw.schema !== AGING_SCHEMAS.FIXTURE_MANIFEST) {
    throw new Error(`unexpected aging fixture schema: ${raw.schema}`);
  }
  return raw;
}

export function loadAgingPolicy() {
  const filePath = path.join(AGING_POLICY_ROOT, POLICY_FILE);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (policy.schema !== AGING_SCHEMAS.PLAYER_POLICY) {
    throw new Error(`unexpected aging policy schema: ${policy.schema}`);
  }
  return {
    policy,
    policy_path: filePath,
    policy_hash: sha256File(filePath),
  };
}

export function buildTrackedItemRegistry(fixture = null) {
  const fx = fixture ?? loadAgingFixtureManifest();
  const items = (fx.tracked_items ?? []).map((item) => ({
    ...item,
    semantic_fingerprint: semanticFingerprint(item.semantic_proposition),
    establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
    establishment_attempted: false,
    establishment_turn_arm_a: null,
    establishment_turn_arm_b: null,
    establishment_evidence_arm_a: null,
    establishment_evidence_arm_b: null,
    semantic_establishment_arm_a: false,
    semantic_establishment_arm_b: false,
    paired_semantic_equivalence: null,
    aging_clock_started: false,
    aging_clock_start_turn_a: null,
    aging_clock_start_turn_b: null,
    contamination: null,
    causal_item_valid: true,
    aging_state: AGING_STATES.UNESTABLISHED,
    aging_history: [],
    last_raw_presence_turn: null,
    first_lean_other_turn: null,
    first_aged_out_turn: null,
    confirmatory_aged_out_turn: null,
    opportunity_eligible: false,
    tested_turn: null,
    persistence_provenance_chain: [],
  }));
  return {
    schema: AGING_SCHEMAS.TRACKED_ITEM_REGISTRY,
    fixture_id: fx.fixture_id,
    tracked_items: items,
  };
}

export function trackedItemById(fixture, trackedItemId) {
  return fixture.tracked_items.find((t) => t.tracked_item_id === trackedItemId) ?? null;
}

export function obligationById(fixture, obligationId) {
  return fixture.obligations.find((o) => o.obligation_id === obligationId) ?? null;
}

export function expandAgingPolicyTurns(policy, maxTurns) {
  const turns = [...policy.turns];
  const existing = new Set(turns.map((t) => t.turn_index));
  let i = 0;
  for (let turnIndex = 1; turnIndex <= maxTurns; turnIndex += 1) {
    if (existing.has(turnIndex)) continue;
    turns.push({
      turn_index: turnIndex,
      branch_mode: 'fixed',
      objective: 'Intervening — household evaluation',
      realization: INTERVENING_REALIZATIONS[i % INTERVENING_REALIZATIONS.length],
    });
    i += 1;
  }
  turns.sort((a, b) => a.turn_index - b.turn_index);
  return { ...policy, turns };
}

const INTERVENING_REALIZATIONS = [
  'Kizzie asks whether the pantry stores should be inventoried before the weekend.',
  'Kizzie offers to air the guest-room linens while the weather is dry.',
  'Kizzie mentions the front hall clock needs winding and asks if that is within staff duties.',
  'Kizzie asks whether visitors usually arrive through the main entrance or the service door.',
  'Kizzie offers to polish the foyer table before the household receives mail.',
  'Kizzie asks if there are household pets she should account for during rounds.',
  'Kizzie asks whether the kitchen range has been serviced recently.',
  'Kizzie offers to reorganize the coat closet if it would help.',
];

export function forkShapeForTrackedItem(item, decisionTurn = 40) {
  return {
    fork_id: item.fork_id,
    obligation_ids: [item.obligation_id],
    consumer: 'character_move',
    decision_turn: decisionTurn,
    with_obligation_choice_classes: [{
      class_id: `${item.tracked_item_id}-with`,
      behavior_markers: item.behavior_markers ?? [],
    }],
    without_obligation_choice_classes: [{
      class_id: `${item.tracked_item_id}-without`,
      behavior_markers: [],
    }],
  };
}
