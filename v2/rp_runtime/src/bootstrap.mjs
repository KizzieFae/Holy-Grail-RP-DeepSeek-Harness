import { Context } from '@deepseek-ai/cordis';

import { mountRpStack } from './lib/mount-rp-stack.mjs';
import HgContextBridge from './plugins/hg-context-bridge/service.mjs';
import HgPhaseExecutors from './plugins/hg-phase-executors/service.mjs';
import HgRoundOrchestrator from './plugins/hg-round-orchestrator/service.mjs';
import HgTraceEmitter from './plugins/hg-trace-emitter/service.mjs';

export async function createHolyGrailRpContext(options = {}) {
  const ctx = new Context();
  const runtimeConfig = {
    domainApi: options.domainApi,
    inference: options.inference,
  };
  const contextBridge = new HgContextBridge(ctx);
  const traceEmitter = new HgTraceEmitter(ctx);
  const phaseExecutors = new HgPhaseExecutors(ctx, runtimeConfig);
  const orchestrator = new HgRoundOrchestrator(ctx, runtimeConfig);
  await mountRpStack(ctx, runtimeConfig, options);
  return { ctx, orchestrator, contextBridge, phaseExecutors, traceEmitter };
}

export {
  HgContextBridge,
  HgPhaseExecutors,
  HgRoundOrchestrator,
  HgTraceEmitter,
};
