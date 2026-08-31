import assert from 'node:assert/strict';
import fs from 'node:fs';
import net from 'node:net';
import test from 'node:test';

import { DOMAIN_HOST_SERVICE_ID } from '../src/lib/runtime-config.mjs';
import {
  reserveLocalPort,
  stopDomainHostProcess,
  waitForHealthyDomainHost,
} from '../src/runtime-supervisor/domain-host-process.mjs';
import { startHarnessRuntime } from '../src/scenario-harness/harness-runtime.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

function listenOnPort(host, port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(port, host, () => resolve(server));
  });
}

test('domain host port allocation: default path avoids a known occupied port', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const occupiedPort = await reserveLocalPort();
  const blocker = await listenOnPort('127.0.0.1', occupiedPort);
  t.after(() => new Promise((resolve, reject) => {
    blocker.close((err) => (err ? reject(err) : resolve()));
  }));

  const host = await startDomainApi(undefined, { sessionsDir });
  t.after(async () => {
    await host.stop();
  });

  assert.notEqual(host.port, occupiedPort);
  const health = await waitForHealthyDomainHost(host.baseUrl);
  assert.equal(health.service, DOMAIN_HOST_SERVICE_ID);
  assert.equal(health.status, 'ok');
});

test('domain host port allocation: explicit port is honored when available', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const explicitPort = await reserveLocalPort();
  const host = await startDomainApi(explicitPort, { sessionsDir });
  t.after(async () => {
    await stopDomainHostProcess(host.proc);
  });

  assert.equal(host.port, explicitPort);
  const health = await waitForHealthyDomainHost(host.baseUrl);
  assert.equal(health.service, DOMAIN_HOST_SERVICE_ID);
  assert.equal(health.status, 'ok');
});

test('harness runtime: default allocation avoids a known occupied port', async (t) => {
  const occupiedPort = await reserveLocalPort();
  const blocker = await listenOnPort('127.0.0.1', occupiedPort);
  t.after(() => new Promise((resolve, reject) => {
    blocker.close((err) => (err ? reject(err) : resolve()));
  }));

  const runtime = await startHarnessRuntime();
  t.after(async () => {
    await runtime.dispose();
    fs.rmSync(runtime.sessionsDir, { recursive: true, force: true });
  });

  const hostPort = Number(new URL(runtime.baseUrl).port);
  assert.notEqual(hostPort, occupiedPort);
  const health = await waitForHealthyDomainHost(runtime.baseUrl);
  assert.equal(health.service, DOMAIN_HOST_SERVICE_ID);
  assert.equal(health.status, 'ok');
});

test('harness runtime: explicit port is honored when available', async (t) => {
  const explicitPort = await reserveLocalPort();
  const runtime = await startHarnessRuntime({ port: explicitPort });
  t.after(async () => {
    await runtime.dispose();
    fs.rmSync(runtime.sessionsDir, { recursive: true, force: true });
  });

  const hostPort = Number(new URL(runtime.baseUrl).port);
  assert.equal(hostPort, explicitPort);
  const health = await waitForHealthyDomainHost(runtime.baseUrl);
  assert.equal(health.service, DOMAIN_HOST_SERVICE_ID);
  assert.equal(health.status, 'ok');
});
