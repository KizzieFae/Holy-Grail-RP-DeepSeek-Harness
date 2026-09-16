/**
 * Issue #201 LH-1A — blind sequence packet transport (pre-decode).
 */
import fs from 'node:fs';

import { LH1A_BLIND_FORBIDDEN_PATTERNS, LH1A_SCHEMAS } from './issue201-lh1a-contract.mjs';

export function buildLh1aBlindPacket({ campaignPlan, rubric, toneContracts = {} }) {
  const sequences = campaignPlan.sequences.map((seq) => ({
    blind_label: seq.blind_label,
    scenario_briefing: toneContracts[seq.scenario_id] ?? {
      setting: seq.scenario_id,
      tone: 'See scenario tone contract.',
    },
    turn_count: seq.turn_count,
    checkpoint_turns: seq.checkpoints,
    turns: seq.turns.map((t) => ({
      turn_index: t.turn_index,
      player_stimulus: t.player_stimulus,
      presentation_text: '[presentation recorded at live execution — apparatus validation uses policy stimuli only]',
    })),
  }));
  return {
    schema: LH1A_SCHEMAS.BLIND_PACKET,
    purpose: 'Issue #201 LH-1A — story-aging screening (8 sequences)',
    instructions: 'Score using locked lh1a_blind_rubric_v1 dimensions. Do not request arm identity or mechanism topology until after scoring is locked.',
    rubric_id: rubric.rubric_id,
    rubric_locked: rubric.locked === true,
    core_dimensions: rubric.core_dimensions.map((d) => d.id),
    long_horizon_dimensions: rubric.long_horizon_dimensions.map((d) => d.id),
    dark_story_safeguards: rubric.dark_story_safeguards,
    sequences,
  };
}

export function buildLh1aAnswerKey(campaignPlan) {
  return campaignPlan.sequences.map((seq) => ({
    blind_label: seq.blind_label,
    sequence_id: seq.sequence_id,
    arm: seq.arm,
    arm_label: seq.arm_label,
    scenario_key: seq.scenario_key,
    scenario_id: seq.scenario_id,
    fixture_id: seq.fixture_id,
    fixture_hash: seq.fixture_hash,
    policy_id: seq.policy_id,
    policy_hash: seq.policy_hash,
  }));
}

export function validateLh1aBlindPacketIntegrity(packet) {
  const packetText = JSON.stringify(packet).toLowerCase();
  const leaked = LH1A_BLIND_FORBIDDEN_PATTERNS
    .filter((re) => re.test(packetText))
    .map((re) => re.source);
  const hasArmInSequences = packet.sequences?.some((s) => (
    JSON.stringify(s).toLowerCase().includes('lh_a')
    || JSON.stringify(s).toLowerCase().includes('plot_scribe')
  ));
  if (hasArmInSequences) leaked.push('arm_identity_in_sequence_payload');
  return {
    pass: leaked.length === 0,
    leaked_patterns: leaked,
    sequence_count: packet.sequences?.length ?? 0,
  };
}

export function writeLh1aBlindArtifacts({ outputDir, packet, answerKey }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const packetPath = `${outputDir}/issue201-lh1a-blind-sequence-packet.json`;
  const keyPath = `${outputDir}/issue201-lh1a-blind-sequence-answer-key.json`;
  fs.writeFileSync(packetPath, `${JSON.stringify(packet, null, 2)}\n`);
  fs.writeFileSync(keyPath, `${JSON.stringify(answerKey, null, 2)}\n`);
  return { packetPath, keyPath };
}
