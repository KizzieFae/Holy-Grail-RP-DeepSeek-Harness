import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { Service } from '@deepseek-ai/cordis';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { mountHolyGrailServices } from '../src/lib/mount-hg-services.mjs';
import HgContextBridge from '../src/plugins/hg-context-bridge/service.mjs';
import HgPhaseExecutors from '../src/plugins/hg-phase-executors/service.mjs';
import HgRoundOrchestrator from '../src/plugins/hg-round-orchestrator/service.mjs';
import HgTraceEmitter from '../src/plugins/hg-trace-emitter/service.mjs';

const srcRoot = fileURLToPath(new URL('../src/', import.meta.url));

function readSrc(relativePath) {
  return readFileSync(path.join(srcRoot, relativePath), 'utf8');
}

test('bootstrap composition: activates HG services and matches return handles', async (t) => {
  const runtime = await createHolyGrailRpContext();
  t.after(async () => {
    await runtime.ctx.fiber.dispose();
  });

  assert.ok(runtime.ctx.reflect.get('agentLoop'));
  assert.ok(runtime.ctx.hgContextBridge);
  assert.ok(runtime.ctx.hgTraceEmitter);
  assert.ok(runtime.ctx.hgPhaseExecutors);
  assert.ok(runtime.ctx.hgRoundOrchestrator);
  assert.ok(runtime.contextBridge instanceof HgContextBridge);
  assert.ok(runtime.traceEmitter instanceof HgTraceEmitter);
  assert.ok(runtime.phaseExecutors instanceof HgPhaseExecutors);
  assert.ok(runtime.orchestrator instanceof HgRoundOrchestrator);
  assert.equal(runtime.contextBridge.name, 'hgContextBridge');
  assert.equal(runtime.traceEmitter.name, 'hgTraceEmitter');
  assert.equal(runtime.phaseExecutors.name, 'hgPhaseExecutors');
  assert.equal(runtime.orchestrator.name, 'hgRoundOrchestrator');
  assert.equal(typeof runtime.orchestrator.runRound, 'function');
});

test('bootstrap composition: accepted inject DAG on HG services', () => {
  assert.deepEqual(HgPhaseExecutors.inject, ['hgContextBridge']);
  assert.deepEqual(HgRoundOrchestrator.inject, [
    'hgPhaseExecutors',
    'hgTraceEmitter',
    'agentLoop',
  ]);
  assert.equal(HgContextBridge.inject, undefined);
  assert.equal(HgTraceEmitter.inject, undefined);
});

test('bootstrap composition: no parallel production new/ensure bootstrap paths', () => {
  const bootstrap = readSrc('bootstrap.mjs');
  const mountRpStack = readSrc('lib/mount-rp-stack.mjs');
  const mountHgServices = readSrc('lib/mount-hg-services.mjs');
  const phaseExecutors = readSrc('plugins/hg-phase-executors/service.mjs');
  const traceEmitter = readSrc('plugins/hg-trace-emitter/service.mjs');

  assert.doesNotMatch(bootstrap, /new Hg(?:ContextBridge|TraceEmitter|PhaseExecutors|RoundOrchestrator)/);
  assert.doesNotMatch(mountRpStack, /new Hg|\.ensure\(/);
  assert.match(mountHgServices, /await ctx\.plugin\(HgContextBridge\)/);
  assert.match(mountHgServices, /await ctx\.plugin\(HgTraceEmitter\)/);
  assert.match(mountHgServices, /await ctx\.plugin\(HgPhaseExecutors/);
  assert.match(mountHgServices, /await ctx\.plugin\(HgRoundOrchestrator/);
  assert.doesNotMatch(phaseExecutors, /static ensure|\.ensure\(/);
  assert.doesNotMatch(traceEmitter, /static ensure|\.ensure\(/);
});

test('bootstrap composition: root dispose clears HG service registrations', async (t) => {
  const { ctx } = await createHolyGrailRpContext();
  assert.ok(ctx.hgRoundOrchestrator);

  await ctx.fiber.dispose();

  assert.equal(ctx.reflect.get('hgContextBridge'), undefined);
  assert.equal(ctx.reflect.get('hgTraceEmitter'), undefined);
  assert.equal(ctx.reflect.get('hgPhaseExecutors'), undefined);
  assert.equal(ctx.reflect.get('hgRoundOrchestrator'), undefined);
});

test('bootstrap composition: plugin activation failure rejects without return', async () => {
  class FailingHgPlugin extends Service {
    static name = 'hgContextBridge';

    constructor(ctx) {
      super(ctx, FailingHgPlugin.name);
      throw new Error('bootstrap plugin failure');
    }
  }

  const { Context } = await import('@deepseek-ai/cordis');
  const { mountRpStack } = await import('../src/lib/mount-rp-stack.mjs');
  const ctx = new Context();

  try {
    await mountRpStack(ctx, {}, {});
    await assert.rejects(
      async () => {
        await ctx.plugin(FailingHgPlugin);
      },
      /bootstrap plugin failure/,
    );
  } finally {
    await ctx.fiber.dispose();
  }
});

test('bootstrap composition: mountHolyGrailServices failure leaves disposable context', async () => {
  class FailingOrchestrator extends Service {
    static name = 'hgRoundOrchestrator';

    static inject = ['hgPhaseExecutors', 'hgTraceEmitter', 'agentLoop'];

    constructor(ctx, config = {}) {
      super(ctx, FailingOrchestrator.name);
      this.config = config;
      throw new Error('orchestrator bootstrap failure');
    }
  }

  const { Context } = await import('@deepseek-ai/cordis');
  const { mountRpStack } = await import('../src/lib/mount-rp-stack.mjs');
  const ctx = new Context();
  const config = {};

  try {
    await mountRpStack(ctx, config, {});
    await ctx.plugin(HgContextBridge);
    await ctx.plugin(HgTraceEmitter);
    await ctx.plugin(HgPhaseExecutors, config);
    await assert.rejects(
      async () => {
        await ctx.plugin(FailingOrchestrator, config);
      },
      /orchestrator bootstrap failure/,
    );
  } finally {
    await ctx.fiber.dispose();
    assert.equal(ctx.reflect.get('hgRoundOrchestrator'), undefined);
  }
});
