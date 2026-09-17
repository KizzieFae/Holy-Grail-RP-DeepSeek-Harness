/**
 * Issue #201 LH-1B — R0–R5 causal stage classification.
 */
import { LH1B_R_STAGES } from './issue201-lh1b-contract.mjs';
import {
  extractLh0ObligationIdsFromManifest,
} from './issue201-lh0-consumer-evidence.mjs';
import { projectionSemanticAdequate } from './issue201-lh0-consumer-evidence.mjs';

export function classifyForkRStages({
  fork,
  storeSnapshot = null,
  projected = false,
  receivedIds = [],
  manifest = null,
  consumerUsed = false,
  decisionInfluenced = false,
  substrate = null,
}) {
  const obligationIds = fork?.obligation_ids ?? [];
  const stored = (storeSnapshot?.obligations ?? []).filter((o) => (
    obligationIds.includes(o.obligation_id)
  ));
  const generated = stored.length > 0;
  const persisted = stored.length > 0;
  const semanticReceipt = receivedIds.length > 0
    && projectionSemanticAdequate({ contributions: manifest?.contributions ?? [] });
  const r5 = decisionInfluenced && substrate?.persistence_unique === true;

  const reached = {
    R0_generated: generated,
    R1_projected: projected && generated,
    R2_semantically_received: semanticReceipt,
    R3_used: consumerUsed,
    R4_decision_influence: decisionInfluenced,
    R5_marginal_persistence_value: r5,
  };

  let highest = 'none';
  if (r5) highest = LH1B_R_STAGES[5];
  else if (decisionInfluenced) highest = LH1B_R_STAGES[4];
  else if (consumerUsed) highest = LH1B_R_STAGES[3];
  else if (semanticReceipt) highest = LH1B_R_STAGES[2];
  else if (projected && generated) highest = LH1B_R_STAGES[1];
  else if (generated) highest = LH1B_R_STAGES[0];

  return {
    stages: reached,
    highest_stage: highest,
    substrate_explained: decisionInfluenced && substrate?.persistence_unique !== true,
    marginal_persistence_value: r5,
  };
}

export function archaeologyStageFromRStages(rStages) {
  if (rStages?.stages?.R5_marginal_persistence_value) return 'marginal_persistence_value_demonstrated';
  if (rStages?.stages?.R4_decision_influence && rStages?.substrate_explained) {
    return 'influence_but_substrate_explained';
  }
  if (rStages?.stages?.R4_decision_influence) return 'influence_demonstrated';
  if (rStages?.stages?.R3_used) return 'use_without_demonstrated_influence';
  if (rStages?.stages?.R2_semantically_received) return 'receipt_without_use';
  if (rStages?.stages?.R1_projected) return 'projection_without_receipt';
  if (rStages?.stages?.R0_generated) return 'generated_only';
  return 'no_projection';
}

export function extractReceiptFromManifest(manifest) {
  const ids = extractLh0ObligationIdsFromManifest(manifest);
  const samples = (manifest?.contributions ?? [])
    .filter((c) => c?.provenance?.lh0_obligation_id)
    .map((c) => ({
      obligation_id: c.provenance.lh0_obligation_id,
      contribution_id: c.contribution_id,
      source_kind: c.source_kind,
      content: c.content,
      knowledge_ids: c.knowledge_ids ?? [],
    }));
  return { obligation_ids: ids, samples };
}
