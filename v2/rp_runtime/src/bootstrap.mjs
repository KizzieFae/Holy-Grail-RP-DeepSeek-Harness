import { Context } from '@deepseek-ai/cordis';

import HolyGrailRpRuntime from './plugins/hg-rp-runtime/service.mjs';

export async function createHolyGrailRpContext(options = {}) {
  const ctx = new Context();
  const runtime = new HolyGrailRpRuntime(ctx, {
    domainApi: options.domainApi,
    inference: options.inference,
  });
  await runtime.mountStack(options);
  return { ctx, runtime };
}

export { HolyGrailRpRuntime };
