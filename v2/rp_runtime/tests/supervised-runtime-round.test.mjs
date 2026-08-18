import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { startSupervisedRuntime } from '../src/runtime-supervisor/index.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

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
  reason: 'Alice should speak.',
  environment_event: '',
  tension_shift: '',
};

test('supervised runtime: full round through SessionRepository', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const { supervisor, orchestrator } = await startSupervisedRuntime({
    domainHost: { sessionsDir },
  });
  t.after(async () => {
    await supervisor.stop();
  });

  const result = await orchestrator.runRound({
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  assert.ok(result.hg_session_id);
  assert.equal(result.continuity_turn_index, 1);
  assert.ok(fs.existsSync(`${sessionsDir}/${result.hg_session_id}.json`));
  const labels = result.boundary_metrics.calls.map((c) => c.label);
  assert.ok(labels.includes('createSession'));
});
