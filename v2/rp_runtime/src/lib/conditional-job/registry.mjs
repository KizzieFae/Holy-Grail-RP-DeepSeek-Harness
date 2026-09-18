/**
 * Canonical semantic job kind registry (#215 Child B).
 * Single taxonomy authority — maps job_kind → inference operations (catalog).
 */

import { PRIMARY_RUNTIME_CATALOG } from '../../application/llm-call-catalog.mjs';

export const REGISTRY_SCHEMA = 'hg_semantic_job_kind_registry_v1';

/** @typedef {{ inference_kinds: string[], catalog_call_ids: string[], disposition_record_kinds?: string[], description: string }} RegistryEntry */

/** @type {Record<string, RegistryEntry>} */
export const SEMANTIC_JOB_KIND_REGISTRY = Object.freeze({
  knowledge_mediation: Object.freeze({
    description: 'Librarian contextual knowledge mediation (conditional tool).',
    inference_kinds: Object.freeze([
      'librarian_mediation',
      'librarian_mediation_contract_correction',
    ]),
    catalog_call_ids: Object.freeze([
      'librarian_mediation@character',
      'librarian_mediation@narrator',
      'librarian_mediation_contract_correction',
    ]),
  }),
  routing_selection: Object.freeze({
    description: 'Semantic routing / actor selection (legacy director_turn pathway; forensic wrap only).',
    inference_kinds: Object.freeze(['director_turn']),
    catalog_call_ids: Object.freeze(['director_turn']),
  }),
  semantic_quality_evaluation: Object.freeze({
    description: 'Bounded semantic QA/evaluation of another semantic job candidate.',
    inference_kinds: Object.freeze([
      'director_semantic_qa',
      'narrator_semantic_qa',
      'character_semantic_evaluation',
    ]),
    catalog_call_ids: Object.freeze([
      'director_semantic_qa',
      'narrator_semantic_qa',
      'character_semantic_evaluation',
    ]),
  }),
  post_commit_semantic: Object.freeze({
    description: 'Post-commit semantic overlay / issue-pressure (fire or eligibility skip).',
    inference_kinds: Object.freeze([
      'storyteller_post_commit_issue_pressure',
      'storyteller_post_commit_issue_pressure_contract_correction',
    ]),
    catalog_call_ids: Object.freeze([
      'storyteller_post_commit_issue_pressure',
      'storyteller_post_commit_issue_pressure_contract_correction',
    ]),
    disposition_record_kinds: Object.freeze(['post_commit_semantic_disposition']),
  }),
});

const CATALOG_KINDS = new Set(
  PRIMARY_RUNTIME_CATALOG.map((row) => row.canonical_inference_kind),
);

export function listSemanticJobKinds() {
  return Object.keys(SEMANTIC_JOB_KIND_REGISTRY);
}

export function getRegistryEntry(jobKind) {
  return SEMANTIC_JOB_KIND_REGISTRY[jobKind] ?? null;
}

export function inferenceKindAllowedForJobKind(jobKind, inferenceKind) {
  const entry = getRegistryEntry(jobKind);
  if (!entry || !inferenceKind) return false;
  if (entry.inference_kinds.includes(inferenceKind)) return true;
  if (entry.disposition_record_kinds?.includes(inferenceKind)) return true;
  return false;
}

/**
 * Deterministic registry validation (tests + CI).
 * @returns {{ ok: true } | { ok: false, errors: string[] }}
 */
export function validateSemanticJobRegistry() {
  const errors = [];
  const kindsSeen = new Set();
  for (const [jobKind, entry] of Object.entries(SEMANTIC_JOB_KIND_REGISTRY)) {
    if (kindsSeen.has(jobKind)) {
      errors.push(`duplicate job_kind ${jobKind}`);
    }
    kindsSeen.add(jobKind);
    for (const kind of entry.inference_kinds) {
      if (!CATALOG_KINDS.has(kind) && !entry.disposition_record_kinds?.includes(kind)) {
        errors.push(`${jobKind}: unknown inference_kind ${kind} (not in llm-call-catalog)`);
      }
    }
    for (const callId of entry.catalog_call_ids) {
      const row = PRIMARY_RUNTIME_CATALOG.find((item) => item.call_id === callId);
      if (!row) {
        errors.push(`${jobKind}: catalog_call_id ${callId} not found`);
        continue;
      }
      if (!entry.inference_kinds.includes(row.canonical_inference_kind)) {
        errors.push(
          `${jobKind}: call_id ${callId} kind ${row.canonical_inference_kind} not listed on job_kind`,
        );
      }
    }
  }
  return errors.length ? { ok: false, errors } : { ok: true };
}
