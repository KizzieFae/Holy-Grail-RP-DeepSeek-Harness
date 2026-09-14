import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const scriptPath = path.join(__dirname, '../scripts/issue193-r16-live-validation.mjs');

test('issue193 live R16 validation script (bounded matrix A–H)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 900_000,
}, async () => {
  const exitCode = await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [scriptPath], {
      cwd: path.join(__dirname, '..'),
      stdio: 'inherit',
      env: process.env,
    });
    child.on('error', reject);
    child.on('close', resolve);
  });
  assert.equal(exitCode, 0, 'issue193 live validation script failed');
});
