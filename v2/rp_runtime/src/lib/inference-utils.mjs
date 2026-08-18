export function waitForIdle(ctx, agent) {
  return new Promise((resolve) => {
    const dispose = ctx.on('agent/status', ({ agent: subject, status }) => {
      if (subject === agent && status === 'idle') {
        dispose();
        resolve();
      }
    });
  });
}

export function finalAssistantText(events) {
  const message = [...events].reverse().find((event) => event.type === 'assistant/message');
  if (!message || message.type !== 'assistant/message') return '';
  return message.data.message.content
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('');
}

export function parseJsonObject(text) {
  const trimmed = text.trim();
  const start = trimmed.indexOf('{');
  const end = trimmed.lastIndexOf('}');
  if (start < 0 || end < start) {
    throw new Error('model output did not contain a JSON object');
  }
  return JSON.parse(trimmed.slice(start, end + 1));
}

export function trackBoundaryCall(metrics, label, body) {
  const payload = JSON.stringify(body ?? {});
  metrics.calls.push({
    label,
    bytes: payload.length,
  });
  return payload.length;
}
