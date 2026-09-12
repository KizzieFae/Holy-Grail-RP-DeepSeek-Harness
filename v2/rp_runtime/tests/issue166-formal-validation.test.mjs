import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

import { runPlotCognitionPendingWorkLifecycle } from '../src/lib/plot-cognition-orchestration.mjs';
import { runCharacterProjectionLifecycle } from '../src/plugins/hg-phase-executors/plot-cognition-character-projection.mjs';
import {
  createTrackingInference,
  epistemicPass,
  readForensicIndex,
  seedCharacterOverlayGoal,
  seedCharacterOverlayPressure,
  setupProjectionSession,
  startProjectionDomainHost,
} from './helpers/plot-cognition-projection-fixtures.mjs';

const noopTrace = { emit: () => {} };
const noopSceneAgent = { session: {} };

test('issue166 validation: stable projection state reuses Layer B (performance probe)', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference, calls } = createTrackingInference([epistemicPass(), epistemicPass()]);

  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-perf-1',
    turnIndex: ctx.turnIndex,
  });
  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-perf-2',
    turnIndex: ctx.turnIndex,
  });

  const evalCalls = calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval');
  assert.equal(evalCalls.length, 1, 'candidate should eliminate one redundant Layer B inference');
});

test('issue166 validation: strategic overlay change forces fresh Layer B', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference, calls } = createTrackingInference([epistemicPass(), epistemicPass()]);

  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-strat-1',
    turnIndex: ctx.turnIndex,
  });

  seedCharacterOverlayGoal(sessionsDir, ctx.scopeId, {
    characterId: 'Alice',
    direction: 'Pursue the hidden vault route instead.',
  });

  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-strat-2',
    turnIndex: ctx.turnIndex,
  });

  assert.equal(
    calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval').length,
    2,
  );
});

test('issue166 validation: evolving multi-pressure overlay lifecycle', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const session = await api.createSession({ cast: ['Alice', 'Bob'], memory_scope_id: `scope-evolve-${crypto.randomUUID()}` });
  const scopeId = session.plot_cognition_scope_id ?? session.memory_scope_id;
  seedCharacterOverlayGoal(sessionsDir, scopeId, { characterId: 'Alice', direction: 'Secure the household ledger.' });
  seedCharacterOverlayPressure(sessionsDir, scopeId, {
    characterId: 'Alice',
    pressureText: 'A rival faction is closing in.',
    dramaticRationale: 'Escalating external threat.',
  });
  seedCharacterOverlayPressure(sessionsDir, scopeId, {
    characterId: 'Bob',
    pressureText: 'Bob must decide whether to warn Alice.',
    dramaticRationale: 'Interpersonal tension.',
  });
  await api.finalizePlotCognitionReconciliation({ hg_scene_id: session.hg_scene_id });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const { runEphemeralInference, calls } = createTrackingInference([epistemicPass(), epistemicPass()]);

  const first = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    inferenceId: 'inf-evolve-1',
    turnIndex: Number(round.turn_index ?? 0),
  });
  const second = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    inferenceId: 'inf-evolve-2',
    turnIndex: Number(round.turn_index ?? 0),
  });
  assert.equal(first.ok, true);
  assert.equal(second.ok, true);
  const evalCalls = calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval');
  assert.ok(evalCalls.length >= 1);
  assert.ok(
    second.callLog.some((entry) => entry.startsWith('reuse:'))
      || evalCalls.length >= 2,
    'evolving overlay must either reuse or recompute when state diverges',
  );
});

test('issue166 validation: none orchestration records non-mutation forensic', async (t) => {
  const { api, sessionsDir, forensicsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const fresh = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
  assert.equal(fresh.fresh, true);

  await runPlotCognitionPendingWorkLifecycle({
    domainApi: api,
    trace: noopTrace,
    sceneAgent: noopSceneAgent,
    scope: { hgRoundId: ctx.hgRoundId },
    hgSceneId: ctx.hgSceneId,
    inferenceId: 'inf-none-forensic',
    runEphemeralInference: async () => ({ failed: true, raw: '', evidenceId: null }),
  });

  const chronicle = readForensicIndex(forensicsDir, ctx.scopeId);
  const keys = Object.keys(chronicle?.by_idempotency_key ?? {});
  const gateKey = keys.find((key) => key.includes(':orchestration:') && key.endsWith(':none'));
  assert.ok(gateKey, 'expected orchestration none gate chronicle key');
  const entry = chronicle.by_idempotency_key[gateKey];
  const recordId = typeof entry === 'string' ? entry : entry?.record ?? entry?.record_id;
  assert.ok(recordId, `expected chronicle record id for orchestration gate: ${JSON.stringify(entry)}`);
  const recordPath = path.join(
    forensicsDir,
    ctx.scopeId.replace(/\//g, '_').replace(/\\/g, '_'),
    'records',
    `${recordId}.json`,
  );
  const record = JSON.parse(fs.readFileSync(recordPath, 'utf8'));
  assert.equal(record.record_class, 'semantic_decision');
  assert.equal(record.payload.mutation_lifecycle_entered, false);
});

test('issue166 validation: reuse forensic lineage recorded', async (t) => {
  const { api, sessionsDir, forensicsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference([epistemicPass()]);

  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-forensic-1',
    turnIndex: ctx.turnIndex,
  });
  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-forensic-2',
    turnIndex: ctx.turnIndex,
  });

  const chronicle = readForensicIndex(forensicsDir, ctx.scopeId);
  const keys = Object.keys(chronicle?.by_idempotency_key ?? {});
  const reused = keys.filter((key) => key.includes(':layer_b:') && key.endsWith(':reused'));
  const invoked = keys.filter((key) => key.includes(':layer_b:') && key.endsWith(':invoke'));
  assert.ok(reused.length >= 1, 'expected reused Layer B forensic record');
  assert.ok(invoked.length >= 1, 'expected invoke Layer B forensic record');
});
