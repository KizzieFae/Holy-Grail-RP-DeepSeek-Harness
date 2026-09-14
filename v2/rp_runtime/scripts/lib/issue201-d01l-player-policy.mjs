import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const GOVERNANCE_POLICY_ROOT = path.resolve(
  __dirname,
  '../../../..',
  'governance',
  'records',
  'issue201-d01l-policies',
);
const DATA_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'data', 'investigation', 'policies');

export function resolvePolicyRoot() {
  if (fs.existsSync(GOVERNANCE_POLICY_ROOT)) return GOVERNANCE_POLICY_ROOT;
  return DATA_POLICY_ROOT;
}

export const POLICY_ROOT = resolvePolicyRoot();

export function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

export function loadPolicy(policyId) {
  const filePath = path.join(POLICY_ROOT, `${policyId}.json`);
  if (!fs.existsSync(filePath)) throw new Error(`Policy not found: ${filePath}`);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const policy_hash = sha256File(filePath);
  return { policy, policy_path: filePath, policy_hash };
}

function normalizeText(text) {
  return String(text ?? '').replace(/\s+/g, ' ').trim();
}

function matchesAllPatterns(text, patterns) {
  return patterns.every((p) => new RegExp(p, 'i').test(text));
}

function matchesAnyPattern(text, patterns) {
  return patterns.some((p) => new RegExp(p, 'i').test(text));
}

function evaluatePredicate(predicate, presentationText, predicateHits, priorPresentations) {
  if (predicate.default) return true;
  if (predicate.unless_predicate_ids?.some((id) => predicateHits.has(id))) return false;
  if (predicate.all_patterns?.length) {
    return matchesAllPatterns(presentationText, predicate.all_patterns);
  }
  if (predicate.any_patterns?.length) {
    return matchesAnyPattern(presentationText, predicate.any_patterns);
  }
  if (predicate.cumulative_any_predicate_ids?.length) {
    if (predicate.cumulative_any_predicate_ids.some((id) => predicateHits.has(id))) return true;
  }
  if (predicate.or_source_turn_pattern) {
    const { turn_index, any_patterns } = predicate.or_source_turn_pattern;
    const src = priorPresentations[turn_index];
    if (src && matchesAnyPattern(src, any_patterns)) return true;
  }
  if (predicate.cumulative_any_predicate_ids?.length) return false;
  return false;
}

/**
 * Select player stimulus for a turn from frozen policy.
 * @param {object} policy
 * @param {number} turnIndex 1-based
 * @param {Array<{turn_index:number,presentation_text:string,winning_predicate:string}>} priorTurns
 */
export function selectPlayerStimulus(policy, turnIndex, priorTurns) {
  const turnDef = policy.turns.find((t) => t.turn_index === turnIndex);
  if (!turnDef) throw new Error(`No turn ${turnIndex} in policy ${policy.policy_id}`);

  const predicateHits = new Set(
    priorTurns.map((t) => t.winning_predicate).filter(Boolean),
  );
  const priorPresentations = {};
  for (const row of priorTurns) {
    priorPresentations[row.turn_index] = normalizeText(row.presentation_text);
  }

  if (turnDef.branch_mode === 'fixed') {
    return {
      turn: turnIndex,
      policy_hash: null,
      predicate_hits: [...predicateHits],
      winning_predicate: 'FIXED',
      branch_id: 'FIXED',
      exact_player_stimulus: turnDef.realization,
    };
  }

  const sourceTurn = priorTurns.find((t) => t.turn_index === turnDef.predicate_source_turn);
  const presentationText = normalizeText(sourceTurn?.presentation_text ?? '');
  const sorted = [...turnDef.predicates].sort((a, b) => a.priority - b.priority);
  const hits = [];
  let winning = null;
  for (const pred of sorted) {
    const matched = evaluatePredicate(pred, presentationText, predicateHits, priorPresentations);
    hits.push({ predicate_id: pred.predicate_id, matched });
    if (matched && !winning) winning = pred;
  }
  if (!winning) {
    winning = sorted.find((p) => p.default) ?? sorted[sorted.length - 1];
  }
  const branch_id = winning.predicate_id;
  const exact_player_stimulus = turnDef.realizations[branch_id];
  if (!exact_player_stimulus) {
    throw new Error(`Missing realization for ${branch_id} turn ${turnIndex}`);
  }
  return {
    turn: turnIndex,
    predicate_hits: hits,
    winning_predicate: branch_id,
    branch_id,
    exact_player_stimulus,
  };
}

export function buildPolicyManifest() {
  const ids = ['arkham_d01l_policy_v1', 'ayame_d01l_policy_v1'];
  const frozen_at = new Date().toISOString();
  const policies = ids.map((id) => {
    const { policy, policy_path, policy_hash } = loadPolicy(id);
    return {
      policy_id: id,
      policy_path,
      policy_hash,
      scenario_key: policy.scenario_key,
      turn_count: policy.turn_count,
    };
  });
  const manifest = {
    schema: 'issue201_d01l_policy_manifest_v1',
    frozen_at,
    policies,
  };
  const manifestPath = path.join(GOVERNANCE_POLICY_ROOT, 'd01l_policy_manifest.json');
  fs.mkdirSync(GOVERNANCE_POLICY_ROOT, { recursive: true });
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  const dataManifestPath = path.join(DATA_POLICY_ROOT, 'd01l_policy_manifest.json');
  fs.mkdirSync(DATA_POLICY_ROOT, { recursive: true });
  fs.writeFileSync(dataManifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}
