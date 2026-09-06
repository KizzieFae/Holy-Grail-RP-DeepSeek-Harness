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
  const fromManifest = manifest?.inference_kind;
  if (fromManifest) return resolveInferenceKind(String(fromManifest));
  if (inferenceKind) return resolveInferenceKind(String(inferenceKind));
  return null;
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
