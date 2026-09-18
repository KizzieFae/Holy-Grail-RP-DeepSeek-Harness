/**
 * Issue #201 R5 — G1/G2 establishment equivalence and entailment (deterministic).
 */
import { R5_SCHEMAS } from './issue201-r5-contract.mjs';
import { obligationById } from './issue201-r5-fixtures.mjs';

function normalize(text) {
  return String(text ?? '').toLowerCase();
}

export function proveEstablishmentEquivalence(fixture) {
  const est = fixture.establishment;
  const ob = obligationById(fixture, fixture.obligations[0].obligation_id);
  const sharedHaystack = normalize([
    est.shared_committed_presentation,
    est.character_move_dialogue,
    est.plot_scribe_source_excerpt,
  ].join('\n'));
  const obligationText = normalize(ob.semantic_content);
  const q = fixture.qualification;

  const requiredPresent = (q.establishment_entailment_required_phrases ?? []).every(
    (phrase) => sharedHaystack.includes(normalize(phrase)) && obligationText.includes(normalize(phrase)),
  );
  const forbiddenAbsent = (q.establishment_forbidden_extra_facts ?? []).every(
    (fact) => !obligationText.includes(normalize(fact)),
  );
  const plotUsesShared = normalize(est.plot_scribe_source_excerpt).length > 20;
  const armNeutral = est.arm_neutral === true;

  return {
    schema: R5_SCHEMAS.ESTABLISHMENT_EQUIVALENCE,
    g1_shared_establishment: requiredPresent && armNeutral && plotUsesShared,
    g2_entailment_no_extra_facts: requiredPresent && forbiddenAbsent,
    detail: {
      required_phrases_present: requiredPresent,
      forbidden_extra_absent: forbiddenAbsent,
      arm_neutral: armNeutral,
      shared_presentation: est.shared_committed_presentation,
      obligation_semantic: ob.semantic_content,
      plot_scribe_source: est.plot_scribe_source_excerpt,
    },
  };
}
