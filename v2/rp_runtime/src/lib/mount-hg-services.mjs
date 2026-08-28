import HgContextBridge from '../plugins/hg-context-bridge/service.mjs';
import HgPhaseExecutors from '../plugins/hg-phase-executors/service.mjs';
import HgRoundOrchestrator from '../plugins/hg-round-orchestrator/service.mjs';
import HgTraceEmitter from '../plugins/hg-trace-emitter/service.mjs';

/**
 * Mount long-lived Holy Grail Cordis services via plugin fibers.
 * Sole production construction path for HG runtime services (#56 C4).
 */
export async function mountHolyGrailServices(ctx, config = {}) {
  await ctx.plugin(HgContextBridge);
  await ctx.plugin(HgTraceEmitter);
  await ctx.plugin(HgPhaseExecutors, config);
  await ctx.plugin(HgRoundOrchestrator, config);
}
