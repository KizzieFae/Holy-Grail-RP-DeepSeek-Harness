import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';

import { startDomainHost, stopDomainHostProcess } from '../../src/runtime-supervisor/domain-host-process.mjs';

export { repoRoot, defaultPythonExecutable } from '../../src/lib/runtime-config.mjs';

/**
 * Start a Domain Host for integration tests using production supervisor primitives.
 */
export async function startDomainApi(port, options = {}) {
  const host = await startDomainHost({
    host: '127.0.0.1',
    port,
    sessionsDir: options.sessionsDir,
    timeoutMs: options.timeoutMs,
    env: options.hostEnv,
  });
  const result = {
    proc: host.proc,
    baseUrl: host.baseUrl,
    async stop() {
      await stopDomainHostProcess(host.proc);
    },
  };
  if (options.withSession) {
    result.scene = await createTestSession(host.baseUrl, options.cast ?? ['Alice', 'Bob']);
  }
  return result;
}

export async function createTestSession(baseUrl, cast = ['Alice', 'Bob']) {
  const res = await fetch(`${baseUrl}/v1/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast }),
  });
  if (!res.ok) throw new Error(`sessions/create failed: ${res.status}`);
  return res.json();
}

export async function fetchSessionState(baseUrl, hgSessionId) {
  const res = await fetch(`${baseUrl}/v1/sessions/${encodeURIComponent(hgSessionId)}/state`);
  if (!res.ok) throw new Error(`session state failed: ${res.status}`);
  return res.json();
}

export function makeTempSessionsDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'hg-sessions-'));
}

export async function withDomainHost(t, options, fn) {
  const host = await startDomainHost({
    host: '127.0.0.1',
    port: options.port,
    sessionsDir: options.sessionsDir,
  });
  t.after(async () => {
    await stopDomainHostProcess(host.proc);
    await once(host.proc, 'exit').catch(() => {});
  });
  return fn(host);
}
