// Node/DSH tests for Narrator environmental cognition orchestration (#49 remediation).

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCognitionPrompt,
  parseCognitionResult,
  runNarratorEnvironmentCognition,
} from '../src/lib/narrator-environment-cognition-substrate.mjs';

test('narrator environment cognition substrate imports librarian mediation sibling', async () => {
  const mod = await import('../src/lib/narrator-environment-cognition-substrate.mjs');
  assert.equal(typeof mod.runNarratorEnvironmentCognition, 'function');
});

test('parseCognitionResult rejects invalid JSON', () => {
  const parsed = parseCognitionResult('not-json');
  assert.equal(parsed.ok, false);
});

function createMockApi({
  finalizeResult = { accepted: true, audit: { cognition_id: 'cog-1' } },
  mediationOutcome = 'no_match',
} = {}) {
  const calls = {
    prepare: 0,
    kar: 0,
    finalize: 0,
    librarianPrepare: 0,
    librarianFinalize: 0,
  };
  return {
    calls,
    async prepareNarratorEnvironmentCognitionContext() {
      calls.prepare += 1;
      return {
        manifest: { contributions: [] },
        context: { environmental_current_view: { location_ref: 'location:workshop' } },
      };
    },
    async buildNarratorEnvironmentKnowledgeRequests({ n1_result: n1 }) {
      calls.kar += 1;
      if (n1?.baseline_sufficient) {
        return { knowledge_access_requests: [] };
      }
      return {
        knowledge_access_requests: [{
          request_id: 'kar-need-1',
          consumer_role: 'narrator',
        }],
      };
    },
    async finalizeNarratorEnvironmentCognition(body) {
      calls.finalize += 1;
      return {
        ...finalizeResult,
        audit: {
          cognition_id: 'cog-test',
          establishment_decisions: finalizeResult.establishment_decisions ?? [],
          ...finalizeResult.audit,
        },
        cognition_result: body.cognition_result,
        librarian_outcomes: body.librarian_outcomes,
      };
    },
    async prepareLibrarianMediationContext() {
      calls.librarianPrepare += 1;
      return {
        request_id: 'req-lib-1',
        mediation_catalog: [],
        manifest: { contributions: [] },
      };
    },
    async finalizeLibrarianMediation() {
      calls.librarianFinalize += 1;
      return {
        mediation_outcome: mediationOutcome,
        bundle: { mediation_outcome: mediationOutcome },
        audit: { host_validation: { accepted: true } },
      };
    },
  };
}

const NO_MATCH_MEDIATION_RESPONSE = JSON.stringify({
  schema: 'hg_librarian_mediation_result_v1',
  mediation_outcome: 'no_match',
  selected_source_ids: [],
  rationale: 'test no match',
});

test('baseline sufficient skips Librarian mediation', async () => {
  const api = createMockApi();
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async () => ({ failed: false, raw: JSON.stringify({
      baseline_sufficient: true,
      information_needs: [],
      resolutions: [],
    }) }),
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    inferenceId: 'inf-1',
    characterId: 'Alice',
    domainCommitId: 'commit-1',
    continuityTurnIndex: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(api.calls.kar, 1);
  assert.equal(api.calls.librarianPrepare, 0);
  assert.equal(api.calls.finalize, 1);
});

test('information need invokes Librarian mediation', async () => {
  const api = createMockApi();
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async ({ inferenceKind }) => ({
      failed: false,
      raw: inferenceKind === 'librarian_mediation'
        ? NO_MATCH_MEDIATION_RESPONSE
        : JSON.stringify({
          baseline_sufficient: false,
          information_needs: [{ need_id: 'need-1', question: 'What color are the walls?' }],
          resolutions: [{
            need_id: 'need-1',
            category: 'B2',
            detail: 'walls are teal',
            property_key: 'wall_color',
            value: 'teal',
            stable_refs: ['location:workshop'],
          }],
        }),
    }),
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    inferenceId: 'inf-2',
    characterId: 'Alice',
    domainCommitId: 'commit-2',
    continuityTurnIndex: 2,
  });
  assert.equal(api.calls.librarianPrepare, 1);
  assert.equal(api.calls.librarianFinalize, 1);
  assert.equal(result.librarianOutcomes[0].mediation_outcome, 'no_match');
  assert.equal(result.ok, true);
});

test('match mediation outcome forwarded to finalize without duplicate B2 persistence', async () => {
  const api = createMockApi({
    mediationOutcome: 'match',
    finalizeResult: {
      accepted: true,
      establishment_decisions: [{ accepted: false, reason: 'origination_requires_no_match' }],
    },
  });
  let finalizeBody = null;
  const baseFinalize = api.finalizeNarratorEnvironmentCognition.bind(api);
  api.finalizeNarratorEnvironmentCognition = async (body) => {
    finalizeBody = body;
    return baseFinalize(body);
  };
  await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async ({ inferenceKind }) => ({
      failed: false,
      raw: inferenceKind === 'librarian_mediation'
        ? JSON.stringify({
          schema: 'hg_librarian_mediation_result_v1',
          mediation_outcome: 'match',
          selected_source_ids: ['src-1'],
          rationale: 'matched authored detail',
        })
        : JSON.stringify({
          baseline_sufficient: false,
          information_needs: [{ need_id: 'need-1', question: 'Wall color?' }],
          resolutions: [{
            need_id: 'need-1',
            category: 'B2',
            detail: 'teal walls',
            property_key: 'wall_color',
            value: 'teal',
          }],
        }),
    }),
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    inferenceId: 'inf-match',
    characterId: 'Alice',
    domainCommitId: 'commit-match',
    continuityTurnIndex: 3,
  });
  assert.equal(finalizeBody.librarian_outcomes[0].mediation_outcome, 'match');
  assert.equal(finalizeBody.cognition_result.resolutions[0].mediation_outcome, 'match');
});

test('cognition inference failure returns auditable failure when fallback disabled', async () => {
  const api = createMockApi();
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async () => ({ failed: true, failure: { reason: 'provider_error' } }),
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    inferenceId: 'inf-fail',
    characterId: 'Alice',
    domainCommitId: 'commit-fail',
    continuityTurnIndex: 4,
    allowDeterministicFallback: false,
  });
  assert.equal(result.ok, false);
  assert.equal(result.stage, 'cognition_inference');
  assert.match(result.failureReason, /provider_error/);
});

test('buildCognitionPrompt mentions no_match origination rule', () => {
  const prompt = buildCognitionPrompt();
  assert.match(prompt, /no_match/i);
});
