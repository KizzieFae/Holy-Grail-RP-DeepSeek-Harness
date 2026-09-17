/**
 * Issue #201 LH-1B — archaeology exporter from live evidence sources.
 */
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';
import { obligationById, listLh1bDecisionForks } from './issue201-lh1b-fixtures.mjs';
import { archaeologyStageFromRStages } from './issue201-lh1b-causal-r0-r5.mjs';

export function buildLh1bMaterialObligationDossier({
  fixtureObligation,
  turnTraces = [],
  forkResults = [],
}) {
  const obligationId = fixtureObligation.obligation_id;
  const forkRows = forkResults.filter((f) => (f.obligation_ids ?? []).includes(obligationId));
  const projectionEvents = turnTraces
    .filter((t) => t?.lh1b_projection?.projected)
    .map((t) => ({
      turn_index: t.turn_index,
      projected: true,
      received: t.lh1b_projection?.consumer_received === true,
      consumer_used: t.lh1b_projection?.consumer_used === true,
      decision_influenced: t.lh1b_projection?.decision_influenced === true,
      hg_round_id: t.hg_round_id ?? null,
    }));
  const bestFork = forkRows[0] ?? null;
  const stage = bestFork?.r_stages
    ? archaeologyStageFromRStages(bestFork.r_stages)
    : (projectionEvents.some((e) => e.received) ? 'receipt_without_use' : 'no_projection');

  return {
    obligation_id: obligationId,
    class: fixtureObligation.class,
    origin_turn: fixtureObligation.intro_turn,
    authorized_consumer: fixtureObligation.authorized_consumer,
    projection_events: projectionEvents,
    archaeology_stage: stage,
    consumer_use: bestFork?.causal_evidence?.consumer_used ? 'demonstrated' : 'non_use_or_pending',
    decision_influence: bestFork?.causal_evidence?.decision_influenced ? 'demonstrated' : 'pending',
    substrate_primary: bestFork?.substrate_uniqueness?.primary_classification ?? null,
    r_highest_stage: bestFork?.r_stages?.highest_stage ?? null,
    semantic_content_forensic: fixtureObligation.semantic_content,
  };
}

export function buildLh1bArchaeologyDossier({ sequencePlan, fixture, turnRecords = [], forkResults = [] }) {
  const materialEvents = fixture.obligations.map((ob) => buildLh1bMaterialObligationDossier({
    fixtureObligation: ob,
    turnTraces: turnRecords,
    forkResults,
  }));
  return {
    schema: LH1B_SCHEMAS.ARCHAEOLOGY_DOSSIER,
    sequence_id: sequencePlan.sequence_id,
    scenario_key: sequencePlan.scenario_key,
    arm: sequencePlan.arm,
    blind_label: sequencePlan.blind_label ?? null,
    material_events: materialEvents,
    fork_results: forkResults,
    observation_only: true,
    mutates_story_state: false,
    human_summary: `LH-1B archaeology dossier for ${fixture.obligations.length} obligations from live traces.`,
  };
}
