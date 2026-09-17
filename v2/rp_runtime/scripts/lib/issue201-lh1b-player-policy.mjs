import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH1B_SCHEMAS, LH1B_SCENARIO_FAMILIES } from './issue201-lh1b-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const LH1B_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-lh1b-policies');

const POLICY_IDS = {
  [LH1B_SCENARIO_FAMILIES.AYAME]: 'ayame_lh1b_policy_v1',
};

export function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

export function loadLh1bPolicy(scenarioKey = LH1B_SCENARIO_FAMILIES.AYAME) {
  const policyId = POLICY_IDS[scenarioKey];
  if (!policyId) throw new Error(`unknown LH-1B scenario for policy: ${scenarioKey}`);
  const filePath = path.join(LH1B_POLICY_ROOT, `${policyId}.json`);
  if (!fs.existsSync(filePath)) throw new Error(`LH-1B policy not found: ${policyId}`);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (policy.schema !== LH1B_SCHEMAS.PLAYER_POLICY) {
    throw new Error(`unexpected policy schema: ${policy.schema}`);
  }
  return { policy, policy_path: filePath, policy_hash: sha256File(filePath) };
}

export function selectLh1bPlayerStimulus(policy, turnIndex) {
  const turn = policy.turns.find((t) => t.turn_index === turnIndex);
  if (!turn) throw new Error(`no policy turn ${turnIndex} in ${policy.policy_id}`);
  return turn.realization;
}
