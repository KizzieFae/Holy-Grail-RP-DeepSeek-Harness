import { trackBoundaryCall } from './inference-utils.mjs';

async function postJson(metrics, baseUrl, path, body, label) {
  trackBoundaryCall(metrics, label, body);
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

export function createDomainApiClient(baseUrl) {
  const metrics = { calls: [] };
  return {
    metrics,
    async health() {
      trackBoundaryCall(metrics, 'health', {});
      const res = await fetch(`${baseUrl}/health`);
      if (!res.ok) throw new Error(`health failed: ${res.status}`);
      return res.json();
    },
    createSession(body = {}) {
      return postJson(metrics, baseUrl, '/v1/sessions/create', body, 'createSession');
    },
    openSession(hgSessionId) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/open',
        { hg_session_id: hgSessionId },
        'openSession',
      );
    },
    /** @deprecated Transitional/test-only — production uses createSession/openSession */
    async createScene(body = {}) {
      trackBoundaryCall(metrics, 'createScene', body);
      const res = await fetch(`${baseUrl}/v1/scenes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`createScene failed: ${res.status}`);
      return res.json();
    },
    startRound(body) {
      return postJson(metrics, baseUrl, '/v1/rounds/start', body, 'startRound');
    },
    getEligibleActors(body) {
      return postJson(metrics, baseUrl, '/v1/rounds/eligible-actors', body, 'getEligibleActors');
    },
    getParticipationDecision(body) {
      return postJson(metrics, baseUrl, '/v1/rounds/participation-decision', body, 'getParticipationDecision');
    },
    prepareDirectorContext(body) {
      return postJson(metrics, baseUrl, '/v1/director/context/prepare', body, 'prepareDirectorContext');
    },
    validateDirectorDecision(body) {
      return postJson(metrics, baseUrl, '/v1/director/decisions/validate', body, 'validateDirectorDecision');
    },
    prepareCharacterContext(body) {
      return postJson(metrics, baseUrl, '/v1/context/prepare', body, 'prepareCharacterContext');
    },
    validateMove(body) {
      return postJson(metrics, baseUrl, '/v1/moves/validate', body, 'validateMove');
    },
    commitMove(body) {
      return postJson(metrics, baseUrl, '/v1/moves/commit', body, 'commitMove');
    },
    prepareNarratorContext(body) {
      return postJson(metrics, baseUrl, '/v1/narrator/context/prepare', body, 'prepareNarratorContext');
    },
    async getSceneState(hgSceneId) {
      trackBoundaryCall(metrics, 'getSceneState', { hg_scene_id: hgSceneId });
      const res = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(hgSceneId)}/state`);
      if (!res.ok) throw new Error(`getSceneState failed: ${res.status}`);
      return res.json();
    },
  };
}
