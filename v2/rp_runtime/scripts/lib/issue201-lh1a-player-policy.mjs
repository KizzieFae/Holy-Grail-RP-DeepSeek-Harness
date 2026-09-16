import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH1A_SCHEMAS, LH1A_SCENARIO_FAMILIES } from './issue201-lh1a-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const LH1A_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-lh1a-policies');

const POLICY_IDS = {
  [LH1A_SCENARIO_FAMILIES.AYAME]: 'ayame_lh1a_policy_v1',
  [LH1A_SCENARIO_FAMILIES.ARKHAM]: 'arkham_lh1a_policy_v1',
};

export function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

export function loadLh1aPolicy(scenarioKey) {
  const policyId = POLICY_IDS[scenarioKey];
  if (!policyId) throw new Error(`unknown LH-1A scenario for policy: ${scenarioKey}`);
  const filePath = path.join(LH1A_POLICY_ROOT, `${policyId}.json`);
  if (!fs.existsSync(filePath)) throw new Error(`LH-1A policy not found: ${policyId}`);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (policy.schema !== LH1A_SCHEMAS.PLAYER_POLICY) {
    throw new Error(`unexpected policy schema: ${policy.schema}`);
  }
  return { policy, policy_path: filePath, policy_hash: sha256File(filePath) };
}

export function selectLh1aPlayerStimulus(policy, turnIndex) {
  const turn = policy.turns.find((t) => t.turn_index === turnIndex);
  if (!turn) throw new Error(`no policy turn ${turnIndex} in ${policy.policy_id}`);
  return turn.realization;
}

export function policyModelFacingText(policy) {
  return policy.turns.map((t) => t.realization).join(' ');
}
