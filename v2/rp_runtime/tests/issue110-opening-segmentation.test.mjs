import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import {
  modelProfileForInferenceKind,
  resolveApplicationRoleProfiles,
} from '../src/application/application-settings.mjs';
import { classifyReasoningBudgetOutcome } from '../src/lib/reasoning-provider-options.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

test('issue110: opening_segmentation profile disables thinking at application client wiring', () => {
  const opening = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  }).opening;
  const profile = modelProfileForInferenceKind(opening, 'opening_segmentation');
  assert.equal(profile.reasoningEffort, 'off');
  assert.equal(profile.maxTokens, undefined);
});

test('issue110: reasoning-budget exhaustion classifier unchanged', () => {
  const outcome = classifyReasoningBudgetOutcome(
    { outputTokens: 4096, reasoningTokens: 4096 },
    { kind: 'max-tokens' },
    '',
  );
  assert.equal(outcome.reasoning_budget_exhausted, true);
});

test('issue110: empty segmentation output remains failure path with canon preserved', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  const openers = await client.listTemplateOpeners('ayame_household_entry_evaluation');
  const created = await client.createSession({
    characters: ['ayame', 'kizzie'],
    sceneTemplateId: 'ayame_household_entry_evaluation',
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    opening: { mode: 'template', opener_id: openers[0].opener_id },
    mockOpeningSegmentationResponses: ['', ''],
    openingSegmentationMaxAttempts: 2,
  });

  const transcript = client.getTranscript();
  assert.ok(transcript[0]?.content?.length > 0);
  assert.match(transcript[0].content, /horrible week/);
});
