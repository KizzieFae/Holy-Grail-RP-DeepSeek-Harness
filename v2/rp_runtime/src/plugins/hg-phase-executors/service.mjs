import { Service } from '@deepseek-ai/cordis';

import HgContextBridge from '../hg-context-bridge/service.mjs';
import { baseCorrelation } from '../hg-rp-runtime/events.mjs';
import { runCharacterPhase } from './character-phase.mjs';
import { runDirectorPhase } from './director-phase.mjs';
import { createInferenceSubstrate } from './inference-substrate.mjs';
import { runNarratorPhase } from './narrator-phase.mjs';

/**
 * Coherent RP phase execution capability: Director, Character, and Narrator
 * inference against the shared ephemeral inference substrate.
 */
export default class HgPhaseExecutors extends Service {
  static name = 'hgPhaseExecutors';

  constructor(ctx, config = {}) {
    super(ctx, HgPhaseExecutors.name);
    this.config = config;
    const substrate = createInferenceSubstrate(ctx, config.inference);
    this.runEphemeralInference = substrate.runEphemeralInference;
  }

  _correlation({ hgSceneId, hgRoundId, sceneSessionId }) {
    return baseCorrelation({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      dsh_scene_session_id: String(sceneSessionId),
    });
  }

  _phaseDeps() {
    return {
      runEphemeralInference: this.runEphemeralInference.bind(this),
      correlation: this._correlation.bind(this),
    };
  }

  runDirector(params) {
    return runDirectorPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runCharacter(params) {
    return runCharacterPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runNarrator(params) {
    return runNarratorPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  static ensure(ctx, config = {}) {
    if (!ctx.hgContextBridge) {
      new HgContextBridge(ctx);
    }
    if (!ctx.hgPhaseExecutors) {
      new HgPhaseExecutors(ctx, config);
    }
    return ctx.hgPhaseExecutors;
  }
}
