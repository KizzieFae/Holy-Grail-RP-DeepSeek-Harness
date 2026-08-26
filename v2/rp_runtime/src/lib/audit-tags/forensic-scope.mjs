import { isExecutionEvidenceEnabled } from '../execution-evidence/config.mjs';

/**
 * Best-effort forensic_scope enrichment for audit tags (#45).
 * Must never throw — tag creation is failure-independent.
 */
export function resolveTagForensicScope({
  hgSessionId,
  anchor,
  evidenceRecorder = null,
  evidenceIndex = null,
}) {
  const base = {
    hg_round_id: anchor?.hg_round_id ?? null,
    domain_commit_id: anchor?.domain_commit_id ?? null,
    entry_sequence_index: anchor?.sequence_index ?? null,
  };

  if (!isExecutionEvidenceEnabled()) {
    return {
      resolution_status: 'evidence_disabled',
      ...base,
    };
  }

  if (!evidenceRecorder?.isEnabled?.()) {
    return {
      resolution_status: 'evidence_unavailable',
      ...base,
    };
  }

  try {
    const index = evidenceIndex ?? evidenceRecorder.readIndex(hgSessionId);
    if (!index) {
      return {
        resolution_status: 'evidence_unavailable',
        ...base,
      };
    }

    const roundId = anchor?.hg_round_id;
    const commitId = anchor?.domain_commit_id;
    const ni = index.ni ?? {};
    const roundChains = roundId ? (ni.by_round?.[String(roundId)] ?? {}) : {};
    const commitChain = commitId ? (ni.by_commit?.[String(commitId)] ?? {}) : {};
    const evidenceEntryPoints = {
      storyteller_chain: {},
      character_chains: {},
      proposal_evidence_id: commitChain.proposal_evidence_id ?? null,
      move_evidence_id: commitChain.move_evidence_id ?? null,
    };

    for (const [parentInferenceId, kinds] of Object.entries(roundChains)) {
      if (kinds.storyteller_assessment) {
        evidenceEntryPoints.storyteller_chain.assessment_evidence_id = kinds.storyteller_assessment;
      }
      if (kinds.storyteller_orientation) {
        evidenceEntryPoints.storyteller_chain.orientation_evidence_id = kinds.storyteller_orientation;
      }
      if (kinds.librarian_mediation && parentInferenceId.includes('storyteller')) {
        evidenceEntryPoints.storyteller_chain.mediation_evidence_id = kinds.librarian_mediation;
      }
      if (parentInferenceId.includes('character') || kinds.character_move) {
        evidenceEntryPoints.character_chains[parentInferenceId] = {
          move_evidence_id: kinds.character_move ?? null,
          orientation_evidence_id: kinds.character_orientation ?? null,
          mediation_evidence_id: kinds.librarian_mediation ?? null,
        };
      }
    }

    const hasPointers = Boolean(
      evidenceEntryPoints.proposal_evidence_id
      || evidenceEntryPoints.move_evidence_id
      || evidenceEntryPoints.storyteller_chain.assessment_evidence_id
      || Object.keys(evidenceEntryPoints.character_chains).length,
    );

    return {
      resolution_status: hasPointers ? 'complete' : 'partial',
      resolved_at: new Date().toISOString(),
      ...base,
      evidence_entry_points: evidenceEntryPoints,
    };
  } catch (error) {
    return {
      resolution_status: 'resolution_failed',
      resolution_notes: String(error?.message ?? error ?? 'resolution_failed'),
      ...base,
    };
  }
}

export function enrichTagWithForensicScope(tag, forensicScope, evidenceRecorder, hgSessionId) {
  if (!forensicScope) return tag;
  const enriched = {
    ...tag,
    forensic_scope: forensicScope,
  };
  if (
    evidenceRecorder?.isEnabled?.()
    && hgSessionId
    && tag?.tag_id
    && forensicScope.resolution_status !== 'evidence_disabled'
  ) {
    try {
      evidenceRecorder.indexTagForensicScope(hgSessionId, tag.tag_id, forensicScope);
    } catch {
      // enrichment index is best-effort
    }
  }
  return enriched;
}
