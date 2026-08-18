import { Context } from '@deepseek-ai/cordis';

import HgContextBridge from './plugins/hg-context-bridge/service.mjs';
import HolyGrailRpRuntime from './plugins/hg-rp-runtime/service.mjs';

export async function createHolyGrailRpContext(options = {}) {
  const ctx = new Context();
  const contextBridge = new HgContextBridge(ctx);
  const runtime = new HolyGrailRpRuntime(ctx, {
    domainApi: options.domainApi,
    inference: options.inference,
  });
  await runtime.mountStack(options);
  return { ctx, runtime, contextBridge };
}

export { HgContextBridge, HolyGrailRpRuntime };
