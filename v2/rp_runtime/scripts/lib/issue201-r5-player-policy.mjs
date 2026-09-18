import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { R5_SCHEMAS } from './issue201-r5-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const R5_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-r5-policies');

export function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

export function loadR5Policy() {
  const filePath = path.join(R5_POLICY_ROOT, 'ayame_r5_policy_v1.json');
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (policy.schema !== R5_SCHEMAS.PLAYER_POLICY) {
    throw new Error(`unexpected R5 policy schema: ${policy.schema}`);
  }
  return { policy, policy_path: filePath, policy_hash: sha256File(filePath) };
}

export function selectR5PlayerStimulus(policy, turnIndex) {
  const turn = policy.turns.find((t) => t.turn_index === turnIndex);
  if (!turn) throw new Error(`no R5 policy turn ${turnIndex}`);
  return turn.realization;
}
