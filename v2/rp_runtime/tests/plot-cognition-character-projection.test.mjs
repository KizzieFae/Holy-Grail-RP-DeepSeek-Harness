import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { buildNoChangeUpdateInference } from '../src/lib/plot-cognition-update-envelope.mjs';
import { runCharacterProjectionLifecycle } from '../src/plugins/hg-phase-executors/plot-cognition-character-projection.mjs';
import { runCharacterPhase } from '../src/plugins/hg-phase-executors/character-phase.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { attachCharacterCognitionApiStubs } from './helpers/character-cognition-mock.mjs';
import {
  createFailingInference,
  createTrackingInference,
  epistemicMalformed,
  epistemicPass,
  epistemicRewriteRequired,
  epistemicWithhold,
  instrumentProjectionApi,
  readForensicIndex,
  setupProjectionSession,
  startProjectionDomainHost,
} from './helpers/plot-cognition-projection-fixtures.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'checks the latch carefully' }],
  motivation: {
    goal: 'inspect',
    tactic: 'slow check',
    emotional_driver: 'wary',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const BOB_ANXIETY_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'fidgets nervously and admits he cannot stop thinking about the vault' }],
  motivation: {
    goal: 'express anxiety',
    tactic: 'visible tension',
    emotional_driver: 'anxious',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak next.`,
  environment_event: '',
  tension_shift: 'steady',
});

const NARRATOR_PROSE = 'Bob shifted uneasily near the vault.';

function semanticPassChar() {
  return JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'pass',
    findings: [],
  });
}

const noopTrace = { emit: () => {} };
const noopSceneAgent = { session: {} };

test('projection seam: call-order prepare → eval → register → finalize → character context', async (t) => {
  const { api, sessionsDir, dataDir, forensicsDir } = await startProjectionDomainHost(t, {
    hostEnv: { HG_EXECUTION_EVIDENCE: 'on' },
  });
  const ctx = await setupProjectionSession(api, sessionsDir);
  const instrumented = instrumentProjectionApi(api);
  const { runEphemeralInference, calls } = createTrackingInference([epistemicPass()]);

  const result = await runCharacterProjectionLifecycle({
    api: instrumented,
    runEphemeralInference,
    scope: { hgSessionId: ctx.session.hg_session_id },
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-order',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.ok(instrumented._order.indexOf('prepare') < instrumented._order.indexOf('register'));
  assert.ok(instrumented._order.indexOf('register') < instrumented._order.indexOf('finalize'));
  assert.equal(calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval').length, 1);

  const context = await instrumented.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-proj-order',
    character_id: 'Alice',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: result.finalized.binding,
      contributions: result.finalized.contributions,
    },
  });
  assert.ok(
    instrumented._order.indexOf('finalize') < instrumented._order.indexOf('character_context'),
  );
  const storyteller = (context.contributions ?? []).filter((c) => (
    String(c.source_kind ?? '').startsWith('storyteller')
  ));
  assert.ok(storyteller.length > 0, 'expected storyteller contribution after pass');

  const chronicle = readForensicIndex(forensicsDir, ctx.scopeId);
  assert.ok(chronicle?.by_idempotency_key);
  const finalizeKey = Object.keys(chronicle.by_idempotency_key).find((k) => k.includes(':projection:'));
  assert.ok(finalizeKey, 'expected projection finalize chronicle key');
});

test('projection seam: zero candidates skips evaluator and regeneration inference', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir, { withCharacterGoal: false });
  const { runEphemeralInference, calls } = createTrackingInference([]);
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-zero',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(result.ok, true);
  assert.equal(result.prepare.candidate_count, 0);
  assert.deepEqual(
    calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval'),
    [],
  );
  assert.deepEqual(
    calls.filter((c) => c.inferenceKind === 'character_advisory_generation'),
    [],
  );
  assert.deepEqual(result.callLog, ['prepare', 'finalize']);
});

test('projection seam: first-pass pass admits contribution to character context', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference([epistemicPass()]);
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-pass',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(result.ok, true);
  assert.ok(result.finalized.contributions.length > 0);
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-proj-pass',
    character_id: 'Alice',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: result.finalized.binding,
      contributions: result.finalized.contributions,
    },
  });
  const joined = (manifest.contributions ?? []).map((c) => c.content).join('\n');
  assert.match(joined, /Find the key quietly/);
});

test('projection seam: withhold does not reach character context', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference([epistemicWithhold()]);
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-withhold',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(result.ok, true);
  assert.equal(result.finalized.contributions.length, 0);
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-proj-withhold',
    character_id: 'Alice',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: result.finalized.binding,
      contributions: result.finalized.contributions,
    },
  });
  const joined = (manifest.contributions ?? []).map((c) => c.content).join('\n');
  assert.doesNotMatch(joined, /Find the key quietly/);
});

test('projection seam: rewrite_required runs single regen and two semantic evals', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference, calls } = createTrackingInference();
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-regen',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
    mockRegenerationResponses: ['Revised advisory without hidden vault details.'],
  });
  assert.equal(result.ok, true);
  const evalCalls = calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval');
  const genCalls = calls.filter((c) => c.inferenceKind === 'character_advisory_generation');
  assert.equal(evalCalls.length, 2);
  assert.equal(genCalls.length, 1);
  assert.deepEqual(
    result.callLog.filter((entry) => entry.startsWith('regen_')),
    [`regen_prepare:${result.prepare.items[0].evaluation_pass_id}`, `regen_infer:${result.prepare.items[0].evaluation_pass_id}`, `regen_finalize:${result.prepare.items[0].evaluation_pass_id}`],
  );
});

test('projection seam: regenerated pass admits contribution under fresh overlay', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const freshness = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
  assert.equal(freshness.fresh, true);
  const { runEphemeralInference } = createTrackingInference();
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-regen-fresh',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
    mockRegenerationResponses: ['Revised advisory without hidden vault details.'],
  });
  assert.equal(result.ok, true);
  assert.ok(result.finalized.contributions.length > 0);
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-proj-regen-fresh',
    character_id: 'Alice',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: result.finalized.binding,
      contributions: result.finalized.contributions,
    },
  });
  const storyteller = (manifest.contributions ?? []).filter((c) => (
    String(c.source_kind ?? '').startsWith('storyteller')
  ));
  assert.ok(storyteller.length > 0, 'expected regenerated storyteller contribution under fresh overlay');
  const joined = storyteller.map((c) => c.content).join('\n');
  assert.match(joined, /Revised advisory without hidden vault details/);
});

test('projection seam: finalized regen contribution withheld when overlay stale', async (t) => {
  const { api, sessionsDir, baseUrl } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { ctx: rpCtx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await rpCtx.fiber.dispose();
  });
  const seedRound = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: ctx.session.hg_session_id },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(BOB_ANXIETY_MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });
  assert.equal(seedRound.committed, true);
  const stale = await api.assessPlotCognitionFreshness({ hg_scene_id: ctx.hgSceneId });
  assert.equal(stale.fresh, false);
  assert.ok(stale.pending_work);

  const { runEphemeralInference } = createTrackingInference();
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-regen-stale',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
    mockRegenerationResponses: ['Safe regenerated advisory text.'],
  });
  assert.equal(result.ok, true);
  assert.ok(result.finalized.contributions.length > 0, 'finalize may still contain approved contribution');

  const manifest = await api.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-proj-regen-stale',
    character_id: 'Alice',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: result.finalized.binding,
      contributions: result.finalized.contributions,
    },
  });
  const storyteller = (manifest.contributions ?? []).filter((c) => (
    String(c.source_kind ?? '').startsWith('storyteller')
  ));
  assert.equal(storyteller.length, 0, 'stale overlay must withhold finalized storyteller contribution');
});

test('projection seam: regenerated reject withholds contribution', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference();
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-regen-reject',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired(), epistemicWithhold()],
    mockRegenerationResponses: ['Still leaky rewrite attempt.'],
  });
  assert.equal(result.ok, true);
  assert.equal(result.finalized.contributions.length, 0);
});

test('projection seam: malformed evaluator output fails closed', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference([epistemicMalformed()]);
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-malformed',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicMalformed()],
  });
  assert.equal(result.ok, true);
  assert.equal(result.finalized.contributions.length, 0);
});

test('projection seam: generator failure withholds', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const tracking = createTrackingInference([epistemicRewriteRequired()]);
  const failingGen = createFailingInference();
  let phase = 'eval';
  async function runEphemeralInference(args) {
    if (phase === 'eval') {
      phase = 'gen';
      return tracking.runEphemeralInference(args);
    }
    return failingGen.runEphemeralInference(args);
  }
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-gen-fail',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired()],
  });
  assert.equal(result.ok, false);
  assert.equal(result.stage, 'regen_infer');
});

test('projection seam: forged regeneration prepare rejected before generator inference', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const prepare = await api.preparePlotCognitionProjection({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    character_id: 'Alice',
    manifest_id: 'manifest-forged',
  });
  assert.equal(prepare.accepted, true);
  const item = prepare.items[0];
  const { calls } = createTrackingInference();
  const denied = await api.preparePlotCognitionProjectionRegeneration({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    batch_id: prepare.batch_id,
    evaluation_pass_id: item.evaluation_pass_id,
  });
  assert.equal(denied.accepted, false);
  assert.equal(calls.filter((c) => c.inferenceKind === 'character_advisory_generation').length, 0);
});

test('projection seam: second regeneration attempt rejected by Domain', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const prepare = await api.preparePlotCognitionProjection({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    character_id: 'Alice',
    manifest_id: 'manifest-regen-twice',
  });
  const item = prepare.items[0];
  await api.registerPlotCognitionProjectionSemanticResult({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    batch_id: prepare.batch_id,
    evaluation_pass_id: item.evaluation_pass_id,
    candidate_id: item.candidate_id,
    evaluation_attempt: 1,
    semantic: JSON.parse(epistemicRewriteRequired()),
    inference_evidence_id: 'ev-1',
  });
  const first = await api.preparePlotCognitionProjectionRegeneration({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    batch_id: prepare.batch_id,
    evaluation_pass_id: item.evaluation_pass_id,
  });
  assert.equal(first.accepted, true);
  const second = await api.preparePlotCognitionProjectionRegeneration({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    batch_id: prepare.batch_id,
    evaluation_pass_id: item.evaluation_pass_id,
  });
  assert.equal(second.accepted, false);
});

test('projection seam: finalize forensic failure prevents projection handoff', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const wrappedApi = {
    ...api,
    async finalizePlotCognitionProjection(body) {
      return { accepted: false, reason: 'forensic_persistence_failed', contributions: [] };
    },
  };
  const { runEphemeralInference } = createTrackingInference();
  const result = await runCharacterProjectionLifecycle({
    api: wrappedApi,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-chronicle-fail',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicPass()],
  });
  assert.equal(result.ok, false);
  assert.equal(result.stage, 'finalize');
  assert.equal(result.finalized, null);
});

test('projection seam: stale finalized binding stripped from character context', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference([epistemicPass()]);
  const result = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-binding',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicPass()],
  });
  const manifest = await api.prepareCharacterContext({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    inference_id: 'inf-binding',
    character_id: 'Bob',
    role: 'guest',
    turn_index: ctx.turnIndex,
    attempt_index: 0,
    plot_cognition_finalized_projection: {
      batch_id: result.finalized.batch_id,
      binding_digest: result.finalized.binding_digest,
      binding: {
        ...result.finalized.binding,
        character_id: 'Alice',
      },
      contributions: result.finalized.contributions,
    },
  });
  const joined = (manifest.contributions ?? []).map((c) => c.content).join('\n');
  assert.doesNotMatch(joined, /Find the key quietly/);
});

test('projection seam: character move retry does not re-run projection prepare', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  let prepareCount = 0;
  const characterContextCalls = [];
  const wrappedApi = attachCharacterCognitionApiStubs({
    ...api,
    async preparePlotCognitionProjection(body) {
      prepareCount += 1;
      return api.preparePlotCognitionProjection(body);
    },
    async prepareCharacterContext(body) {
      characterContextCalls.push(body);
      return api.prepareCharacterContext(body);
    },
    async getSceneState() {
      return { turn_counter: ctx.turnIndex };
    },
    async validateMove(body) {
      const retryable = body.attempt_index === 0;
      return {
        accepted: !retryable,
        validation_class: retryable ? 'objective' : 'valid',
        reason: retryable ? 'retry once' : '',
        retryable,
        normalized_move: VALID_MOVE,
      };
    },
    async prepareSemanticEvaluationContext(body) {
      return {
        manifest_id: 'manifest-semantic',
        inference_id: body.inference_id,
        contributions: [],
        authority_references: [],
      };
    },
    async commitMove() {
      return { committed: true, continuity_turn_index: 1, domain_commit_id: 'dc-1' };
    },
  });
  const result = await runCharacterPhase({
    runEphemeralInference: async ({ mockResponses }) => ({
      failed: false,
      raw: mockResponses?.[0] ?? JSON.stringify(VALID_MOVE),
      evidenceId: `ev-char-move-${characterContextCalls.length}`,
      inferenceSessionId: 'sess-char',
      trace: {},
    }),
    recorder: null,
    trace: noopTrace,
    api: wrappedApi,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: ctx.session.hg_session_id,
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    directorDecision: { next_actor: 'Bob' },
    characterInferenceId: 'inf-char-retry',
    mockResponses: [JSON.stringify(VALID_MOVE), JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPassChar()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
    mockProjectionEpistemicResponses: [epistemicPass()],
  });
  assert.equal(result.committed, true);
  assert.equal(prepareCount, 1);
  assert.ok(characterContextCalls.length >= 2);
  const batchIds = characterContextCalls.map((body) => body.plot_cognition_finalized_projection?.batch_id);
  assert.ok(batchIds[0]);
  assert.ok(batchIds.every((id) => id === batchIds[0]));
});

test('projection seam: transient batch loss cannot reuse prior batch registration', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference } = createTrackingInference();
  const lifecycle = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-transient-complete',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicPass()],
  });
  assert.equal(lifecycle.ok, true);
  const item = lifecycle.prepare.items[0];
  const denied = await api.registerPlotCognitionProjectionSemanticResult({
    hg_scene_id: ctx.hgSceneId,
    hg_round_id: ctx.hgRoundId,
    batch_id: lifecycle.prepare.batch_id,
    evaluation_pass_id: item.evaluation_pass_id,
    candidate_id: item.candidate_id,
    evaluation_attempt: 1,
    semantic: JSON.parse(epistemicPass()),
    inference_evidence_id: 'ev-after-finalize',
  });
  assert.equal(denied.accepted, false);
  assert.equal(denied.reason, 'unknown_or_expired_batch');
});

test('projection seam: execution evidence links eval and generator kinds', async (t) => {
  const { api, sessionsDir, dataDir } = await startProjectionDomainHost(t, {
    hostEnv: { HG_EXECUTION_EVIDENCE: 'on' },
  });
  const ctx = await setupProjectionSession(api, sessionsDir);
  const recorder = createExecutionEvidenceRecorder({ dataDir });
  const { runEphemeralInference, calls } = createTrackingInference();
  await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference: async (args) => {
      const run = await runEphemeralInference(args);
      recorder?.recordAttempt?.({
        hgSessionId: ctx.session.hg_session_id,
        evidenceId: run.evidenceId,
        correlation: args.evidenceContext ?? {},
        decision: { outcome: args.evidenceContext?.inferenceKind ?? 'unknown' },
      });
      return run;
    },
    scope: { hgSessionId: ctx.session.hg_session_id },
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-evidence-link',
    turnIndex: ctx.turnIndex,
    mockEpistemicResponses: [epistemicRewriteRequired(), epistemicPass()],
    mockRegenerationResponses: ['Safe regenerated advisory text.'],
  });
  const kinds = calls.map((c) => c.inferenceKind);
  assert.deepEqual(
    kinds.filter((k) => k === 'plot_cognition_epistemic_eval').length,
    2,
  );
  assert.equal(kinds.filter((k) => k === 'character_advisory_generation').length, 1);
});

test('projection seam: identical Layer B state reuses prior epistemic eval (#166)', async (t) => {
  const { api, sessionsDir } = await startProjectionDomainHost(t);
  const ctx = await setupProjectionSession(api, sessionsDir);
  const { runEphemeralInference, calls } = createTrackingInference([epistemicPass(), epistemicPass()]);

  const first = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-reuse-1',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(first.ok, true, JSON.stringify(first));
  assert.ok((first.prepare?.items?.length ?? first.prepare?.candidate_count ?? 0) > 0);
  assert.ok(first.callLog.some((entry) => entry.startsWith('eval:')));

  const second = await runCharacterProjectionLifecycle({
    api,
    runEphemeralInference,
    scope: {},
    hgSceneId: ctx.hgSceneId,
    hgRoundId: ctx.hgRoundId,
    characterId: 'Alice',
    inferenceId: 'inf-proj-reuse-2',
    turnIndex: ctx.turnIndex,
  });
  assert.equal(second.ok, true, JSON.stringify(second));
  assert.ok(second.callLog.some((entry) => entry.startsWith('reuse:')));

  const evalCalls = calls.filter((c) => c.inferenceKind === 'plot_cognition_epistemic_eval');
  assert.equal(evalCalls.length, 1, 'expected one Layer B inference across two identical lifecycles');
});
