/**
 * Closed-field transport adapter from Host prepare metadata to bridge-bound manifests (#138).
 *
 * Copies only PromptContributionManifest contract fields present on the Host response.
 * Does not validate policy or invent authority.
 */

const BRIDGE_MANIFEST_FIELDS = [
  'manifest_id',
  'inference_id',
  'inference_kind',
  'hg_scene_id',
  'hg_round_id',
  'role',
  'character_id',
  'turn_index',
  'attempt_index',
];

/**
 * @param {object|null|undefined} prepareResponse
 * @param {Array<object>|null|undefined} contributions
 * @returns {object}
 */
export function bridgeManifestFromHostPrepare(prepareResponse, contributions) {
  const source = prepareResponse?.manifest && typeof prepareResponse.manifest === 'object'
    ? prepareResponse.manifest
    : (prepareResponse ?? {});
  const manifest = {};
  for (const field of BRIDGE_MANIFEST_FIELDS) {
    if (source[field] !== undefined && source[field] !== null && source[field] !== '') {
      manifest[field] = source[field];
    }
  }
  if (contributions !== undefined) {
    manifest.contributions = contributions ?? [];
  } else if (source.contributions !== undefined) {
    manifest.contributions = source.contributions ?? [];
  } else {
    manifest.contributions = [];
  }
  return manifest;
}

/**
 * Normalize contribution objects for bridge registration without reordering.
 *
 * @param {Array<object>|null|undefined} contributions
 * @returns {Array<object>}
 */
export function normalizeBridgeContributions(contributions) {
  return (contributions ?? []).map((c) => ({
    contribution_id: c.contribution_id,
    source_kind: c.source_kind,
    authority_class: c.authority_class,
    priority: c.priority,
    content: c.content,
    knowledge_ids: c.knowledge_ids,
    provenance: c.provenance,
  }));
}
