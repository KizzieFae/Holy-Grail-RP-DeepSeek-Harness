import { ASSEMBLED_REQUEST_SCHEMA } from './config.mjs';

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
    inference_profile: {
      provider: profile?.provider ?? null,
      model: profile?.model ?? null,
      reasoning_effort: profile?.reasoningEffort ?? profile?.reasoning_effort ?? null,
    },
    manifest_id: manifestId ?? manifest?.manifest_id ?? null,
    contribution_ids: [...(contributionIds ?? [])],
  };
}
