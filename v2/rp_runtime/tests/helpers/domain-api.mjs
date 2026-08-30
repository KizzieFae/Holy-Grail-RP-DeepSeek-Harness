import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';

import {
  getDomainHostDiagnostics,
  reserveLocalPort,
  startDomainHost,
  stopDomainHostProcess,
} from '../../src/runtime-supervisor/domain-host-process.mjs';

export { repoRoot, defaultPythonExecutable } from '../../src/lib/runtime-config.mjs';
export { reserveLocalPort } from '../../src/runtime-supervisor/domain-host-process.mjs';

/**
 * Start a Domain Host for integration tests using production supervisor primitives.
 * When `options.t` is provided, teardown is registered immediately via `t.after`.
 */
export async function startDomainApi(port, options = {}) {
  const resolvedPort = port ?? await reserveLocalPort();
  const host = await startDomainHost({
    host: '127.0.0.1',
    port: resolvedPort,
    sessionsDir: options.sessionsDir,
    timeoutMs: options.timeoutMs,
    env: options.hostEnv,
  });
  const handle = {
    proc: host.proc,
    baseUrl: host.baseUrl,
    port: host.port,
    pid: host.proc.pid,
    getDiagnostics() {
      return getDomainHostDiagnostics(host.proc);
    },
    async stop() {
      return stopDomainHostProcess(host.proc);
    },
  };
  if (options.t) {
    options.t.after(async () => {
      await handle.stop();
    });
  }
  if (options.withSession) {
    handle.scene = await createTestSession(host.baseUrl, options.cast ?? ['Alice', 'Bob']);
  }
  return handle;
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
  const port = options.port ?? await reserveLocalPort();
  const host = await startDomainHost({
    host: '127.0.0.1',
    port,
    sessionsDir: options.sessionsDir,
    env: options.hostEnv,
  });
  const handle = {
    proc: host.proc,
    baseUrl: host.baseUrl,
    port: host.port,
    pid: host.proc.pid,
    getDiagnostics() {
      return getDomainHostDiagnostics(host.proc);
    },
    async stop() {
      return stopDomainHostProcess(host.proc);
    },
  };
  t.after(async () => {
    await handle.stop();
    await once(host.proc, 'exit').catch(() => {});
  });
  return fn(handle);
}
