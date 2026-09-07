import { bridgeManifestFromHostPrepare } from './bridge-manifest.mjs';

/** Test/mock compatibility only — canonical authority is Host `storyteller_orientation_response_contract`. */
export const STORYTELLER_ORIENTATION_SCHEMA = 'hg_storyteller_orientation_v1';

export function manifestFromStorytellerPrepareResponse(prepareResponse) {
  return bridgeManifestFromHostPrepare(
    prepareResponse,
    prepareResponse.contributions ?? [],
  );
}
