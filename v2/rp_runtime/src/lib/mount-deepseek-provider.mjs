/**
 * Mount the official DSH DeepSeek adapter on an existing Cordis context.
 * Loaded dynamically so mock-only tests do not require the provider package.
 */
export async function mountDeepSeekProvider(ctx, config = {}) {
  const { apply: mountDeepSeekAdapter } = await import('@deepseek-ai/dsh-llm-deepseek');
  mountDeepSeekAdapter(ctx, {
    apiKeyEnv: config.apiKeyEnv ?? 'DEEPSEEK_API_KEY',
    thinking: config.thinking ?? 'enabled',
    reasoningEffort: config.reasoningEffort ?? 'low',
    maxTokens: config.maxTokens ?? 4096,
    ...config,
  });
}
