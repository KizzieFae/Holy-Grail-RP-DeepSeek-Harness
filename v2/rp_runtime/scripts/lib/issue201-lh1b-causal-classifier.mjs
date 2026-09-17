/**
 * Issue #201 LH-1B — fixture-aware causal fork classifier (Character + Director).
 */
import {
  classifyBehaviorAgainstFork,
  evaluateTurnCausalEvidence,
} from './issue201-lh0-semantic-content.mjs';
import {
  extractLh0ObligationIdsFromManifest,
  extractLh0ObligationIdsFromProjection,
} from './issue201-lh0-consumer-evidence.mjs';
import { forkForTurn, listLh1bDecisionForks } from './issue201-lh1b-fixtures.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { classifyForkRStages } from './issue201-lh1b-causal-r0-r5.mjs';

function normalizeHaystack(...parts) {
  return parts.map((p) => String(p ?? '').toLowerCase()).join('\n');
}

export function evaluateCharacterForkAtTurn({
  fixture,
  turnIndex,
  manifest,
  finalizedProjection,
  moveText = '',
  presentationText = '',
  playerStimulus = '',
  presentationTranscript = '',
  continuitySnapshot = null,
  retrievalContributions = [],
  storeSnapshot = null,
}) {
  const forks = forkForTurn(fixture, turnIndex, { consumer: 'character_move' });
  return forks.map((fork) => {
    const receivedIds = extractLh0ObligationIdsFromManifest(manifest);
    const projectedIds = extractLh0ObligationIdsFromProjection(finalizedProjection);
    const linked = (fork.obligation_ids ?? []).filter((id) => receivedIds.includes(id));
    const causal = evaluateTurnCausalEvidence({
      turnIndex,
      moveText,
      presentationText,
      receivedObligationIds: linked,
      fixture,
    });
    const substrate = classifyActualSubstrateUniqueness({
      fixture,
      fork,
      manifestContributions: manifest?.contributions ?? [],
      playerStimulus,
      presentationTranscript,
      continuitySnapshot,
      retrievalContributions,
    });
    const rStages = classifyForkRStages({
      fork,
      storeSnapshot,
      projected: projectedIds.length > 0,
      receivedIds: linked,
      manifest,
      consumerUsed: causal.consumer_used,
      decisionInfluenced: causal.decision_influenced,
      substrate,
    });
    return {
      fork_id: fork.fork_id,
      consumer: 'character_move',
      turn_index: turnIndex,
      obligation_ids: fork.obligation_ids,
      received_obligation_ids: linked,
      projected_obligation_ids: projectedIds.filter((id) => (fork.obligation_ids ?? []).includes(id)),
      causal_evidence: causal,
      substrate_uniqueness: substrate,
      r_stages: rStages,
    };
  });
}

export function evaluateDirectorForkAtTurn({
  fixture,
  turnIndex,
  manifest,
  finalizedProjection,
  directorDecision = null,
  playerStimulus = '',
  presentationTranscript = '',
  continuitySnapshot = null,
  storeSnapshot = null,
}) {
  const forks = forkForTurn(fixture, turnIndex, { consumer: 'director_turn' });
  const receivedIds = extractLh0ObligationIdsFromManifest(manifest);
  const projectedIds = extractLh0ObligationIdsFromProjection(finalizedProjection);
  const haystack = normalizeHaystack(
    JSON.stringify(directorDecision ?? {}),
    directorDecision?.reason ?? '',
    directorDecision?.tension_shift ?? '',
  );

  return forks.map((fork) => {
    const linked = (fork.obligation_ids ?? []).filter((id) => receivedIds.includes(id));
    let consumerUsed = false;
    let decisionInfluenced = false;
    const matchedForks = [];
    if (linked.length) {
      const { withClass, withoutClass } = classifyBehaviorAgainstFork({ fork, haystack });
      if (withClass) {
        consumerUsed = true;
        decisionInfluenced = true;
        matchedForks.push({
          fork_id: fork.fork_id,
          choice_class: withClass.class_id,
          direction: 'with_obligation',
        });
      } else if (withoutClass) {
        matchedForks.push({
          fork_id: fork.fork_id,
          choice_class: withoutClass.class_id,
          direction: 'without_obligation_pattern',
        });
      }
    }
    const substrate = classifyActualSubstrateUniqueness({
      fixture,
      fork,
      manifestContributions: manifest?.contributions ?? [],
      playerStimulus,
      presentationTranscript,
      continuitySnapshot,
    });
    const rStages = classifyForkRStages({
      fork,
      storeSnapshot,
      projected: projectedIds.length > 0,
      receivedIds: linked,
      manifest,
      consumerUsed,
      decisionInfluenced,
      substrate,
    });
    return {
      fork_id: fork.fork_id,
      consumer: 'director_turn',
      turn_index: turnIndex,
      obligation_ids: fork.obligation_ids,
      received_obligation_ids: linked,
      projected_obligation_ids: projectedIds.filter((id) => (fork.obligation_ids ?? []).includes(id)),
      causal_evidence: {
        consumer_used: consumerUsed,
        decision_influenced: decisionInfluenced,
        matched_forks: matchedForks,
        influenced_obligation_ids: decisionInfluenced ? linked : [],
      },
      substrate_uniqueness: substrate,
      r_stages: rStages,
      director_decision: directorDecision,
    };
  });
}

export function evaluateAllForksForSequence({ fixture, turnRecords = [] }) {
  const results = [];
  for (const turn of turnRecords) {
    const turnIndex = turn.turn_index;
    for (const fork of listLh1bDecisionForks(fixture)) {
      if (fork.decision_turn !== turnIndex) continue;
      if (fork.consumer === 'director_turn') continue;
      const evalRow = evaluateCharacterForkAtTurn({
        fixture,
        turnIndex,
        manifest: turn.consumer_manifest ?? turn.lh1b_causal_trace?.character_manifest ?? null,
        finalizedProjection: turn.lh1b_projection?.finalized_projection ?? null,
        moveText: turn.move_text ?? '',
        presentationText: turn.presentation_text ?? '',
        playerStimulus: turn.exact_player_stimulus ?? '',
        presentationTranscript: turn.presentation_transcript_window ?? '',
        continuitySnapshot: turn.continuity_snapshot ?? null,
        storeSnapshot: turn.lh1b_projection?.lh0_store_snapshot ?? null,
      });
      results.push(...evalRow);
    }
  }
  return results;
}
