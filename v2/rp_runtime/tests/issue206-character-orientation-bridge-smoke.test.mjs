/**
 * #206 bounded composition smoke: Host prepareCharacterOrientationContext → DSH bridge validation.
 * Exercises the production contract boundary that blocked #201 Package D Stage 1.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { validateBridgeManifest } from '../src/lib/manifest-validation.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

test('issue206: character orientation Host manifest with inventory passes bridge validation', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const host = await startDomainApi(undefined, { sessionsDir, t });
  const api = createDomainApiClient(host.baseUrl);

  const session = await api.createSession({
    cast: ['Ayame', 'Kizzie'],
    location: 'Entry',
  });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const prepare = await api.prepareCharacterOrientationContext({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-issue206-orient',
    character_id: 'Ayame',
    role: 'host',
    turn_index: 0,
  });

  const inventory = (prepare.contributions ?? []).find(
    (item) => item.source_kind === 'authoritative_perceptual_inventory',
  );
  assert.ok(inventory, 'Host must project authoritative_perceptual_inventory for orientation');

  const resolved = validateBridgeManifest({
    manifest: {
      manifest_id: prepare.manifest_id,
      inference_id: 'inf-issue206-orient',
      inference_kind: 'character_orientation',
      contributions: prepare.contributions,
    },
  });
  assert.equal(resolved, 'character_orientation');
});
