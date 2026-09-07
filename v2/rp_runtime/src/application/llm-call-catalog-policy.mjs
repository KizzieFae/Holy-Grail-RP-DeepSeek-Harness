import {
  PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES,
  ROLE_REASONING_DEFAULTS,
  UNCAPPED_INFERENCE_KINDS,
  modelProfileForInferenceKind,
  resolveApplicationRoleProfiles,
  resolveReasoningEffortForRole,
  tokenCeilingForInferenceKind,
  tokenCeilingForRole,
} from './application-settings.mjs';

/** Catalog documents production executable policy, not characterization/calibration runtime. */
const PRODUCTION_POLICY_OPTIONS = {
  inferenceCharacterization: false,
  inferenceCalibration: false,
};

/**
 * Resolve production application token quota for a catalog entry.
 * @returns {number | 'UNCAPPED'}
 */
export function resolveCatalogApplicationTokenQuota(entry, settings = {}, options = {}) {
  const policyOptions = { ...PRODUCTION_POLICY_OPTIONS, ...options };
  if (entry.profile_source === 'uncapped') {
    return 'UNCAPPED';
  }
  if (entry.profile_source === 'kind_override' && entry.kind_override) {
    const ceiling = tokenCeilingForInferenceKind(entry.kind_override, settings, policyOptions);
    if (!Number.isFinite(ceiling)) {
      if (UNCAPPED_INFERENCE_KINDS.has(entry.kind_override)) return 'UNCAPPED';
      throw new Error(`unable to resolve kind quota for ${entry.call_id}`);
    }
    return ceiling;
  }
  const role = entry.profile_source === 'parent_role'
    ? entry.parent_role
    : entry.profile_role;
  if (!role) {
    throw new Error(`unable to resolve role quota for ${entry.call_id}`);
  }
  const ceiling = tokenCeilingForRole(role, settings, policyOptions);
  if (!Number.isFinite(ceiling)) {
    throw new Error(`unable to resolve role quota for ${entry.call_id}`);
  }
  return ceiling;
}

/** @returns {string} */
export function resolveCatalogReasoningPolicy(entry, settings = {}) {
  const kind = entry.kind_override ?? entry.canonical_inference_kind;
  const kindOverride = PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES[kind];
  if (kindOverride !== undefined) return kindOverride;
  const role = entry.profile_source === 'parent_role'
    ? entry.parent_role
    : entry.profile_role ?? entry.role_agent;
  return resolveReasoningEffortForRole(role, settings, PRODUCTION_POLICY_OPTIONS);
}

/** Human-readable quota resolution source for catalog export. */
export function resolveCatalogQuotaResolutionSource(entry) {
  if (entry.profile_source === 'uncapped') {
    return 'UNCAPPED_INFERENCE_KINDS';
  }
  if (entry.profile_source === 'kind_override' && entry.kind_override) {
    return `PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS.${entry.kind_override}`;
  }
  const role = entry.profile_source === 'parent_role'
    ? entry.parent_role
    : entry.profile_role;
  return `PRODUCTION_TOKEN_CEILINGS.${role}`;
}

/**
 * Resolve the production model profile used at runtime for a catalog entry.
 */
export function resolveCatalogProductionProfile(entry, settings = {}, options = {}) {
  const policyOptions = { ...PRODUCTION_POLICY_OPTIONS, ...options };
  const roleProfiles = resolveApplicationRoleProfiles(settings, policyOptions);
  if (entry.profile_source === 'uncapped') {
    const base = roleProfiles[entry.profile_role ?? 'character'];
    return modelProfileForInferenceKind(base, entry.kind_override ?? entry.canonical_inference_kind, settings, policyOptions);
  }
  if (entry.profile_source === 'kind_override') {
    const baseRole = entry.profile_role ?? 'storyteller';
    const base = roleProfiles[baseRole] ?? roleProfiles.storyteller;
    return modelProfileForInferenceKind(base, entry.kind_override, settings, policyOptions);
  }
  if (entry.profile_source === 'parent_role') {
    return roleProfiles[entry.parent_role ?? entry.profile_role ?? 'character'];
  }
  return roleProfiles[entry.profile_role ?? entry.role_agent];
}

/**
 * Build one generated catalog row (policy fields derived from executable settings).
 */
export function buildGeneratedCatalogRow(entry, settings = {}, options = {}, empirical = {}) {
  const applicationTokenQuota = resolveCatalogApplicationTokenQuota(entry, settings, options);
  return {
    call_id: entry.call_id,
    catalog_scope: entry.catalog_scope,
    canonical_inference_kind: entry.canonical_inference_kind,
    evidence_aliases: [...entry.evidence_aliases],
    role_agent: entry.role_agent,
    subsystem: entry.subsystem,
    purpose: entry.purpose,
    owner_module: entry.owner_module,
    owner_export: entry.owner_export,
    invocation_condition: entry.invocation_condition,
    profile_source: entry.profile_source,
    application_token_quota: applicationTokenQuota,
    application_token_quota_resolution: resolveCatalogQuotaResolutionSource(entry),
    reasoning_policy: resolveCatalogReasoningPolicy(entry, settings),
    external_limits_note: 'UNCAPPED means no Holy-Grail application maxTokens; provider/model limits may still apply.',
    current_exception_note: entry.current_exception_note,
    characterization_status: empirical.characterization_status ?? 'pending',
    characterization_summary_ref: empirical.characterization_summary_ref ?? null,
    production_quota_at_characterization: empirical.production_quota_at_characterization ?? applicationTokenQuota,
  };
}
