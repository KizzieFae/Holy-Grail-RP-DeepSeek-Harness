import {
  deepseekInferenceProfile,
  HG_DEEPSEEK_DEFAULT_MODEL,
  mockInferenceProfile,
} from '../lib/inference-profile.mjs';
import { REASONING_LEVELS } from '../lib/reasoning-provider-options.mjs';

/** Internal per-role reasoning defaults (#29 calibration). */
export const ROLE_REASONING_DEFAULTS = {
  director: 'low',
  character: 'low',
  narrator: 'low',
  opening: 'low',
  semantic_evaluator: 'off',
};

/**
 * Reference token ceilings per role (#29) — baseline for catalog/telemetry comparison.
 * Not currently enforced at runtime; see APPLICATION_TOKEN_QUOTAS_ENFORCED.
 */
export const PRODUCTION_TOKEN_CEILINGS = {
  director: 4096,
  character: 4096,
  narrator: 8192,
  opening: 4096,
  semantic_evaluator: 2048,
};

/** Holy Grail API validation cap for explicit output overrides. */
export const PRODUCTION_MAX_TOKEN_CEILING = 8192;

/**
 * Reference operation-specific output headroom (#111).
 * Not currently enforced at runtime; see APPLICATION_TOKEN_QUOTAS_ENFORCED.
 */
export const PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS = {
  opening_segmentation: PRODUCTION_TOKEN_CEILINGS.opening,
  player_visibility_triage: 32,
  plot_cognition_update: PRODUCTION_MAX_TOKEN_CEILING,
  plot_cognition_update_contract_correction: PRODUCTION_MAX_TOKEN_CEILING,
  librarian_proposal: PRODUCTION_MAX_TOKEN_CEILING,
  librarian_proposal_contract_correction: PRODUCTION_MAX_TOKEN_CEILING,
};

/** Inference kinds that were reference-UNCAPPED before global quota disable (#124). */
export const UNCAPPED_INFERENCE_KINDS = new Set(['player_decomposition']);

/** Operation-specific reasoning overrides (#110). Role defaults remain unchanged. */
export const PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES = {
  opening_segmentation: 'off',
  player_visibility_triage: 'off',
};

/** Historical diagnostic ceiling label for calibration mode (not enforced while quotas disabled). */
export const DIAGNOSTIC_TOKEN_CEILING = 4096;

/**
 * Global HG application token quota enforcement (#152 revised consensus).
 * When false, runtime inference omits Holy-Grail maxTokens unconditionally.
 */
export const APPLICATION_TOKEN_QUOTAS_ENFORCED = false;

export const DEFAULT_RUNTIME_SETTINGS = {
  inferenceMode: 'live',
  roleRouting: 'simple',
  model: HG_DEEPSEEK_DEFAULT_MODEL,
  // Upper-bound input for live Character/Director candidate generation. Those phases
  // apply a shared effective ceiling of 3; values above 3 do not increase candidate budgets.
  liveMaxAttempts: 5,
};

function calibrationModeEnabled(settings = {}, options = {}) {
  const flag = settings.inferenceCalibration ?? settings.inference_calibration
    ?? options.inferenceCalibration;
  if (flag === false || flag === '0') return false;
  if (flag === true || flag === '1') return true;
  return process.env.HG_INFERENCE_CALIBRATION === '1';
}

function characterizationModeEnabled(settings = {}, options = {}) {
  const flag = settings.inferenceCharacterization ?? settings.inference_characterization
    ?? options.inferenceCharacterization;
  if (flag === false || flag === '0') return false;
  if (flag === true || flag === '1') return true;
  return process.env.HG_INFERENCE_CHARACTERIZATION === '1';
}

/** Calibration and characterization are mutually exclusive (#152). */
export function assertMutuallyExclusiveInferenceModes(settings = {}, options = {}) {
  if (calibrationModeEnabled(settings, options) && characterizationModeEnabled(settings, options)) {
    throw new Error(
      'HG_INFERENCE_CALIBRATION and HG_INFERENCE_CHARACTERIZATION cannot both be active',
    );
  }
}

export function isCharacterizationModeEnabled(settings = {}, options = {}) {
  assertMutuallyExclusiveInferenceModes(settings, options);
  return characterizationModeEnabled(settings, options);
}

export function isCalibrationModeEnabled(settings = {}, options = {}) {
  assertMutuallyExclusiveInferenceModes(settings, options);
  return calibrationModeEnabled(settings, options);
}

export function isApplicationTokenQuotaEnforced() {
  return APPLICATION_TOKEN_QUOTAS_ENFORCED;
}

/** Remove Holy-Grail application maxTokens while preserving other profile fields. */
export function stripApplicationMaxTokens(profile) {
  if (!profile || typeof profile !== 'object') return profile;
  const { maxTokens: _removed, max_tokens: _legacy, ...rest } = profile;
  return rest;
}

/** Reference-only role quota for catalog/telemetry (ignores runtime enforcement flag). */
export function referenceTokenCeilingForRole(role) {
  return PRODUCTION_TOKEN_CEILINGS[role] ?? PRODUCTION_TOKEN_CEILINGS.character;
}

/**
 * Reference-only kind quota for catalog/telemetry.
 * @returns {number | null} null when historically UNCAPPED
 */
export function referenceTokenCeilingForInferenceKind(inferenceKind) {
  if (UNCAPPED_INFERENCE_KINDS.has(inferenceKind)) {
    return null;
  }
  const ceiling = PRODUCTION_INFERENCE_KIND_TOKEN_CEILINGS[inferenceKind];
  return Number.isFinite(ceiling) ? ceiling : null;
}

/** Per-role reasoning: internal defaults; optional API global override for director/character only. */
export function resolveReasoningEffortForRole(role, settings = {}) {
  const advanced = settings.roleRouting === 'advanced' && settings.roleProfiles?.[role];
  if (advanced?.reasoningEffort != null && String(advanced.reasoningEffort).trim() !== '') {
    return advanced.reasoningEffort;
  }
  const global = settings.reasoningEffort ?? settings.reasoning_effort;
  if (
    global
    && settings.roleRouting !== 'advanced'
    && (role === 'director' || role === 'character')
  ) {
    return global;
  }
  return ROLE_REASONING_DEFAULTS[role] ?? 'low';
}

/** Enforced runtime ceiling; null while APPLICATION_TOKEN_QUOTAS_ENFORCED is false. */
export function tokenCeilingForRole(role, settings = {}, options = {}) {
  assertMutuallyExclusiveInferenceModes(settings, options);
  if (!APPLICATION_TOKEN_QUOTAS_ENFORCED) {
    return null;
  }
  if (characterizationModeEnabled(settings, options)) {
    return null;
  }
  if (calibrationModeEnabled(settings, options)) {
    return DIAGNOSTIC_TOKEN_CEILING;
  }
  const advanced = settings.roleRouting === 'advanced' && settings.roleProfiles?.[role];
  if (advanced?.maxTokens !== undefined) {
    return advanced.maxTokens;
  }
  const legacyKey = role === 'narrator' || role === 'opening'
    ? settings.narratorMaxTokens ?? settings.narrator_max_tokens
    : settings.maxTokens ?? settings.max_tokens;
  if (legacyKey !== undefined && Number.isFinite(Number(legacyKey))) {
    return Number(legacyKey);
  }
  return referenceTokenCeilingForRole(role);
}

/** Enforced runtime kind ceiling; null while APPLICATION_TOKEN_QUOTAS_ENFORCED is false. */
export function tokenCeilingForInferenceKind(inferenceKind, settings = {}, options = {}) {
  assertMutuallyExclusiveInferenceModes(settings, options);
  if (!APPLICATION_TOKEN_QUOTAS_ENFORCED) {
    return null;
  }
  if (characterizationModeEnabled(settings, options)) {
    return null;
  }
  if (calibrationModeEnabled(settings, options)) {
    return DIAGNOSTIC_TOKEN_CEILING;
  }
  return referenceTokenCeilingForInferenceKind(inferenceKind);
}

/** Apply operation-specific profile overrides; HG maxTokens always stripped when quotas disabled. */
export function modelProfileForInferenceKind(modelProfile, inferenceKind, settings = {}, options = {}) {
  if (!modelProfile || !inferenceKind || modelProfile.kind === 'mock') {
    return modelProfile;
  }
  assertMutuallyExclusiveInferenceModes(settings, options);
  const reasoningOverride = PRODUCTION_INFERENCE_KIND_REASONING_OVERRIDES[inferenceKind];
  if (!APPLICATION_TOKEN_QUOTAS_ENFORCED) {
    return stripApplicationMaxTokens({
      ...modelProfile,
      ...(reasoningOverride !== undefined ? { reasoningEffort: reasoningOverride } : {}),
    });
  }
  if (characterizationModeEnabled(settings, options)) {
    return stripApplicationMaxTokens({
      ...modelProfile,
      ...(reasoningOverride !== undefined ? { reasoningEffort: reasoningOverride } : {}),
    });
  }
  if (UNCAPPED_INFERENCE_KINDS.has(inferenceKind)) {
    const { maxTokens: _removed, ...rest } = modelProfile;
    return {
      ...rest,
      ...(reasoningOverride !== undefined ? { reasoningEffort: reasoningOverride } : {}),
    };
  }
  const ceiling = tokenCeilingForInferenceKind(inferenceKind, settings, options);
  if (!Number.isFinite(ceiling) && reasoningOverride === undefined) {
    return modelProfile;
  }
  return {
    ...modelProfile,
    ...(Number.isFinite(ceiling) ? { maxTokens: ceiling } : {}),
    ...(reasoningOverride !== undefined ? { reasoningEffort: reasoningOverride } : {}),
  };
}

function liveProfileForRole(role, settings = {}, options = {}) {
  const advanced = settings.roleRouting === 'advanced' && settings.roleProfiles?.[role];
  if (advanced) {
    const profile = {
      ...deepseekInferenceProfile({
        model: advanced.model ?? settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
        reasoningEffort: resolveReasoningEffortForRole(role, settings),
        ...(Number.isFinite(tokenCeilingForRole(role, settings, options))
          ? { maxTokens: tokenCeilingForRole(role, settings, options) }
          : {}),
      }),
      ...advanced,
      kind: advanced.kind ?? 'dsh',
    };
    return stripApplicationMaxTokens(profile);
  }
  const ceiling = tokenCeilingForRole(role, settings, options);
  return stripApplicationMaxTokens(deepseekInferenceProfile({
    model: settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
    reasoningEffort: resolveReasoningEffortForRole(role, settings),
    ...(Number.isFinite(ceiling) ? { maxTokens: ceiling } : {}),
  }));
}

export function defaultRuntimeSettings(options = {}) {
  const inferenceMode = options.inferenceMode ?? DEFAULT_RUNTIME_SETTINGS.inferenceMode;
  if (inferenceMode === 'mock') {
    return {
      ...DEFAULT_RUNTIME_SETTINGS,
      inferenceMode: 'mock',
      roleRouting: 'simple',
    };
  }
  return { ...DEFAULT_RUNTIME_SETTINGS, inferenceMode: 'live' };
}

export function validateSessionSetup(input = {}) {
  const errors = [];
  const characters = input.characters ?? input.character_ids ?? [];
  const playerCharacterFileId =
    input.player_character_file_id ?? input.playerCharacterFileId ?? null;
  if (playerCharacterFileId) {
    const fileId = String(playerCharacterFileId).trim();
    if (characters.length && !characters.includes(fileId)) {
      errors.push('player_character_file_id must be one of the selected characters');
    }
  }
  const persona = String(input.user_persona_id ?? input.userPersonaId ?? 'Player').trim();
  if (!persona) {
    errors.push('user_persona_id is required');
  }
  const scope = input.memory_scope_id ?? input.memoryScopeId;
  if (scope && !/^hg-memory-scope-[0-9a-f-]{36}$/i.test(String(scope).trim())) {
    errors.push('memory_scope_id must match hg-memory-scope-{uuid}');
  }
  return { valid: errors.length === 0, errors };
}

export function validateRuntimeSettings(input = {}) {
  const errors = [];
  const reasoning = input.reasoningEffort ?? input.reasoning_effort;
  if (reasoning !== undefined && reasoning !== null && String(reasoning).trim() !== '') {
    const level = String(reasoning);
    if (!REASONING_LEVELS.includes(level)) {
      errors.push(`reasoningEffort must be one of: ${REASONING_LEVELS.join(', ')}`);
    }
  }
  const roleRouting = String(input.roleRouting ?? input.role_routing ?? 'simple');
  if (!['simple', 'advanced'].includes(roleRouting)) {
    errors.push('roleRouting must be simple or advanced');
  }
  const maxTokens = input.maxTokens ?? input.max_tokens;
  if (maxTokens !== undefined && maxTokens !== null && maxTokens !== '') {
    const n = Number(maxTokens);
    if (!Number.isFinite(n) || n < 64 || n > 8192) {
      errors.push('maxTokens must be between 64 and 8192');
    }
  }
  return { valid: errors.length === 0, errors };
}

export function resolveApplicationRoleProfiles(settings = {}, options = {}) {
  if ((settings.inferenceMode ?? options.inferenceMode) === 'mock') {
    const mock = mockInferenceProfile();
    return {
      director: mock,
      character: mock,
      narrator: mock,
      opening: mock,
      semantic_evaluator: mock,
      storyteller: mock,
    };
  }

  return {
    director: liveProfileForRole('director', settings, options),
    character: liveProfileForRole('character', settings, options),
    narrator: liveProfileForRole('narrator', settings, options),
    opening: liveProfileForRole('opening', settings, options),
    semantic_evaluator: liveProfileForRole('semantic_evaluator', settings, options),
    storyteller: liveProfileForRole('storyteller', settings, options),
  };
}

export function buildInferenceOptions(settings = {}, options = {}) {
  const inferenceMode =
    settings.inferenceMode ?? options.inferenceMode ?? DEFAULT_RUNTIME_SETTINGS.inferenceMode;
  const runtime = { ...defaultRuntimeSettings({ inferenceMode }), ...settings, inferenceMode };
  const roleProfiles = resolveApplicationRoleProfiles(runtime, { inferenceMode });
  return {
    inferenceMode: runtime.inferenceMode,
    roleProfiles,
    liveMaxAttempts: runtime.liveMaxAttempts,
    model: runtime.model,
    roleRouting: runtime.roleRouting,
    inferenceCalibration: calibrationModeEnabled(runtime, options),
    inferenceCharacterization: characterizationModeEnabled(runtime, options),
    applicationTokenQuotasEnforced: APPLICATION_TOKEN_QUOTAS_ENFORCED,
  };
}

export function settingsView(runtimeSettings = {}) {
  return {
    runtime: { ...defaultRuntimeSettings(), ...runtimeSettings },
    role_profiles: resolveApplicationRoleProfiles(runtimeSettings),
    role_reasoning_defaults: { ...ROLE_REASONING_DEFAULTS },
    production_token_ceilings: { ...PRODUCTION_TOKEN_CEILINGS },
    application_token_quotas_enforced: APPLICATION_TOKEN_QUOTAS_ENFORCED,
  };
}
