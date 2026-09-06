import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

test('live storyteller orientation bounded validation (no transport 400 on schema omission)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 180_000,
}, async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-live-st-142-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const host = await startDomainApi(undefined, { sessionsDir, t });
  const { ctx, orchestrator } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { defaultProfile: deepseekInferenceProfile({ reasoningEffort: 'low' }) },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    skipPlotCognitionOrchestration: true,
    storytellerAllowDeterministicFallback: false,
    roleProfiles: {
      storyteller: deepseekInferenceProfile({ reasoningEffort: 'low' }),
      director: deepseekInferenceProfile({ reasoningEffort: 'low' }),
    },
    mockDirectorResponses: [JSON.stringify({
      next_actor: 'Alice',
      end_round: true,
      reason: 'Stop after storyteller probe.',
      environment_event: '',
      tension_shift: 'steady',
    })],
  });

  const skipped = result.scene_events.find((event) => event.type === 'hg/storyteller-skipped');
  const completed = result.scene_events.find((event) => event.type === 'hg/storyteller-completed');
  const storytellerSummary = result.storyteller ?? result.storyteller_round_summary ?? null;

  assert.ok(skipped || completed, 'storyteller cognition attempted');
  if (skipped) {
    assert.notEqual(skipped.data?.reason, undefined);
    assert.match(
      String(skipped.data?.reason ?? ''),
      /schema_mismatch|orientation_finalize|orientation_invalid|assessment_finalize|assessment_invalid|librarian|orientation_inference|assessment_inference|^error$/,
    );
  }

  const auditText = JSON.stringify({
    skipped,
    completed,
    storytellerSummary,
    completionReason: result.completion_reason,
  });
  assert.doesNotMatch(auditText, /dictionary update sequence element #0 has length 1/);
  assert.doesNotMatch(auditText, /orientation\/finalize failed \(400\)/);
});
