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

const DOMAIN_HOST_LIFECYCLE = Symbol('domainHostLifecycle');
const STDERR_TAIL_MAX_BYTES = 8_192;

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

function attachPipeDrainers(proc, lifecycle) {
  proc.stdout?.on('data', () => {});
  proc.stderr?.on('data', (chunk) => {
    const text = typeof chunk === 'string' ? chunk : chunk.toString('utf8');
    lifecycle.stderrTail = `${lifecycle.stderrTail}${text}`.slice(-STDERR_TAIL_MAX_BYTES);
  });
}

function attachDomainHostLifecycle(proc, meta) {
  const lifecycle = {
    pid: proc.pid,
    host: meta.host,
    port: meta.port,
    baseUrl: meta.baseUrl,
    stderrTail: '',
    stopped: false,
    stopPromise: null,
  };
  proc[DOMAIN_HOST_LIFECYCLE] = lifecycle;
  attachPipeDrainers(proc, lifecycle);
  return lifecycle;
}

export function getDomainHostLifecycle(proc) {
  return proc?.[DOMAIN_HOST_LIFECYCLE] ?? null;
}

export function getDomainHostDiagnostics(proc) {
  if (!proc) {
    return {
      pid: null,
      alive: false,
      stopped: true,
    };
  }
  const lifecycle = getDomainHostLifecycle(proc);
  const alive = !lifecycle?.stopped && proc.exitCode === null && !proc.killed;
  return {
    pid: lifecycle?.pid ?? proc.pid ?? null,
    port: lifecycle?.port ?? null,
    host: lifecycle?.host ?? null,
    baseUrl: lifecycle?.baseUrl ?? null,
    alive,
    stopped: lifecycle?.stopped ?? !alive,
    exitCode: proc.exitCode,
    signal: proc.signalCode,
    stderrTail: lifecycle?.stderrTail ? lifecycle.stderrTail.slice(-2_048) : undefined,
  };
}

export async function isDomainHostPortAvailable(host, port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    const done = (available) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(available);
    };
    socket.once('connect', () => done(false));
    socket.once('error', (err) => {
      done(err?.code === 'ECONNREFUSED' || err?.code === 'ENOTFOUND');
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
  attachDomainHostLifecycle(proc, { host, port, baseUrl });
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

function formatLifecycleDiagnostics(proc) {
  return JSON.stringify(getDomainHostDiagnostics(proc));
}

export async function stopDomainHostProcess(proc, options = {}) {
  if (!proc) {
    return { alreadyStopped: true, diagnostics: getDomainHostDiagnostics(proc) };
  }

  const lifecycle = getDomainHostLifecycle(proc);
  if (lifecycle?.stopped) {
    return {
      alreadyStopped: true,
      exitCode: proc.exitCode,
      signal: proc.signalCode,
      diagnostics: getDomainHostDiagnostics(proc),
    };
  }
  if (lifecycle?.stopPromise) {
    return lifecycle.stopPromise;
  }

  if (proc.exitCode !== null || proc.killed) {
    if (lifecycle) lifecycle.stopped = true;
    return {
      alreadyStopped: true,
      exitCode: proc.exitCode,
      signal: proc.signalCode,
      diagnostics: getDomainHostDiagnostics(proc),
    };
  }

  const runStop = async () => {
    const signal = options.signal ?? 'SIGTERM';
    proc.kill(signal);
    const exitTimer = setTimeout(() => {
      if (proc.exitCode === null && !proc.killed) {
        proc.kill('SIGKILL');
      }
    }, Number(options.forceKillAfterMs ?? 5_000));
    try {
      await once(proc, 'exit');
    } finally {
      clearTimeout(exitTimer);
    }

    if (lifecycle) {
      lifecycle.stopped = true;
    }

    const diagnostics = getDomainHostDiagnostics(proc);
    const verifyPortRelease = options.verifyPortRelease !== false;
    if (verifyPortRelease && lifecycle?.port && lifecycle?.host) {
      diagnostics.portReleased = await isDomainHostPortAvailable(lifecycle.host, lifecycle.port);
    }

    return {
      exitCode: proc.exitCode,
      signal: proc.signalCode,
      diagnostics,
    };
  };

  if (lifecycle) {
    lifecycle.stopPromise = runStop();
    return lifecycle.stopPromise;
  }
  return runStop();
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
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`${message} [Domain Host lifecycle: ${formatLifecycleDiagnostics(proc)}]`);
  }
}
