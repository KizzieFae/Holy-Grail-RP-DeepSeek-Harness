/**
 * Issue #201 R5 — real-runner mock qualification (RG1–RG8).
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { buildLh0ArmConfig, LH0_ARMS } from './issue201-lh0-arms.mjs';
import { evaluateCharacterForkAtTurn } from './issue201-lh1b-causal-classifier.mjs';
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import { R5_SCHEMAS } from './issue201-r5-contract.mjs';
import { verifyR5FrozenHashes } from './issue201-r5-frozen-hashes.mjs';
import { loadR5FixtureManifest, primaryR5Fork } from './issue201-r5-fixtures.mjs';
import { loadR5Policy } from './issue201-r5-player-policy.mjs';
import { buildR5CampaignPlan } from './issue201-r5-orchestrator.mjs';
import { runR5ApparatusQualification } from './issue201-r5-qualification-lib.mjs';
import { executeR5MockSequence } from './issue201-r5-live-lib.mjs';
import {
  classifyRunnerSubstrate,
  normalizedSubstrateDiff,
  proveRunnerEstablishmentEquivalence,
  reviewInterveningTurnsForRuleRefresh,
  stimulusLeakageOnActualStimulus,
} from './issue201-r5-runner-analysis.mjs';
import { LH1B_TURN_ORDERING } from './issue201-lh1b-live-lib.mjs';
import { readLh0Store } from './issue201-lh0-persistent-store.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';

const MOVE_BASE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'considers the question carefully' }],
  motivation: { goal: 'respond', tactic: 'measured', emotional_driver: 'neutral', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const GENERIC_CHARACTER_MOVE = JSON.stringify(MOVE_BASE);
const GENERIC_NARRATOR = 'Ayame regarded the applicant with measured attention.';

function charMove(dialogue) {
  return JSON.stringify({
    ...MOVE_BASE,
    beats: [{ type: 'speech', dialogue }],
  });
}

function narratorForSpeech(dialogue) {
  return `Ayame said, "${dialogue}"`;
}

function gate(name, pass, detail = null) {
  return { name, pass, detail };
}

function buildDefaultMockOverrides(fixture) {
  const est = fixture.establishment;
  const generic = {
    forceMockInferenceProfiles: true,
    beatOptions: {
      mockCharacterResponses: [GENERIC_CHARACTER_MOVE],
      mockNarratorResponses: [GENERIC_NARRATOR],
    },
  };
  const byTurn = {};
  for (let t = 1; t <= fixture.turns; t += 1) {
    byTurn[t] = { ...generic };
  }
  byTurn[est.turn_index] = {
    forceMockInferenceProfiles: true,
    beatOptions: {
      mockCharacterResponses: [charMove(est.character_move_dialogue)],
      mockNarratorResponses: [narratorForSpeech(est.character_move_dialogue)],
    },
  };
  return byTurn;
}

function forkEvalAtTurn({ fixture, turnRow, moveText, storeSnapshot }) {
  const manifest = turnRow.assembled_request_character
    ? { contributions: turnRow.assembled_request_character.contributions ?? [] }
    : null;
  if (!manifest) return null;
  const persistenceContribs = (manifest.contributions ?? []).filter(
    (c) => c?.provenance?.lh0_obligation_id,
  );
  return evaluateCharacterForkAtTurn({
    fixture,
    turnIndex: turnRow.turn_index,
    manifest,
    finalizedProjection: persistenceContribs.length
      ? { contributions: persistenceContribs }
      : null,
    moveText,
    presentationText: turnRow.presentation_text ?? '',
    playerStimulus: turnRow.exact_player_stimulus ?? '',
    storeSnapshot,
  })[0];
}

export async function runR5RunnerMockQualification({ evidenceRoot = null } = {}) {
  const root = evidenceRoot ?? fs.mkdtempSync(path.join(os.tmpdir(), 'r5-runner-qual-'));
  fs.mkdirSync(root, { recursive: true });

  const fixture = loadR5FixtureManifest();
  const fork = primaryR5Fork(fixture);
  const decisionTurn = fixture.qualification.decision_turn_index;
  const establishmentTurn = fixture.establishment.turn_index;
  const { policy } = loadR5Policy();
  const campaignPlan = buildR5CampaignPlan({ candidateSha: gitSha() });
  const planA = campaignPlan.sequences.find((s) => s.blind_label === 'R5-A1');
  const planB = campaignPlan.sequences.find((s) => s.blind_label === 'R5-B1');
  if (!planA || !planB) throw new Error('R5 campaign plan missing A1/B1');

  const mockByTurn = buildDefaultMockOverrides(fixture);
  const positiveMove = charMove(
    'During your trial week, staff meals stay in the staff pantry alcove—not at the household dining table when guests are expected at formal meal.',
  );
  const negativeMove = charMove(
    'Of course—keep a chair ready at the dining table; you may assist from there during the guest meal.',
  );
  const positiveDialogue = JSON.parse(positiveMove).beats[0].dialogue;
  mockByTurn[decisionTurn] = {
    forceMockInferenceProfiles: true,
    beatOptions: {
      mockCharacterResponses: [positiveMove],
      mockNarratorResponses: [narratorForSpeech(positiveDialogue)],
    },
  };

  const hashGate = verifyR5FrozenHashes();
  const apparatus = runR5ApparatusQualification();
  const lh1bApparatus = runLh1bApparatusValidationSuite();
  const gates = [];

  gates.push(gate('frozen_hash_gate', hashGate.pass, hashGate));
  gates.push(gate('authoritative_turn_ordering', LH1B_TURN_ORDERING.includes('lh0_projection_transport_before_director')));

  const seqA = await executeR5MockSequence({
    sequencePlan: planA,
    evidenceRoot: root,
    mockOverridesByTurn: mockByTurn,
  });
  const seqB = await executeR5MockSequence({
    sequencePlan: planB,
    evidenceRoot: root,
    mockOverridesByTurn: mockByTurn,
  });

  if (seqA.failed || seqB.failed) {
    return {
      schema: R5_SCHEMAS.RUNNER_QUALIFICATION,
      pass: false,
      failures: ['sequence_execution_failed'],
      gates,
      seq_a: seqA,
      seq_b: seqB,
      evidence_root: root,
    };
  }

  const t6A = seqA.turns.find((t) => t.turn_index === establishmentTurn);
  const t6B = seqB.turns.find((t) => t.turn_index === establishmentTurn);
  const t14A = seqA.turns.find((t) => t.turn_index === decisionTurn);
  const t14B = seqB.turns.find((t) => t.turn_index === decisionTurn);

  const establishment = proveRunnerEstablishmentEquivalence({ t6RowA: t6A, t6RowB: t6B, fixture });
  gates.push(gate('RG1_shared_establishment', establishment.rg1_pass, establishment.detail));
  gates.push(gate('RG2_persistence_entailment', establishment.rg2_pass, establishment.detail));

  const substrateA = classifyRunnerSubstrate({
    fixture,
    assembledRequest: t14A.assembled_request_character,
    playerStimulus: t14A.exact_player_stimulus,
    continuitySnapshot: t14A.continuity_snapshot,
  });
  const substrateB = classifyRunnerSubstrate({
    fixture,
    assembledRequest: t14B.assembled_request_character,
    playerStimulus: t14B.exact_player_stimulus,
    continuitySnapshot: t14B.continuity_snapshot,
  });

  const aFlags = substrateA.classification.flags;
  const g3Pass = Object.values(aFlags).every((v) => v === false)
    && !substrateA.classification.semantic_fragment_in_lean_substrate;
  gates.push(gate('RG3_a1_complete_substrate_absence', g3Pass, {
    flags: aFlags,
    classification: substrateA.classification.primary_classification,
    contribution_kinds: substrateA.contributions.map((c) => c.source_kind),
  }));

  const strippedFlags = substrateB.stripped_classification.flags;
  const g4Pass = substrateB.persistence_contributions.length >= 1
    && substrateB.classification.persistence_unique === true
    && Object.values(strippedFlags).every((v) => v === false)
    && !substrateB.stripped_classification.semantic_fragment_in_lean_substrate;
  gates.push(gate('RG4_b1_persistence_only_presence', g4Pass, {
    persistence: substrateB.persistence_contributions,
    with_persistence: substrateB.classification,
    stripped: substrateB.stripped_classification,
  }));

  const stimulusCheck = stimulusLeakageOnActualStimulus(t14A.exact_player_stimulus, fixture);
  const policyStimulus = policy.turns.find((t) => t.turn_index === decisionTurn)?.realization ?? '';
  const stimulusExact = normalize(policyStimulus) === normalize(t14A.exact_player_stimulus)
    && normalize(policyStimulus) === normalize(fixture.qualification.decision_player_stimulus);
  gates.push(gate('RG5_decision_stimulus_neutrality', stimulusCheck.pass && stimulusExact, {
    ...stimulusCheck,
    policy_match: stimulusExact,
  }));

  const withClass = fork.with_obligation_choice_classes?.[0];
  const withoutClass = fork.without_obligation_choice_classes?.[0];
  const g6Pass = (withClass?.behavior_markers?.length ?? 0) > 0
    && (withoutClass?.behavior_markers?.length ?? 0) > 0;
  gates.push(gate('RG6_behavioral_discriminability', g6Pass, {
    with_class: withClass?.class_id,
    without_class: withoutClass?.class_id,
  }));

  const sessionsDir = defaultSessionsDir();
  const storeB = readLh0Store(sessionsDir, seqB.hg_session_id);
  const forkPosB = forkEvalAtTurn({
    fixture,
    turnRow: t14B,
    moveText: JSON.parse(positiveMove).beats[0].dialogue,
    storeSnapshot: storeB,
  });
  const g7Pass = forkPosB?.causal_evidence?.decision_influenced === true
    && (forkPosB?.received_obligation_ids?.length ?? 0) > 0
    && forkPosB?.r_stages?.marginal_persistence_value === true;
  gates.push(gate('RG7_causal_chain_r0_r5', g7Pass, {
    positive_fork: forkPosB,
  }));

  const diff = normalizedSubstrateDiff(
    t14A.assembled_request_character,
    t14B.assembled_request_character,
  );
  const g8Pass = diff.lean_substrate_equivalent
    && diff.potentially_causal_non_persistence_differences.length === 0;
  gates.push(gate('RG8_no_arm_leakage_or_substrate_asymmetry', g8Pass, diff));

  const forkNegB = forkEvalAtTurn({
    fixture,
    turnRow: t14B,
    moveText: JSON.parse(negativeMove).beats[0].dialogue,
    storeSnapshot: storeB,
  });
  const negativeControlPass = forkNegB?.causal_evidence?.decision_influenced !== true;

  const forkA = forkEvalAtTurn({
    fixture,
    turnRow: t14A,
    moveText: JSON.parse(positiveMove).beats[0].dialogue,
    storeSnapshot: { obligations: [] },
  });
  const a1NoR5 = forkA?.r_stages?.marginal_persistence_value !== true;

  const naturalness = reviewInterveningTurnsForRuleRefresh(seqA.turns, fixture);
  gates.push(gate('naturalness_no_intervening_refresh', naturalness.pass, naturalness));

  const armConfigA = buildLh0ArmConfig(LH0_ARMS.LH_A);
  const armConfigB = buildLh0ArmConfig(LH0_ARMS.LH_B);
  gates.push(gate('arm_isolation_config', armConfigA.persistent_cognition_enabled === false
    && armConfigB.persistent_cognition_enabled === true));

  const failures = gates.filter((g) => !g.pass).map((g) => g.name);
  const pass = failures.length === 0
    && negativeControlPass
    && a1NoR5
    && apparatus.pass
    && lh1bApparatus.pass;

  const report = {
    schema: R5_SCHEMAS.RUNNER_QUALIFICATION,
    pass,
    candidate_sha: gitSha(),
    apparatus_candidate_sha: '8c4c32a',
    frozen_hashes: hashGate.measured,
    gates,
    failures,
    apparatus_g1_g8: apparatus,
    lh1b_apparatus_regression: lh1bApparatus.pass,
    sequences: { r5_a1: seqA, r5_b1: seqB },
    establishment,
    t6: { a1: t6A, b1: t6B },
    t14: {
      a1: {
        player_stimulus: t14A.exact_player_stimulus,
        assembled_request_character: t14A.assembled_request_character,
        substrate: substrateA,
      },
      b1: {
        player_stimulus: t14B.exact_player_stimulus,
        assembled_request_character: t14B.assembled_request_character,
        substrate: substrateB,
      },
    },
    substrate_diff: diff,
    stimulus_leakage: stimulusCheck,
    naturalness,
    mock_causal: {
      b1_positive: forkPosB,
      b1_negative: forkNegB,
      a1_no_r5: a1NoR5,
      negative_control_pass: negativeControlPass,
    },
    player_policy_synopsis: policy.turns.map((t) => ({
      turn_index: t.turn_index,
      objective: t.objective,
      realization: t.realization,
    })),
    evidence_root: root,
    turn_ordering: LH1B_TURN_ORDERING,
    live_authorized: false,
  };

  fs.writeFileSync(path.join(root, 'r5_runner_qualification.json'), JSON.stringify(report, null, 2));
  return report;
}

function normalize(text) {
  return String(text ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}
