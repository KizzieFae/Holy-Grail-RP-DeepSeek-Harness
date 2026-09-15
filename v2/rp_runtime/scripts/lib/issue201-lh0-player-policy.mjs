import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { selectPlayerStimulus } from './issue201-d01l-player-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const LH0_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance/records/issue201-lh0-policies');

export function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

export function loadLh0Policy(policyId = 'ayame_lh0_policy_v1') {
  const filePath = path.join(LH0_POLICY_ROOT, `${policyId}.json`);
  if (!fs.existsSync(filePath)) throw new Error(`LH-0 policy not found: ${policyId}`);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  return { policy, policy_path: filePath, policy_hash: sha256File(filePath) };
}

export { selectPlayerStimulus };
