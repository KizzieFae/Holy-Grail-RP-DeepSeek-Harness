import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { buildNarratorSummary } from '../src/lib/role-inference-summary.mjs';
import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';

const VALID_PRESENTATION = 'Alice nodded thoughtfully, taking in the workshop around her.';

function makeSemanticSoftReject(passId = 'narrator-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'Tone could be tighter',
      rationale: 'test',
    }],
  });
}

function createMockApi() {
  return {
    async prepareNarratorContext(body) {
      return {
        manifest_id: `manifest-narrator-${body.inference_id}-${body.attempt_index ?? 0}`,
        inference_id: body.inference_id,
        contributions: body.correction_context
          ? [{ source_kind: 'semantic_correction', content: JSON.stringify(body.correction_context) }]
          : [],
      };
    },
    async prepareNarratorSemanticQaContext() {
      return {
        manifest_id: 'manifest-narrator-qa-1',
        inference_id: 'inf-narrator-1',
        hg_scene_id: 'scene-1',
        hg_round_id: 'round-1',
        turn_index: 0,
        authority_references: [{
          ref_id: 'commit:abc',
          kind: 'committed_move',
          authority_class: 'authoritative',
          label: 'Committed move',
          text: 'Alice nods.',
        }],
        contributions: [{
          contribution_id: 'manifest-narrator-qa-1-role',
          source_kind: 'committed_move',
          authority_class: 'authoritative',
          priority: 10,
          content: 'Narrator QA context',
          knowledge_ids: [],
          provenance: {},
        }],
      };
    },
    async validateNarratorPresentation() {
      return { accepted: true, validation_class: 'accepted', reason: '' };
    },
    async prepareNarratorEnvironmentCognitionContext() {
      return { manifest: { contributions: [] } };
    },
    async buildNarratorEnvironmentKnowledgeRequests() {
      return { knowledge_access_requests: [] };
    },
    async finalizeNarratorEnvironmentCognition() {
      return { accepted: true, audit: { cognition_id: 'cog-1' } };
    },
  };
}

function createTrace() {
  const events = [];
  return {
    events,
    emit(_session, type, _scope, payload) {
      events.push({ type, payload });
    },
  };
}

function tempRecorder(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-narrator-last-attempt-'));
  t.after(() => {
    fs.rmSync(root, { recursive: true, force: true });
  });
  return createExecutionEvidenceRecorder({ enabled: true, root });
}

test('runNarratorPhase regen then inference throw clears stale attempt metadata', async (t) => {
  const api = createMockApi();
  const trace = createTrace();
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-regen-throw';

  const result = await runNarratorPhase({
    api,
    recorder,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-regen-throw',
    mockNarratorResponses: [VALID_PRESENTATION, 'Alice nodded again with richer detail.'],
    mockNarratorSemanticQaResponses: [makeSemanticSoftReject('inf-narrator-regen-throw-qa-0')],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ evidenceContext, mockResponses }) => {
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
      if (evidenceContext?.role === 'semantic_evaluator') {
        return {
          evidenceId: 'ev-eval',
          inferenceSessionId: 'is-eval',
          raw: mockResponses?.[0] ?? makeSemanticSoftReject(),
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      if (evidenceContext?.attemptIndex === 1) {
        throw new TypeError('fetch failed');
      }
      const evidenceId = recorder.recordInferenceAttempt({
        evidenceContext,
        manifest: { contributions: [] },
        contextRegistration: { manifestId: 'm-1', contributionIds: [] },
        prompt: 'narrator',
        profile: { kind: 'mock' },
        trace: { provider: 'hg-mock', failed: false, finish: { kind: 'stop' } },
        assistantText: mockResponses?.[0] ?? VALID_PRESENTATION,
        inferenceSessionId: 'is-attempt-0',
      });
      return {
        evidenceId,
        inferenceSessionId: 'is-attempt-0',
        raw: mockResponses?.[0] ?? VALID_PRESENTATION,
        failed: false,
        trace: { provider: 'hg-mock', failed: false, finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_failed, true);
  assert.equal(result.narrator_inference_trace, null);
  assert.equal(result.narrator_inference_session_id, null);
  assert.equal(result.presentation_failure_reason, 'fetch failed');
  assert.ok(result.narrator_evidence_id);

  const summary = buildNarratorSummary(result);
  assert.equal(summary.phase_outcome, 'degraded');
  assert.equal(summary.inference_execution, 'attempted');
  assert.equal(summary.inference_trace, null);
  assert.equal(summary.inference_session_id, null);
  assert.equal(summary.evidence_id, result.narrator_evidence_id);

  const attempts = recorder.readIndex(hgSessionId).attempt_ids.map(
    (id) => recorder.readAttempt(hgSessionId, id),
  );
  const mainNarrator = attempts.filter(
    (attempt) => attempt.correlation.role === 'narrator'
      && attempt.correlation.inference_kind !== 'narrator_environment_cognition',
  );
  assert.ok(mainNarrator.length >= 2);
  const finalFailure = mainNarrator.find(
    (attempt) => attempt.decision.forensic_attribution?.failure_class === 'inference_boundary_throw',
  );
  assert.ok(finalFailure);
  assert.equal(result.narrator_evidence_id, finalFailure.evidence_id);
  assert.notEqual(finalFailure.evidence_id, mainNarrator[0].evidence_id);
});

test('runNarratorPhase first inference throw remains attempted without stale metadata', async (t) => {
  const api = createMockApi();
  const trace = createTrace();
  const recorder = tempRecorder(t);
  const hgSessionId = 'scene-first-throw';

  const result = await runNarratorPhase({
    api,
    recorder,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-first-throw',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async ({ evidenceContext }) => {
      if (evidenceContext?.inferenceKind === 'narrator_environment_cognition') {
        return {
          failed: false,
          raw: '{}',
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

  assert.equal(result.narrator_inference_trace, null);
  assert.equal(result.narrator_inference_session_id, null);
  const summary = buildNarratorSummary(result);
  assert.equal(summary.phase_outcome, 'degraded');
  assert.equal(summary.inference_execution, 'attempted');
});
