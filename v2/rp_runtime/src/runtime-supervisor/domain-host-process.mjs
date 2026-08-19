import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import { once } from 'node:events';
import path from 'node:path';

import {
  DOMAIN_HOST_SERVICE_ID,
  defaultPythonExecutable,
  domainHostSpawnEnv,
  repoRoot,
} from '../lib/runtime-config.mjs';

export async function reserveLocalPort(host = '127.0.0.1') {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, host, () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      server.close((err) => {
        if (err) reject(err);
        else resolve(port);
      });
    });
  });
}

export function spawnDomainHostProcess(options = {}) {
  const host = options.host ?? '127.0.0.1';
  const port = Number(options.port);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`invalid Domain Host port: ${options.port}`);
  }
  const pythonExecutable = options.pythonExecutable ?? defaultPythonExecutable();
  if (path.isAbsolute(pythonExecutable) && !fs.existsSync(pythonExecutable)) {
    const provisionHint = pythonExecutable.includes(`${path.sep}.venv${path.sep}`)
      || pythonExecutable.includes('/.venv/')
      ? ' Provision the canonical environment at the repository root: python -m venv .venv (see v2/README.md).'
      : '';
    throw new Error(`Python executable not found: ${pythonExecutable}.${provisionHint}`);
  }
  const baseUrl = `http://${host}:${port}`;
  const proc = spawn(
    pythonExecutable,
    ['-m', 'domain_api', '--host', host, '--port', String(port)],
    {
      cwd: path.join(repoRoot, 'v2'),
      env: domainHostSpawnEnv(options),
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  return { proc, baseUrl, host, port };
}

export async function waitForHealthyDomainHost(baseUrl, options = {}) {
  const timeoutMs = Number(options.timeoutMs ?? 12_000);
  const intervalMs = Number(options.intervalMs ?? 150);
  const serviceId = options.serviceId ?? DOMAIN_HOST_SERVICE_ID;
  const started = Date.now();
  let lastError = 'Domain Host did not become healthy';

  while (Date.now() - started < timeoutMs) {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) {
        const payload = await res.json();
        if (payload?.service === serviceId && payload?.status === 'ok') {
          return payload;
        }
        lastError = `unexpected health payload: ${JSON.stringify(payload)}`;
      } else {
        lastError = `health returned HTTP ${res.status}`;
      }
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`${lastError} (timeout ${timeoutMs}ms waiting for ${baseUrl}/health)`);
}

export async function stopDomainHostProcess(proc, options = {}) {
  if (!proc || proc.killed || proc.exitCode !== null) return;
  const signal = options.signal ?? 'SIGTERM';
  proc.kill(signal);
  const exitTimer = setTimeout(() => {
    if (proc.exitCode === null) proc.kill('SIGKILL');
  }, Number(options.forceKillAfterMs ?? 5_000));
  try {
    await once(proc, 'exit');
  } finally {
    clearTimeout(exitTimer);
  }
}

export async function startDomainHost(options = {}) {
  const host = options.host ?? '127.0.0.1';
  const port = options.port ?? await reserveLocalPort(host);
  const { proc, baseUrl } = spawnDomainHostProcess({ ...options, host, port });
  proc.on('exit', (code, signal) => {
    if (options.onExit) options.onExit(code, signal);
  });

  try {
    const health = await waitForHealthyDomainHost(baseUrl, options);
    return { proc, baseUrl, host, port, health };
  } catch (err) {
    await stopDomainHostProcess(proc);
    throw err;
  }
}
