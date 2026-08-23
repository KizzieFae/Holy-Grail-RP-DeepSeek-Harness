/** Mirror of Domain Host `project_history_to_transcript` for client-side use if needed. */
export function projectHistoryToTranscript(entries = []) {
  const presentationsByCommit = new Map(
    entries
      .filter((entry) => entry.kind === 'presentation' && entry.domain_commit_id)
      .map((entry) => [entry.domain_commit_id, entry]),
  );
  const transcript = [];

  for (const entry of entries) {
    if (entry.kind === 'user') {
      transcript.push({
        role: 'user',
        content: entry.content,
        speaker: entry.actor_id || entry.metadata?.speaker || 'Player',
        entry_id: entry.entry_id,
        sequence_index: entry.sequence_index,
      });
      continue;
    }
    if (entry.kind === 'player_skip') {
      transcript.push({
        role: 'assistant',
        content: entry.content,
        speaker: entry.actor_id || entry.metadata?.speaker || 'Player',
        entry_id: entry.entry_id,
        sequence_index: entry.sequence_index,
        player_skip: true,
      });
      continue;
    }
    if (entry.kind === 'presentation') {
      transcript.push({
        role: 'assistant',
        content: entry.content,
        speaker: entry.actor_id || 'Narrator',
        entry_id: entry.entry_id,
        sequence_index: entry.sequence_index,
        domain_commit_id: entry.domain_commit_id,
        presentation_failed: entry.presentation_status === 'failed',
      });
      continue;
    }
    if (entry.kind === 'committed_turn') {
      if (entry.domain_commit_id && presentationsByCommit.has(entry.domain_commit_id)) {
        continue;
      }
      transcript.push({
        role: 'assistant',
        content: entry.content,
        speaker: entry.actor_id || 'Character',
        entry_id: entry.entry_id,
        sequence_index: entry.sequence_index,
        domain_commit_id: entry.domain_commit_id,
        presentation_failed: true,
      });
    }
  }

  return transcript;
}
