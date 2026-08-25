import { trackBoundaryCall } from './inference-utils.mjs';
import { projectHistoryToTranscript } from './project-history.mjs';

export { projectHistoryToTranscript };

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

async function getJson(metrics, baseUrl, path, label) {
  trackBoundaryCall(metrics, label, {});
  const res = await fetch(`${baseUrl}${path}`);
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
    recordUserTurn(body) {
      return postJson(metrics, baseUrl, '/v1/sessions/history/user-turn', body, 'recordUserTurn');
    },
    recordPlayerSkip(body) {
      return postJson(metrics, baseUrl, '/v1/sessions/history/player-skip', body, 'recordPlayerSkip');
    },
    recordPresentation(body) {
      return postJson(metrics, baseUrl, '/v1/sessions/history/presentation', body, 'recordPresentation');
    },
    async getSessionHistory(hgSessionId) {
      trackBoundaryCall(metrics, 'getSessionHistory', { hg_session_id: hgSessionId });
      const res = await fetch(`${baseUrl}/v1/sessions/${encodeURIComponent(hgSessionId)}/history`);
      if (!res.ok) throw new Error(`getSessionHistory failed: ${res.status}`);
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
    prepareDirectorSemanticQaContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/director/semantic-qa/context/prepare',
        body,
        'prepareDirectorSemanticQaContext',
      );
    },
    prepareCharacterContext(body) {
      return postJson(metrics, baseUrl, '/v1/context/prepare', body, 'prepareCharacterContext');
    },
    prepareSemanticEvaluationContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/context/prepare-semantic-evaluation',
        body,
        'prepareSemanticEvaluationContext',
      );
    },
    prepareLibrarianMediationContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/librarian/mediation/prepare',
        body,
        'prepareLibrarianMediationContext',
      );
    },
    finalizeLibrarianMediation(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/librarian/mediation/finalize',
        body,
        'finalizeLibrarianMediation',
      );
    },
    prepareStorytellerOrientationContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/storyteller/orientation/prepare',
        body,
        'prepareStorytellerOrientationContext',
      );
    },
    finalizeStorytellerOrientation(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/storyteller/orientation/finalize',
        body,
        'finalizeStorytellerOrientation',
      );
    },
    prepareStorytellerAssessmentContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/storyteller/assessment/prepare',
        body,
        'prepareStorytellerAssessmentContext',
      );
    },
    finalizeStorytellerAssessment(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/storyteller/assessment/finalize',
        body,
        'finalizeStorytellerAssessment',
      );
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
    prepareNarratorSemanticQaContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/narrator/semantic-qa/context/prepare',
        body,
        'prepareNarratorSemanticQaContext',
      );
    },
    validateNarratorPresentation(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/narrator/presentation/validate',
        body,
        'validateNarratorPresentation',
      );
    },
    prepareOpeningContext(body) {
      return postJson(metrics, baseUrl, '/v1/opening/context/prepare', body, 'prepareOpeningContext');
    },
    persistOpening(body) {
      return postJson(metrics, baseUrl, '/v1/sessions/opening/persist', body, 'persistOpening');
    },
    async getSessionState(hgSessionId) {
      trackBoundaryCall(metrics, 'getSessionState', { hg_session_id: hgSessionId });
      const res = await fetch(`${baseUrl}/v1/sessions/${encodeURIComponent(hgSessionId)}/state`);
      if (!res.ok) throw new Error(`getSessionState failed: ${res.status}`);
      return res.json();
    },
    listCharacters() {
      return getJson(metrics, baseUrl, '/v1/catalog/characters', 'listCharacters');
    },
    listSceneTemplates() {
      return getJson(metrics, baseUrl, '/v1/catalog/scene-templates', 'listSceneTemplates');
    },
    listTemplateOpeners(templateId) {
      return getJson(
        metrics,
        baseUrl,
        `/v1/catalog/scene-templates/${encodeURIComponent(templateId)}/openers`,
        'listTemplateOpeners',
      );
    },
    async getSceneState(hgSceneId) {
      return this.getSessionState(hgSceneId);
    },
  };
}
