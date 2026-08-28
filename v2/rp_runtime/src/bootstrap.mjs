import { Context } from '@deepseek-ai/cordis';

import { mountHolyGrailServices } from './lib/mount-hg-services.mjs';
import { mountRpStack } from './lib/mount-rp-stack.mjs';
import { resolveDomainHostUrl } from './lib/runtime-config.mjs';

export async function createHolyGrailRpContext(options = {}) {
  const domainHostUrl = resolveDomainHostUrl(options);
  if (options.requireDomainHost && !domainHostUrl) {
    throw new Error('HG_DOMAIN_HOST_URL is required (set env or pass domainApi.baseUrl)');
  }
  const ctx = new Context();
  const runtimeConfig = {
    domainApi: domainHostUrl ? { baseUrl: domainHostUrl } : options.domainApi,
    inference: options.inference,
  };
  await mountRpStack(ctx, runtimeConfig, options);
  await mountHolyGrailServices(ctx, runtimeConfig);
  return {
    ctx,
    orchestrator: ctx.hgRoundOrchestrator,
    contextBridge: ctx.hgContextBridge,
    phaseExecutors: ctx.hgPhaseExecutors,
    traceEmitter: ctx.hgTraceEmitter,
  };
}

export { default as HgContextBridge } from './plugins/hg-context-bridge/service.mjs';
export { default as HgPhaseExecutors } from './plugins/hg-phase-executors/service.mjs';
export { default as HgRoundOrchestrator } from './plugins/hg-round-orchestrator/service.mjs';
export { default as HgTraceEmitter } from './plugins/hg-trace-emitter/service.mjs';
