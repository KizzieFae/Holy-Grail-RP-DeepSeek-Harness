import AgentLoop from '@deepseek-ai/dsh-agent-loop';
import { mountAgentLoopTestDependencies } from '@deepseek-ai/dsh-agent-loop-testkit';

/**
 * Mount the DSH/Cordis substrate required for Holy Grail RP runtime services.
 * Holy Grail service plugins are mounted separately via mountHolyGrailServices.
 */
export async function mountRpStack(ctx, config = {}, options = {}) {
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
