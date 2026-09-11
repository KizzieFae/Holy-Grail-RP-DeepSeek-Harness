import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { runBoundedConcurrency } from '../src/lib/bounded-concurrency.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import {
  DEFAULT_MAX_PARALLEL_NARRATOR_MEDIATION_INFERENCES,
  effectiveNarratorMediationParallelism,
  narratorMediationExecutionMode,
  resolveMaxParallelNarratorMediationInferences,
} from '../src/lib/narrator-mediation-concurrency.mjs';
import { runNarratorEnvironmentCognition } from '../src/lib/narrator-environment-cognition-substrate.mjs';
import { LIBRARIAN_MEDIATION_CORRECTION_KIND } from '../src/lib/librarian-mediation-envelope.mjs';

const WORKER_SCRIPT = fileURLToPath(new URL('./helpers/concurrent-evidence-write-worker.mjs', import.meta.url));

const VALID_MEDIATION = JSON.stringify({
  schema: 'hg_librarian_mediation_result_v1',
  mediation_outcome: 'match',
  selected_source_ids: ['src-1'],
  rationale: 'matched',
});

const MALFORMED_MEDIATION = '{"mediation_outcome":"match"';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function spawnEvidenceWrite(root, hgSessionId, evidenceId) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [WORKER_SCRIPT, root, hgSessionId, evidenceId],
      { stdio: 'ignore' },
    );
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`worker exit ${code} for ${evidenceId}`));
    });
  });
}

function buildMultiNeedCognition(needCount) {
  const informationNeeds = Array.from({ length: needCount }, (_, index) => ({
    need_id: `need-${index + 1}`,
    question: `Question ${index + 1}?`,
  }));
  const resolutions = informationNeeds.map((need, index) => ({
    need_id: need.need_id,
    category: 'B2',
    detail: `detail-${index + 1}`,
    property_key: `prop-${index + 1}`,
    value: `value-${index + 1}`,
    stable_refs: ['location:workshop'],
  }));
  return JSON.stringify({
    baseline_sufficient: false,
    information_needs: informationNeeds,
    resolutions,
  });
}

function createParallelMockApi({
  needCount = 3,
  mediationDelayMs = 40,
  mediationOutcomeByIndex = () => 'match',
  hostRejectIndex = null,
  trackConcurrency = null,
} = {}) {
  const calls = {
    prepare: 0,
    kar: 0,
    finalize: 0,
    librarianPrepare: 0,
    librarianFinalize: 0,
    preparePayloads: [],
    finalizeBodies: [],
  };
  let active = 0;
  let maxActive = 0;

  const api = {
    calls,
    async prepareNarratorEnvironmentCognitionContext() {
      calls.prepare += 1;
      return { manifest: { contributions: [] }, context: {} };
    },
    async buildNarratorEnvironmentKnowledgeRequests({ cognition_raw }) {
      calls.kar += 1;
      const parsed = JSON.parse(cognition_raw);
      const needs = parsed.information_needs ?? [];
      return {
        knowledge_access_requests: needs.map((need, index) => ({
          request_id: `kar-${index + 1}`,
          consumer_role: 'narrator',
          need_id: need.need_id,
        })),
      };
    },
    async finalizeNarratorEnvironmentCognition(body) {
      calls.finalize += 1;
      calls.finalizeBodies.push(body);
      return {
        accepted: true,
        audit: { cognition_id: 'cog-parallel' },
        cognition_result: body.cognition_result,
        librarian_outcomes: body.librarian_outcomes,
      };
    },
    async prepareLibrarianMediationContext({ inference_id, knowledge_access_request }) {
      calls.librarianPrepare += 1;
      calls.preparePayloads.push({ inference_id, knowledge_access_request });
      active += 1;
      maxActive = Math.max(maxActive, active);
      if (trackConcurrency) {
        trackConcurrency(active, maxActive);
      }
      await sleep(mediationDelayMs);
      return {
        request_id: knowledge_access_request.request_id,
        mediation_catalog: [{ source_id: 'src-1' }],
        manifest: { contributions: [] },
      };
    },
    async finalizeLibrarianMediation({
      inference_id,
      allow_deterministic_fallback,
      mediation_result,
    }) {
      calls.librarianFinalize += 1;
      active -= 1;
      const index = Number.parseInt(String(inference_id).split('-lib-').pop(), 10);
      if (hostRejectIndex === index) {
        return {
          mediation_outcome: 'mediation_failure',
          entries: [],
          audit: { host_validation: { accepted: false, rejection_codes: ['host_rejected'] } },
        };
      }
      if (!mediation_result) {
        return {
          mediation_outcome: 'mediation_failure',
          entries: [],
          audit: { host_validation: { accepted: false, rejection_codes: ['structural_parse_failed'] } },
          mediation_mode: allow_deterministic_fallback ? 'deterministic_fallback' : 'authoritative_only',
        };
      }
      const outcome = mediationOutcomeByIndex(index);
      return {
        mediation_outcome: outcome,
        entries: outcome === 'match' ? [{ content: `grounding-${index}` }] : [],
        audit: { host_validation: { accepted: true, rejection_codes: [] } },
        mediation_mode: allow_deterministic_fallback ? 'contextual_semantic' : 'authoritative_only',
      };
    },
    getMaxActive: () => maxActive,
  };
  return api;
}

function runEnvCognition({
  api,
  needCount = 3,
  inferenceConfig = { narratorMediation: { maxParallelInferences: 4 } },
  runEphemeralInference = null,
  cognitionRaw = null,
}) {
  const defaultInference = async ({ inferenceId, inferenceKind, evidenceContext }) => {
    const kind = evidenceContext?.inferenceKind ?? inferenceKind;
    if (kind === 'narrator_environment_cognition') {
      return { failed: false, raw: cognitionRaw ?? buildMultiNeedCognition(needCount) };
    }
    const indexSource = String(evidenceContext?.parentInferenceId ?? inferenceId);
    const index = Number.parseInt(indexSource.split('-lib-').pop(), 10);
    if (kind === LIBRARIAN_MEDIATION_CORRECTION_KIND) {
      return { failed: false, raw: VALID_MEDIATION };
    }
    if (index === 1) {
      return { failed: false, raw: MALFORMED_MEDIATION };
    }
    return { failed: false, raw: VALID_MEDIATION };
  };
  return runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: runEphemeralInference ?? defaultInference,
    hgSessionId: 'scene-parallel',
    hgSceneId: 'scene-parallel',
    hgRoundId: 'round-parallel',
    inferenceId: 'inf-parallel',
    characterId: 'Alice',
    domainCommitId: 'commit-parallel',
    continuityTurnIndex: 1,
    inferenceConfig,
    mockCognitionResponse: cognitionRaw ?? buildMultiNeedCognition(needCount),
  });
}

test('narrator mediation concurrency config defaults to 4', () => {
  assert.equal(
    resolveMaxParallelNarratorMediationInferences(),
    DEFAULT_MAX_PARALLEL_NARRATOR_MEDIATION_INFERENCES,
  );
  assert.equal(DEFAULT_MAX_PARALLEL_NARRATOR_MEDIATION_INFERENCES, 4);
});

test('effective parallelism is min(needCount, configured max)', () => {
  assert.equal(effectiveNarratorMediationParallelism(0, 4), 1);
  assert.equal(effectiveNarratorMediationParallelism(1, 4), 1);
  assert.equal(effectiveNarratorMediationParallelism(3, 4), 3);
  assert.equal(effectiveNarratorMediationParallelism(6, 4), 4);
});

test('execution mode is serial for 0-1 needs and parallel otherwise', () => {
  assert.equal(narratorMediationExecutionMode(0, 4), 'serial');
  assert.equal(narratorMediationExecutionMode(1, 4), 'serial');
  assert.equal(narratorMediationExecutionMode(2, 4), 'parallel');
});

test('runBoundedConcurrency preserves logical order with reversed completion', async () => {
  const items = ['a', 'b', 'c', 'd', 'e'];
  const delays = [50, 10, 40, 5, 30];
  const results = await runBoundedConcurrency(items, 4, async (item, index) => {
    await sleep(delays[index]);
    return `${item}:${index}`;
  });
  assert.deepEqual(results, ['a:0', 'b:1', 'c:2', 'd:3', 'e:4']);
});

test('runBoundedConcurrency waits for siblings before rethrowing', async () => {
  let completed = 0;
  await assert.rejects(
    () => runBoundedConcurrency([0, 1, 2], 2, async (value) => {
      await sleep(20);
      completed += 1;
      if (value === 1) {
        throw new Error('need-1-failed');
      }
      return value;
    }),
    /need-1-failed/,
  );
  assert.equal(completed, 3);
});

test('zero needs: baseline path unchanged', async () => {
  const api = createParallelMockApi({ needCount: 0 });
  const result = await runEnvCognition({
    api,
    needCount: 0,
    cognitionRaw: JSON.stringify({
      baseline_sufficient: true,
      information_needs: [],
      resolutions: [],
    }),
  });
  assert.equal(result.ok, true);
  assert.deepEqual(result.librarianOutcomes, []);
  assert.equal(api.calls.librarianPrepare, 0);
});

test('one need remains serial execution mode', async () => {
  const api = createParallelMockApi({ needCount: 1, mediationDelayMs: 5 });
  const result = await runEnvCognition({ api, needCount: 1 });
  assert.equal(result.librarianOutcomes.length, 1);
  assert.equal(result.librarianOutcomes[0].mediation_execution_mode, 'serial');
  assert.equal(result.librarianOutcomes[0].need_index, 0);
  assert.equal(api.getMaxActive(), 1);
});

test('parallel overlap: multiple mediations are concurrently active', async () => {
  const peaks = [];
  const api = createParallelMockApi({
    needCount: 4,
    mediationDelayMs: 60,
    trackConcurrency: (active) => peaks.push(active),
  });
  await runEnvCognition({ api, needCount: 4 });
  assert.ok(peaks.some((value) => value >= 2), `expected overlap, peaks=${peaks.join(',')}`);
  assert.equal(api.getMaxActive(), 4);
});

test('bounded concurrency: active mediation never exceeds configured max', async () => {
  const api = createParallelMockApi({ needCount: 7, mediationDelayMs: 50 });
  await runEnvCognition({
    api,
    needCount: 7,
    inferenceConfig: { narratorMediation: { maxParallelInferences: 3 } },
  });
  assert.equal(api.getMaxActive(), 3);
});

test('librarian_outcomes remain in logical need order', async () => {
  const completionOrder = [];
  const api = createParallelMockApi({ needCount: 5, mediationDelayMs: 5 });
  const baseFinalize = api.finalizeLibrarianMediation.bind(api);
  api.finalizeLibrarianMediation = async (payload) => {
    const index = Number.parseInt(String(payload.inference_id).split('-lib-').pop(), 10);
    const delayByIndex = [80, 10, 70, 20, 60];
    await sleep(delayByIndex[index] ?? 5);
    completionOrder.push(index);
    return baseFinalize(payload);
  };
  const result = await runEnvCognition({ api, needCount: 5 });
  assert.notDeepEqual(completionOrder, [0, 1, 2, 3, 4]);
  assert.deepEqual(
    result.librarianOutcomes.map((item) => item.need_index),
    [0, 1, 2, 3, 4],
  );
  assert.deepEqual(
    result.librarianOutcomes.map((item) => item.need_id),
    ['need-1', 'need-2', 'need-3', 'need-4', 'need-5'],
  );
});

test('serial reference and parallel execution produce equivalent ordered outcomes', async () => {
  const serialApi = createParallelMockApi({ needCount: 3, mediationDelayMs: 0 });
  const parallelApi = createParallelMockApi({ needCount: 3, mediationDelayMs: 0 });
  const cognitionRaw = buildMultiNeedCognition(3);
  const serial = await runEnvCognition({
    api: serialApi,
    needCount: 3,
    cognitionRaw,
    inferenceConfig: { narratorMediation: { maxParallelInferences: 1 } },
  });
  const parallel = await runEnvCognition({
    api: parallelApi,
    needCount: 3,
    cognitionRaw,
    inferenceConfig: { narratorMediation: { maxParallelInferences: 4 } },
  });
  assert.deepEqual(
    serial.librarianOutcomes.map(({ need_id, mediation_outcome, request_id }) => ({
      need_id,
      mediation_outcome,
      request_id,
    })),
    parallel.librarianOutcomes.map(({ need_id, mediation_outcome, request_id }) => ({
      need_id,
      mediation_outcome,
      request_id,
    })),
  );
});

test('correction isolation: sibling correction does not affect other needs', async () => {
  const api = createParallelMockApi({ needCount: 3, mediationDelayMs: 5 });
  const result = await runEnvCognition({ api, needCount: 3 });
  assert.equal(result.librarianOutcomes[0].mediation_outcome, 'match');
  assert.equal(result.librarianOutcomes[1].mediation_outcome, 'match');
  assert.equal(result.librarianOutcomes[2].mediation_outcome, 'match');
});

test('correction failure degrades only the affected need', async () => {
  const api = createParallelMockApi({ needCount: 3, mediationDelayMs: 5 });
  const result = await runEnvCognition({
    api,
    needCount: 3,
    runEphemeralInference: async ({ inferenceId, inferenceKind, evidenceContext }) => {
      const kind = evidenceContext?.inferenceKind ?? inferenceKind;
      if (kind === 'narrator_environment_cognition') {
        return { failed: false, raw: buildMultiNeedCognition(3) };
      }
      const indexSource = String(evidenceContext?.parentInferenceId ?? inferenceId);
      const index = Number.parseInt(indexSource.split('-lib-').pop(), 10);
      if (kind === LIBRARIAN_MEDIATION_CORRECTION_KIND && index === 1) {
        return { failed: false, raw: MALFORMED_MEDIATION };
      }
      if (index === 1) {
        return { failed: false, raw: MALFORMED_MEDIATION };
      }
      return { failed: false, raw: VALID_MEDIATION };
    },
  });
  assert.equal(result.librarianOutcomes[0].mediation_outcome, 'match');
  assert.equal(result.librarianOutcomes[1].mediation_outcome, 'mediation_failure');
  assert.equal(result.librarianOutcomes[2].mediation_outcome, 'match');
});

test('input equivalence: serial and parallel use identical per-need mediation inputs', async () => {
  const serialApi = createParallelMockApi({ needCount: 4, mediationDelayMs: 0 });
  const parallelApi = createParallelMockApi({ needCount: 4, mediationDelayMs: 0 });
  const cognitionRaw = buildMultiNeedCognition(4);
  await runEnvCognition({
    api: serialApi,
    needCount: 4,
    cognitionRaw,
    inferenceConfig: { narratorMediation: { maxParallelInferences: 1 } },
  });
  await runEnvCognition({
    api: parallelApi,
    needCount: 4,
    cognitionRaw,
    inferenceConfig: { narratorMediation: { maxParallelInferences: 4 } },
  });
  assert.deepEqual(
    serialApi.calls.preparePayloads.map(({ inference_id, knowledge_access_request }) => ({
      inference_id,
      request_id: knowledge_access_request.request_id,
      need_id: knowledge_access_request.need_id,
    })),
    parallelApi.calls.preparePayloads.map(({ inference_id, knowledge_access_request }) => ({
      inference_id,
      request_id: knowledge_access_request.request_id,
      need_id: knowledge_access_request.need_id,
    })),
  );
});

test('host rejection isolation: rejected need does not contaminate siblings', async () => {
  const api = createParallelMockApi({ needCount: 3, mediationDelayMs: 5, hostRejectIndex: 1 });
  const result = await runEnvCognition({ api, needCount: 3 });
  assert.equal(result.librarianOutcomes[0].mediation_outcome, 'match');
  assert.equal(result.librarianOutcomes[1].mediation_outcome, 'mediation_failure');
  assert.equal(result.librarianOutcomes[2].mediation_outcome, 'match');
});

test('forensics include execution mode, group id, and need index', async () => {
  const api = createParallelMockApi({ needCount: 3, mediationDelayMs: 5 });
  const result = await runEnvCognition({ api, needCount: 3 });
  for (const [index, outcome] of result.librarianOutcomes.entries()) {
    assert.equal(outcome.mediation_execution_mode, 'parallel');
    assert.equal(outcome.parallel_group_id, 'inf-parallel-narrator-env-cog');
    assert.equal(outcome.need_index, index);
    assert.equal(outcome.need_id, `need-${index + 1}`);
  }
});

test('execution evidence index: concurrent process writes preserve all entries', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-evidence-concurrent-'));
  const hgSessionId = 'sess-concurrent';
  const count = 16;
  try {
    await Promise.all(
      Array.from({ length: count }, (_, index) => spawnEvidenceWrite(root, hgSessionId, `ev-${index}`)),
    );
    const store = new ExecutionEvidenceStore(root);
    const index = store.readIndex(hgSessionId);
    assert.equal(index.attempt_ids.length, count);
    assert.equal(new Set(index.attempt_ids).size, count);
    const parsed = JSON.parse(fs.readFileSync(path.join(root, hgSessionId, 'index.json'), 'utf8'));
    assert.equal(parsed.schema, index.schema);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
