import assert from 'node:assert/strict';
import test from 'node:test';

import { runNarratorEnvironmentCognition } from '../src/lib/narrator-environment-cognition-substrate.mjs';
import {
  classifyCognitionResultDeliberationProfile,
  DELIBERATION_PROFILE_CONSTRAINED,
  DELIBERATION_PROFILE_DEEP,
  shouldEscalateConstrainedCognitionToDeep,
} from '../src/lib/narrator-environment-deliberation-profile.mjs';

test('mediation outcome on cognition result classifies deep', () => {
  const profile = classifyCognitionResultDeliberationProfile({
    information_needs: [{ need_id: 'a' }],
    resolutions: [{ category: 'B2', mediation_outcome: 'match' }],
  });
  assert.equal(profile, DELIBERATION_PROFILE_DEEP);
});

test('constrained probe that reveals multi-need escalates to deep before KAR', async () => {
  const prepareCalls = [];
  const reasoningEfforts = [];
  const complexProbe = JSON.stringify({
    baseline_sufficient: false,
    information_needs: [{ need_id: 'a' }, { need_id: 'b' }],
    resolutions: [{ category: 'B2', need_id: 'a' }, { category: 'B2', need_id: 'b' }],
  });
  const deepResult = JSON.stringify({
    baseline_sufficient: false,
    information_needs: [{ need_id: 'a' }],
    resolutions: [{ category: 'B2', need_id: 'a', property_key: 'house_number', value: '12' }],
  });

  const api = {
    async prepareNarratorEnvironmentCognitionContext(body) {
      prepareCalls.push(body);
      const profile = body.deliberation_profile_override === DELIBERATION_PROFILE_DEEP
        ? DELIBERATION_PROFILE_DEEP
        : DELIBERATION_PROFILE_CONSTRAINED;
      return {
        manifest: { contributions: [{ source_kind: 'narrator_environment_cognition', content: profile }] },
        deliberation_profile: { profile },
      };
    },
    async buildNarratorEnvironmentKnowledgeRequests() {
      return { knowledge_access_requests: [] };
    },
    async finalizeNarratorEnvironmentCognition(body) {
      return {
        accepted: true,
        cognition_status: 'determined',
        audit: { cognition_id: 'cog-194' },
        baseline_sufficient: false,
        cognition_result: body.cognition_result,
      };
    },
  };

  let inferenceAttempt = 0;
  const result = await runNarratorEnvironmentCognition({
    api,
    runEphemeralInference: async ({ modelProfile }) => {
      reasoningEfforts.push(modelProfile?.reasoningEffort ?? null);
      inferenceAttempt += 1;
      return {
        failed: false,
        raw: inferenceAttempt === 1 ? complexProbe : deepResult,
        trace: { finish: { kind: 'complete' } },
      };
    },
    hgSessionId: 'scene-194',
    hgSceneId: 'scene-194',
    hgRoundId: 'round-194',
    inferenceId: 'inf-194',
    characterId: 'Kizzie',
    domainCommitId: 'commit-194',
    continuityTurnIndex: 1,
    modelProfile: { kind: 'dsh', provider: 'deepseek-official', model: 'deepseek-v4-flash', reasoningEffort: 'low' },
  });

  assert.equal(prepareCalls.length, 2);
  assert.equal(prepareCalls[1].deliberation_profile_override, DELIBERATION_PROFILE_DEEP);
  assert.equal(reasoningEfforts.length, 2);
  assert.equal(reasoningEfforts[0], 'off');
  assert.equal(reasoningEfforts[1], 'low');
  assert.equal(result.deliberationProfileEscalated, true);
  assert.equal(result.initialDeliberationProfile, DELIBERATION_PROFILE_CONSTRAINED);
  assert.equal(result.deliberationProfile, DELIBERATION_PROFILE_DEEP);
  assert.equal(
    shouldEscalateConstrainedCognitionToDeep(
      DELIBERATION_PROFILE_CONSTRAINED,
      JSON.parse(complexProbe),
    ),
    true,
  );
});
