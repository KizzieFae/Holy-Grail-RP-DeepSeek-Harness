import path from 'node:path';

import { createHolyGrailRpContext } from '../bootstrap.mjs';
import {
  deepseekInferenceProfile,
  mockInferenceProfile,
  resolveRoleProfiles,
} from '../lib/inference-profile.mjs';

export function hasLiveApiKey(env = process.env) {
  return Boolean(env.DEEPSEEK_API_KEY?.trim());
}

export function requireLiveApiKey(env = process.env) {
  if (!hasLiveApiKey(env)) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }
}

/**
 * Production live harness context: DeepSeek mount + evidence recorder aligned to harness data dir.
 */
export async function createLiveHarnessRpContext({ baseUrl, dataDir, env = process.env }) {
  requireLiveApiKey(env);
  const evidenceRoot = path.join(dataDir, 'execution_evidence');
  return createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: {
        enabled: true,
        root: evidenceRoot,
      },
    },
  });
}

export function createLiveRuntimeConfig() {
  const defaultProfile = deepseekInferenceProfile();
  return {
    defaultProfile,
    roleProfiles: resolveRoleProfiles({}, { defaultProfile }),
  };
}

export function describeResolvedProfiles(runtimeConfig) {
  const profiles = runtimeConfig.roleProfiles ?? {};
  const out = {};
  for (const [role, profile] of Object.entries(profiles)) {
    out[role] = {
      kind: profile?.kind ?? null,
      provider: profile?.provider ?? null,
      model: profile?.model ?? null,
      reasoning_effort: profile?.reasoningEffort ?? null,
      max_tokens: profile?.maxTokens ?? null,
    };
  }
  return out;
}

export function mockRuntimeConfig() {
  const defaultProfile = mockInferenceProfile();
  return {
    defaultProfile,
    roleProfiles: resolveRoleProfiles({}, { defaultProfile }),
  };
}
