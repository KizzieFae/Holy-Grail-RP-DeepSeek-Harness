/**
 * Mount the official DSH DeepSeek adapter on an existing Cordis context.
 * Loaded dynamically so mock-only tests do not require the provider package.
 *
 * Per-call agent options (reasoningEffort, thinking, maxTokens) must define effective
 * provider behavior; mount-time defaults must not override role profiles.
 */
export async function mountDeepSeekProvider(ctx, config = {}) {
  const { apply: mountDeepSeekAdapter } = await import('@deepseek-ai/dsh-llm-deepseek');
  mountDeepSeekAdapter(ctx, {
    apiKeyEnv: config.apiKeyEnv ?? 'DEEPSEEK_API_KEY',
    ...config,
  });
}
