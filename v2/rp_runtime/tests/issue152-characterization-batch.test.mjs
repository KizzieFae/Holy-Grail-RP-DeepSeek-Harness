import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { listPrimaryCharacterizationFixtures } from '../src/lib/llm-characterization/fixtures.mjs';
import { runCharacterizationBatch } from '../scripts/run-llm-characterization-batch.mjs';

test('issue152: mock characterization batch covers all 25 primary identities', async () => {
  const charRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-char-summary-'));
  const result = await runCharacterizationBatch({
    characterizationRoot: charRoot,
    inferenceMode: 'mock',
  });
  assert.equal(listPrimaryCharacterizationFixtures().length, 25);
  assert.equal(Object.keys(result.summaries).length, 25);
  for (const callId of listPrimaryCharacterizationFixtures()) {
    const summary = result.summaries[callId];
    assert.ok(summary, `missing summary for ${callId}`);
    assert.equal(summary.characterization_mode, true);
    assert.ok(summary.valid_natural_attempt_count >= 3, `${callId} needs baseline valid attempts`);
    assert.ok(summary.stability_class, `${callId} missing stability class`);
  }
  const envSummary = result.summaries.narrator_environment_cognition;
  assert.match(
    envSummary.comparison_notes.join(' '),
    /c73d368c/,
  );
});
