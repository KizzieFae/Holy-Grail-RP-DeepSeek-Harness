import fs from 'node:fs';
import path from 'node:path';

const LOCK_TIMEOUT_MS = 10_000;
const LOCK_RETRY_MS = 1;

function sleepSync(ms) {
  if (typeof Atomics !== 'undefined' && typeof SharedArrayBuffer !== 'undefined') {
    const buffer = new SharedArrayBuffer(4);
    const view = new Int32Array(buffer);
    Atomics.wait(view, 0, 0, ms);
    return;
  }
  const start = Date.now();
  while (Date.now() - start < ms) {
    // Single-threaded spin for environments without Atomics.wait.
  }
}

/**
 * Serialize session index.json mutations across concurrent inference completions (#165).
 * Uses an exclusive lock file per session directory.
 *
 * @param {string} sessionDir
 * @param {() => void} task
 */
export function withSessionIndexLockSync(sessionDir, task) {
  fs.mkdirSync(sessionDir, { recursive: true });
  const lockPath = path.join(sessionDir, '.index-write.lock');
  const startedAt = Date.now();
  while (Date.now() - startedAt < LOCK_TIMEOUT_MS) {
    try {
      const fd = fs.openSync(lockPath, 'wx');
      try {
        return task();
      } finally {
        fs.closeSync(fd);
        try {
          fs.unlinkSync(lockPath);
        } catch {
          // ignore stale lock cleanup failures
        }
      }
    } catch (error) {
      if (error?.code !== 'EEXIST') {
        throw error;
      }
      sleepSync(LOCK_RETRY_MS);
    }
  }
  throw new Error(`execution evidence index lock timeout: ${lockPath}`);
}
