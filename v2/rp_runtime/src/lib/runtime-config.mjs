import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');

export const DOMAIN_HOST_SERVICE_ID = 'holy-grail-domain-host';

export const CANONICAL_VENV_DIR_NAME = '.venv';

/** Repo-local Holy Grail Python virtual environment root. */
export function canonicalVenvRoot(root = repoRoot) {
  return path.join(root, CANONICAL_VENV_DIR_NAME);
}

/**
 * Resolve the interpreter inside a venv root for the given platform.
 * @param {string} venvRoot
 * @param {NodeJS.Platform} [platform]
 */
export function pythonExecutableForVenvRoot(venvRoot, platform = process.platform) {
  if (platform === 'win32') {
    return path.join(venvRoot, 'Scripts', 'python.exe');
  }
  return path.join(venvRoot, 'bin', 'python');
}

/** Canonical repo-local Domain Host interpreter path. */
export function canonicalPythonExecutable(root = repoRoot) {
  return pythonExecutableForVenvRoot(canonicalVenvRoot(root));
}

/**
 * Production/test default Python interpreter.
 * Precedence: HG_PYTHON_EXECUTABLE → canonical repo `.venv` (no legacy fallback).
 */
export function defaultPythonExecutable() {
  const explicit = process.env.HG_PYTHON_EXECUTABLE?.trim();
  if (explicit) {
    return explicit;
  }
  return canonicalPythonExecutable();
}

export function defaultDataDir() {
  return process.env.HG_DATA_DIR
    ?? path.join(repoRoot, 'data');
}

export function defaultSessionsDir() {
  return process.env.HG_SESSIONS_DIR
    ?? path.join(defaultDataDir(), 'sessions');
}

export function defaultExecutionEvidenceDir() {
  return process.env.HG_EXECUTION_EVIDENCE_DIR
    ?? path.join(defaultDataDir(), 'execution_evidence');
}

export function defaultAuditTagsDir() {
  return process.env.HG_AUDIT_TAGS_DIR
    ?? path.join(defaultDataDir(), 'audit_tags');
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
  if (!env.HG_DATA_DIR) {
    env.HG_DATA_DIR = defaultDataDir();
  }
  const sessionsDir = options.sessionsDir ?? defaultSessionsDir();
  if (sessionsDir) env.HG_SESSIONS_DIR = sessionsDir;
  if (options.env && typeof options.env === 'object') {
    Object.assign(env, options.env);
  }
  return env;
}
