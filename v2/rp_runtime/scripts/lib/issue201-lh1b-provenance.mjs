/**
 * Issue #201 LH-1B — provenance audit helpers for causal traces.
 */
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';
import { extractLh0ObligationIdsFromManifest } from './issue201-lh0-consumer-evidence.mjs';

export function buildLhProvenanceAuditBlock({
  obligationIds = [],
  projection = null,
  manifest = null,
  inferenceId = null,
  hgRoundId = null,
  domainCommitId = null,
  consumer = null,
}) {
  const receipt = extractLh0ObligationIdsFromManifest(manifest);
  const contributions = (manifest?.contributions ?? [])
    .filter((c) => c?.provenance?.lh0_obligation_id)
    .map((c) => ({
      contribution_id: c.contribution_id,
      source_kind: c.source_kind,
      obligation_id: c.provenance.lh0_obligation_id,
      knowledge_ids: c.knowledge_ids ?? [],
      content_preview: String(c.content ?? '').slice(0, 160),
    }));
  return {
    schema: 'issue201_lh_provenance_audit_v1',
    obligation_ids: obligationIds,
    projection_batch_id: projection?.batch_id ?? null,
    projection_binding_digest: projection?.binding_digest ?? null,
    inference_id: inferenceId,
    hg_round_id: hgRoundId,
    domain_commit_id: domainCommitId,
    consumer,
    received_obligation_ids: receipt,
    contributions,
  };
}

export function buildLh1bCausalTraceRow({
  turnIndex,
  hgRoundId,
  arm,
  characterTrace = null,
  directorTrace = null,
  forkEvaluations = [],
}) {
  return {
    schema: LH1B_SCHEMAS.CAUSAL_TRACE,
    turn_index: turnIndex,
    hg_round_id: hgRoundId,
    arm,
    character: characterTrace,
    director: directorTrace,
    fork_evaluations: forkEvaluations,
  };
}
