/**
 * Issue #201 R5 — deterministic apparatus qualification (G1–G8).
 */
import crypto from 'node:crypto';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import { evaluateCharacterForkAtTurn } from './issue201-lh1b-causal-classifier.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';
import { R5_SCHEMAS, R5_QUALIFIED_LH1B_RUNNER_SHA } from './issue201-r5-contract.mjs';
import { proveEstablishmentEquivalence } from './issue201-r5-establishment-equivalence.mjs';
import {
  buildLhAManifestFromQualification,
  buildLhBManifestFromQualification,
  loadR5FixtureManifest,
  obligationById,
  primaryR5Fork,
  fixturePathForR5,
} from './issue201-r5-fixtures.mjs';
import { loadR5Policy, sha256File } from './issue201-r5-player-policy.mjs';
import { buildR5CampaignPlan } from './issue201-r5-orchestrator.mjs';

function gate(name, pass, detail = null) {
  return { name, pass, detail };
}

function stimulusLeakageCheck(fixture, fork) {
  const stimulus = fixture.qualification.decision_player_stimulus;
  const semantic = obligationById(fixture, fork.obligation_ids[0])?.semantic_content ?? '';
  const sub = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: [],
    playerStimulus: stimulus,
  });
  const markers = (fork.with_obligation_choice_classes ?? [])
    .flatMap((c) => c.behavior_markers ?? []);
  const stimLower = stimulus.toLowerCase();
  const markerInStimulus = markers.filter((m) => stimLower.includes(String(m).toLowerCase()));
  const passes = !sub.flags.stimulus_sufficient && markerInStimulus.length === 0;
  return {
    pass: passes,
    stimulus_sufficient: sub.flags.stimulus_sufficient,
    marker_overlap: markerInStimulus,
    stimulus,
  };
}

export function runR5ApparatusQualification() {
  const fixture = loadR5FixtureManifest();
  const fork = primaryR5Fork(fixture);
  const q = fixture.qualification;
  const decisionTurn = q.decision_turn_index;
  const gates = [];
  const lh1bApparatus = runLh1bApparatusValidationSuite();

  const equiv = proveEstablishmentEquivalence(fixture);
  gates.push(gate('G1_shared_establishment', equiv.g1_shared_establishment, equiv.detail));
  gates.push(gate('G2_persistence_entailment', equiv.g2_entailment_no_extra_facts, equiv.detail));

  const lhAManifest = buildLhAManifestFromQualification(fixture);
  const lhBManifest = buildLhBManifestFromQualification(fixture);
  const playerStimulus = q.decision_player_stimulus;
  const continuity = q.continuity_snapshot;
  const retrieval = q.retrieval_contributions ?? [];
  const memoryExtra = q.memory_contributions ?? [];

  const lhASubstrate = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: [...lhAManifest.contributions, ...memoryExtra],
    playerStimulus,
    continuitySnapshot: continuity,
    retrievalContributions: retrieval,
  });
  const sufficiencyFlags = lhASubstrate.flags;
  const g3Pass = Object.values(sufficiencyFlags).every((v) => v === false)
    && !lhASubstrate.semantic_fragment_in_lean_substrate;
  gates.push(gate('G3_lh_a_complete_substrate_absence', g3Pass, {
    classification: lhASubstrate.primary_classification,
    flags: sufficiencyFlags,
    semantic_fragment_in_lean: lhASubstrate.semantic_fragment_in_lean_substrate,
  }));

  const lhBSubstrate = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: lhBManifest.contributions,
    playerStimulus,
    continuitySnapshot: continuity,
    retrievalContributions: retrieval,
  });
  const stripped = lhBManifest.contributions.filter((c) => !c?.provenance?.lh0_obligation_id);
  const strippedSubstrate = classifyActualSubstrateUniqueness({
    fixture,
    fork,
    manifestContributions: stripped,
    playerStimulus,
    continuitySnapshot: continuity,
    retrievalContributions: retrieval,
  });
  const g4Pass = lhBSubstrate.persistence_unique === true
    && strippedSubstrate.semantic_fragment_in_lean_substrate === false
    && Object.values(strippedSubstrate.flags).every((v) => v === false);
  gates.push(gate('G4_lh_b_persistence_only_presence', g4Pass, {
    with_persistence: lhBSubstrate.primary_classification,
    stripped_classification: strippedSubstrate.primary_classification,
  }));

  const leak = stimulusLeakageCheck(fixture, fork);
  gates.push(gate('G5_decision_stimulus_neutrality', leak.pass, leak));

  const withClass = fork.with_obligation_choice_classes?.[0];
  const withoutClass = fork.without_obligation_choice_classes?.[0];
  const g6Pass = (withClass?.behavior_markers?.length ?? 0) > 0
    && (withoutClass?.behavior_markers?.length ?? 0) > 0;
  gates.push(gate('G6_behavioral_discriminability', g6Pass, {
    with_class: withClass?.class_id,
    without_class: withoutClass?.class_id,
  }));

  const mockMove = JSON.stringify({
    move_schema_version: 2,
    beats: [{ type: 'speech', dialogue: 'During your trial week, staff meals stay in the pantry alcove—not at the household dining table when guests are expected.' }],
    motivation: { goal: 'clarify', tactic: 'direct', emotional_driver: 'neutral', risk_level: 'low' },
    semantic_evaluation: { decision: 'no_covered_change' },
  });
  const forkEval = evaluateCharacterForkAtTurn({
    fixture,
    turnIndex: decisionTurn,
    manifest: lhBManifest,
    finalizedProjection: { contributions: [fixture.qualification.lh_b_persistence_contribution] },
    moveText: mockMove,
    presentationText: mockMove,
    playerStimulus,
    storeSnapshot: { obligations: fixture.obligations },
  })[0];
  const g7Pass = forkEval?.causal_evidence?.decision_influenced === true
    && forkEval?.received_obligation_ids?.length > 0;
  gates.push(gate('G7_provenance_r0_r4_readiness', g7Pass, {
    r_stages: forkEval?.r_stages,
    causal: forkEval?.causal_evidence,
  }));

  const lhA = buildLh0ArmConfig('lh_a');
  const lhB = buildLh0ArmConfig('lh_b');
  const g8Pass = lhA.persistent_cognition_enabled === false
    && lhB.persistent_cognition_enabled === true
    && lhAManifest.contributions.every((c) => !c?.provenance?.lh0_obligation_id);
  gates.push(gate('G8_arm_isolation', g8Pass, {
    lh_a_persistence: lhA.persistent_cognition_enabled,
    lh_b_persistence: lhB.persistent_cognition_enabled,
  }));

  const hashCheck = (() => {
    const measured = {
      fixture_hash: sha256File(fixturePathForR5()),
      policy_hash: loadR5Policy().policy_hash,
      causal_design_hash: crypto.createHash('sha256')
        .update(JSON.stringify(fixture.causal_design))
        .digest('hex'),
    };
    return measured;
  })();

  const failures = gates.filter((g) => !g.pass);
  return {
    schema: R5_SCHEMAS.QUALIFICATION,
    pass: failures.length === 0 && lh1bApparatus.pass,
    candidate_sha: gitSha(),
    qualified_lh1b_runner_sha: R5_QUALIFIED_LH1B_RUNNER_SHA,
    frozen_hashes_measured: hashCheck,
    fork_id: fork.fork_id,
    establishment_turn: fixture.establishment.turn_index,
    decision_turn: decisionTurn,
    horizon_turns: fixture.turns,
    aging_rationale: q.aging_rationale,
    gates,
    failures: failures.map((f) => f.name),
    lh_a_substrate: lhASubstrate,
    lh_b_substrate: lhBSubstrate,
    lh_a_manifest_summary: lhAManifest.contributions.map((c) => c.source_kind),
    lh_b_provenance: fixture.qualification.lh_b_persistence_contribution.provenance,
    campaign_plan: buildR5CampaignPlan(),
    lh1b_apparatus_regression: lh1bApparatus.pass,
    naturalness_note: 'Trial-week staff meal location is a plausible household procedure during live-in evaluation.',
  };
}
