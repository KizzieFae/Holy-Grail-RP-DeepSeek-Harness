import { Service } from '@deepseek-ai/cordis';

/** Holy Grail execution-event types (log-only; never imply canon). */
export const HG_EVENT_TYPES = [
  'hg/round-started',
  'hg/storyteller-started',
  'hg/storyteller-completed',
  'hg/storyteller-skipped',
  'hg/storyteller-invalidated',
  'hg/character-knowledge-cognition',
  'hg/character-projection-lifecycle',
  'hg/eligibility-snapshot',
  'hg/eligibility-exhausted',
  'hg/participation-decision',
  'hg/director-proposed',
  'hg/director-rejected',
  'hg/director-accepted',
  'hg/director-semantic-qa',
  'hg/narrator-semantic-qa',
  'hg/move-proposed',
  'hg/move-rejected',
  'hg/semantic-evaluation',
  'hg/move-committed',
  'hg/inference-failed',
  'hg/narrator-started',
  'hg/narrator-environment-cognition-failed',
  'hg/narrator-completed',
  'hg/narrator-failed',
  'hg/librarian-proposal-started',
  'hg/librarian-proposal-completed',
  'hg/librarian-proposal-failed',
  'hg/librarian-proposal-join',
  'hg/plot-cognition-resume',
  'hg/plot-cognition-started',
  'hg/plot-cognition-completed',
  'hg/plot-cognition-failed',
  'hg/plot-cognition-join',
  'hg/opening-started',
  'hg/opening-completed',
  'hg/opening-failed',
  'hg/opening-segmentation-started',
  'hg/opening-segmentation-completed',
  'hg/opening-segmentation-failed',
  'hg/player-decomposition-started',
  'hg/player-decomposition-completed',
  'hg/player-decomposition-failed',
  'hg/round-completed',
];

/**
 * Sole production API for Holy Grail hg/* execution-event emission.
 * Evidence-only: correlates runtime decisions; does not create domain truth.
 */
export default class HgTraceEmitter extends Service {
  static name = 'hgTraceEmitter';

  constructor(ctx) {
    super(ctx, HgTraceEmitter.name);
  }

  /**
   * Normalize round/scene correlation fields for one scene-session log entry.
   *
   * @param {{ hgSceneId: string, hgRoundId: string, sceneSessionId: unknown }} scope
   */
  correlation(scope) {
    return {
      hg_session_id: scope.hgSessionId ?? scope.hgSceneId,
      hg_scene_id: scope.hgSceneId,
      hg_round_id: scope.hgRoundId,
      dsh_scene_session_id: String(scope.sceneSessionId),
    };
  }

  /**
   * Emit one typed Holy Grail execution event into the scene session log.
   *
   * @param {object} session - DSH scene session (sceneAgent.session)
   * @param {string} type - hg/* event type
   * @param {{ hgSceneId: string, hgRoundId: string, sceneSessionId: unknown }} scope
   * @param {object} [payload] - event-specific fields (merged after correlation)
   */
  emit(session, type, scope, payload = {}) {
    if (!HG_EVENT_TYPES.includes(type)) {
      throw new Error(`unknown Holy Grail event type: ${type}`);
    }
    return session.append(type, {
      ...this.correlation(scope),
      ...payload,
    });
  }
}
