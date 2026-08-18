import { finalAssistantText } from './inference-utils.mjs';

function eventData(event) {
  return event?.data ?? {};
}

function latestEvent(events, type) {
  return [...events].reverse().find((event) => event.type === type) ?? null;
}

function collectStreamChunks(events) {
  const summary = {
    text_delta_count: 0,
    reasoning_delta_count: 0,
    block_start_count: 0,
    usage: null,
    finish: null,
  };

  for (const event of events) {
    if (event.type !== 'assistant/chunk') continue;
    const chunk = eventData(event).chunk ?? eventData(event);
    if (!chunk || typeof chunk !== 'object') continue;
    switch (chunk.type) {
      case 'text-delta':
        summary.text_delta_count += 1;
        break;
      case 'reasoning-delta':
        summary.reasoning_delta_count += 1;
        break;
      case 'block-start':
        summary.block_start_count += 1;
        break;
      case 'usage':
        summary.usage = chunk.usage ?? null;
        break;
      case 'finish':
        summary.finish = chunk.reason ?? null;
        break;
      default:
        break;
    }
  }

  return summary;
}

function reasoningTextFromMessage(message) {
  if (!message?.content) return '';
  return message.content
    .filter((block) => block.type === 'reasoning')
    .map((block) => block.text)
    .join('');
}

/**
 * Reconstruct DSH/provider evidence for one ephemeral inference session.
 * Holy Grail domain evidence remains separate (manifest, validation, commit).
 */
export function extractInferenceTrace(events, extras = {}) {
  const list = [...events];
  const requestHeader = latestEvent(list, 'request/header');
  const assistantMessage = latestEvent(list, 'assistant/message');
  const turnEnd = latestEvent(list, 'turn/end');
  const stream = collectStreamChunks(list);

  const headerConfig = eventData(requestHeader).config ?? {};
  const message = eventData(assistantMessage).message ?? null;
  const source = message?.source ?? {};

  const finish = stream.finish ?? eventData(turnEnd).reason ?? null;
  const failed = Boolean(
    finish
    && typeof finish === 'object'
    && (finish.kind === 'error' || finish.kind === 'aborted'),
  );

  return {
    provider: headerConfig.provider ?? source.provider ?? extras.provider ?? null,
    model: headerConfig.model ?? source.model ?? extras.model ?? null,
    reasoning_effort: headerConfig.reasoningEffort ?? extras.reasoningEffort ?? null,
    adapter_defaults: eventData(requestHeader).adapterDefaults ?? null,
    request_header_reason: eventData(requestHeader).reason ?? null,
    manifest_id: extras.manifestId ?? null,
    contribution_ids: extras.contributionIds ?? [],
    stream,
    reasoning_text: reasoningTextFromMessage(message),
    assistant_text: finalAssistantText(list),
    usage: stream.usage ?? message?.usage ?? null,
    finish,
    turn_end_reason: eventData(turnEnd).reason ?? null,
    failed,
    failure: failed && finish?.failure ? finish.failure : null,
  };
}
