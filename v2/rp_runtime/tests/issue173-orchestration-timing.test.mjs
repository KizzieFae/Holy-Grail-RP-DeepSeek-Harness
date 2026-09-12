import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { runInferenceWithContractCorrection } from '../src/lib/contract-correction-substrate.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { ExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ORCHESTRATION_GRAPH_SCHEMA } from '../src/lib/orchestration-graph.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { LIFECYCLE_MILESTONES } from '../src/application/application-turn-lifecycle.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

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

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice speaks.',
  environment_event: '',
  tension_shift: '',
};

function tempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-173-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const prev = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    for (const [key, value] of Object.entries(prev)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  return { dataDir, sessionsDir };
}

function readAttempts(dataDir, hgSessionId) {
  const root = path.join(dataDir, 'execution_evidence', hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((id) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${id}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

function readAttemptsAtEvidenceRoot(evidenceRoot, hgSessionId) {
  const root = path.join(evidenceRoot, hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((id) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${id}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

function graphSpans(attempts) {
  return attempts.filter((entry) => entry.correlation?.role === 'execution_span'
    && entry.decision?.orchestration_graph?.schema === ORCHESTRATION_GRAPH_SCHEMA);
}

const REQUIRED_CHARACTER_TURN_PHASES = [
  'director_phase',
  'character_prep_phase',
  'domain_commit_boundary',
  'post_commit_parallel_group',
];

function phaseId(span) {
  return span.decision?.phase_id ?? span.correlation?.phase_id ?? null;
}

function hasCompleteCharacterTurnGraph(graphs, { domainCommitId = null, characterTurnIndex = null } = {}) {
  const scoped = graphs.filter((span) => {
    const graph = span.decision?.orchestration_graph ?? {};
    if (domainCommitId && graph.domain_commit_id && graph.domain_commit_id !== domainCommitId) {
      return false;
    }
    if (characterTurnIndex != null && graph.character_turn_index != null
      && graph.character_turn_index !== characterTurnIndex) {
      return false;
    }
    return true;
  });
  const present = new Set(scoped.map((span) => phaseId(span)).filter(Boolean));
  return REQUIRED_CHARACTER_TURN_PHASES.every((required) => present.has(required));
}

function hasCompleteRoundGraph(graphs, expectedTurnCount) {
  const present = new Set(graphs.map((span) => phaseId(span)).filter(Boolean));
  if (!present.has('round_internal_serial')) return false;
  const turnSerials = graphs.filter((span) => phaseId(span) === 'character_turn_serial');
  return turnSerials.length === expectedTurnCount;
}

test('T1: ordinary serial inference retains dsh_session_turn_boundary timing', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 36765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const inferAttempts = attempts.filter((entry) => entry.request?.schema === 'hg_assembled_request_v1');
  assert.ok(inferAttempts.length >= 2);
  for (const attempt of inferAttempts) {
    const timing = attempt.inference_health?.timing;
    assert.equal(timing?.timing_observed, true);
    assert.equal(timing?.measurement, 'dsh_session_turn_boundary');
  }
});

test('T2: contract correction retains separate timed attempts', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-173-corr-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const recorder = new ExecutionEvidenceRecorder({ enabled: true, root });
  const substrate = {
    runEphemeralInference: async ({ inferenceId, evidenceContext }) => {
      const evidenceId = `${inferenceId}-evidence`;
      const store = new ExecutionEvidenceStore(root);
      store.writeAttempt({
        evidence_id: evidenceId,
        correlation: {
          evidence_id: evidenceId,
          hg_session_id: 'sess-corr',
          hg_scene_id: 'sess-corr',
          hg_round_id: 'round-corr',
          role: 'semantic_evaluator',
          inference_id: inferenceId,
          inference_kind: evidenceContext?.inferenceKind,
          attempt_index: 0,
        },
        request: { schema: 'hg_assembled_request_v1', contributions: [] },
        response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
        inference_health: {
          timing: {
            timing_observed: true,
            measurement: 'dsh_session_turn_boundary',
            inference_wall_clock_ms: 12,
          },
        },
      });
      return { evidenceId, raw: '{}', failed: false };
    },
  };

  const outcome = await runInferenceWithContractCorrection({
    runEphemeralInference: substrate.runEphemeralInference,
    primaryInferenceId: 'inf-primary',
    primaryInferenceKind: 'plot_cognition_epistemic_eval',
    correctionInferenceKind: 'plot_cognition_epistemic_eval_contract_correction',
    buildPrimaryPrompt: () => 'primary',
    buildCorrectionPrompt: () => 'correction',
    parseFn: () => ({ ok: false, error: 'bad_json' }),
    manifest: { contributions: [] },
    evidenceContextBase: { hgSessionId: 'sess-corr' },
    maxCorrections: 1,
  });

  assert.equal(outcome.inferRuns.length, 2);
  const store = new ExecutionEvidenceStore(root);
  const index = store.readIndex('sess-corr');
  assert.equal((index.attempt_ids ?? []).length, 2);
});

test('T3/T4: post-commit parallel graph and join barriers', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 37765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    mockNarratorTurnResponses: [['Narrator prose.']],
    librarianProposalDelayMs: 120,
    plotCognitionDelayMs: 80,
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const graphs = graphSpans(attempts);
  const kinds = graphs.map((span) => span.decision.orchestration_graph.node_kind);
  assert.ok(kinds.includes('parallel_group'));
  assert.ok(kinds.includes('lane'));
  assert.ok(kinds.filter((kind) => kind === 'join_barrier').length >= 1);
  const join = graphs.find((span) => span.decision.orchestration_graph.node_kind === 'join_barrier');
  assert.equal(typeof join.execution?.wall_ms, 'number');
});

test('T5: application-bound operation records lifecycle and operation_id correlation', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-173-app-'));
  const prevEvidenceDir = process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    fs.rmSync(evidenceRoot, { recursive: true, force: true });
    if (prevEvidenceDir === undefined) delete process.env.HG_EXECUTION_EVIDENCE_DIR;
    else process.env.HG_EXECUTION_EVIDENCE_DIR = prevEvidenceDir;
  });
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  process.env.HG_EXECUTION_EVIDENCE_DIR = evidenceRoot;

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  await client.createSession({ cast: ['Alice'] });
  const turn = await client.submitUserTurn({
    userMessage: 'Hello',
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    mockNarratorTurnResponses: [['Narrator prose.']],
  });

  assert.ok(turn.client_operation_id);
  const { attempts } = readAttemptsAtEvidenceRoot(evidenceRoot, turn.session.hg_session_id);
  const lifecycle = attempts.filter((entry) => entry.correlation?.role === 'application_lifecycle');
  const milestones = lifecycle.map((entry) => entry.correlation?.milestone ?? entry.decision?.milestone);
  assert.ok(milestones.includes(LIFECYCLE_MILESTONES.OPERATION_BEGAN));
  assert.ok(milestones.includes(LIFECYCLE_MILESTONES.ROUND_TERMINAL_SUCCEEDED));
  const inferWithOp = attempts.filter(
    (entry) => entry.request?.schema === 'hg_assembled_request_v1'
      && entry.correlation?.operation_id === turn.client_operation_id,
  );
  assert.ok(inferWithOp.length > 0);
});

test('T6: direct orchestrator run has no synthetic operation_id on inference attempts', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 38765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const inferAttempts = attempts.filter((entry) => entry.request?.schema === 'hg_assembled_request_v1');
  assert.ok(inferAttempts.length > 0);
  for (const attempt of inferAttempts) {
    assert.equal(attempt.correlation?.operation_id ?? null, null);
  }
  const lifecycle = attempts.filter((entry) => entry.correlation?.role === 'application_lifecycle');
  assert.equal(lifecycle.length, 0);
});

test('T7: complete character-turn causal graph and proven attribution', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 39765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    mockNarratorTurnResponses: [['Narrator prose.']],
    librarianProposalDelayMs: 40,
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const graphs = graphSpans(attempts);
  const phaseIds = graphs.map((span) => span.decision?.phase_id ?? span.correlation?.phase_id);
  assert.ok(phaseIds.includes('director_phase'));
  assert.ok(phaseIds.includes('character_prep_phase'));
  assert.ok(phaseIds.includes('domain_commit_boundary'));
  assert.ok(phaseIds.includes('post_commit_parallel_group'));
  const parallelGroup = graphs.find((span) => span.decision?.phase_id === 'post_commit_parallel_group');
  const commitBoundary = graphs.find((span) => span.decision?.phase_id === 'domain_commit_boundary');
  assert.ok(parallelGroup);
  assert.ok(commitBoundary);
  assert.ok(
    (parallelGroup.decision.orchestration_graph.predecessor_span_ids ?? []).includes(
      commitBoundary.correlation.span_id,
    ),
  );

  const domainCommitId = result.character_turns[0]?.domain_commit_id;
  assert.ok(domainCommitId);
  assert.ok(hasCompleteCharacterTurnGraph(graphs, {
    domainCommitId,
    characterTurnIndex: 0,
  }));
  const linkedInference = graphs.filter(
    (span) => (span.associations?.evidence_ids ?? []).length > 0,
  );
  assert.ok(linkedInference.length > 0);
});

test('T8: multi-turn round-internal graph chaining', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 40765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const directorBob = { ...VALID_DIRECTOR, next_actor: 'Bob', reason: 'Bob speaks.' };
  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    skipStorytellerCognition: true,
    skipPlotCognitionOrchestration: true,
    mockDirectorResponses: [
      JSON.stringify(VALID_DIRECTOR),
      JSON.stringify(directorBob),
    ],
    mockCharacterTurnResponses: [
      [JSON.stringify(VALID_MOVE)],
      [JSON.stringify(VALID_MOVE)],
    ],
    mockNarratorTurnResponses: [['Narrator one.'], ['Narrator two.']],
  });

  assert.equal(result.character_turn_count, 2);
  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const turnSerials = graphSpans(attempts).filter(
    (span) => span.decision?.phase_id === 'character_turn_serial',
  );
  assert.equal(turnSerials.length, 2);

  const allGraphs = graphSpans(attempts);
  assert.ok(hasCompleteRoundGraph(allGraphs, 2));
  assert.ok(hasCompleteCharacterTurnGraph(allGraphs, { characterTurnIndex: 0 }));
  assert.ok(hasCompleteCharacterTurnGraph(allGraphs, { characterTurnIndex: 1 }));
  const turnOne = turnSerials[0];
  const turnTwo = turnSerials[1];
  const turnTwoPred = turnTwo.decision?.orchestration_graph?.predecessor_span_ids ?? [];
  assert.ok(turnTwoPred.length > 0);
  assert.notEqual(turnTwoPred[0], turnOne.correlation?.span_id);
});

test('T9: post-commit-only graph is not proven for character_turn scope', async () => {
  const postCommitOnly = [
    {
      correlation: { role: 'execution_span', span_id: 'lane', hg_round_id: 'r1' },
      decision: {
        phase_id: 'post_commit_lane_narrator',
        orchestration_graph: {
          schema: ORCHESTRATION_GRAPH_SCHEMA,
          node_kind: 'lane',
          graph_id: 'g1',
          domain_commit_id: 'c1',
          character_turn_index: 0,
        },
      },
    },
    {
      correlation: { role: 'execution_span', span_id: 'group', hg_round_id: 'r1' },
      decision: {
        phase_id: 'post_commit_parallel_group',
        orchestration_graph: {
          schema: ORCHESTRATION_GRAPH_SCHEMA,
          node_kind: 'parallel_group',
          graph_id: 'g1',
          domain_commit_id: 'c1',
          character_turn_index: 0,
        },
      },
    },
    {
      correlation: { role: 'execution_span', span_id: 'join', hg_round_id: 'r1' },
      decision: {
        phase_id: 'post_commit_join_narrator',
        orchestration_graph: {
          schema: ORCHESTRATION_GRAPH_SCHEMA,
          node_kind: 'join_barrier',
          graph_id: 'g1',
          domain_commit_id: 'c1',
          character_turn_index: 0,
        },
      },
    },
  ];
  const postCommitComplete = new Set(postCommitOnly.map((span) => phaseId(span)));
  assert.ok(postCommitComplete.has('post_commit_parallel_group'));
  assert.equal(hasCompleteCharacterTurnGraph(postCommitOnly, {
    domainCommitId: 'c1',
    characterTurnIndex: 0,
  }), false);
});
