import crypto from 'node:crypto';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  APPLICATION_TOKEN_QUOTAS_ENFORCED,
  PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES,
  PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS,
  PRODUCTION_TOKEN_CEILINGS,
  ROLE_REASONING_DEFAULTS,
  UNCAPPED_INFERENCE_KINDS,
  buildInferenceOptions,
  modelProfileForInferenceKind,
} from '../application/application-settings.mjs';
import { isExecutionEvidenceEnabled } from './execution-evidence/config.mjs';

export const BUILD_PROVENANCE_SCHEMA = 'hg_runtime_build_provenance_v1';
export const EFFECTIVE_CONFIGURATION_SCHEMA = 'hg_runtime_effective_configuration_v1';

const POST_COMMIT_SEMANTIC_INFERENCE_KIND = 'storyteller_post_commit_issue_pressure';
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const CATALOG_PATH = path.join(REPO_ROOT, 'docs', 'llm-call-catalog.json');
const BOUND_REPOSITORY = 'KizzieFae/Holy-Grail-RP-DeepSeek-Harness';

export function canonicalizeValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => canonicalizeValue(item));
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = canonicalizeValue(value[key]);
    }
    return out;
  }
  return value;
}

export function canonicalJsonString(value) {
  return JSON.stringify(canonicalizeValue(value));
}

export function sha256CanonicalFingerprint(value) {
  return crypto.createHash('sha256').update(canonicalJsonString(value), 'utf8').digest('hex');
}

function tryReadCatalog() {
  try {
    if (!fs.existsSync(CATALOG_PATH)) return null;
    return JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf8'));
  } catch {
    return null;
  }
}

export function buildCatalogSemanticFingerprint(catalogDoc = tryReadCatalog()) {
  if (!catalogDoc || !Array.isArray(catalogDoc.primary_runtime)) {
    return { catalog_schema: null, catalog_content_fingerprint: null };
  }
  const rows = catalogDoc.primary_runtime
    .map((row) => ({
      canonical_inference_kind: row.canonical_inference_kind ?? null,
      profile_source: row.profile_source ?? null,
      reasoning_policy: row.reasoning_policy ?? null,
      application_token_quota_enforced: row.application_token_quota_enforced ?? null,
      reference_application_token_quota: row.reference_application_token_quota ?? null,
      application_token_quota: row.application_token_quota ?? null,
    }))
    .sort((left, right) => String(left.canonical_inference_kind)
      .localeCompare(String(right.canonical_inference_kind)));
  return {
    catalog_schema: catalogDoc.schema ?? 'hg_llm_call_catalog_v1',
    catalog_content_fingerprint: sha256CanonicalFingerprint({ primary_runtime: rows }),
  };
}

function resolveRepositoryCommitSha(env = process.env) {
  const fromEnv = String(env.HG_REPO_COMMIT_SHA ?? '').trim();
  if (fromEnv) {
    return { repository_commit_sha: fromEnv, commit_sha_source: 'env' };
  }
  try {
    const sha = String(execSync('git rev-parse HEAD', {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    })).trim();
    if (sha) {
      return { repository_commit_sha: sha, commit_sha_source: 'git' };
    }
  } catch {
    // unavailable
  }
  return { repository_commit_sha: null, commit_sha_source: 'unavailable' };
}

export function captureBuildProvenance(env = process.env) {
  const catalog = buildCatalogSemanticFingerprint();
  const commit = resolveRepositoryCommitSha(env);
  return {
    schema: BUILD_PROVENANCE_SCHEMA,
    captured_at: new Date().toISOString(),
    repository_slug: BOUND_REPOSITORY,
    repository_commit_sha: commit.repository_commit_sha,
    commit_sha_source: commit.commit_sha_source,
    catalog_schema: catalog.catalog_schema,
    catalog_generated_at: tryReadCatalog()?.generated_at ?? null,
    catalog_content_fingerprint: catalog.catalog_content_fingerprint,
  };
}

function normalizeProfile(profile) {
  if (!profile || typeof profile !== 'object') return null;
  const normalized = {
    provider: profile.provider ?? null,
    model: profile.model ?? null,
    kind: profile.kind ?? null,
    reasoningEffort: profile.reasoningEffort ?? profile.reasoning_effort ?? null,
    maxTokens: profile.maxTokens ?? profile.max_tokens ?? null,
  };
  return normalized;
}

export function buildEffectiveConfigurationSnapshot(settings = {}, options = {}) {
  const inference = buildInferenceOptions(settings, options);
  const unavailableFields = [];
  const roleProfiles = {};
  for (const role of ['director', 'character', 'narrator', 'opening', 'semantic_evaluator', 'storyteller']) {
    const profile = inference.roleProfiles?.[role];
    if (!profile) {
      unavailableFields.push(`role_profiles.${role}`);
    }
    roleProfiles[role] = normalizeProfile(profile);
  }
  const postCommitProfile = modelProfileForInferenceKind(
    inference.roleProfiles?.storyteller ?? inference.roleProfiles?.character ?? null,
    POST_COMMIT_SEMANTIC_INFERENCE_KIND,
    settings,
    options,
  );
  const resolved = {
    inference_mode: inference.inferenceMode ?? null,
    role_routing: settings.roleRouting ?? 'simple',
    application_token_quotas_enforced: APPLICATION_TOKEN_QUOTAS_ENFORCED,
    role_profiles: roleProfiles,
    role_reasoning_defaults: { ...ROLE_REASONING_DEFAULTS },
    production_token_ceilings: { ...PRODUCTION_TOKEN_CEILINGS },
    production_inference_kind_token_ceilings: { ...PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS },
    uncapped_inference_kinds: [...UNCAPPED_INFERENCE_KINDS].sort(),
    production_inference_kind_reasoning_overrides: {
      ...PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES,
    },
    inference_calibration_enabled: Boolean(inference.inferenceCalibration),
    inference_characterization_enabled: Boolean(inference.inferenceCharacterization),
    execution_evidence_enabled: isExecutionEvidenceEnabled(options.env ?? process.env),
    post_commit_semantic_policy: {
      inference_kind: POST_COMMIT_SEMANTIC_INFERENCE_KIND,
      semantic_producer_role: 'storyteller',
      resolved_storyteller_profile: normalizeProfile(postCommitProfile),
    },
  };
  const captureStatus = unavailableFields.length ? 'partial' : 'complete';
  return {
    resolved,
    capture_status: captureStatus,
    unavailable_fields: unavailableFields,
  };
}

export function computeEffectiveConfigurationFingerprint(snapshot) {
  return sha256CanonicalFingerprint(snapshot.resolved ?? snapshot);
}

export function createEffectiveConfigurationEpoch({
  settings = {},
  options = {},
  effectiveFrom = 'session_open',
  epochId = `cfg-epoch-${crypto.randomUUID()}`,
}) {
  const snapshot = buildEffectiveConfigurationSnapshot(settings, options);
  const fingerprint = computeEffectiveConfigurationFingerprint(snapshot);
  return {
    epoch_id: epochId,
    effective_from: effectiveFrom,
    effective_configuration_fingerprint: fingerprint,
    capture_status: snapshot.capture_status,
    unavailable_fields: [...snapshot.unavailable_fields],
    resolved: snapshot.resolved,
  };
}

export function appendEffectiveConfigurationEpoch(existingConfig, epoch) {
  const base = existingConfig && typeof existingConfig === 'object'
    ? existingConfig
    : { schema: EFFECTIVE_CONFIGURATION_SCHEMA, epochs: [] };
  const epochs = [...(base.epochs ?? [])];
  const latest = epochs[epochs.length - 1];
  if (latest?.effective_configuration_fingerprint === epoch.effective_configuration_fingerprint) {
    return base;
  }
  epochs.push(epoch);
  return {
    schema: EFFECTIVE_CONFIGURATION_SCHEMA,
    epochs,
    current_epoch_id: epoch.epoch_id,
  };
}

export function currentEffectiveConfigurationEpoch(config) {
  const epochs = config?.epochs ?? [];
  return epochs[epochs.length - 1] ?? null;
}

export function ensureRuntimeProvenanceState(hostState = {}) {
  return {
    runtime_build_provenance: hostState.runtime_build_provenance ?? null,
    runtime_effective_configuration: hostState.runtime_effective_configuration ?? null,
  };
}
