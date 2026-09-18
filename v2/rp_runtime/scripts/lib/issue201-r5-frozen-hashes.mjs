import crypto from 'node:crypto';

import { fixturePathForR5, loadR5FixtureManifest } from './issue201-r5-fixtures.mjs';
import { loadR5Policy, sha256File } from './issue201-r5-player-policy.mjs';

export const R5_FROZEN_HASHES = Object.freeze({
  fixture_hash: '896377dcc6a6cd1de9e92db262fb65c7cffb66f7764b8eddc4a47498d67d4068',
  policy_hash: 'bbf280f06a57466709e351ce57a86ea9188dfc63e70624a3752dceb66dfadc82',
  causal_design_hash: '26abbc25a866e52ca31b6caba49be614560b37bdc4a589f4128841d38d569b13',
});

export function verifyR5FrozenHashes() {
  const measured = {
    fixture_hash: sha256File(fixturePathForR5()),
    policy_hash: loadR5Policy().policy_hash,
    causal_design_hash: crypto.createHash('sha256')
      .update(JSON.stringify(loadR5FixtureManifest().causal_design))
      .digest('hex'),
  };
  const drift = Object.entries(R5_FROZEN_HASHES).filter(([k, v]) => measured[k] !== v);
  return { pass: drift.length === 0, measured, drift };
}
