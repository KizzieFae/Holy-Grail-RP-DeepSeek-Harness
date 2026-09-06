import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createExecutionEvidenceRecorder } from '../../lib/execution-evidence/recorder.mjs';
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
export function createInferenceSubstrate(inferenceConfig = {}) {
  const recorder = createExecutionEvidenceRecorder({
    enabled: inferenceConfig.executionEvidence?.enabled,
    root: inferenceConfig.executionEvidence?.root,
    systemPersona: inferenceConfig.systemPersona ?? 'Holy Grail RP runtime.',
  });

  async function runEphemeralInference(ctx, {
    inferenceId,
    prompt,
    manifest,
    mockResponses,
    modelProfile,
    evidenceContext = null,
  }) {
    const profile = resolveInferenceProfile(inferenceConfig, modelProfile);
    const agentOpts = agentOptionsFromProfile(profile);
    let disposeAdapter = () => {};
    let disposeRequestHook = () => {};

    if (profile.kind === 'mock') {
      const adapter = new HgMockLlmAdapter(
        mockResponses.length ? mockResponses : ['{}'],
      );
      disposeAdapter = ctx.llm.registerAdapter([profile.provider], adapter);
    }

    const agent = ctx.agentLoop.create(
      SessionId(`hg-inf-${inferenceId}`),
      {
        provider: agentOpts.provider,
        model: agentOpts.model,
        maxTokens: agentOpts.maxTokens,
      },
    );
    if (agentOpts.reasoningEffort !== undefined) {
      disposeRequestHook = agent.ctx.on('agent/request', async (_payload, next) => {
        const resolved = await next();
        return {
          ...resolved,
          reasoningEffort: agentOpts.reasoningEffort,
        };
      });
    }
    const contextRegistration = ctx.hgContextBridge.registerManifest({
      agent,
      manifest,
      inferenceKind: evidenceContext?.inferenceKind ?? null,
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
    const evidenceId = recorder.recordInferenceAttempt({
      evidenceContext,
      manifest,
      contextRegistration,
      prompt,
      profile,
      trace,
      assistantText: raw,
      inferenceSessionId: String(agent.id),
    });
    contextRegistration.dispose();
    disposeRequestHook();
    disposeAdapter();

    return {
      raw,
      inferenceSessionId: String(agent.id),
      trace,
      failed: trace.failed,
      failure: trace.failure,
      inferenceSessionEvents: [...agent.session.events],
      evidenceId,
    };
  }

  return { runEphemeralInference, recorder };
}
