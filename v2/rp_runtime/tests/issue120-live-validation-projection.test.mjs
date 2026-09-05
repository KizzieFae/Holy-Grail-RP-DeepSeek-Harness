import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import {
  analyzeSemantics,
  buildSemanticPass,
  evaluateAyameProjection,
  JAPAN_TOKEN,
  projectPlayerUserTurnForAyame,
  readProjectionFromRecordUserTurnMetadata,
} from '../scripts/lib/issue120-projection.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = path.join(
  __dirname,
  'fixtures',
  'issue120-live-call-1-decomposition.json',
);

const CAST = ['Ayame', 'Kizzie', 'Harley', 'Celina'];
const CONTENT =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you '
  + 'realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

test('issue120 harness projection uses authoritative player viewer path (G-122-01)', async (t) => {
  const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
  const host = await startDomainApi(undefined, { t });
  const api = createDomainApiClient(host.baseUrl);
  const sessionId = 'issue120-projection-test';
  await api.createSession({ cast: CAST, hg_session_id: sessionId });

  const domain = await projectPlayerUserTurnForAyame({
    api,
    sessionId,
    content: CONTENT,
    decomposition: fixture.raw_decomposition,
    presentCharacters: CAST,
  });
  const units = fixture.raw_decomposition.perceptual_visibility?.units ?? [];
  const semantics = analyzeSemantics(units);
  const projection = evaluateAyameProjection({ semantics, assembly: domain.assembly });
  const legacyProjection = readProjectionFromRecordUserTurnMetadata(domain.entry);

  assert.equal(domain.validation_accepted, true);
  assert.deepEqual(legacyProjection, {}, 'recordUserTurn metadata must not expose projection');
  assert.equal(projection.japan_excluded_from_ayame, true);
  assert.equal(projection.japan_exclusion_reason, 'player_internal_ineligible');
  assert.equal(projection.japan_token_in_ayame_content, false);
  assert.equal(projection.seiza_included_for_ayame, true);
  assert.equal(projection.hesitation_included_for_ayame, true);
  assert.equal(projection.speech_included_for_ayame, true);
  assert.equal(projection.projection_pass, true);
  assert.equal(buildSemanticPass({ semantics, projection }), true);
  assert.equal(String(domain.assembly.content ?? '').includes(JAPAN_TOKEN), false);
});
