export async function createScene(config, body = {}) {
  const res = await fetch(`${config.baseUrl}/v1/scenes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`createScene failed: ${res.status}`);
  }
  return res.json();
}

async function postJson(baseUrl, path, body) {
  const res = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Domain API ${path} failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function prepareContext(config, body) {
  return postJson(config.baseUrl, '/v1/context/prepare', body);
}

export async function validateMove(config, body) {
  return postJson(config.baseUrl, '/v1/moves/validate', body);
}

export async function commitMove(config, body) {
  return postJson(config.baseUrl, '/v1/moves/commit', body);
}

export async function getSceneState(config, hgSceneId) {
  const res = await fetch(`${config.baseUrl}/v1/scenes/${encodeURIComponent(hgSceneId)}/state`);
  if (!res.ok) {
    throw new Error(`getSceneState failed: ${res.status}`);
  }
  return res.json();
}
