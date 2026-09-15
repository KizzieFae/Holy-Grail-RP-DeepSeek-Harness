import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { selectPlayerStimulus } from './issue201-d01l-player-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const G3D_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance', 'records', 'issue201-g3d-policies');
const D10_POLICY_ROOT = path.resolve(__dirname, '../../../..', 'governance', 'records', 'issue201-d10-policies');

export function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

export function loadPolicy(policyId) {
  const roots = [G3D_POLICY_ROOT, D10_POLICY_ROOT];
  let filePath = null;
  for (const root of roots) {
    const candidate = path.join(root, `${policyId}.json`);
    if (fs.existsSync(candidate)) {
      filePath = candidate;
      break;
    }
  }
  if (!filePath) throw new Error(`Policy not found: ${policyId}`);
  const policy = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const policy_hash = sha256File(filePath);
  return { policy, policy_path: filePath, policy_hash };
}

export function buildPolicyManifest() {
  const ids = ['arkham_g3d_policy_v1', 'ayame_d10_policy_v1'];
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
    schema: 'issue201_g3d_policy_manifest_v1',
    frozen_at,
    policies,
  };
  fs.mkdirSync(G3D_POLICY_ROOT, { recursive: true });
  fs.writeFileSync(path.join(G3D_POLICY_ROOT, 'g3d_policy_manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

export { selectPlayerStimulus };
