import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import {
  ENV_COGNITION_STAGES,
  FORENSIC_BOUNDARIES,
  NARRATOR_FAILURE_CLASSES,
  NarratorEnvironmentCognitionError,
  extractEnvironmentCognitionFailure,
} from '../src/lib/narrator-forensic-attribution.mjs';
import { runNarratorEnvironmentCognition } from '../src/lib/narrator-environment-cognition-substrate.mjs';

const VALID_PRESENTATION = 'Alice opened the door.';

function createTrace() {
  const events = [];
  return {
    events,
    emit(_session, type, _scope, payload) {
      events.push({ type, payload });
    },
  };
}

function createEnvCognitionApi(overrides = {}) {
  return {
    async prepareNarratorEnvironmentCognitionContext() {
      return { manifest: { contributions: [] } };
    },
    async buildNarratorEnvironmentKnowledgeRequests() {
      return { knowledge_access_requests: [] };
    },
    async finalizeNarratorEnvironmentCognition() {
      return { accepted: true, audit: { cognition_id: 'cog-1' } };
    },
    async prepareNarratorContext() {
      return {
        manifest_id: 'manifest-narrator-1',
        inference_id: 'inf-narrator-1',
        contributions: [],
      };
    },
    async validateNarratorPresentation() {
      return { accepted: true, validation_class: 'accepted', reason: '' };
    },
    ...overrides,
  };
}

function tempRecorder(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-narrator-forensic-'));
  t.after(() => {
    fs.rmSync(root, { recursive: true, force: true });
  });
  return createExecutionEvidenceRecorder({ enabled: true, root });
}

test('extractEnvironmentCognitionFailure preserves structured stage attribution', () => {
  const error = new NarratorEnvironmentCognitionError({
    stage: ENV_COGNITION_STAGES.PREPARE,
    boundary: FORENSIC_BOUNDARIES.DOMAIN_API,
    cause: new TypeError('fetch failed'),
  });
  const extracted = extractEnvironmentCognitionFailure(error);
  assert.equal(extracted.stage, ENV_COGNITION_STAGES.PREPARE);
  assert.equal(extracted.boundary, FORENSIC_BOUNDARIES.DOMAIN_API);
  assert.equal(extracted.reason, 'fetch failed');
});

test('environment cognition retains hgSessionId on inference evidence', async (t) => {
  const recorder = tempRecorder(t);
  const hgSessionId = 'hg-session-env-lineage';
  let capturedContext = null;
  const api = {
    async prepareNarratorEnvironmentCognitionContext() {
      return { manifest: { contributions: [] } };
    },
    async buildNarratorEnvironmentKnowledgeRequests() {
      return { knowledge_access_requests: [] };
    },
    async finalizeNarratorEnvironmentCognition() {
      return { accepted: true, audit: { cognition_id: 'cog-lineage' } };
    },
  };

  await runNarratorEnvironmentCognition({
    api,
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    inferenceId: 'inf-env-1',
    characterId: 'Alice',
    domainCommitId: 'commit-1',
    continuityTurnIndex: 1,
    runEphemeralInference: async ({ evidenceContext }) => {
      capturedContext = evidenceContext;
      const evidenceId = recorder.recordInferenceAttempt({
        evidenceContext,
        manifest: { contributions: [] },
        contextRegistration: { manifestId: 'm1', contributionIds: [] },
        prompt: 'test',
        profile: { kind: 'mock' },
        trace: { finish: { kind: 'stop' } },
        assistantText: JSON.stringify({
          baseline_sufficient: true,
          information_needs: [],
          resolutions: [],
        }),
        inferenceSessionId: 'is-env-1',
      });
      return {
        failed: false,
        raw: JSON.stringify({
          baseline_sufficient: true,
          information_needs: [],
          resolutions: [],
        }),
        evidenceId,
      };
    },
  });

  assert.equal(capturedContext?.hgSessionId, hgSessionId);
  assert.equal(capturedContext?.inferenceKind, 'narrator_environment_cognition');
  const index = recorder.readIndex(hgSessionId);
  assert.equal(index.attempt_ids.length, 1);
  const attempt = recorder.readAttempt(hgSessionId, index.attempt_ids[0]);
  assert.equal(attempt.correlation.hg_session_id, hgSessionId);
  assert.equal(attempt.correlation.inference_kind, 'narrator_environment_cognition');
});

test('environment cognition prepare failure returns structured stage attribution', async () => {
  const api = {
    async prepareNarratorEnvironmentCognitionContext() {
      throw new TypeError('fetch failed');
    },
  };
  await assert.rejects(
    () => runNarratorEnvironmentCognition({
      api,
      hgSessionId: 'scene-1',
      hgSceneId: 'scene-1',
      hgRoundId: 'round-1',
      inferenceId: 'inf-env-fail',
      characterId: 'Alice',
      domainCommitId: 'commit-1',
      continuityTurnIndex: 1,
      runEphemeralInference: async () => ({ failed: false, raw: '{}' }),
    }),
    (error) => {
      assert.ok(error instanceof NarratorEnvironmentCognitionError);
      assert.equal(error.stage, ENV_COGNITION_STAGES.PREPARE);
      assert.equal(error.boundary, FORENSIC_BOUNDARIES.DOMAIN_API);
      return true;
    },
  );
});

test('runNarratorPhase records pre-inference context prepare failure', async (t) => {
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-prepare-fail';
  const api = createEnvCognitionApi({
    async prepareNarratorContext() {
      throw new TypeError('fetch failed');
    },
  });
  const result = await runNarratorPhase({
    api,
    recorder,
    trace: createTrace(),
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-prepare-fail',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async () => ({
      evidenceId: 'should-not-run',
      failed: false,
      raw: VALID_PRESENTATION,
      trace: { finish: { kind: 'stop' } },
    }),
  });

  assert.equal(result.presentation_failed, true);
  const attempts = recorder.readIndex(hgSessionId).attempt_ids.map(
    (id) => recorder.readAttempt(hgSessionId, id),
  );
  const narratorAttempts = attempts.filter((attempt) => attempt.correlation.role === 'narrator');
  assert.equal(narratorAttempts.length, 1);
  const forensic = narratorAttempts[0].decision.forensic_attribution;
  assert.equal(forensic.failure_class, NARRATOR_FAILURE_CLASSES.CONTEXT_PREPARE);
  assert.equal(forensic.boundary, FORENSIC_BOUNDARIES.DOMAIN_API);
  assert.equal(forensic.pre_inference_record, true);
});

test('runNarratorPhase records inference-boundary throw without normal attempt record', async (t) => {
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-inference-throw';
  const api = createEnvCognitionApi();
  const result = await runNarratorPhase({
    api,
    recorder,
    trace: createTrace(),
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-throw',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async ({ evidenceContext }) => {
      if (evidenceContext?.inferenceKind === 'narrator_environment_cognition') {
        return {
          failed: false,
          raw: JSON.stringify({
            baseline_sufficient: true,
            information_needs: [],
            resolutions: [],
          }),
          evidenceId: recorder.recordInferenceAttempt({
            evidenceContext,
            manifest: { contributions: [] },
            contextRegistration: { manifestId: 'm-env', contributionIds: [] },
            prompt: 'env',
            profile: { kind: 'mock' },
            trace: { finish: { kind: 'stop' } },
            assistantText: '{}',
            inferenceSessionId: 'is-env',
          }),
        };
      }
      throw new TypeError('fetch failed');
    },
  });

  assert.equal(result.presentation_failed, true);
  const attempts = recorder.readIndex(hgSessionId).attempt_ids.map(
    (id) => recorder.readAttempt(hgSessionId, id),
  );
  const mainNarrator = attempts.filter(
    (attempt) => attempt.correlation.role === 'narrator'
      && attempt.correlation.inference_kind !== 'narrator_environment_cognition',
  );
  assert.ok(mainNarrator.length >= 1);
  assert.ok(
    mainNarrator.some(
      (attempt) => attempt.decision.forensic_attribution?.failure_class
        === NARRATOR_FAILURE_CLASSES.INFERENCE_BOUNDARY_THROW,
    ),
  );
  for (const attempt of mainNarrator) {
    assert.equal(attempt.request, null);
    assert.equal(attempt.response, null);
    assert.equal(attempt.decision.forensic_attribution.pre_inference_record, true);
  }
});

test('runNarratorPhase healthy path unchanged and records normal narrator evidence', async (t) => {
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-healthy';
  const api = createEnvCognitionApi();
  const result = await runNarratorPhase({
    api,
    recorder,
    trace: createTrace(),
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-healthy',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async ({ evidenceContext, mockResponses }) => {
      const evidenceId = recorder.recordInferenceAttempt({
        evidenceContext,
        manifest: { contributions: [] },
        contextRegistration: { manifestId: 'm1', contributionIds: [] },
        prompt: 'test',
        profile: { kind: 'mock' },
        trace: { finish: { kind: 'stop' } },
        assistantText: mockResponses?.[0] ?? VALID_PRESENTATION,
        inferenceSessionId: `is-${evidenceContext.inferenceId}`,
      });
      return {
        evidenceId,
        failed: false,
        raw: mockResponses?.[0] ?? VALID_PRESENTATION,
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(result.presentation_failed, false);
  const attempts = recorder.readIndex(hgSessionId).attempt_ids.map(
    (id) => recorder.readAttempt(hgSessionId, id),
  );
  const mainNarrator = attempts.find(
    (attempt) => attempt.correlation.inference_id === 'inf-narrator-healthy',
  );
  assert.ok(mainNarrator?.request);
  assert.ok(mainNarrator?.response);
  assert.equal(mainNarrator.decision.outcome, 'succeeded');
});

test('runNarratorPhase empty narrator output still uses degraded fallback path', async (t) => {
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-empty';
  const api = createEnvCognitionApi();
  const result = await runNarratorPhase({
    api,
    recorder,
    trace: createTrace(),
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-empty',
    mockNarratorResponses: [''],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async ({ evidenceContext }) => {
      const evidenceId = recorder.recordInferenceAttempt({
        evidenceContext,
        manifest: { contributions: [] },
        contextRegistration: { manifestId: 'm1', contributionIds: [] },
        prompt: 'test',
        profile: { kind: 'mock' },
        trace: { finish: { kind: 'stop' } },
        assistantText: '',
        inferenceSessionId: 'is-empty',
      });
      return {
        evidenceId,
        failed: false,
        raw: '',
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_failed, true);
  assert.equal(result.terminal_disposition, 'committed_fallback');
});
