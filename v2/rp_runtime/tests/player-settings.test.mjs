import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { createHolyGrailAppServer } from '../src/application/app-server.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

const MOCK_ROUND = {
  mockDirectorResponses: [
    JSON.stringify({
      next_actor: 'Willow Reeves',
      end_round: true,
      reason: 'AI character responds.',
      environment_event: '',
      tension_shift: '',
    }),
  ],
  mockCharacterTurnResponses: [[
    JSON.stringify({
      move_schema_version: 2,
      beats: [{ type: 'action', action: 'nods thoughtfully' }],
      motivation: {
        goal: 'acknowledge',
        tactic: 'subtle gesture',
        emotional_driver: 'calm',
        risk_level: 'low',
      },
      semantic_evaluation: { decision: 'no_covered_change' },
    }),
  ]],
  mockNarratorTurnResponses: [['Willow nodded.']],
};

test('player settings: player-controlled character excluded from eligibility', async (t) => {
  const port = 42765 + Math.floor(Math.random() * 1000);
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const created = await fetch(`${host.baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      characters: ['kizzie', 'willow'],
      scene_template_id: 'celina_apartment_recovery_watch',
      role_assignments: {
        kizzie: 'recovering_demi_human',
        willow: 'protector',
      },
      player_character_file_id: 'kizzie',
      user_persona_id: 'Player',
    }),
  }).then((r) => r.json());

  const round = await fetch(`${host.baseUrl}/v1/rounds/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_scene_id: created.hg_session_id }),
  }).then((r) => r.json());

  const eligibility = await fetch(`${host.baseUrl}/v1/rounds/eligible-actors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_scene_id: created.hg_session_id,
      hg_round_id: round.hg_round_id,
    }),
  }).then((r) => r.json());

  const playerName = created.setup_provenance.player_character_display_name;
  const aiName = created.setup_provenance.character_display_names.find(
    (name) => name !== playerName,
  );
  assert.ok(aiName);
  assert.ok(!eligibility.eligible_actors.includes(playerName));
  assert.ok(eligibility.eligible_actors.includes(aiName));
});

test('player settings: application round selects AI actor when player is in cast', async (t) => {
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

  const created = await client.createSession({
    characters: ['kizzie', 'willow'],
    scene_template_id: 'celina_apartment_recovery_watch',
    role_assignments: {
      kizzie: 'recovering_demi_human',
      willow: 'protector',
    },
    player_character_file_id: 'kizzie',
    opening: { mode: 'minimal' },
  });

  const aiName = created.setup_provenance.character_display_names.find(
    (name) => name !== created.setup_provenance.player_character_display_name,
  );
  assert.ok(aiName);

  const turn = await client.submitUserTurn({
    userMessage: 'What do you think?',
    userName: 'Player',
    forcedDesignation: aiName,
    mockDirectorResponses: [
      JSON.stringify({
        next_actor: aiName,
        end_round: true,
        reason: 'AI character responds.',
        environment_event: '',
        tension_shift: '',
      }),
    ],
    mockCharacterTurnResponses: MOCK_ROUND.mockCharacterTurnResponses,
    mockNarratorTurnResponses: MOCK_ROUND.mockNarratorTurnResponses,
  });

  assert.ok((turn.round.character_turn_count ?? turn.round.character_turns?.length ?? 0) >= 1);
  assert.equal(turn.forced_designation, aiName);
});

test('player settings: app server runtime settings and reopen restore session identity', async (t) => {
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

  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  const defaults = await fetch(`${baseUrl}/api/settings/defaults`).then((r) => r.json());
  assert.ok(defaults.runtime);
  assert.ok(defaults.role_profiles);

  const updated = await fetch(`${baseUrl}/api/settings/runtime`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reasoningEffort: 'high', roleRouting: 'simple' }),
  }).then((r) => r.json());
  assert.equal(updated.runtime.reasoningEffort, 'high');

  const created = await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      characters: ['kizzie'],
      player_character_file_id: 'kizzie',
      user_persona_id: 'Operator',
      opening: { mode: 'minimal' },
    }),
  }).then((r) => r.json());
  const sessionId = created.session.hg_session_id;
  assert.equal(created.session.setup_provenance.user_persona_id, 'Operator');

  await client.stop();
  const reopenedClient = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await reopenedClient.start();
  t.after(() => reopenedClient.stop());

  const reopened = await reopenedClient.openSession(sessionId);
  assert.equal(reopened.setup_provenance.player_character_file_id, 'kizzie');
  assert.equal(reopened.setup_provenance.user_persona_id, 'Operator');
  assert.equal(reopenedClient.getRuntimeSettings().reasoningEffort, undefined);
});
