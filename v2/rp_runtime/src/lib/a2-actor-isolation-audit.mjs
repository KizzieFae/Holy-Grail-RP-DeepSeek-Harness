/**
 * Issue #201 G3-C — ActorContextPackage capture and private-knowledge isolation audit.
 */

function privateContentFromManifest(manifest) {
  if (!manifest?.contributions) return [];
  return manifest.contributions
    .filter((c) => c.source_kind === 'character_private')
    .map((c) => String(c.content ?? '').trim())
    .filter(Boolean);
}

function manifestSummary(manifest, characterId) {
  const contributions = manifest?.contributions ?? [];
  return {
    character_id: characterId,
    manifest_id: manifest?.manifest_id ?? null,
    contribution_source_kinds: [...new Set(contributions.map((c) => c.source_kind))],
    has_character_private: contributions.some((c) => c.source_kind === 'character_private'),
    has_director_scratch: contributions.some((c) => c.source_kind === 'director_scratch'),
    private_excerpt_hashes: privateContentFromManifest(manifest).map((t) => t.slice(0, 80)),
  };
}

/**
 * Capture prepareCharacterContext manifests for eligible actors (audit-only; no inference).
 */
export async function captureActorContextPackages({
  api,
  hgSceneId,
  hgRoundId,
  turnIndex,
  eligibleActors,
  characterRoles = {},
}) {
  const packages = [];
  for (const characterId of eligibleActors) {
    const manifest = await api.prepareCharacterContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: `g3c-audit-${characterId}`,
      character_id: characterId,
      role: characterRoles[characterId] ?? 'guest',
      turn_index: turnIndex,
      attempt_index: 0,
    });
    packages.push({
      character_id: characterId,
      manifest,
      summary: manifestSummary(manifest, characterId),
      private_content: privateContentFromManifest(manifest),
    });
  }
  return packages;
}

/**
 * Prove Character A private content does not appear in Character B manifest inputs.
 */
export function auditPrivateKnowledgeIsolation(actorPackages) {
  const leaks = [];
  const privateByActor = {};
  for (const pkg of actorPackages) {
    privateByActor[pkg.character_id] = pkg.private_content;
  }
  for (const observer of actorPackages) {
    const observerId = observer.character_id;
    const observerText = (observer.manifest?.contributions ?? [])
      .map((c) => String(c.content ?? ''))
      .join('\n');
    for (const [ownerId, secrets] of Object.entries(privateByActor)) {
      if (ownerId === observerId) continue;
      for (const secret of secrets) {
        if (!secret || secret.length < 12) continue;
        const fingerprint = secret.slice(0, 48);
        if (observerText.includes(fingerprint)) {
          leaks.push({
            leaked_from: ownerId,
            observed_in: observerId,
            fingerprint,
          });
        }
      }
    }
  }
  return {
    packages_audited: actorPackages.length,
    leak_count: leaks.length,
    leaks,
    pass: leaks.length === 0,
  };
}
