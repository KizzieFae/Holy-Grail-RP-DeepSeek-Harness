import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { DOMAIN_HOST_SERVICE_ID } from '../src/lib/runtime-config.mjs';
import {
  reserveLocalPort,
  startDomainHost,
  stopDomainHostProcess,
  waitForHealthyDomainHost,
} from '../src/runtime-supervisor/domain-host-process.mjs';
import { HolyGrailRuntimeSupervisor } from '../src/runtime-supervisor/supervisor.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

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
  await supervisor.stop();
  assert.equal(supervisor.domainHost, null);
  assert.ok(proc.exitCode !== null || proc.signalCode === 'SIGTERM');
  assert.equal(supervisor.state, 'stopped');
  assert.equal(ready.dsh_runtime, 'ready');
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
