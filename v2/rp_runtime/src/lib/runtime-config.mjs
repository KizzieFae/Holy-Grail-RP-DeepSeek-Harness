import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');

export const DOMAIN_HOST_SERVICE_ID = 'holy-grail-domain-host';

export function defaultPythonExecutable() {
  if (process.env.HG_PYTHON_EXECUTABLE) {
    return process.env.HG_PYTHON_EXECUTABLE;
  }
  const winVenv = path.join(repoRoot, 'autogen_rp', 'python', '.venv', 'Scripts', 'python.exe');
  const posixVenv = path.join(repoRoot, 'autogen_rp', 'python', '.venv', 'bin', 'python');
  if (process.platform === 'win32' && fs.existsSync(winVenv)) return winVenv;
  if (fs.existsSync(posixVenv)) return posixVenv;
  return process.platform === 'win32' ? 'python' : 'python3';
}

export function defaultSessionsDir() {
  return process.env.HG_SESSIONS_DIR
    ?? path.join(repoRoot, 'autogen_rp', 'python', 'data', 'sessions');
}

export function resolveDomainHostUrl(options = {}) {
  const explicit = options.domainApi?.baseUrl ?? options.domainHostUrl;
  if (explicit) return String(explicit).replace(/\/$/, '');
  const fromEnv = process.env.HG_DOMAIN_HOST_URL;
  if (fromEnv) return String(fromEnv).replace(/\/$/, '');
  return null;
}

export function domainHostSpawnEnv(options = {}) {
  const env = {
    ...process.env,
    PYTHONPATH: path.join(repoRoot, 'v2'),
  };
  const sessionsDir = options.sessionsDir ?? defaultSessionsDir();
  if (sessionsDir) env.HG_SESSIONS_DIR = sessionsDir;
  return env;
}
