import fs from 'node:fs';
import path from 'node:path';

import { createDomainApiClient } from '../lib/domain-api-client.mjs';
import { makeTempSessionsDir, startDomainApi } from '../../tests/helpers/domain-api.mjs';

/**
 * Start production Domain Host + API client for headless scenario runs.
 * Mirrors integration-test host setup without node:test lifecycle hooks.
 */
export async function startHarnessRuntime(options = {}) {
  const sessionsDir = options.sessionsDir ?? makeTempSessionsDir();
  const dataDir = options.dataDir ?? path.join(path.dirname(sessionsDir), 'hg-harness-data');
  const forensicsDir = options.forensicsDir ?? path.join(dataDir, 'plot_cognition_forensics');
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.mkdirSync(forensicsDir, { recursive: true });
  const port = options.port ?? (51765 + Math.floor(Math.random() * 1000));
  const hostEnv = {
    HG_DATA_DIR: dataDir,
    HG_SESSIONS_DIR: sessionsDir,
    HG_PLOT_COGNITION_FORENSICS_DIR: forensicsDir,
    HG_EXECUTION_EVIDENCE: options.executionEvidence === false ? 'off' : 'on',
    ...(options.hostEnv ?? {}),
  };
  const host = await startDomainApi(port, { sessionsDir, hostEnv });
  const api = createDomainApiClient(host.baseUrl);
  return {
    api,
    baseUrl: host.baseUrl,
    sessionsDir,
    dataDir,
    forensicsDir,
    hostEnv,
    async dispose() {
      await host.stop();
    },
  };
}
