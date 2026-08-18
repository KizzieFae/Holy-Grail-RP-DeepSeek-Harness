/**
 * Request-boundary ingress: map user text to participation forced designation.
 * Mirrors V1 `detect_forced_speaker` intent without Streamlit session flags.
 */
export function detectForcedSpeaker(content, {
  participantNames = [],
  previousParticipantSpeaker = null,
  resolveDisplayName = (name) => name,
  characterFileIds = {},
} = {}) {
  if (!content || !participantNames.length) return null;

  const contentLower = String(content).toLowerCase();
  const mentioned = [];

  for (const name of participantNames) {
    const variants = new Set([
      String(name).toLowerCase(),
      String(name).toLowerCase().replace(/_/g, ' '),
    ]);
    const resolved = String(resolveDisplayName(name) || '').trim().toLowerCase();
    if (resolved) variants.add(resolved);
    const fileId = characterFileIds[name];
    if (fileId) {
      variants.add(String(fileId).toLowerCase());
      variants.add(String(fileId).toLowerCase().replace(/_/g, ' '));
    }

    const ordered = [...variants].filter(Boolean).sort((a, b) => b.length - a.length);
    for (const variant of ordered) {
      const pattern = new RegExp(`\\b${variant.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?:'s)?\\b`, 'i');
      const match = contentLower.match(pattern);
      if (match) {
        mentioned.push({ index: match.index ?? 0, name });
        break;
      }
    }
  }

  if (mentioned.length) {
    mentioned.sort((a, b) => a.index - b.index);
    return mentioned[mentioned.length - 1].name;
  }

  if (previousParticipantSpeaker) {
    if (
      participantNames.length === 2
      && /\b(friend|other\s+(?:woman|girl|one))\b/i.test(contentLower)
    ) {
      return participantNames.find((name) => name !== previousParticipantSpeaker) ?? null;
    }
    return previousParticipantSpeaker;
  }

  return null;
}
