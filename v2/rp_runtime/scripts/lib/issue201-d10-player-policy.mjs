import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  selectPlayerStimulus,
} from './issue201-d01l-player-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const GOVERNANCE_POLICY_ROOT = path.resolve(
  __dirname,
  '../../../..',
  'governance',
  'records',
  'issue201-d10-policies',
);

export const POLICY_ROOT = GOVERNANCE_POLICY_ROOT;

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

export function buildPolicyManifest() {
  const ids = ['arkham_d10_policy_v1', 'ayame_d10_policy_v1'];
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
    schema: 'issue201_d10_policy_manifest_v1',
    frozen_at,
    policies,
  };
  const manifestPath = path.join(GOVERNANCE_POLICY_ROOT, 'd10_policy_manifest.json');
  fs.mkdirSync(GOVERNANCE_POLICY_ROOT, { recursive: true });
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

export { selectPlayerStimulus };
