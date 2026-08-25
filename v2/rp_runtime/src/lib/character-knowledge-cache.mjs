const cache = new Map();

export function getCharacterKnowledgeCacheEntry(reuseKey) {
  if (!reuseKey) return null;
  return cache.get(reuseKey) ?? null;
}

export function setCharacterKnowledgeCacheEntry(reuseKey, entry) {
  if (!reuseKey) return;
  cache.set(reuseKey, entry);
}

export function clearCharacterKnowledgeCacheForRound(hgRoundId) {
  for (const key of [...cache.keys()]) {
    if (key.includes(`round:${hgRoundId}`)) {
      cache.delete(key);
    }
  }
}

export function resetCharacterKnowledgeCacheForTests() {
  cache.clear();
}
