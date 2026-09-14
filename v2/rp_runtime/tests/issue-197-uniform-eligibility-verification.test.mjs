import assert from 'node:assert/strict';
import test from 'node:test';

import { parsePlayerUniformEligibilityVerificationEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import {
  isUniformEligibilityVerificationClear,
  runPlayerUniformEligibilityVerification,
} from '../src/plugins/hg-phase-executors/player-uniform-eligibility-verification.mjs';
import {
  runPlayerVisibilityTriagePhase,
} from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { mockInferenceProfile } from '../src/lib/inference-profile.mjs';

const AFFIRMATIVE_TRIAGE = JSON.stringify({
  uniform_projection_safe: true,
  reason: 'affirmative_uniform_present',
});
const NEGATIVE_TRIAGE = JSON.stringify({
  uniform_projection_safe: false,
  reason: 'requires_semantic_decomposition',
});
const VERIFICATION_CLEAR = JSON.stringify({
  uniform_eligibility_disposition: 'clear',
  reason: 'no_disqualifier_found',
});
const VERIFICATION_DISQUALIFIED = JSON.stringify({
  uniform_eligibility_disposition: 'disqualified',
  reason: 'implicit_internal_state',
});
const VERIFICATION_UNCERTAIN = JSON.stringify({
  uniform_eligibility_disposition: 'uncertain',
  reason: 'ambiguous_internal_state',
});

function triageApi() {
  return {
    preparePlayerVisibilityTriageContext: async () => ({ manifest_id: 'm-triage', contributions: [] }),
    preparePlayerUniformEligibilityVerificationContext: async () => ({
      manifest_id: 'm-verify',
      contributions: [],
    }),
  };
}

function makeInferenceQueue(responses) {
  const queue = [...responses];
  return async () => {
    const raw = queue.shift();
    if (raw === 'THROW') {
      return { failed: true, failure: { message: 'unavailable' }, evidenceId: 'e-fail' };
    }
    return { failed: false, raw, evidenceId: `e-${queue.length}` };
  };
}

test('parsePlayerUniformEligibilityVerificationEnvelope accepts clear disposition', () => {
  const parsed = parsePlayerUniformEligibilityVerificationEnvelope(VERIFICATION_CLEAR);
  assert.equal(parsed.parseError, null);
  assert.equal(parsed.disposition, 'clear');
  assert.equal(isUniformEligibilityVerificationClear(parsed), true);
});

test('parsePlayerUniformEligibilityVerificationEnvelope rejects malformed output', () => {
  const parsed = parsePlayerUniformEligibilityVerificationEnvelope('not-json');
  assert.ok(parsed.parseError);
});

test('negative triage does not invoke verifier', async () => {
  let inferenceCalls = 0;
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference: async () => {
      inferenceCalls += 1;
      return { failed: false, raw: NEGATIVE_TRIAGE, evidenceId: 'e1' };
    },
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'Secret thought.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(inferenceCalls, 1);
  assert.equal(result.route, 'full_pvr');
});

test('affirmative triage + verification clear routes to uniform', async () => {
  const runEphemeralInference = makeInferenceQueue([AFFIRMATIVE_TRIAGE, VERIFICATION_CLEAR]);
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'The player waves.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'uniform_projection');
  assert.equal(result.checkerResult.verification.disposition, 'clear');
});

test('affirmative triage + disqualifier routes to full_pvr', async () => {
  const runEphemeralInference = makeInferenceQueue([AFFIRMATIVE_TRIAGE, VERIFICATION_DISQUALIFIED]);
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-2',
    inferenceId: 'triage-test',
    playerContent: 'Mixed internal and observable.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
  assert.equal(result.checkerResult.triage_affirmative, true);
  assert.equal(result.checkerResult.fail_safe, 'uniform_eligibility_verification_blocked');
});

test('affirmative triage + uncertain verification routes to full_pvr', async () => {
  const runEphemeralInference = makeInferenceQueue([AFFIRMATIVE_TRIAGE, VERIFICATION_UNCERTAIN]);
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-3',
    inferenceId: 'triage-test',
    playerContent: 'Maybe internal.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
});

test('affirmative triage + malformed verification routes to full_pvr', async () => {
  const runEphemeralInference = makeInferenceQueue([AFFIRMATIVE_TRIAGE, 'not-json']);
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-4',
    inferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
});

test('affirmative triage + verification inference failure routes to full_pvr', async () => {
  const runEphemeralInference = makeInferenceQueue([AFFIRMATIVE_TRIAGE, 'THROW']);
  const result = await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-5',
    inferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
});

test('triage failure does not invoke verifier', async () => {
  let inferenceCalls = 0;
  const result = await runPlayerVisibilityTriagePhase({
    api: {
      preparePlayerVisibilityTriageContext: async () => {
        throw new Error('context prepare failed');
      },
    },
    runEphemeralInference: async () => {
      inferenceCalls += 1;
      return { failed: false, raw: AFFIRMATIVE_TRIAGE, evidenceId: 'e1' };
    },
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-6',
    inferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(inferenceCalls, 0);
  assert.equal(result.route, 'full_pvr');
});

test('verifier invoked exactly once for affirmative proposal', async () => {
  let inferenceCalls = 0;
  const runEphemeralInference = async () => {
    inferenceCalls += 1;
    return {
      failed: false,
      raw: inferenceCalls === 1 ? AFFIRMATIVE_TRIAGE : VERIFICATION_CLEAR,
      evidenceId: `e-${inferenceCalls}`,
    };
  };
  await runPlayerVisibilityTriagePhase({
    api: triageApi(),
    runEphemeralInference,
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-7',
    inferenceId: 'triage-test',
    playerContent: 'The player nods.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(inferenceCalls, 2);
});

test('standalone verifier context prepare failure is fail-closed', async () => {
  const result = await runPlayerUniformEligibilityVerification({
    api: {
      preparePlayerUniformEligibilityVerificationContext: async () => {
        throw new Error('prepare failed');
      },
    },
    runEphemeralInference: async () => ({ failed: false, raw: VERIFICATION_CLEAR }),
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-8',
    triageInferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.passed, false);
});
