import { trackBoundaryCall } from './inference-utils.mjs';
import { projectHistoryToTranscript } from './project-history.mjs';

export { projectHistoryToTranscript };

export class DomainApiTransportError extends Error {
  constructor({ label, path, cause }) {
    const code = cause?.code ?? null;
    const causeMessage = cause?.message ?? 'fetch failed';
    const suffix = code ? ` [${code}]` : '';
    super(`Domain API transport failure for ${label} (${path})${suffix}: ${causeMessage}`);
    this.name = 'DomainApiTransportError';
    this.failureClass = 'transport_error';
    this.operation = label;
    this.path = path;
    if (code) {
      this.transportCode = code;
    }
    this.cause = cause;
  }
}

function parseErrorKind(text) {
  try {
    const payload = JSON.parse(text);
    return typeof payload?.error_kind === 'string' ? payload.error_kind : null;
  } catch {
    return null;
  }
}

function classifyHttpFailure(errorKind, status) {
  if (errorKind === 'host_internal_error') {
    return 'host_internal_error';
  }
  if (errorKind === 'persistence_failure' || status === 503) {
    return 'service_unavailable';
  }
  return 'api_http_error';
}

function throwHttpError(path, status, text, label) {
  const errorKind = parseErrorKind(text);
  const err = new Error(`Domain API ${path} failed (${status}): ${text}`);
  err.name = 'DomainApiHttpError';
  err.failureClass = classifyHttpFailure(errorKind, status);
  err.httpStatus = status;
  err.operation = label;
  err.path = path;
  err.errorKind = errorKind;
  throw err;
}

async function fetchJson(baseUrl, path, init, label) {
  let res;
  try {
    res = await fetch(`${baseUrl}${path}`, init);
  } catch (cause) {
    throw new DomainApiTransportError({ label, path, cause });
  }
  if (!res.ok) {
    const text = await res.text();
    throwHttpError(path, res.status, text, label);
  }
  return res.json();
}

async function postJson(metrics, baseUrl, path, body, label) {
  trackBoundaryCall(metrics, label, body);
  return fetchJson(
    baseUrl,
    path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    label,
  );
}

async function getJson(metrics, baseUrl, path, label) {
  trackBoundaryCall(metrics, label, {});
  return fetchJson(baseUrl, path, undefined, label);
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
    updateRuntimeProvenance(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/runtime-provenance',
        body,
        'updateRuntimeProvenance',
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
    prepareCharacterOrientationContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/character/orientation/prepare',
        body,
        'prepareCharacterOrientationContext',
      );
    },
    finalizeCharacterOrientation(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/character/orientation/finalize',
        body,
        'finalizeCharacterOrientation',
      );
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
    prepareLibrarianProposalContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/librarian/proposals/prepare',
        body,
        'prepareLibrarianProposalContext',
      );
    },
    finalizeLibrarianProposals(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/librarian/proposals/finalize',
        body,
        'finalizeLibrarianProposals',
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
    bindStorytellerAdvisoryPackage(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/storyteller/round/bind',
        body,
        'bindStorytellerAdvisoryPackage',
      );
    },
    getStorytellerRoundState({ hgSceneId, hgRoundId }) {
      const params = new URLSearchParams({
        hg_scene_id: String(hgSceneId),
        hg_round_id: String(hgRoundId),
      });
      return fetch(`${baseUrl}/v1/storyteller/round/state?${params.toString()}`).then(async (res) => {
        if (!res.ok) {
          throw new Error(`getStorytellerRoundState failed: ${res.status}`);
        }
        return res.json();
      });
    },
    validateMove(body) {
      return postJson(metrics, baseUrl, '/v1/moves/validate', body, 'validateMove');
    },
    preparePlotCognitionProjection(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/projection/prepare',
        body,
        'preparePlotCognitionProjection',
      );
    },
    finalizePlotCognitionProjection(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/projection/finalize',
        body,
        'finalizePlotCognitionProjection',
      );
    },
    registerPlotCognitionProjectionSemanticResult(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/projection/register-semantic-result',
        body,
        'registerPlotCognitionProjectionSemanticResult',
      );
    },
    preparePlotCognitionProjectionRegeneration(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/projection/regeneration/prepare',
        body,
        'preparePlotCognitionProjectionRegeneration',
      );
    },
    finalizePlotCognitionProjectionRegeneration(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/projection/regeneration/finalize',
        body,
        'finalizePlotCognitionProjectionRegeneration',
      );
    },
    assessPlotCognitionFreshness(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/freshness/assess',
        body,
        'assessPlotCognitionFreshness',
      );
    },
    planPostCommitPlotCognitionWork(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/pending-work/plan',
        body,
        'planPostCommitPlotCognitionWork',
      );
    },
    finalizePlotCognitionReconciliation(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/reconciliation/finalize',
        body,
        'finalizePlotCognitionReconciliation',
      );
    },
    finalizePlotCognitionAuthorityAdvance(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/authority-advance/finalize',
        body,
        'finalizePlotCognitionAuthorityAdvance',
      );
    },
    clearPlotCognitionPendingWork(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/pending-work/clear',
        body,
        'clearPlotCognitionPendingWork',
      );
    },
    preparePlotCognitionInit(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/init/prepare', body, 'preparePlotCognitionInit');
    },
    finalizePlotCognitionInit(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/init/finalize', body, 'finalizePlotCognitionInit');
    },
    preparePlotCognitionUpdate(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/update/prepare', body, 'preparePlotCognitionUpdate');
    },
    finalizePlotCognitionUpdate(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/update/finalize', body, 'finalizePlotCognitionUpdate');
    },
    preparePlotCognitionReplan(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/replan/prepare', body, 'preparePlotCognitionReplan');
    },
    finalizePlotCognitionReplan(body) {
      return postJson(metrics, baseUrl, '/v1/plot-cognition/replan/finalize', body, 'finalizePlotCognitionReplan');
    },
    prepareCharacterAdvisoryGeneration(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/advisory-generation/prepare',
        body,
        'prepareCharacterAdvisoryGeneration',
      );
    },
    finalizeCharacterAdvisoryGeneration(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/plot-cognition/advisory-generation/finalize',
        body,
        'finalizeCharacterAdvisoryGeneration',
      );
    },
    commitMove(body) {
      return postJson(metrics, baseUrl, '/v1/moves/commit', body, 'commitMove');
    },
    prepareNarratorContext(body) {
      return postJson(metrics, baseUrl, '/v1/narrator/context/prepare', body, 'prepareNarratorContext');
    },
    prepareNarratorEnvironmentCognitionContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/narrator/environment/cognition/prepare',
        body,
        'prepareNarratorEnvironmentCognitionContext',
      );
    },
    finalizeNarratorEnvironmentCognition(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/narrator/environment/cognition/finalize',
        body,
        'finalizeNarratorEnvironmentCognition',
      );
    },
    buildNarratorEnvironmentKnowledgeRequests(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/narrator/environment/knowledge-requests/build',
        body,
        'buildNarratorEnvironmentKnowledgeRequests',
      );
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
    validatePerceptualVisibility(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/perceptual-visibility/validate',
        body,
        'validatePerceptualVisibility',
      );
    },
    attachOpeningPerceptualVisibility(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/opening/perceptual-visibility',
        body,
        'attachOpeningPerceptualVisibility',
      );
    },
    prepareOpeningContext(body) {
      return postJson(metrics, baseUrl, '/v1/opening/context/prepare', body, 'prepareOpeningContext');
    },
    prepareOpeningSegmentationContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/opening/segmentation/context/prepare',
        body,
        'prepareOpeningSegmentationContext',
      );
    },
    preparePlayerDecompositionContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/player-decomposition/context/prepare',
        body,
        'preparePlayerDecompositionContext',
      );
    },
    normalizePlayerDecomposition(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/player-decomposition/normalize',
        body,
        'normalizePlayerDecomposition',
      );
    },
    preparePlayerVisibilityTriageContext(body) {
      return postJson(
        metrics,
        baseUrl,
        '/v1/sessions/player-visibility-triage/context/prepare',
        body,
        'preparePlayerVisibilityTriageContext',
      );
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
