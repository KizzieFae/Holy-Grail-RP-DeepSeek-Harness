/**
 * Build observational anchor from a canonical rp_history entry.
 * @param {object} entry
 */
export function buildAnchorFromHistoryEntry(entry) {
  const kind = String(entry.kind ?? '');
  const opening = kind === 'opening';
  const playerSkip = kind === 'player_skip';
  let transcriptRole = 'assistant';
  if (kind === 'user') transcriptRole = 'user';

  let speaker = entry.actor_id || 'Player';
  if (kind === 'user') {
    speaker = entry.actor_id || entry.metadata?.speaker || 'Player';
  } else if (playerSkip) {
    speaker = entry.actor_id || entry.metadata?.speaker || 'Player';
  } else if (kind === 'presentation') {
    speaker = entry.actor_id || 'Narrator';
  } else if (kind === 'committed_turn') {
    speaker = entry.actor_id || 'Character';
  } else if (opening) {
    speaker = 'Narrator';
  }

  let presentationFailed = false;
  if (kind === 'presentation') {
    presentationFailed = entry.presentation_status === 'failed';
  } else if (kind === 'committed_turn') {
    presentationFailed = true;
  }

  return {
    kind: 'transcript_entry',
    entry_id: String(entry.entry_id),
    sequence_index: Number(entry.sequence_index),
    transcript_role: transcriptRole,
    speaker: String(speaker),
    hg_round_id: entry.hg_round_id ?? null,
    domain_commit_id: entry.domain_commit_id ?? null,
    opening,
    player_skip: playerSkip,
    presentation_failed: presentationFailed,
  };
}

/**
 * @param {object[]} entries
 * @param {string} entryId
 */
export function findHistoryEntryById(entries, entryId) {
  return entries.find((item) => String(item.entry_id) === String(entryId)) ?? null;
}
