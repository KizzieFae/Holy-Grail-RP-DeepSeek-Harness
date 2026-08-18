#!/usr/bin/env node
import { HolyGrailRuntimeSupervisor } from '../src/runtime-supervisor/index.mjs';

const supervisor = new HolyGrailRuntimeSupervisor();

async function shutdown(signal) {
  if (supervisor.state === 'stopped') return;
  console.log(`[hg-runtime] received ${signal}, shutting down...`);
  await supervisor.stop();
  process.exit(0);
}

process.on('SIGINT', () => { shutdown('SIGINT'); });
process.on('SIGTERM', () => { shutdown('SIGTERM'); });

try {
  const ready = await supervisor.start();
  console.log('[hg-runtime] ready:', JSON.stringify(ready, null, 2));
  console.log('[hg-runtime] press Ctrl+C to stop');
} catch (err) {
  console.error('[hg-runtime] startup failed:', err instanceof Error ? err.message : err);
  process.exit(1);
}
