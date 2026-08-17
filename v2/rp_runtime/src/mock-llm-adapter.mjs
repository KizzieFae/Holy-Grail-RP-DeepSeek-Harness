import { LlmAdapter } from '@deepseek-ai/dsh-llm';

const PROVIDER = 'hg-mock';
const MODEL = 'deterministic-v2';

/** Deterministic mock adapter for architecture validation (not production). */
export class HgMockLlmAdapter extends LlmAdapter {
  constructor(responses) {
    super();
    this.responses = responses;
    this.callIndex = 0;
  }

  providerInfo(provider) {
    return { id: provider, name: 'Holy Grail Mock LLM' };
  }

  async listModels(_provider) {
    return [{ id: MODEL, name: 'Deterministic V2 Move', inputModalities: ['text'] }];
  }

  async resolveModel(provider, model) {
    return {
      provider,
      id: model,
      name: model,
      inputModalities: ['text'],
      context: { contextWindow: 8192 },
      defaultMaxTokens: 1024,
    };
  }

  async *stream(options) {
    if (options.signal?.aborted) {
      yield {
        type: 'finish',
        reason: { kind: 'aborted', failure: { message: 'aborted', code: 'ABORTED' } },
      };
      return;
    }

    const text = this.responses[this.callIndex] ?? this.responses[this.responses.length - 1] ?? '{}';
    this.callIndex += 1;
    const index = 0;
    yield { type: 'block-start', index, blockType: 'text' };
    yield { type: 'text-delta', index, text };
    yield { type: 'block-end', index, block: { type: 'text', text } };
    yield { type: 'usage', usage: { inputTokens: 12, outputTokens: text.length } };
    yield { type: 'finish', reason: { kind: 'stop' } };
  }
}

export const HG_MOCK_PROVIDER = PROVIDER;
export const HG_MOCK_MODEL = MODEL;
