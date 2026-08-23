#!/usr/bin/env node
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createHolyGrailAppServer } from '../src/application/app-server.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { defaultPythonExecutable, repoRoot } from '../src/lib/runtime-config.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const uiDir = path.join(repoRoot, 'v2', 'ui');

/** Holy Grail UI port — avoids colliding with other Streamlit apps on 8501. */
const DEFAULT_STREAMLIT_PORT = 8510;

function resolveStreamlitPort() {
  const raw = process.env.HG_STREAMLIT_PORT?.trim();
  if (!raw) return DEFAULT_STREAMLIT_PORT;
  const port = Number(raw);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`invalid HG_STREAMLIT_PORT: ${raw}`);
  }
  return port;
}

function resolveStreamlitExecutable() {
  const venvPython = defaultPythonExecutable();
  return { python: venvPython, module: 'streamlit' };
}

async function maybeSpawnStreamlit(apiBaseUrl) {
  if (process.env.HG_SKIP_STREAMLIT === '1') {
    console.log('[hg-app] HG_SKIP_STREAMLIT=1 — API only');
    return null;
  }

  const streamlitScript = path.join(uiDir, 'streamlit_app.py');
  if (!fs.existsSync(streamlitScript)) {
    console.warn('[hg-app] streamlit_app.py not found — API only');
    return null;
  }

  const { python } = resolveStreamlitExecutable();
  const streamlitPort = resolveStreamlitPort();
  const env = {
    ...process.env,
    HG_APP_API_URL: apiBaseUrl,
    PYTHONPATH: path.join(repoRoot, 'v2'),
  };
  const args = [
    '-m', 'streamlit', 'run', streamlitScript,
    '--server.headless', 'true',
    '--server.port', String(streamlitPort),
    '--browser.gatherUsageStats', 'false',
  ];
  const proc = spawn(python, args, {
    cwd: uiDir,
    env,
    stdio: 'inherit',
    shell: false,
  });
  proc.on('exit', (code) => {
    if (code && code !== 0) {
      console.error(`[hg-app] Streamlit exited with code ${code}`);
    }
  });
  return { proc, port: streamlitPort };
}

const client = new HolyGrailApplicationClient({
  inferenceMode: process.env.HG_INFERENCE_MODE === 'mock' ? 'mock' : 'live',
  runtime: {
    inference: { mountDeepSeek: process.env.HG_INFERENCE_MODE !== 'mock' },
  },
});
const appServer = createHolyGrailAppServer(client);
let streamlitProc = null;

async function shutdown(signal) {
  console.log(`[hg-app] received ${signal}, shutting down...`);
  if (streamlitProc?.proc && !streamlitProc.proc.killed) {
    streamlitProc.proc.kill('SIGTERM');
  }
  await appServer.close().catch(() => {});
  await client.stop().catch(() => {});
  process.exit(0);
}

process.on('SIGINT', () => { shutdown('SIGINT'); });
process.on('SIGTERM', () => { shutdown('SIGTERM'); });

try {
  const ready = await client.start();
  const listen = await appServer.listen(Number(process.env.HG_APP_PORT ?? 0));
  streamlitProc = await maybeSpawnStreamlit(listen.baseUrl);

  console.log('[hg-app] ready:', JSON.stringify({
    ...ready,
    application_api_url: listen.baseUrl,
    streamlit: streamlitProc ? 'started' : 'skipped',
    streamlit_url: streamlitProc ? `http://localhost:${streamlitProc.port}` : null,
  }, null, 2));
  console.log('[hg-app] press Ctrl+C to stop');
} catch (err) {
  console.error('[hg-app] startup failed:', err instanceof Error ? err.message : err);
  process.exit(1);
}
