/** @typedef {import('./manifest-projection-policy.mjs').InferenceKind} InferenceKind */

import {
  assertValidModelContextPackage,
  resolveInferenceKind,
} from './manifest-projection-policy.mjs';

/**
 * @param {object|null|undefined} manifest
 * @param {string|undefined|null} inferenceKind
 */
export function resolveManifestInferenceKind(manifest, inferenceKind) {
  const contributions = manifest?.contributions ?? [];
  const hasManifestContract = Boolean(manifest?.manifest_id);
  const fromManifest = manifest?.inference_kind;
  const manifestKind = fromManifest ? resolveInferenceKind(String(fromManifest)) : null;
  const callerKind = inferenceKind ? resolveInferenceKind(String(inferenceKind)) : null;

  if (hasManifestContract) {
    if (!manifestKind) {
      throw new Error(
        'model-context package rejected: PromptContributionManifest missing required inference_kind',
      );
    }
    if (callerKind && callerKind !== manifestKind) {
      throw new Error(
        `model-context package rejected: inference_kind mismatch (manifest='${manifestKind}', caller='${callerKind}')`,
      );
    }
    return manifestKind;
  }

  if (!callerKind) {
    throw new Error('model-context package rejected: missing inference_kind');
  }
  return callerKind;
}

/**
 * Fail closed before any contribution registration (#134).
 *
 * @param {object|null|undefined} manifest
 * @param {string|undefined|null} inferenceKind
 */
export function validateBridgeManifest({ manifest, inferenceKind }) {
  const resolvedKind = resolveManifestInferenceKind(manifest, inferenceKind);
  if (!resolvedKind) {
    throw new Error('model-context package rejected: missing inference_kind');
  }
  const contributions = manifest?.contributions ?? [];
  assertValidModelContextPackage(resolvedKind, contributions);
  return resolvedKind;
}
