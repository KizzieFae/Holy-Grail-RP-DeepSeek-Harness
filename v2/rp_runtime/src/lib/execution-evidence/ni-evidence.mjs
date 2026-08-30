/**
 * NI forensic evidence helpers (#45).
 * Observational only — not Continuity authority.
 */

export const NI_FORENSICS_CONTRACT = 'hg_ni_forensics_v1';

const CATALOG_CONTRIBUTION_SUFFIX = '-catalog';

/**
 * @param {object|null} request
 * @returns {{ catalogContributionId: string|null, catalogSourceIds: string[] }}
 */
export function extractMediationCatalogFromRequest(request) {
  const contributions = request?.contributions ?? [];
  const catalogContribution = contributions.find(
    (item) => String(item?.contribution_id ?? '').endsWith(CATALOG_CONTRIBUTION_SUFFIX)
      || String(item?.provenance?.catalog_count ?? '') !== '',
  ) ?? contributions.find(
    (item) => String(item?.content ?? '').includes('Eligible mediation catalog'),
  );
  if (!catalogContribution) {
    return { catalogContributionId: null, catalogSourceIds: [] };
  }
  const knowledgeIds = catalogContribution.knowledge_ids ?? catalogContribution.knowledgeIds ?? [];
  const catalogSourceIds = [...knowledgeIds].map((id) => String(id)).filter(Boolean);
  return {
    catalogContributionId: catalogContribution.contribution_id
      ?? catalogContribution.contributionId
      ?? null,
    catalogSourceIds,
  };
}

/**
 * @param {object[]} selectedItems
 * @returns {string[]}
 */
export function selectedSourceIdsFromMediationResult(selectedItems = []) {
  return selectedItems
    .map((item) => String(item?.source_id ?? '').trim())
    .filter(Boolean);
}

/**
 * @param {object} bundle
 * @returns {{ sourceIdToEntryId: Record<string, string>, bundleEntryIds: string[] }}
 */
export function sourceIdToEntryIdFromBundle(bundle) {
  const sourceIdToEntryId = {};
  const bundleEntryIds = [];
  for (const entry of bundle?.entries ?? []) {
    const entryId = String(entry?.entry_id ?? '').trim();
    if (entryId) bundleEntryIds.push(entryId);
    const catalogSourceId = entry?.provenance?.catalog_source_id
      ?? entry?.ref?.display_hint
      ?? null;
    if (catalogSourceId && entryId) {
      sourceIdToEntryId[String(catalogSourceId)] = entryId;
    }
  }
  return { sourceIdToEntryId, bundleEntryIds };
}

/**
 * @param {object} prepareResponse
 * @returns {object[]}
 */
export function normalizeRetrievalDisposition(prepareResponse) {
  const raw = prepareResponse?.retrieval_disposition ?? [];
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => ({
    request_id: item.request_id ?? null,
    candidate_ids_returned: [...(item.candidate_ids_returned ?? [])],
    diagnostics: { ...(item.diagnostics ?? {}) },
    retrieval_omitted: Boolean(item.retrieval_omitted),
  }));
}

export function buildCharacterOrientationDecisionPatch({
  accepted,
  reason = null,
  reuseKey = null,
  knowledgeAccessRequestId = null,
  upstreamFingerprint = null,
}) {
  return {
    decision: {
      character_orientation: {
        accepted: Boolean(accepted),
        reason: reason ?? null,
        reuse_key: reuseKey ?? null,
        knowledge_access_request_id: knowledgeAccessRequestId ?? null,
        upstream_fingerprint: upstreamFingerprint ?? null,
      },
    },
  };
}

export function buildLibrarianMediationDecisionPatch({
  prepareResponse,
  parsedResult,
  bundle,
  hostAccepted,
  hostReason = null,
  hostRejectionCodes = [],
  mediationMode = null,
}) {
  const catalogFromPrepare = (prepareResponse?.mediation_catalog ?? [])
    .map((item) => String(item?.source_id ?? '').trim())
    .filter(Boolean);
  const manifestId = prepareResponse?.manifest_id ?? null;
  const catalogContributionId = manifestId ? `${manifestId}-catalog` : null;
  const catalogSourceIds = catalogFromPrepare.length
    ? catalogFromPrepare
    : extractMediationCatalogFromRequest({
      contributions: prepareResponse?.contributions ?? [],
    }).catalogSourceIds;
  const selectedSourceIds = selectedSourceIdsFromMediationResult(
    parsedResult?.selected_items ?? [],
  );
  const { sourceIdToEntryId, bundleEntryIds } = sourceIdToEntryIdFromBundle(bundle ?? {});
  const budgetAccounting = bundle?.budget_accounting ?? {};
  return {
    decision: {
      librarian_mediation: {
        catalog_contribution_id: catalogContributionId,
        catalog_source_ids: catalogSourceIds,
        selected_source_ids: selectedSourceIds,
        retrieval_request_ids: [...(prepareResponse?.retrieval_request_ids ?? [])],
        retrieval_disposition: normalizeRetrievalDisposition(prepareResponse),
        bundle_id: bundle?.bundle_id ?? null,
        bundle_entry_ids: bundleEntryIds,
        bundle_entries_truncated: Number(budgetAccounting.entries_truncated ?? 0),
        source_id_to_entry_id: sourceIdToEntryId,
        mediation_mode: mediationMode ?? bundle?.mediation_mode ?? null,
        host_accepted: Boolean(hostAccepted),
        host_reason: hostReason ?? null,
        host_rejection_codes: [...(hostRejectionCodes ?? [])],
      },
    },
  };
}

export function buildStorytellerOrientationDecisionPatch({
  accepted,
  reason = null,
}) {
  return {
    decision: {
      storyteller_orientation: {
        accepted: Boolean(accepted),
        reason: reason ?? null,
      },
    },
  };
}

export function buildStorytellerAdvisoryDecisionPatch({
  assessmentAccepted,
  assessmentReason = null,
  packageId = null,
  bindAccepted = null,
  bindRejectionReason = null,
  degradationLevel = null,
  invalidated = false,
  invalidationReason = null,
}) {
  const patch = {
    decision: {
      storyteller_advisory: {
        assessment_accepted: Boolean(assessmentAccepted),
        assessment_reason: assessmentReason ?? null,
        package_id: packageId ?? null,
        degradation_level: degradationLevel ?? null,
        invalidated: Boolean(invalidated),
        invalidation_reason: invalidationReason ?? null,
      },
    },
  };
  if (bindAccepted !== null && bindAccepted !== undefined) {
    patch.decision.storyteller_advisory.bind_accepted = Boolean(bindAccepted);
    patch.decision.storyteller_advisory.bind_rejection_reason = bindRejectionReason ?? null;
  }
  return patch;
}

export function buildLibrarianProposalDecisionPatch({
  batch,
  proposalContentHash = null,
  characterMoveEvidenceId = null,
  contractLineage = null,
  structuralParseError = null,
  proposalGenerationStage = null,
  proposalGenerationFailure = null,
}) {
  const hostValidation = batch?.host_validation ?? batch?.audit?.host_validation ?? {};
  const continuity = batch?.continuity_decision
    ?? batch?.continuityDecision
    ?? batch?.audit?.continuity_decision
    ?? null;
  const batchId = batch?.batch_id
    ?? batch?.librarian_proposal_batch_id
    ?? batch?.audit?.batch_id
    ?? null;
  const domainCommitId = batch?.domain_commit_id
    ?? batch?.audit?.domain_commit_id
    ?? null;
  const itemDispositions = (continuity?.item_decisions ?? batch?.item_dispositions ?? [])
    .slice(0, 64)
    .map((item) => ({
      proposal_id: item.proposal_id ?? item.proposalId ?? null,
      outcome: item.outcome ?? item.decision ?? null,
      reason_code: item.reason_code ?? item.reason ?? null,
    }));
  return {
    decision: {
      librarian_proposal: {
        batch_id: batchId,
        host_accepted: Boolean(hostValidation.accepted ?? batch?.host_accepted),
        host_rejection_codes: [
          ...(hostValidation.rejection_codes ?? batch?.host_rejection_codes ?? []),
        ],
        orchestration_status: batch?.orchestration_status ?? null,
        continuity_accepted_count: continuity?.accepted_count
          ?? batch?.continuity_accepted_count
          ?? 0,
        continuity_rejected_count: continuity?.rejected_count
          ?? batch?.continuity_rejected_count
          ?? 0,
        durable_mutation_applied: Boolean(
          batch?.durable_mutation_applied ?? batch?.librarian_proposal_durable_mutation_applied,
        ),
        item_dispositions: itemDispositions,
        proposal_content_hash: proposalContentHash ?? null,
        proposal_generation_failure: proposalGenerationFailure
          ?? batch?.proposal_generation_failure
          ?? null,
        structural_parse_error: structuralParseError ?? null,
        proposal_generation_stage: proposalGenerationStage ?? null,
        contract_correction_used: contractLineage?.correction_used === true,
        contract_lineage: contractLineage ?? null,
      },
    },
    associations: {
      domain_commit_id: domainCommitId,
      character_move_evidence_id: characterMoveEvidenceId ?? null,
    },
  };
}

export function buildPackagingDispositionAssociation({
  bundleId = null,
  packageId = null,
  sourceNiEvidenceId = null,
  storytellerAssessmentEvidenceId = null,
  packagingResult = null,
  mappedContributions = [],
}) {
  const mappedEntryIds = packagingResult?.mapped_entry_ids
    ?? packagingResult?.mappedEntryIds
    ?? [];
  const mappedContributionIds = (mappedContributions.length
    ? mappedContributions
    : (packagingResult?.contributions ?? []))
    .map((c) => String(c?.contribution_id ?? c?.contributionId ?? ''))
    .filter(Boolean);
  return {
    associations: {
      librarian_mediation_evidence_id: sourceNiEvidenceId ?? null,
      storyteller_assessment_evidence_id: storytellerAssessmentEvidenceId ?? null,
      packaging_disposition: {
        bundle_id: bundleId ?? null,
        package_id: packageId ?? null,
        entries_considered: Number(packagingResult?.entries_considered ?? 0),
        entries_mapped: Number(packagingResult?.entries_mapped ?? 0),
        mapped_entry_ids: [...mappedEntryIds],
        mapped_contribution_ids: mappedContributionIds,
        omitted_reason: packagingResult?.omitted_reason ?? null,
      },
    },
  };
}

/**
 * Derive omission at Librarian mediation boundary.
 * @param {string[]} catalogSourceIds
 * @param {string[]} selectedSourceIds
 * @param {string} candidateId - retrieval candidate_id (not source_id)
 */
export function librarianOmittedCandidateId(catalogSourceIds, selectedSourceIds, candidateId) {
  const sourceId = `lmi:cand:${candidateId}`;
  if (!catalogSourceIds.includes(sourceId)) return null;
  if (selectedSourceIds.includes(sourceId)) return null;
  return candidateId;
}

export function extractLibrarianPackagingAuditFromManifest(manifest) {
  const contributions = manifest?.contributions ?? [];
  const instruction = contributions.find(
    (item) => String(item?.source_kind ?? '') === 'inference_instruction',
  );
  const audit = instruction?.provenance?.librarian_knowledge_audit ?? {};
  const mappedContributionIds = contributions
    .filter((item) => String(item?.source_kind ?? '').startsWith('librarian'))
    .map((item) => String(item.contribution_id ?? item.contributionId ?? ''))
    .filter(Boolean);
  return {
    bundle_id: audit.bundle_id ?? null,
    entries_considered: Number(audit.entries_considered ?? 0),
    entries_mapped: Number(audit.entries_mapped ?? mappedContributionIds.length),
    omitted_reason: audit.omitted_reason ?? null,
    mapped_contribution_ids: mappedContributionIds,
    eligibility_accepted: audit.eligibility_accepted ?? null,
  };
}

export function extractStorytellerPackagingAuditFromManifest(manifest) {
  const contributions = manifest?.contributions ?? [];
  const storytellerContributions = contributions.filter(
    (item) => String(item?.source_kind ?? '').startsWith('storyteller_'),
  );
  const packageId = storytellerContributions
    .map((item) => item?.provenance?.package_id)
    .find(Boolean) ?? null;
  const mappedContributionIds = storytellerContributions
    .map((item) => String(item.contribution_id ?? item.contributionId ?? ''))
    .filter(Boolean);
  return {
    package_id: packageId,
    entries_considered: storytellerContributions.length,
    entries_mapped: mappedContributionIds.length,
    omitted_reason: mappedContributionIds.length ? null : 'no_storyteller_contributions',
    mapped_contribution_ids: mappedContributionIds,
  };
}

export function patchConsumerNiPackaging(recorder, {
  hgSessionId,
  evidenceId,
  cognitionAudit = null,
  manifest = null,
  storytellerAssessmentEvidenceId = null,
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !evidenceId) return;
  const librarianAudit = extractLibrarianPackagingAuditFromManifest(manifest);
  const storytellerAudit = extractStorytellerPackagingAuditFromManifest(manifest);
  const usesLibrarianPackaging = Boolean(
    cognitionAudit?.mediation_evidence_id ?? librarianAudit.bundle_id,
  );
  const packagingAudit = usesLibrarianPackaging ? librarianAudit : storytellerAudit;
  const patch = buildPackagingDispositionAssociation({
    bundleId: cognitionAudit?.librarian_bundle_id ?? librarianAudit.bundle_id,
    packageId: storytellerAudit.package_id,
    storytellerAssessmentEvidenceId,
    sourceNiEvidenceId: cognitionAudit?.mediation_evidence_id ?? storytellerAssessmentEvidenceId ?? null,
    packagingResult: packagingAudit,
    mappedContributions: packagingAudit.mapped_contribution_ids.map((id) => ({
      contribution_id: id,
    })),
  });
  recorder.patchDecision(evidenceId, hgSessionId, patch);
  if (cognitionAudit?.mediation_evidence_id) {
    recorder.linkNiAssociation(
      hgSessionId,
      cognitionAudit.mediation_evidence_id,
      evidenceId,
      {
        leftKey: 'consumer_evidence_id',
        rightKey: 'librarian_mediation_evidence_id',
      },
    );
  } else if (storytellerAssessmentEvidenceId) {
    recorder.linkNiAssociation(
      hgSessionId,
      storytellerAssessmentEvidenceId,
      evidenceId,
      {
        leftKey: 'consumer_evidence_id',
        rightKey: 'storyteller_assessment_evidence_id',
      },
    );
  }
}
