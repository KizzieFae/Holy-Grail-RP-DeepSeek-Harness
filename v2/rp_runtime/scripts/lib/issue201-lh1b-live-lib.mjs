/**
 * Issue #201 LH-1B — live campaign runner (NOT authorized in implementation phase).
 * Exported for future live authorization only.
 */
import { buildLh1bCampaignPlan } from './issue201-lh1b-orchestrator.mjs';

export function describeLh1bLiveExecutionPlan() {
  const plan = buildLh1bCampaignPlan();
  return {
    authorized: false,
    sequences: plan.sequences.map((s) => ({
      blind_label: s.blind_label,
      arm: s.arm,
      turn_count: s.turn_count,
      fork_ids: s.fork_ids,
    })),
    note: 'Live execution requires separate Governance authorization.',
  };
}
