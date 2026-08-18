import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';

import HgContextBridge from '../plugins/hg-context-bridge/service.mjs';
import HgPhaseExecutors from '../plugins/hg-phase-executors/service.mjs';
import HgTraceEmitter from '../plugins/hg-trace-emitter/service.mjs';

/**
 * Mount the DSH/Cordis composition required for Holy Grail RP runtime services.
 * Composition authority lives in bootstrap, not the round orchestrator.
 */
export async function mountRpStack(ctx, config = {}, options = {}) {
  if (!ctx.hgContextBridge) {
    new HgContextBridge(ctx);
  }
  HgTraceEmitter.ensure(ctx);
  HgPhaseExecutors.ensure(ctx, config);

  await mountAgentLoopTestDependencies(ctx, {
    systemPrompt: { persona: options.persona ?? 'Holy Grail RP runtime.' },
  });

  if (options.inference?.mountDeepSeek || config.inference?.mountDeepSeek) {
    const { mountDeepSeekProvider } = await import('./mount-deepseek-provider.mjs');
    await mountDeepSeekProvider(ctx, {
      ...config.inference?.deepseek,
      ...options.inference?.deepseek,
    });
  }

  await ctx.plugin(AgentLoop, { agents: [] });
}
