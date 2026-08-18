import { Context } from '@deepseek-ai/cordis';

import HgContextBridge from './plugins/hg-context-bridge/service.mjs';
import HgPhaseExecutors from './plugins/hg-phase-executors/service.mjs';
import HgTraceEmitter from './plugins/hg-trace-emitter/service.mjs';
import HolyGrailRpRuntime from './plugins/hg-rp-runtime/service.mjs';

export async function createHolyGrailRpContext(options = {}) {
  const ctx = new Context();
  const runtimeConfig = {
    domainApi: options.domainApi,
    inference: options.inference,
  };
  const contextBridge = new HgContextBridge(ctx);
  const traceEmitter = new HgTraceEmitter(ctx);
  const phaseExecutors = new HgPhaseExecutors(ctx, runtimeConfig);
  const runtime = new HolyGrailRpRuntime(ctx, runtimeConfig);
  await runtime.mountStack(options);
  return { ctx, runtime, contextBridge, phaseExecutors, traceEmitter };
}

export {
  HgContextBridge,
  HgPhaseExecutors,
  HgTraceEmitter,
  HolyGrailRpRuntime,
};
