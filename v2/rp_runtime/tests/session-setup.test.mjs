import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { detectForcedSpeaker } from '../src/application/detect-forced-speaker.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

test('detectForcedSpeaker: resolves canonical display name from character file id mention', () => {
  const forced = detectForcedSpeaker('Hey willow, come here.', {
    participantNames: ['Kizzie', 'Willow Reeves'],
    characterFileIds: {
      Kizzie: 'kizzie',
      'Willow Reeves': 'willow',
    },
  });
  assert.equal(forced, 'Willow Reeves');
});

test('application client: create session from authored character cards', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  const characters = await client.listCharacters();
  assert.ok(characters.length > 0);
  assert.ok(!('system_prompt' in characters[0]));

  const templates = await client.listSceneTemplates();
  assert.ok(templates.some((item) => item.template_id === 'celina_apartment_recovery_watch'));

  const session = await client.createSession({
    characters: ['kizzie', 'willow'],
    sceneTemplateId: 'celina_apartment_recovery_watch',
    roleAssignments: {
      kizzie: 'recovering_demi_human',
      willow: 'protector',
    },
    opening: { mode: 'minimal' },
  });

  assert.ok(session.hg_session_id);
  assert.deepEqual(session.present_characters.sort(), ['Kizzie', 'Willow Reeves'].sort());
  assert.equal(session.setup_provenance?.scene_template_id, 'celina_apartment_recovery_watch');
  assert.equal(session.character_file_ids?.['Willow Reeves'], 'willow');
});
