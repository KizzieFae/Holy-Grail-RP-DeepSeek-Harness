import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');
export const venvPython = path.join(repoRoot, 'autogen_rp', 'python', '.venv', 'Scripts', 'python.exe');

/**
 * @param {number} port
 * @param {{ sessionsDir?: string }} [options]
 */
export async function startDomainApi(port, options = {}) {
  const env = {
    ...process.env,
    PYTHONPATH: path.join(repoRoot, 'v2'),
  };
  if (options.sessionsDir) {
    env.HG_SESSIONS_DIR = options.sessionsDir;
  }
  const proc = spawn(
    venvPython,
    ['-m', 'domain_api', '--host', '127.0.0.1', '--port', String(port)],
    { cwd: path.join(repoRoot, 'v2'), env },
  );
  const baseUrl = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) {
        const result = { proc, baseUrl };
        if (options.withSession) {
          const createRes = await fetch(`${baseUrl}/v1/sessions/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cast: options.cast ?? ['Alice', 'Bob'] }),
          });
          if (!createRes.ok) throw new Error('failed to create session');
          result.scene = await createRes.json();
        }
        return result;
      }
    } catch {
      // server not ready
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  proc.kill();
  throw new Error('Domain API server failed to start');
}

export function makeTempSessionsDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'hg-sessions-'));
}
