import { ASSEMBLED_REQUEST_SCHEMA } from './config.mjs';
import { mapReasoningEffortToProviderOptions } from '../reasoning-provider-options.mjs';

/**
 * Build the exact Holy-Grail-assembled model request at the inference boundary.
 *
 * @param {object} params
 * @param {object|null|undefined} params.manifest
 * @param {string} params.userInstruction
 * @param {string} params.systemPersona
 * @param {object} params.profile
 * @param {string|null|undefined} params.manifestId
 * @param {string[]} params.contributionIds
 */
export function buildAssembledRequest({
  manifest,
  userInstruction,
  systemPersona,
  profile,
  manifestId,
  contributionIds,
}) {
  const contributions = [...(manifest?.contributions ?? [])]
    .map((entry) => ({
      contribution_id: String(entry.contribution_id ?? ''),
      source_kind: String(entry.source_kind ?? ''),
      authority_class: String(entry.authority_class ?? ''),
      priority: Number(entry.priority ?? 0),
      content: String(entry.content ?? ''),
    }))
    .sort((left, right) => left.priority - right.priority);

  return {
    schema: ASSEMBLED_REQUEST_SCHEMA,
    system_persona: String(systemPersona ?? ''),
    contributions,
    user_instruction: { text: String(userInstruction ?? '') },
    inference_profile: (() => {
      const requested = profile?.reasoningEffort ?? profile?.reasoning_effort ?? null;
      const effective = mapReasoningEffortToProviderOptions(requested);
      const maxTokens = profile?.maxTokens ?? profile?.max_tokens;
      const configuredMaxTokens = Number.isFinite(Number(maxTokens)) && Number(maxTokens) > 0
        ? Number(maxTokens)
        : null;
      return {
        provider: profile?.provider ?? null,
        model: profile?.model ?? null,
        max_tokens: configuredMaxTokens,
        reasoning_effort: requested,
        effective_thinking: effective.thinking,
        effective_reasoning_effort: effective.reasoningEffort,
      };
    })(),
    manifest_id: manifestId ?? manifest?.manifest_id ?? null,
    contribution_ids: [...(contributionIds ?? [])],
  };
}
