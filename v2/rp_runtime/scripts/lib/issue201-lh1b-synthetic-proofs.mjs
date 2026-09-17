/**
 * Issue #201 LH-1B — synthetic seam qualification (no live inference).
 */
import {
  buildLh0FinalizedProjection,
  classifyLh0ObligationStates,
  obligationsForConsumer,
} from './issue201-lh0-persistent-store.mjs';
import {
  buildCharacterConsumerEvidence,
  projectionSemanticAdequate,
  validateLh0FinalizedProjectionPackage,
} from './issue201-lh0-consumer-evidence.mjs';
import { prepareLh0RoundTransport } from './issue201-lh0-transport.mjs';
import { loadLh1bFixtureManifest } from './issue201-lh1b-fixtures.mjs';
import {
  evaluateCharacterForkAtTurn,
  evaluateDirectorForkAtTurn,
} from './issue201-lh1b-causal-classifier.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { buildLhProvenanceAuditBlock } from './issue201-lh1b-provenance.mjs';
import { buildLh1bArchaeologyDossier } from './issue201-lh1b-archaeology.mjs';
import { attemptsToInferenceEvents, buildLh1bCostRollup } from './issue201-lh1b-cost-accounting.mjs';
import { seedLh0ObligationFromFixture } from './issue201-lh0-semantic-content.mjs';

function syntheticStore(fixture, turnIndex) {
  const store = {
    schema: 'issue201_lh0_persistent_store_v1',
    campaign: 'lh1b',
    fixture_id: fixture.fixture_id,
    obligations: fixture.obligations.map((o) => seedLh0ObligationFromFixture(o, {
      mechanism: 'plot_cognition_update',
      source: 'fixture_seed',
    })),
    events: [],
  };
  classifyLh0ObligationStates(store, turnIndex);
  return store;
}

function mockManifestFromProjection(projection) {
  return {
    manifest_id: 'synthetic-manifest',
    inference_kind: projection.inference_kind,
    contributions: projection.contributions,
  };
}

export function runLh1bSyntheticProofs() {
  const fixture = loadLh1bFixtureManifest();
  const proofs = [];

  // Character projection + receipt
  {
    const store = syntheticStore(fixture, 17);
    const due = obligationsForConsumer(store, { turn: 17, consumer: 'character_move' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-char-17',
      consumer: 'character_move',
      characterId: 'Ayame',
      turnIndex: 17,
    });
    const manifest = mockManifestFromProjection(projection);
    const evidence = buildCharacterConsumerEvidence({
      manifest,
      finalizedProjection: projection,
      projectionSupplied: true,
      obligationIdsExpected: due.map((o) => o.obligation_id),
    });
    proofs.push({
      name: 'character_projection_semantic_receipt',
      pass: evidence.consumer_received && evidence.semantic_receipt_adequate,
    });
  }

  // Director projection + receipt
  {
    const store = syntheticStore(fixture, 15);
    const due = obligationsForConsumer(store, { turn: 15, consumer: 'director_turn' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-dir-15',
      consumer: 'director_turn',
      turnIndex: 15,
    });
    const valid = validateLh0FinalizedProjectionPackage(projection, { consumer: 'director_turn' });
    const manifest = mockManifestFromProjection(projection);
    const received = (manifest.contributions ?? []).some((c) => (
      c.source_kind === 'scene_pressures' && String(c.content).includes('threshold')
    ));
    proofs.push({
      name: 'director_projection_semantic_receipt',
      pass: valid.valid === true && received && projectionSemanticAdequate(projection),
    });
  }

  // Character positive fork (deferred key)
  {
    const fork = fixture.causal_design.decision_forks.find((f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY');
    const store = syntheticStore(fixture, 17);
    const due = obligationsForConsumer(store, { turn: 17, consumer: 'character_move' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-pos',
      consumer: 'character_move',
      characterId: 'Ayame',
      turnIndex: 17,
    });
    const manifest = mockManifestFromProjection(projection);
    const positiveMove = 'Ayame said: "During a trial week you receive only the pantry submaster key. The household master key is not issued."';
    const evalRow = evaluateCharacterForkAtTurn({
      fixture,
      turnIndex: 17,
      manifest,
      finalizedProjection: projection,
      moveText: positiveMove,
      presentationText: positiveMove,
      playerStimulus: 'Will I receive the master key?',
      storeSnapshot: store,
    })[0];
    proofs.push({
      name: 'character_positive_fork_classifier',
      pass: evalRow?.causal_evidence?.decision_influenced === true,
    });
  }

  // Character negative fork
  {
    const fork = fixture.causal_design.decision_forks.find((f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY');
    const store = syntheticStore(fixture, 17);
    const due = obligationsForConsumer(store, { turn: 17, consumer: 'character_move' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-neg',
      consumer: 'character_move',
      characterId: 'Ayame',
      turnIndex: 17,
    });
    const manifest = mockManifestFromProjection(projection);
    const negativeMove = 'Ayame said: "Take the master key from the hook by the door."';
    const evalRow = evaluateCharacterForkAtTurn({
      fixture,
      turnIndex: 17,
      manifest,
      finalizedProjection: projection,
      moveText: negativeMove,
      presentationText: negativeMove,
      playerStimulus: 'Will I receive the master key?',
      storeSnapshot: store,
    })[0];
    proofs.push({
      name: 'character_negative_fork_classifier',
      pass: evalRow?.causal_evidence?.decision_influenced !== true,
    });
  }

  // Director positive (advisory trajectory — not actor dictation)
  {
    const store = syntheticStore(fixture, 15);
    const due = obligationsForConsumer(store, { turn: 15, consumer: 'director_turn' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-dir-pos',
      consumer: 'director_turn',
      turnIndex: 15,
    });
    const manifest = mockManifestFromProjection(projection);
    const decision = {
      next_actor: 'Ayame',
      tension_shift: 'escalate',
      reason: 'Threshold compensation remains unresolved; applicant not yet seated for full terms.',
      end_round: false,
      environment_event: '',
    };
    const evalRow = evaluateDirectorForkAtTurn({
      fixture,
      turnIndex: 15,
      manifest,
      finalizedProjection: projection,
      directorDecision: decision,
      storeSnapshot: store,
    })[0];
    const advisoryOnly = !String(projection.contributions[0]?.content ?? '').toLowerCase().includes('choose ayame');
    proofs.push({
      name: 'director_positive_fork_classifier',
      pass: evalRow?.causal_evidence?.decision_influenced === true && advisoryOnly,
    });
  }

  // Director negative
  {
    const store = syntheticStore(fixture, 15);
    const due = obligationsForConsumer(store, { turn: 15, consumer: 'director_turn' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-dir-neg',
      consumer: 'director_turn',
      turnIndex: 15,
    });
    const manifest = mockManifestFromProjection(projection);
    const decision = {
      next_actor: 'Ayame',
      tension_shift: 'soften',
      reason: 'Comfortable enough to move on.',
      end_round: false,
      environment_event: '',
    };
    const evalRow = evaluateDirectorForkAtTurn({
      fixture,
      turnIndex: 15,
      manifest,
      finalizedProjection: projection,
      directorDecision: decision,
      storeSnapshot: store,
    })[0];
    proofs.push({
      name: 'director_negative_fork_classifier',
      pass: evalRow?.causal_evidence?.decision_influenced !== true,
    });
  }

  // Transcript sufficiency case
  {
    const fork = fixture.causal_design.decision_forks.find((f) => f.fork_id === 'FORK-LH1B-PROMISE-GATE');
    const substrate = classifyActualSubstrateUniqueness({
      fixture,
      fork,
      manifestContributions: [{
        source_kind: 'recent_scene_transcript',
        content: 'Kizzie committed not to enter any restricted area without written authorization.',
      }],
      playerStimulus: 'May I check the east wing radiator tonight?',
    });
    proofs.push({
      name: 'transcript_sufficiency_detection',
      pass: substrate.flags.transcript_sufficient || substrate.primary_classification === 'stimulus_sufficient'
        || substrate.primary_classification === 'other_substrate_sufficient',
    });
  }

  // Continuity sufficiency case
  {
    const fork = fixture.causal_design.decision_forks.find((f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY');
    const substrate = classifyActualSubstrateUniqueness({
      fixture,
      fork,
      manifestContributions: [],
      continuitySnapshot: {
        character_state: 'Trial staff receive only a pantry submaster key during trial week.',
      },
      playerStimulus: 'Will I receive the master key?',
    });
    proofs.push({
      name: 'continuity_sufficiency_detection',
      pass: substrate.flags.continuity_sufficient === true,
    });
  }

  // Retrieval sufficiency case
  {
    const fork = fixture.causal_design.decision_forks.find((f) => f.fork_id === 'FORK-LH1B-DORMANT-RECORD');
    const substrate = classifyActualSubstrateUniqueness({
      fixture,
      fork,
      manifestContributions: [],
      retrievalContributions: [{
        source_kind: 'indexed_retrieval',
        content: 'Previous assistant dismissed after copying household ledger pages.',
      }],
      playerStimulus: 'I could help with household accounts.',
    });
    proofs.push({
      name: 'retrieval_sufficiency_detection',
      pass: substrate.flags.retrieval_sufficient === true,
    });
  }

  // Provenance round trip
  {
    const store = syntheticStore(fixture, 16);
    const due = obligationsForConsumer(store, { turn: 16, consumer: 'character_move' });
    const projection = buildLh0FinalizedProjection(due, {
      batchId: 'syn-prov',
      consumer: 'character_move',
      characterId: 'Ayame',
      turnIndex: 16,
    });
    const manifest = mockManifestFromProjection(projection);
    const audit = buildLhProvenanceAuditBlock({
      obligationIds: due.map((o) => o.obligation_id),
      projection,
      manifest,
      inferenceId: 'inf-syn',
      hgRoundId: 'hg-round-syn',
      consumer: 'character_move',
    });
    proofs.push({
      name: 'provenance_round_trip',
      pass: audit.received_obligation_ids.length > 0
        && audit.contributions.every((c) => c.obligation_id),
    });
  }

  // Negative / not-due obligation
  {
    const store = syntheticStore(fixture, 8);
    const due = obligationsForConsumer(store, { turn: 8, consumer: 'character_move' });
    const negDue = due.filter((o) => o.obligation_id === 'LH1B-AYA-NEG-CONTROL');
    proofs.push({
      name: 'negative_obligation_not_due_early',
      pass: negDue.length === 0,
    });
  }

  // Transport seam
  {
    const store = syntheticStore(fixture, 17);
    const transport = prepareLh0RoundTransport({
      sessionsDir: null,
      hgSessionId: 'hg-syn',
      hgRoundId: 'hg-round-syn',
      fixtureTurnIndex: 17,
      characterId: 'Ayame',
      arm: 'lh_b',
      storeOverride: store,
    });
    proofs.push({
      name: 'lh0_transport_character_projection',
      pass: transport.projected_finalized === true && transport.characterDue.length > 0,
    });
  }

  // Archaeology reconstruction
  {
    const dossier = buildLh1bArchaeologyDossier({
      sequencePlan: { sequence_id: 'syn', scenario_key: 'ayame_controlled', arm: 'lh_b' },
      fixture,
      turnRecords: [{
        turn_index: 17,
        hg_round_id: 'r1',
        lh1b_projection: { projected: true, consumer_received: true, consumer_used: false },
      }],
      forkResults: [],
    });
    proofs.push({
      name: 'archaeology_reconstruction',
      pass: dossier.material_events.some((e) => e.projection_events.length > 0),
    });
  }

  // Non-zero synthetic cost
  {
    const events = attemptsToInferenceEvents([
      {
        correlation: { inference_kind: 'plot_cognition_update' },
        response: { usage: { input_tokens: 100, output_tokens: 40, reasoning_tokens: 10 } },
        inference_health: { inference_wall_clock_ms: 50 },
      },
      {
        correlation: { inference_kind: 'character_move' },
        response: { usage: { input_tokens: 200, output_tokens: 80, reasoning_tokens: 0 } },
        inference_health: { inference_wall_clock_ms: 120 },
      },
    ]);
    const rollup = buildLh1bCostRollup({
      arm: 'lh_b',
      sequenceId: 'syn',
      inferenceEvents: events,
    });
    proofs.push({
      name: 'non_zero_synthetic_cost_capture',
      pass: rollup.input_tokens > 0 && rollup.output_tokens > 0 && rollup.wall_ms_total > 0,
    });
  }

  const pass = proofs.every((p) => p.pass);
  return { pass, proofs, proof_count: proofs.length };
}
