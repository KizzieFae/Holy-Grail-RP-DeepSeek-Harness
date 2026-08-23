import { Service } from '@deepseek-ai/cordis';

import { createDomainApiClient } from '../../lib/domain-api-client.mjs';
import HgContextBridge from '../hg-context-bridge/service.mjs';
import HgTraceEmitter from '../hg-trace-emitter/service.mjs';
import { runCharacterInferenceSlice } from './character-inference-slice.mjs';
import { runCharacterPhase } from './character-phase.mjs';
import { runDirectorPhase } from './director-phase.mjs';
import { createInferenceSubstrate } from './inference-substrate.mjs';
import { runNarratorPhase } from './narrator-phase.mjs';
import { runOpeningPhase } from './opening-phase.mjs';

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
    this.executionEvidenceRecorder = substrate.recorder;
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
      ...params,
    });
  }

  runOpening(params) {
    return runOpeningPhase({
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

  static ensure(ctx, config = {}) {
    if (!ctx.hgContextBridge) {
      new HgContextBridge(ctx);
    }
    HgTraceEmitter.ensure(ctx);
    if (!ctx.hgPhaseExecutors) {
      new HgPhaseExecutors(ctx, config);
    }
    return ctx.hgPhaseExecutors;
  }
}
