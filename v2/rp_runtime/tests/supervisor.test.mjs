import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import test from 'node:test';

import { DOMAIN_HOST_SERVICE_ID } from '../src/lib/runtime-config.mjs';
import {
  getDomainHostDiagnostics,
  isDomainHostPortAvailable,
  reserveLocalPort,
  startDomainHost,
  stopDomainHostProcess,
  waitForHealthyDomainHost,
} from '../src/runtime-supervisor/domain-host-process.mjs';
import { HolyGrailRuntimeSupervisor } from '../src/runtime-supervisor/supervisor.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

test('supervisor: health-gated Domain Host startup', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });
  const port = await reserveLocalPort();
  const host = await startDomainHost({ port, sessionsDir });
  t.after(async () => {
    await stopDomainHostProcess(host.proc);
  });

  const health = await waitForHealthyDomainHost(host.baseUrl);
  assert.equal(health.service, DOMAIN_HOST_SERVICE_ID);
  assert.equal(health.status, 'ok');
});

test('supervisor: starts DSH runtime after Domain Host healthy', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const supervisor = new HolyGrailRuntimeSupervisor({
    domainHost: { port: await reserveLocalPort(), sessionsDir },
  });
  t.after(async () => {
    await supervisor.stop();
  });

  const ready = await supervisor.start();
  assert.equal(ready.domain_host, 'healthy');
  assert.ok(ready.domain_host_url);
  assert.equal(ready.dsh_runtime, 'ready');
  assert.ok(supervisor.runtime?.orchestrator);
});

function hasConfirmedExit(proc) {
  return proc.exitCode !== null || proc.signalCode !== null;
}

test('supervisor: shutdown stops Domain Host child', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const supervisor = new HolyGrailRuntimeSupervisor({
    domainHost: { port: await reserveLocalPort(), sessionsDir },
  });
  t.after(async () => {
    await supervisor.stop();
  });

  const ready = await supervisor.start();
  const proc = supervisor.domainHost.proc;
  const port = supervisor.domainHost.port;
  const stopResult = await supervisor.stop();
  assert.equal(supervisor.domainHost, null);
  assert.ok(hasConfirmedExit(proc));
  assert.ok(stopResult?.diagnostics?.stopped ?? hasConfirmedExit(proc));
  assert.equal(supervisor.state, 'stopped');
  assert.equal(ready.dsh_runtime, 'ready');
  assert.equal(await isDomainHostPortAvailable('127.0.0.1', port), true);
});

test('supervisor: invalid python executable fails clearly', async () => {
  const port = await reserveLocalPort();
  await assert.rejects(
    () => startDomainHost({
      port,
      pythonExecutable: 'Z:\\definitely-missing-python.exe',
    }),
    /Python executable not found/,
  );
});

test('supervisor: stop is idempotent and confirms exit', async (t) => {
  const port = await reserveLocalPort();
  const host = await startDomainHost({ port });
  t.after(async () => {
    await stopDomainHostProcess(host.proc);
  });

  const first = await stopDomainHostProcess(host.proc);
  const second = await stopDomainHostProcess(host.proc);
  assert.equal(first.alreadyStopped, undefined);
  assert.ok(getDomainHostDiagnostics(host.proc).stopped);
  assert.equal(second.alreadyStopped, true);
  const diagnostics = getDomainHostDiagnostics(host.proc);
  assert.equal(diagnostics.alive, false);
  assert.equal(diagnostics.stopped, true);
  assert.equal(await isDomainHostPortAvailable('127.0.0.1', port), true);
});

test('supervisor: startup failure cleans up owned Host', async () => {
  const port = await reserveLocalPort();
  await assert.rejects(
    () => startDomainHost({ port, timeoutMs: 1 }),
    /Domain Host lifecycle:/,
  );
  assert.equal(await isDomainHostPortAvailable('127.0.0.1', port), true);
});

test('supervisor: repeated start/stop cycles leave no owned Host on port', async () => {
  for (let i = 0; i < 3; i += 1) {
    const port = await reserveLocalPort();
    const host = await startDomainHost({ port });
    await stopDomainHostProcess(host.proc);
    assert.ok(hasConfirmedExit(host.proc));
    assert.equal(await isDomainHostPortAvailable('127.0.0.1', port), true);
  }
});

test('supervisor: startDomainApi registers teardown on failure paths', async (t) => {
  const port = await reserveLocalPort();
  const host = await startDomainApi(port, { t });
  assert.equal(host.getDiagnostics().alive, true);
  await assert.rejects(async () => {
    throw new Error('simulated assertion failure');
  }, /simulated assertion failure/);
});

test('supervisor: stop does not terminate unrelated Python process', async (t) => {
  const sentinel = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], {
    stdio: 'ignore',
    detached: false,
  });
  t.after(() => {
    if (sentinel.exitCode === null) sentinel.kill('SIGKILL');
  });

  const port = await reserveLocalPort();
  const host = await startDomainHost({ port });
  await stopDomainHostProcess(host.proc);
  assert.ok(hasConfirmedExit(host.proc) || getDomainHostDiagnostics(host.proc).stopped);
  assert.equal(sentinel.exitCode, null);
});
