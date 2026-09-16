/**
 * Issue #201 LH-1A — narrative archaeology dossier exporter.
 */
import { LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';
import { loadLh1aFixtureManifest } from './issue201-lh1a-fixtures.mjs';

export function buildRetrievalSufficiencyVerdict({
  transcriptSufficient = false,
  retrievalSufficient = false,
  persistenceSuppliedInterpretation = false,
  persistenceDuplicatedAccessibleContext = false,
} = {}) {
  let marginal_value = 'indeterminate';
  if (persistenceDuplicatedAccessibleContext) marginal_value = 'duplicate_only';
  else if (transcriptSufficient || retrievalSufficient) {
    marginal_value = persistenceSuppliedInterpretation ? 'interpretation_beyond_retrieval' : 'retrieval_sufficient';
  } else if (persistenceSuppliedInterpretation) marginal_value = 'persistence_useful';
  return {
    transcript_sufficient: transcriptSufficient,
    retrieval_sufficient: retrievalSufficient,
    persistence_supplied_interpretation: persistenceSuppliedInterpretation,
    persistence_duplicated_accessible_context: persistenceDuplicatedAccessibleContext,
    marginal_value_attribution: marginal_value,
  };
}

export function buildMaterialObligationDossier({
  fixtureObligation,
  archaeologyRecord = null,
  ledgerEvents = [],
  retrievalVerdict = null,
}) {
  return {
    obligation_id: fixtureObligation.obligation_id,
    class: fixtureObligation.class,
    origin_turn: fixtureObligation.intro_turn,
    producer: fixtureObligation.provenance?.source ?? 'fixture_seed',
    persistence_mechanism: archaeologyRecord?.preservation_mechanism ?? 'continuity_only',
    dormancy_min_turns: fixtureObligation.dormancy_min_turns ?? null,
    scene_transitions_survived: fixtureObligation.class === 'cross_scene_continuity' ? 1 : 0,
    projection_events: archaeologyRecord?.projection_events ?? [],
    authorized_consumer: fixtureObligation.authorized_consumer,
    consumer_use: archaeologyRecord?.decision_influence ? 'demonstrated' : 'non_use_or_pending',
    activation_appropriateness: archaeologyRecord?.terminal_lifecycle_state ?? 'pending',
    payoff_quality: archaeologyRecord?.observable_consequence ? 'consequential' : 'pending',
    repetition_flag: ledgerEvents.filter((e) => e.event_type === 'resurfaced').length > 2,
    premature_activation: archaeologyRecord?.terminal_lifecycle_state === 'ACTIVATED_PREMATURE',
    dead_thread: archaeologyRecord?.terminal_lifecycle_state === 'TRACKED_DEAD',
    retrieval_sufficiency: retrievalVerdict ?? buildRetrievalSufficiencyVerdict(),
    semantic_content_forensic: fixtureObligation.semantic_content,
  };
}

export function buildArchaeologyDossier({ sequencePlan, ledger = null }) {
  const fixture = loadLh1aFixtureManifest(sequencePlan.scenario_key);
  const materialEvents = fixture.obligations.map((ob) => {
    const arch = ledger?.toArchaeologyRecord?.(ob.obligation_id) ?? null;
    const events = ledger?.events?.filter((e) => e.obligation_id === ob.obligation_id) ?? [];
    return buildMaterialObligationDossier({
      fixtureObligation: ob,
      archaeologyRecord: arch,
      ledgerEvents: events,
    });
  });
  return {
    schema: LH1A_SCHEMAS.ARCHAEOLOGY_DOSSIER,
    sequence_id: sequencePlan.sequence_id,
    scenario_key: sequencePlan.scenario_key,
    arm: sequencePlan.arm,
    material_events: materialEvents,
    observation_only: true,
    mutates_story_state: false,
    human_summary: `Archaeology dossier for ${fixture.obligations.length} material obligations.`,
  };
}
