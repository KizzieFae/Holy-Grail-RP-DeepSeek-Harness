/**
 * Issue #201 LH-1A — checkpoint slice exporter (observation-only).
 */
import { LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';

export function buildCheckpointSlice({
  sequencePlan,
  checkpointId,
  turnRecords = [],
  obligationLedger = null,
}) {
  const checkpointTurn = sequencePlan.checkpoints[checkpointId];
  if (!checkpointTurn) throw new Error(`unknown checkpoint: ${checkpointId}`);
  const turnsUpTo = turnRecords.filter((t) => t.turn_index <= checkpointTurn);
  const activeThreads = turnsUpTo.map((t) => t.presentation_text ?? '').join(' ').slice(0, 2000);
  const dormantObligations = obligationLedger
    ? [...obligationLedger.obligations.values()].filter((o) => (
      o.lifecycle_state === 'DEFERRED_VALID' || (o.dormancy_turns ?? 0) >= 8
    )).map((o) => o.obligation_id)
    : sequencePlan.obligation_ids.filter((id) => id.includes('DORMANT') || id.includes('RESURFACE'));
  return {
    schema: LH1A_SCHEMAS.CHECKPOINT_SLICE,
    checkpoint_id: checkpointId,
    approx_turn: checkpointTurn,
    observation_only: true,
    mutates_story_state: false,
    blind_safe: true,
    active_threads_excerpt: activeThreads || '[synthetic checkpoint — no live presentation yet]',
    dormant_obligation_ids: dormantObligations,
    unresolved_promises: sequencePlan.obligation_ids.filter((id) => id.includes('PROMISE')),
    scene_at_checkpoint: sequencePlan.turns.find((t) => t.turn_index === checkpointTurn)?.scene_id ?? null,
    relationship_state_note: 'Captured at checkpoint for blind archaeology; does not influence runtime.',
    dark_tone_trajectory_note: 'Evaluator receives scenario tone contract separately.',
  };
}

export function buildAllCheckpointSlices(sequencePlan, options = {}) {
  return Object.keys(sequencePlan.checkpoints).map((id) => buildCheckpointSlice({
    sequencePlan,
    checkpointId: id,
    ...options,
  }));
}
