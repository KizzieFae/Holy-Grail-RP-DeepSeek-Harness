import {
  deepseekInferenceProfile,
  HG_DEEPSEEK_DEFAULT_MODEL,
  mockInferenceProfile,
  resolveRoleProfiles,
} from '../lib/inference-profile.mjs';

export const REASONING_LEVELS = ['off', 'low', 'high', 'max'];

export const DEFAULT_RUNTIME_SETTINGS = {
  inferenceMode: 'live',
  reasoningEffort: 'low',
  roleRouting: 'simple',
  model: HG_DEEPSEEK_DEFAULT_MODEL,
  maxTokens: 768,
  narratorMaxTokens: 384,
  liveMaxAttempts: 5,
};

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
  const reasoning = String(input.reasoningEffort ?? input.reasoning_effort ?? 'low');
  if (!REASONING_LEVELS.includes(reasoning)) {
    errors.push(`reasoningEffort must be one of: ${REASONING_LEVELS.join(', ')}`);
  }
  const roleRouting = String(input.roleRouting ?? input.role_routing ?? 'simple');
  if (!['simple', 'advanced'].includes(roleRouting)) {
    errors.push('roleRouting must be simple or advanced');
  }
  const maxTokens = Number(input.maxTokens ?? input.max_tokens ?? DEFAULT_RUNTIME_SETTINGS.maxTokens);
  if (!Number.isFinite(maxTokens) || maxTokens < 64 || maxTokens > 8192) {
    errors.push('maxTokens must be between 64 and 8192');
  }
  return { valid: errors.length === 0, errors };
}

function baseLiveProfile(settings) {
  return deepseekInferenceProfile({
    model: settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
    reasoningEffort: settings.reasoningEffort ?? 'low',
    maxTokens: settings.maxTokens ?? DEFAULT_RUNTIME_SETTINGS.maxTokens,
  });
}

export function resolveApplicationRoleProfiles(settings = {}, options = {}) {
  if ((settings.inferenceMode ?? options.inferenceMode) === 'mock') {
    const mock = mockInferenceProfile();
    return {
      director: mock,
      character: mock,
      narrator: mock,
      opening: mock,
    };
  }

  const roleRouting = settings.roleRouting ?? 'simple';
  if (roleRouting === 'advanced' && settings.roleProfiles) {
    const grouped = settings.roleProfiles;
    const fallback = baseLiveProfile(settings);
    return {
      director: grouped.director ?? fallback,
      character: grouped.character ?? fallback,
      narrator: grouped.narrator
        ?? deepseekInferenceProfile({
          model: grouped.narrator?.model ?? settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
          reasoningEffort: 'off',
          maxTokens: settings.narratorMaxTokens ?? DEFAULT_RUNTIME_SETTINGS.narratorMaxTokens,
        }),
      opening: grouped.opening
        ?? deepseekInferenceProfile({
          model: settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
          reasoningEffort: 'off',
          maxTokens: settings.narratorMaxTokens ?? DEFAULT_RUNTIME_SETTINGS.narratorMaxTokens,
        }),
    };
  }

  const shared = baseLiveProfile(settings);
  const narrator = deepseekInferenceProfile({
    model: settings.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
    reasoningEffort: 'off',
    maxTokens: settings.narratorMaxTokens ?? DEFAULT_RUNTIME_SETTINGS.narratorMaxTokens,
  });
  return {
    director: shared,
    character: shared,
    narrator,
    opening: narrator,
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
    reasoningEffort: runtime.reasoningEffort,
    model: runtime.model,
    roleRouting: runtime.roleRouting,
  };
}

export function settingsView(runtimeSettings = {}) {
  return {
    runtime: { ...defaultRuntimeSettings(), ...runtimeSettings },
    role_profiles: resolveApplicationRoleProfiles(runtimeSettings),
  };
}
