import { runCharacterInferenceSlice } from './character-inference-slice.mjs';

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

const INVALID_MOVE = {
  move_schema_version: 2,
  beats: [],
  motivation: { goal: 'x', tactic: 'x', emotional_driver: 'x', risk_level: 'x' },
};

const baseUrl = process.env.HG_DOMAIN_API_URL ?? 'http://127.0.0.1:8765';

const result = await runCharacterInferenceSlice({
  domainApi: { baseUrl },
  mockResponses: [JSON.stringify(INVALID_MOVE), JSON.stringify(VALID_MOVE)],
});

console.log(JSON.stringify({
  committed: result.committed,
  inference_id: result.inference_id,
  hg_scene_id: result.hg_scene_id,
  continuity_turn_index: result.continuity_turn_index,
  domain_commit_id: result.domain_commit_id,
  dsh_session_id: result.dsh_session_id,
  hg_events: result.events
    .filter((event) => String(event.type).startsWith('hg/'))
    .map((event) => ({ type: event.type, seq: event.seq, data: event.data })),
}, null, 2));

if (!result.committed) {
  process.exitCode = 1;
}
