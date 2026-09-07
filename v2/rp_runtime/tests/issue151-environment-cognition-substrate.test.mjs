// Issue #151 — environmental cognition substrate false-sufficiency removal.

import assert from 'node:assert/strict';
import test from 'node:test';

import { runNarratorEnvironmentCognition } from '../src/lib/narrator-environment-cognition-substrate.mjs';

function createMockApi(finalizeHandler = null) {
  const calls = { kar: 0, finalize: 0, librarianPrepare: 0 };
  return {
    calls,
    async prepareNarratorEnvironmentCognitionContext() {
      return { manifest: { contributions: [] } };
    },
    async buildNarratorEnvironmentKnowledgeRequests() {
      calls.kar += 1;
      return { knowledge_access_requests: [] };
    },
    async finalizeNarratorEnvironmentCognition(body) {
      calls.finalize += 1;
      if (finalizeHandler) {
        return finalizeHandler(body);
      }
      const status = body.inference_envelope?.inference_failed
        ? 'indeterminate'
        : (body.cognition_raw ? 'determined' : 'indeterminate');
      const reason = body.inference_envelope?.inference_failed
        ? 'inference_error'
        : (body.cognition_raw ? 'model_result' : 'empty_output');
      const renderBehavior = status === 'determined' ? 'no_material_obligation' : 'sufficiency_undetermined';
      return {
        accepted: true,
        cognition_status: status,
        status_reason: reason,
        baseline_sufficient: status === 'determined' ? true : null,
        audit: {
          cognition_id: 'cog-151',
          cognition_status: status,
          status_reason: reason,
          cognition_failed: false,
          environmental_response_obligations: [{
            render_behavior: renderBehavior,
            sufficiency_state: status === 'determined' ? 'sufficient' : 'undetermined',
          }],
          environmental_response_obligations_text: `render_behavior: ${renderBehavior}`,
          n1: { baseline_sufficient: status === 'determined' ? true : null },
        },
      };
    },
    async prepareLibrarianMediationContext() {
      calls.librarianPrepare += 1;
      return { request_id: 'req-lib', manifest: { contributions: [] } };
    },
    async finalizeLibrarianMediation() {
      return { mediation_outcome: 'no_match', entries: [] };
    },
  };
}

test('empty inference output passes envelope to domain without local sufficiency fallback', async () => {
  const api = createMockApi();
  let finalizeBody = null;
  const baseFinalize = api.finalizeNarratorEnvironmentCognition.bind(api);
  api.finalizeNarratorEnvironmentCognition = async (body) => {
    finalizeBody = body;
    return baseFinalize(body);
  };
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async () => ({ failed: false, raw: '', trace: { finish: { kind: 'max-tokens' } } }),
    hgSessionId: 'scene-151',
    hgSceneId: 'scene-151',
    hgRoundId: 'round-151',
    inferenceId: 'inf-151',
    characterId: 'Kizzie',
    domainCommitId: 'commit-151',
    continuityTurnIndex: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(finalizeBody.inference_envelope.finish_kind, 'max-tokens');
  assert.equal(finalizeBody.cognition_raw, '');
  assert.equal(api.calls.librarianPrepare, 0);
  assert.equal(result.environmentCognitionEvidence.cognition_status, 'indeterminate');
  assert.equal(result.environmentCognitionEvidence.baseline_sufficient, null);
});

test('inference failure does not synthesize parse_fallback_baseline_sufficient', async () => {
  const api = createMockApi();
  let finalizeBody = null;
  const baseFinalize = api.finalizeNarratorEnvironmentCognition.bind(api);
  api.finalizeNarratorEnvironmentCognition = async (body) => {
    finalizeBody = body;
    return baseFinalize(body);
  };
  await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async () => ({ failed: true, raw: '', trace: { finish: { kind: 'error' } } }),
    hgSessionId: 'scene-151b',
    hgSceneId: 'scene-151b',
    hgRoundId: 'round-151b',
    inferenceId: 'inf-151b',
    characterId: 'Kizzie',
    domainCommitId: 'commit-151b',
    continuityTurnIndex: 1,
  });
  assert.equal(finalizeBody.inference_envelope.inference_failed, true);
  assert.notEqual(finalizeBody.cognition_result?.assessment_notes, 'parse_fallback_baseline_sufficient');
  assert.notEqual(finalizeBody.cognition_result?.assessment_notes, 'deterministic_fallback_baseline_sufficient');
});

test('valid cognition still finalizes with model payload', async () => {
  const api = createMockApi();
  const valid = JSON.stringify({
    baseline_sufficient: true,
    information_needs: [],
    resolutions: [],
  });
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async () => ({ failed: false, raw: valid, trace: { finish: { kind: 'complete' } } }),
    hgSessionId: 'scene-151c',
    hgSceneId: 'scene-151c',
    hgRoundId: 'round-151c',
    inferenceId: 'inf-151c',
    characterId: 'Kizzie',
    domainCommitId: 'commit-151c',
    continuityTurnIndex: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(result.environmentCognitionEvidence.cognition_status, 'determined');
});
