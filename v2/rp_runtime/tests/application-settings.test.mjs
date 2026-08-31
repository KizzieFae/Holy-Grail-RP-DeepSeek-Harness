import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildInferenceOptions,
  resolveApplicationRoleProfiles,
  validateRuntimeSettings,
  validateSessionSetup,
} from '../src/application/application-settings.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL, resolveRoleProfiles } from '../src/lib/inference-profile.mjs';

test('application settings: validate session setup rejects invalid player file', () => {
  const result = validateSessionSetup({
    characters: ['kizzie'],
    player_character_file_id: 'willow',
  });
  assert.equal(result.valid, false);
  assert.match(result.errors[0], /player_character_file_id/);
});

test('application settings: simple role routing shares director and character profile', () => {
  const profiles = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    reasoningEffort: 'high',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  });
  assert.equal(profiles.director.reasoningEffort, 'high');
  assert.equal(profiles.character.reasoningEffort, 'high');
  assert.equal(profiles.narrator.reasoningEffort, 'low');
  assert.equal(profiles.semantic_evaluator.reasoningEffort, 'off');
  assert.notEqual(profiles.director.maxTokens, profiles.narrator.maxTokens);
});

test('application settings: advanced role routing preserves distinct profiles', () => {
  const director = {
    kind: 'dsh',
    provider: 'deepseek-official',
    model: 'director-model',
    reasoningEffort: 'max',
    maxTokens: 900,
  };
  const character = {
    kind: 'dsh',
    provider: 'deepseek-official',
    model: 'character-model',
    reasoningEffort: 'low',
    maxTokens: 700,
  };
  const narrator = {
    kind: 'dsh',
    provider: 'deepseek-official',
    model: 'narrator-model',
    reasoningEffort: 'off',
    maxTokens: 200,
  };
  const profiles = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'advanced',
    roleProfiles: { director, character, narrator },
  });
  assert.equal(profiles.director.model, 'director-model');
  assert.equal(profiles.character.model, 'character-model');
  assert.equal(profiles.narrator.model, 'narrator-model');
});

test('application settings: buildInferenceOptions honors mock mode from options', () => {
  const options = buildInferenceOptions({}, { inferenceMode: 'mock' });
  assert.equal(options.inferenceMode, 'mock');
  assert.equal(options.roleProfiles.director.kind, 'mock');
  assert.equal(options.roleProfiles.storyteller.kind, 'mock');
  assert.equal(options.roleProfiles.storyteller.provider, 'hg-mock');
});

test('application settings: live role profiles include explicit non-mock storyteller', () => {
  const profiles = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  });
  assert.ok('storyteller' in profiles);
  assert.equal(profiles.storyteller.kind, 'dsh');
  assert.equal(profiles.storyteller.provider, 'deepseek-official');
  assert.notEqual(profiles.storyteller.provider, 'hg-mock');
  assert.equal(profiles.storyteller.reasoningEffort, 'low');
  assert.equal(profiles.storyteller.maxTokens, 4096);
});

test('application settings: buildInferenceOptions carries live storyteller profile', () => {
  const options = buildInferenceOptions({ inferenceMode: 'live' });
  assert.equal(options.roleProfiles.storyteller.kind, 'dsh');
  assert.equal(options.roleProfiles.storyteller.provider, 'deepseek-official');
});

test('application settings: runtime resolution preserves live storyteller from application profiles', () => {
  const appProfiles = buildInferenceOptions({ inferenceMode: 'live' }).roleProfiles;
  const resolved = resolveRoleProfiles({ roleProfiles: appProfiles }, {});
  assert.equal(resolved.storyteller.kind, 'dsh');
  assert.equal(resolved.storyteller.provider, 'deepseek-official');
  assert.notEqual(resolved.storyteller.provider, 'hg-mock');
});

test('application settings: validate runtime settings bounds', () => {
  assert.equal(validateRuntimeSettings({ reasoningEffort: 'low' }).valid, true);
  assert.equal(validateRuntimeSettings({ reasoningEffort: 'turbo' }).valid, false);
  assert.equal(validateRuntimeSettings({ maxTokens: 32 }).valid, false);
});
