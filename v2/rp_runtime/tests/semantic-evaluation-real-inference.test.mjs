import assert from 'node:assert/strict';
import test from 'node:test';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

test('HTTP prepareSemanticEvaluationContext returns authority references and candidate package', async (t) => {
  const port = 24775 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const session = await api.createSession({ cast: ['Alice'], location: 'Dorm' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const state = await api.getSceneState(session.hg_scene_id);

  const response = await api.prepareSemanticEvaluationContext({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-http-semantic',
    character_id: 'Alice',
    role: 'guest',
    turn_index: Number(state.turn_counter ?? 0),
    evaluation_pass_id: 'eval-http-1',
    candidate_move: VALID_MOVE,
    raw_model_output: JSON.stringify(VALID_MOVE),
  });

  assert.ok(response.manifest_id.startsWith('manifest-semantic-eval-'));
  assert.equal(response.evaluation_pass_id, 'eval-http-1');
  assert.ok(Array.isArray(response.authority_references));
  assert.ok(response.authority_references.some((ref) => ref.ref_id === 'guardrail:player_agency'));
  assert.equal(response.candidate_package.candidate_move.move_schema_version, 2);
});
