import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

function ayameSegmentationMock() {
  return JSON.stringify({
    perceptual_visibility: {
      units: [
        {
          unit_id: 'public_mansion',
          kind: 'observable_scene',
          text:
            'The interview had been scheduled almost at once. Now you stood at the entrance to a mansion that looked too polished, too quiet, and too expensive to belong to your life.',
          recipients: { scope: 'public' },
        },
        {
          unit_id: 'applicant_internal',
          kind: 'internal',
          text:
            'It had been a horrible week. You had lost your job, then your apartment, and desperation was starting to feel like a second skin.',
          recipients: { scope: 'private', characters: ['Kizzie'] },
        },
        {
          unit_id: 'applicant_closer',
          kind: 'internal',
          text:
            'You lifted your hand toward the door, still telling yourself your streak of misfortune had been nothing but bad luck.',
          recipients: { scope: 'private', characters: ['Kizzie'] },
        },
      ],
    },
  });
}

function celinaSegmentationMock() {
  return JSON.stringify({
    perceptual_visibility: {
      units: [
        {
          unit_id: 'public_storm',
          kind: 'observable_scene',
          text:
            "Walking out of one of her boss's hotels, Celina was immediately hit with wind-driven rain splashing directly into her face.",
          recipients: { scope: 'public' },
        },
        {
          unit_id: 'celina_internal',
          kind: 'internal',
          text: 'For a moment, Celina considered walking on. Not her problem.',
          recipients: { scope: 'private', characters: ['Celina'] },
        },
        {
          unit_id: 'rescue_observable',
          kind: 'observable_event',
          text:
            'Celina squatted, hauled you up, and adjusted her grip as your body shook with cold',
          recipients: { scope: 'present' },
        },
      ],
    },
  });
}

async function characterTranscript(api, sessionId, characterId) {
  const round = await api.startRound({ hg_scene_id: sessionId });
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: sessionId,
    hg_round_id: round.hg_round_id,
    inference_id: `inf-${characterId}-nvr-bootstrap`,
    character_id: characterId,
    role: 'guest',
    turn_index: 0,
    attempt_index: 0,
  });
  const contribution = (manifest.contributions ?? []).find(
    (item) => item.source_kind === 'recent_scene_transcript',
  );
  return contribution?.content ?? null;
}

test('production template bootstrap: auto-segments NVR without manual attach (Ayame)', async (t) => {
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

  const openers = await client.listTemplateOpeners('ayame_household_entry_evaluation');
  const created = await client.createSession({
    characters: ['ayame', 'kizzie'],
    sceneTemplateId: 'ayame_household_entry_evaluation',
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
    mockOpeningSegmentationResponses: [ayameSegmentationMock()],
  });

  const api = createDomainApiClient(client.supervisor.domainHostUrl);
  const history = await api.getSessionHistory(created.hg_session_id);
  const opening = history.entries.find((entry) => entry.kind === 'opening');
  assert.ok(opening);
  assert.ok(opening.metadata?.perceptual_visibility?.units?.length > 0);

  const humanTranscript = client.getTranscript();
  assert.match(humanTranscript[0].content, /horrible week/);

  const ayameTranscript = await characterTranscript(api, created.hg_session_id, 'Ayame');
  const kizzieTranscript = await characterTranscript(api, created.hg_session_id, 'Kizzie');
  assert.ok(ayameTranscript);
  assert.ok(kizzieTranscript);
  assert.match(ayameTranscript, /mansion/);
  assert.doesNotMatch(ayameTranscript, /horrible week/);
  assert.match(kizzieTranscript, /horrible week/);
});

test('production template bootstrap: mixed Celina opener projection', async (t) => {
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

  const openers = await client.listTemplateOpeners('celina_apartment_recovery_watch');
  const created = await client.createSession({
    characters: ['celina', 'kizzie'],
    sceneTemplateId: 'celina_apartment_recovery_watch',
    roleAssignments: { celina: 'protector', kizzie: 'recovering_demi_human' },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
    mockOpeningSegmentationResponses: [celinaSegmentationMock()],
  });

  const api = createDomainApiClient(client.supervisor.domainHostUrl);
  const celinaTranscript = await characterTranscript(api, created.hg_session_id, 'Celina');
  const kizzieTranscript = await characterTranscript(api, created.hg_session_id, 'Kizzie');
  assert.match(celinaTranscript, /Not her problem/);
  assert.doesNotMatch(kizzieTranscript ?? '', /Not her problem/);
  assert.match(kizzieTranscript ?? '', /wind-driven rain|Walking out/i);
});

test('production generated opener: combined envelope persists NVR', async (t) => {
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

  const combined = JSON.stringify({
    presentation_text: 'Morning light filters through the vermillion torii as the shrine awakens.',
    perceptual_visibility: {
      units: [
        {
          unit_id: 'public_shrine',
          kind: 'observable_scene',
          text: 'Morning light filters through the vermillion torii as the shrine awakens.',
          recipients: { scope: 'public' },
        },
      ],
    },
  });

  const created = await client.createSession({
    characters: ['yukiko', 'kizzie'],
    sceneTemplateId: 'yukiko_shrine_guided_visit',
    roleAssignments: { yukiko: 'head_miko', kizzie: 'primary_visitor' },
    opening: { mode: 'generated' },
    mockOpeningResponses: [combined],
  });

  const api = createDomainApiClient(client.supervisor.domainHostUrl);
  const history = await api.getSessionHistory(created.hg_session_id);
  const opening = history.entries.find((entry) => entry.kind === 'opening');
  assert.ok(opening?.metadata?.perceptual_visibility?.units?.length);
  assert.equal(
    client.getTranscript()[0].content,
    'Morning light filters through the vermillion torii as the shrine awakens.',
  );
  assert.doesNotMatch(client.getTranscript()[0].content, /perceptual_visibility/);
});

test('production template bootstrap: segmentation failure fails closed for characters', async (t) => {
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

  const openers = await client.listTemplateOpeners('ayame_household_entry_evaluation');
  const created = await client.createSession({
    characters: ['ayame', 'kizzie'],
    sceneTemplateId: 'ayame_household_entry_evaluation',
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
    mockOpeningSegmentationResponses: [
      JSON.stringify({
        perceptual_visibility: {
          units: [
            {
              unit_id: 'bad_internal',
              kind: 'internal',
              text: 'secret',
              recipients: { scope: 'public' },
            },
          ],
        },
      }),
    ],
  });

  const api = createDomainApiClient(client.supervisor.domainHostUrl);
  const history = await api.getSessionHistory(created.hg_session_id);
  const opening = history.entries.find((entry) => entry.kind === 'opening');
  assert.ok(opening);
  assert.equal(opening.metadata?.perceptual_visibility, undefined);
  assert.match(client.getTranscript()[0].content, /horrible week/);

  const ayameTranscript = await characterTranscript(api, created.hg_session_id, 'Ayame');
  assert.equal(ayameTranscript, null);
});
