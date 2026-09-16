#!/usr/bin/env node
/**
 * Issue #201 LH-1A — blind integrity verify, packet rebuild, cost/decode aggregates.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildLh1aBlindPacket,
  buildLh1aAnswerKey,
  validateLh1aBlindPacketIntegrity,
} from '../../v2/rp_runtime/scripts/lib/issue201-lh1a-blind-packet.mjs';
import { LH1A_CHECKPOINTS } from '../../v2/rp_runtime/scripts/lib/issue201-lh1a-contract.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');
const CAMPAIGN_DIR = path.join(
  REPO_ROOT,
  'data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z',
);
const RUBRIC_PATH = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json');
const OUT_DIR = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-evaluation');

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function sha256Text(text) {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

function loadSequences() {
  const files = fs.readdirSync(CAMPAIGN_DIR).filter((f) => f.endsWith('-sequence.json'));
  return files.map((f) => JSON.parse(fs.readFileSync(path.join(CAMPAIGN_DIR, f), 'utf8')));
}

function loadCampaignPlan() {
  return JSON.parse(fs.readFileSync(path.join(CAMPAIGN_DIR, 'issue201-lh1a-campaign-plan-locked.json'), 'utf8'));
}

function rebuildEvaluableBlindPacket(sequences, campaignPlan, rubric) {
  const byBlind = new Map(sequences.map((s) => [s.blind_label, s]));
  const enrichedPlan = {
    ...campaignPlan,
    sequences: campaignPlan.sequences.map((plan) => {
      const live = byBlind.get(plan.blind_label)
        ?? sequences.find((s) => s.arm === plan.arm && s.scenario_key === plan.scenario_key);
      if (!live) return plan;
      return {
        ...plan,
        sequence_id: live.sequence_id,
        turns: plan.turns.map((t) => {
          const liveTurn = live.turns.find((lt) => lt.turn_index === t.turn_index);
          return {
            ...t,
            presentation_text: liveTurn?.presentation_text ?? '',
          };
        }),
      };
    }),
  };
  const basePacket = buildLh1aBlindPacket({ campaignPlan: enrichedPlan, rubric });
  const packet = {
    ...basePacket,
    sequences: enrichedPlan.sequences.map((seq) => ({
      blind_label: seq.blind_label,
      scenario_briefing: basePacket.sequences.find((s) => s.blind_label === seq.blind_label)?.scenario_briefing ?? {
        setting: seq.scenario_id,
        tone: 'See scenario tone contract.',
      },
      turn_count: seq.turn_count,
      checkpoint_turns: seq.checkpoints,
      turns: seq.turns.map((t) => ({
        turn_index: t.turn_index,
        player_stimulus: t.player_stimulus,
        presentation_text: t.presentation_text,
      })),
    })),
  };
  for (const seq of packet.sequences) {
    for (const turn of seq.turns) {
      if (!turn.presentation_text || turn.presentation_text.startsWith('[')) {
        throw new Error(`missing presentation for ${seq.blind_label} T${turn.turn_index}`);
      }
    }
  }
  return { packet, enrichedPlan };
}

function checkpointSlice(seq, throughTurn) {
  return seq.turns
    .filter((t) => t.turn_index <= throughTurn)
    .map((t) => ({
      turn_index: t.turn_index,
      player_stimulus: t.exact_player_stimulus ?? t.player_stimulus,
      presentation_text: t.presentation_text,
    }));
}

function aggregateCosts(sequences) {
  const byArm = {};
  const byScenario = {};
  for (const seq of sequences) {
    const arm = seq.arm;
    const scenario = seq.scenario_key;
    byArm[arm] ??= emptyCostBucket(arm);
    byScenario[scenario] ??= emptyCostBucket(scenario);
    const rollup = seq.cost_rollup ?? {};
    const inf = seq.turns.reduce((acc, t) => {
      const i = t.inference ?? {};
      acc.inference_count += i.inference_count ?? 0;
      acc.sync += i.synchronous_llm_count ?? 0;
      acc.input += i.input_tokens_total ?? 0;
      acc.output += i.output_tokens_total ?? 0;
      acc.reasoning += i.reasoning_tokens_total ?? 0;
      acc.wall += t.operation_wall_ms ?? 0;
      acc.retries += i.retry_count ?? 0;
      return acc;
    }, { inference_count: 0, sync: 0, input: 0, output: 0, reasoning: 0, wall: 0, retries: 0 });
    addBucket(byArm[arm], rollup, inf, seq);
    addBucket(byScenario[scenario], rollup, inf, seq);
  }
  return { byArm, byScenario };
}

function emptyCostBucket(label) {
  return {
    label,
    sequences: 0,
    turns: 0,
    inference_count: 0,
    sync_calls: 0,
    input_tokens: 0,
    output_tokens: 0,
    reasoning_tokens: 0,
    wall_ms: 0,
    retry_count: 0,
    generated_obligations: 0,
    consequential_activations: 0,
    useful_deferred: 0,
    premature_activations: 0,
    tracked_dead: 0,
  };
}

function addBucket(bucket, rollup, inf, seq) {
  bucket.sequences += 1;
  bucket.turns += seq.turn_count_completed ?? 22;
  bucket.inference_count += inf.inference_count;
  bucket.sync_calls += inf.sync;
  bucket.input_tokens += inf.input;
  bucket.output_tokens += inf.output;
  bucket.reasoning_tokens += inf.reasoning;
  bucket.wall_ms += inf.wall;
  bucket.retry_count += inf.retries;
  bucket.generated_obligations += rollup.generated_obligations ?? 0;
  bucket.consequential_activations += rollup.consequential_activations ?? 0;
  bucket.useful_deferred += rollup.useful_deferred_obligations ?? 0;
  bucket.premature_activations += rollup.premature_activations ?? 0;
  bucket.tracked_dead += rollup.tracked_dead_obligations ?? 0;
}

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const rubric = JSON.parse(fs.readFileSync(RUBRIC_PATH, 'utf8'));
  const sequences = loadSequences();
  const campaignPlan = loadCampaignPlan();
  const placeholderPacketPath = path.join(CAMPAIGN_DIR, 'issue201-lh1a-blind-sequence-packet.json');
  const answerKeyPath = path.join(CAMPAIGN_DIR, 'issue201-lh1a-blind-sequence-answer-key.json');

  const integrityReport = {
    sequence_count: sequences.length,
    all_22_turns: sequences.every((s) => s.turn_count_completed === 22 && !s.failed),
    sequences: sequences.map((s) => ({
      blind_label: s.blind_label,
      session: s.hg_session_id,
      turns: s.turn_count_completed,
      failed: s.failed,
    })),
    placeholder_packet_hash: sha256File(placeholderPacketPath),
    placeholder_packet_has_presentations: false,
    answer_key_hash: sha256File(answerKeyPath),
    rubric_hash: sha256File(RUBRIC_PATH),
    rubric_hash_expected: 'f533cc604b276f7798639db863c8e2264254233ab162de03b343841df840bb91',
  };

  const { packet: evalPacket, enrichedPlan } = rebuildEvaluableBlindPacket(sequences, campaignPlan, rubric);
  const blindIntegrity = validateLh1aBlindPacketIntegrity(evalPacket);
  const evalPacketPath = path.join(OUT_DIR, 'issue201-lh1a-blind-sequence-packet-evaluable.json');
  fs.writeFileSync(evalPacketPath, `${JSON.stringify(evalPacket, null, 2)}\n`);

  const checkpointSlices = {};
  for (const seq of sequences) {
    checkpointSlices[seq.blind_label] = {
      C1: checkpointSlice(seq, LH1A_CHECKPOINTS.C1),
      C2: checkpointSlice(seq, LH1A_CHECKPOINTS.C2),
      C3: checkpointSlice(seq, LH1A_CHECKPOINTS.C3),
    };
  }

  const costs = aggregateCosts(sequences);
  const report = {
    schema: 'issue201_lh1a_blind_integrity_v1',
    campaign_dir: CAMPAIGN_DIR,
    remediation_pre_commit_sha: '818afc9a3c9b3e44ab9460ed8558b4c36cb84411',
    remediation_commit_sha: 'bc569c6',
    integrity: integrityReport,
    evaluable_packet_path: evalPacketPath,
    evaluable_packet_sha256: sha256File(evalPacketPath),
    blind_integrity: blindIntegrity,
    checkpoint_slices_path: path.join(OUT_DIR, 'issue201-lh1a-checkpoint-slices.json'),
    costs,
    answer_key_hash: integrityReport.answer_key_hash,
  };

  fs.writeFileSync(
    path.join(OUT_DIR, 'issue201-lh1a-checkpoint-slices.json'),
    `${JSON.stringify(checkpointSlices, null, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(OUT_DIR, 'issue201-lh1a-blind-integrity-report.json'),
    `${JSON.stringify(report, null, 2)}\n`,
  );
  console.log(JSON.stringify(report, null, 2));
}

main();
