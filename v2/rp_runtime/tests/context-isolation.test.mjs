import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';

import { startDomainApi } from './helpers/domain-api.mjs';

async function postJson(baseUrl, pathName, body) {
  const res = await fetch(`${baseUrl}${pathName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  assert.equal(res.ok, true);
  return res.json();
}

test('context isolation: director manifest excludes character-private contributions', async (t) => {
  const port = 23765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl, scene } = await startDomainApi(port, { withSession: true });
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const round = await postJson(baseUrl, '/v1/rounds/start', { hg_scene_id: scene.hg_scene_id });
  const director = await postJson(baseUrl, '/v1/director/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-dir-iso',
    turn_index: round.turn_index,
    attempt_index: 0,
  });
  const character = await postJson(baseUrl, '/v1/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-char-iso',
    character_id: 'Alice',
    role: 'guest',
    turn_index: round.turn_index,
    attempt_index: 0,
  });

  const directorKinds = new Set(director.contributions.map((c) => c.source_kind));
  const characterKinds = new Set(character.contributions.map((c) => c.source_kind));
  assert.equal(directorKinds.has('character_private'), false);
  assert.equal(characterKinds.has('director_scratch'), false);
  assert.equal(characterKinds.has('character_private'), true);
  const privateContribution = character.contributions.find((c) => c.source_kind === 'character_private');
  assert.ok(privateContribution.content.includes('Character-private knowledge'));
  for (const contribution of director.contributions) {
    assert.equal(String(contribution.content).includes('Character-private knowledge'), false);
  }
});

test('context isolation: separate inference sessions remain distinct identities', async (t) => {
  const port = 24765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { createHolyGrailRpContext } = await import('../src/bootstrap.mjs');
  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const VALID_DIRECTOR = {
    next_actor: 'Alice',
    end_round: false,
    reason: 'Alice goes next.',
    environment_event: '',
    tension_shift: '',
  };
  const VALID_MOVE = {
    move_schema_version: 2,
    beats: [{ type: 'action', action: 'nods' }],
    motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
    semantic_evaluation: { decision: 'no_covered_change' },
  };

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });
  assert.notEqual(result.director_inference_session_id, result.dsh_scene_session_id);
  assert.notEqual(result.character_inference_session_id, result.dsh_scene_session_id);
});

test('context isolation: narrator manifest excludes director scratch and character-private', async (t) => {
  const port = 28765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl, scene } = await startDomainApi(port, { withSession: true });
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const round = await postJson(baseUrl, '/v1/rounds/start', { hg_scene_id: scene.hg_scene_id });
  const VALID_MOVE = {
    move_schema_version: 2,
    beats: [{ type: 'action', action: 'nods thoughtfully' }],
    motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
    semantic_evaluation: { decision: 'no_covered_change' },
  };
  const VALID_DIRECTOR = {
    next_actor: 'Alice',
    end_round: false,
    reason: 'Alice goes next.',
    environment_event: '',
    tension_shift: '',
  };

  const validation = await postJson(baseUrl, '/v1/moves/validate', {
    inference_id: 'inf-char-commit',
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    role: 'guest',
    turn_index: round.turn_index,
    attempt_index: 0,
    proposed_move: VALID_MOVE,
    raw_model_output: JSON.stringify(VALID_MOVE),
  });
  assert.equal(validation.accepted, true);

  const commit = await postJson(baseUrl, '/v1/moves/commit', {
    inference_id: 'inf-char-commit',
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    validated_move: validation.normalized_move,
    director_decision: VALID_DIRECTOR,
    expected_turn_index: round.turn_index,
  });
  assert.equal(commit.committed, true);

  const narrator = await postJson(baseUrl, '/v1/narrator/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-narrator-iso',
    character_id: 'Alice',
    domain_commit_id: commit.domain_commit_id,
    continuity_turn_index: commit.continuity_turn_index,
  });

  const kinds = new Set(narrator.contributions.map((c) => c.source_kind));
  assert.equal(kinds.has('director_scratch'), false);
  assert.equal(kinds.has('character_private'), false);
  assert.equal(kinds.has('committed_move'), true);
  for (const contribution of narrator.contributions) {
    assert.equal(String(contribution.content).includes('Character-private knowledge'), false);
    assert.equal(String(contribution.content).includes('Director scratch'), false);
  }
});

test('context isolation: character context excludes director scratch', async (t) => {
  const port = 24765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port, { withSession: true });
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const scene = await postJson(baseUrl, '/v1/sessions/create', { cast: ['Alice'] });
  const round = await postJson(baseUrl, '/v1/rounds/start', { hg_scene_id: scene.hg_scene_id });
  const character = await postJson(baseUrl, '/v1/context/prepare', {
    hg_scene_id: scene.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-char-scratch',
    character_id: 'Alice',
    role: 'guest',
    turn_index: round.turn_index,
    attempt_index: 0,
  });
  const kinds = new Set(character.contributions.map((c) => c.source_kind));
  assert.equal(kinds.has('director_scratch'), false);
});

test('context isolation: round orchestration preserves role boundaries', async (t) => {
  const port = 25765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { createHolyGrailRpContext } = await import('../src/bootstrap.mjs');
  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const VALID_MOVE = {
    move_schema_version: 2,
    beats: [{ type: 'action', action: 'nods thoughtfully' }],
    motivation: {
      goal: 'acknowledge',
      tactic: 'subtle gesture',
      emotional_driver: 'calm',
      risk_level: 'low',
    },
    semantic_evaluation: { decision: 'no_covered_change' },
  };
  const VALID_DIRECTOR = {
    next_actor: 'Alice',
    end_round: false,
    reason: 'Alice should speak next.',
    environment_event: '',
    tension_shift: '',
  };

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const directorProposed = result.scene_events.find((e) => e.type === 'hg/director-proposed');
  const characterProposed = result.scene_events.find((e) => e.type === 'hg/move-proposed');
  assert.ok(directorProposed?.data?.hg_session_id);
  assert.equal(directorProposed.data.hg_session_id, result.hg_session_id);
  assert.equal(characterProposed.data.hg_session_id, result.hg_session_id);
});
