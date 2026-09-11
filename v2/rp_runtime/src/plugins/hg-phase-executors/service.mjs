import { Service } from '@deepseek-ai/cordis';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import { runCharacterInferenceSlice } from './character-inference-slice.mjs';
import { runCharacterPhase } from './character-phase.mjs';
import { runDirectorPhase } from './director-phase.mjs';
import { createInferenceSubstrate } from './inference-substrate.mjs';
import { runNarratorPhase } from './narrator-phase.mjs';
import { runOpeningPhase } from './opening-phase.mjs';
import { runOpeningSegmentationPhase } from './opening-segmentation-phase.mjs';
import { runPlayerDecompositionPhase } from './player-decomposition-phase.mjs';
import { runPlayerVisibilityTriagePhase } from './player-visibility-triage-phase.mjs';

/**
 * Coherent RP phase execution capability: Director, Character, and Narrator
 * inference against the shared ephemeral inference substrate.
 */
export default class HgPhaseExecutors extends Service {
  static name = 'hgPhaseExecutors';

  static inject = ['hgContextBridge'];

  constructor(ctx, config = {}) {
    super(ctx, HgPhaseExecutors.name);
    this.config = config;
    this.inferenceConfig = config.inference ?? {};
    const substrate = createInferenceSubstrate(config.inference);
    this._runEphemeralInference = substrate.runEphemeralInference;
    this.executionEvidenceRecorder = substrate.recorder;
    this._setRoundEffectiveConfigurationEpochId = substrate.setRoundEffectiveConfigurationEpochId;
  }

  setRoundEffectiveConfigurationEpochId(epochId) {
    this._setRoundEffectiveConfigurationEpochId?.(epochId ?? null);
  }

  runEphemeralInference(params) {
    return this._runEphemeralInference(this.ctx, params);
  }

  _phaseDeps() {
    return {
      runEphemeralInference: this.runEphemeralInference.bind(this),
      recorder: this.executionEvidenceRecorder,
      trace: this.ctx.hgTraceEmitter,
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
      inferenceConfig: this.inferenceConfig,
      ...params,
    });
  }

  runOpening(params) {
    return runOpeningPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runOpeningSegmentation(params) {
    return runOpeningSegmentationPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runPlayerDecomposition(params) {
    return runPlayerDecompositionPhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runPlayerVisibilityTriage(params) {
    return runPlayerVisibilityTriagePhase({
      ...this._phaseDeps(),
      ...params,
    });
  }

  runCharacterInference(options) {
    const api = createDomainApiClient(
      options.domainApi?.baseUrl ?? this.config.domainApi?.baseUrl,
    );
    return runCharacterInferenceSlice({
      ctx: this.ctx,
      trace: this.ctx.hgTraceEmitter,
      runEphemeralInference: this.runEphemeralInference.bind(this),
      recorder: this.executionEvidenceRecorder,
      api,
      options,
    });
  }
}
