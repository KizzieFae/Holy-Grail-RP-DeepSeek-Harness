import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import {
  agentOptionsFromProfile,
  resolveInferenceProfile,
} from '../../lib/inference-profile.mjs';
import { extractInferenceTrace } from '../../lib/inference-trace.mjs';
import { waitForIdle } from '../../lib/inference-utils.mjs';
import { HgMockLlmAdapter } from '../../mock-llm-adapter.mjs';

/**
 * Shared ephemeral inference substrate for all RP phase executors.
 */
export function createInferenceSubstrate(ctx, inferenceConfig = {}) {
  async function runEphemeralInference({
    inferenceId,
    prompt,
    manifest,
    mockResponses,
    modelProfile,
  }) {
    const profile = resolveInferenceProfile(inferenceConfig, modelProfile);
    let disposeAdapter = () => {};

    if (profile.kind === 'mock') {
      const adapter = new HgMockLlmAdapter(
        mockResponses.length ? mockResponses : ['{}'],
      );
      disposeAdapter = ctx.llm.registerAdapter([profile.provider], adapter);
    }

    const agent = ctx.agentLoop.create(
      SessionId(`hg-inf-${inferenceId}`),
      agentOptionsFromProfile(profile),
    );
    const contextRegistration = ctx.hgContextBridge.registerManifest({
      agent,
      manifest,
    });
    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: prompt }],
        source: { kind: 'user' },
      }),
    );
    await waitForIdle(ctx, agent);

    const trace = extractInferenceTrace(agent.session.events, {
      provider: profile.provider,
      model: profile.model,
      reasoningEffort: profile.reasoningEffort ?? null,
      manifestId: contextRegistration.manifestId,
      contributionIds: contextRegistration.contributionIds,
    });
    const raw = trace.assistant_text;
    contextRegistration.dispose();
    disposeAdapter();

    return {
      raw,
      inferenceSessionId: String(agent.id),
      trace,
      failed: trace.failed,
      failure: trace.failure,
      inferenceSessionEvents: [...agent.session.events],
    };
  }

  return { runEphemeralInference };
}
