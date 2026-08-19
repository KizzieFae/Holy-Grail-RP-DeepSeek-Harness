import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';

import {
  CANONICAL_VENV_DIR_NAME,
  canonicalPythonExecutable,
  canonicalVenvRoot,
  defaultPythonExecutable,
  pythonExecutableForVenvRoot,
  repoRoot,
} from '../src/lib/runtime-config.mjs';

test('runtime-config: canonical venv root is repo-local .venv', () => {
  assert.equal(canonicalVenvRoot(), path.join(repoRoot, CANONICAL_VENV_DIR_NAME));
});

test('runtime-config: Windows interpreter path under canonical venv', () => {
  const root = path.join('C:', 'Holy Grail Repo', '.venv');
  assert.equal(
    pythonExecutableForVenvRoot(root, 'win32'),
    path.join('C:', 'Holy Grail Repo', '.venv', 'Scripts', 'python.exe'),
  );
});

test('runtime-config: POSIX interpreter path under canonical venv', () => {
  const root = '/opt/holy grail/.venv';
  assert.equal(
    pythonExecutableForVenvRoot(root, 'linux'),
    path.join('/opt/holy grail/.venv', 'bin', 'python'),
  );
});

test('runtime-config: paths with spaces are preserved', () => {
  const spacedRoot = path.join(repoRoot, 'Holy Grail Space', '.venv');
  const resolved = pythonExecutableForVenvRoot(spacedRoot, 'win32');
  assert.match(resolved, /Holy Grail Space/);
  assert.match(resolved, /Scripts[\\/]python\.exe$/);
});

test('runtime-config: HG_PYTHON_EXECUTABLE overrides canonical default', () => {
  const previous = process.env.HG_PYTHON_EXECUTABLE;
  process.env.HG_PYTHON_EXECUTABLE = 'C:\\Custom Python\\python.exe';
  try {
    assert.equal(defaultPythonExecutable(), 'C:\\Custom Python\\python.exe');
  } finally {
    if (previous === undefined) delete process.env.HG_PYTHON_EXECUTABLE;
    else process.env.HG_PYTHON_EXECUTABLE = previous;
  }
});

test('runtime-config: default does not reference historical autogen_rp venv', () => {
  const resolved = defaultPythonExecutable();
  assert.ok(!resolved.replace(/\\/g, '/').includes('autogen_rp/python/.venv'));
  assert.equal(resolved, canonicalPythonExecutable());
});

test('runtime-config: missing canonical interpreter fails clearly', async () => {
  const missingRoot = path.join(repoRoot, '__missing_venv_probe__');
  const missingPython = canonicalPythonExecutable(missingRoot);
  const { spawnDomainHostProcess } = await import('../src/runtime-supervisor/domain-host-process.mjs');
  assert.throws(
    () => spawnDomainHostProcess({
      port: 9,
      pythonExecutable: missingPython,
    }),
    /Python executable not found/,
  );
});
