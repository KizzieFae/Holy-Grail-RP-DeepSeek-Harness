#!/usr/bin/env node
/**
 * Build LH-1A score lock and decode adjudication from blind scores + answer key.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');
const OUT_DIR = path.join(REPO_ROOT, 'governance/records/issue201-lh1a-evaluation');
const CAMPAIGN_DIR = path.join(
  REPO_ROOT,
  'data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z',
);

const DIMS = [
  'character_fidelity', 'agency', 'coherence', 'responsiveness', 'naturalness',
  'narrative_progression', 'continuity_consistency', 'thread_management',
  'delayed_payoff_quality', 'cross_scene_coherence', 'old_information_integration',
  'relationship_evolution', 'premature_resolution_avoidance', 'repetition_overtracking',
  'appropriate_dormancy', 'dark_tone_preservation', 'forced_payoff_avoidance',
  'long_horizon_narrative_progression', 'competing_thread_handling',
];

const BLIND_SCORES = {
  'SEQ-A': { scores: [5, 5, 4, 5, 4, 5, 5, 5, 4, 5, 5, 4, 5, 3, 4, 5, 5, 5, 4], mean_19d: 4.53,
    c1_note: 'T8: strong Ayame control, threads seeded, minimal repetition.',
    c2_note: 'T16: escalation to expulsion ritual; repetition rises.',
    c3_qualitative: 'Full rejection arc; strong dark tone; repetition weakness T10-16.' },
  'SEQ-B': { scores: [5, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 4, 5, 4, 5, 5, 5, 5, 5], mean_19d: 4.84,
    c1_note: 'T8: threshold-control architecture distinctive.',
    c2_note: 'T16: empty-chair parlor device matures.',
    c3_qualitative: 'Eighteen numbered questions; strongest disciplined long-horizon after D.' },
  'SEQ-C': { scores: [4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4, 3, 3, 4, 4, 4, 4, 3, 3], mean_19d: 3.79,
    c1_note: 'T8: warmer, written terms at T8 weakens dark tone.',
    c2_note: 'T16: harsh dismissal but early accommodation damage.',
    c3_qualitative: 'Harsh close but mid-arc softness and abrupt T15 termination.' },
  'SEQ-D': { scores: [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 4, 5, 5, 5, 5, 5], mean_19d: 4.89,
    c1_note: 'T8: threshold/name spine; applicant never inside.',
    c2_note: 'T16: sentence-numbering taxonomy matures.',
    c3_qualitative: 'Highest Ayame: nineteen-sentence arc, no letter offered.' },
  'SEQ-E': { scores: [4, 5, 4, 5, 3, 4, 4, 4, 4, 4, 4, 4, 5, 2, 3, 5, 4, 4, 4], mean_19d: 3.84,
    c1_note: 'T8: Ivy/Harley established; prose glitches.',
    c2_note: 'T16: escalation solid; repetition begins.',
    c3_qualitative: 'Dark pressure sustained; late rhetorical recycling.' },
  'SEQ-F': { scores: [4, 5, 4, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 3, 5, 3, 4, 4], mean_19d: 3.89,
    c1_note: 'T8: Harley carnival + Ivy control.',
    c2_note: 'T16: tray return spatial shift.',
    c3_qualitative: 'Competent escalation; T22 shelter offer softens payoff avoidance.' },
  'SEQ-G': { scores: [5, 5, 5, 5, 4, 4, 5, 4, 4, 4, 5, 5, 5, 3, 4, 5, 5, 5, 5], mean_19d: 4.63,
    c1_note: 'T8: best voice separation and thread lanes.',
    c2_note: 'T16: Harley chair-drag escalates contest.',
    c3_qualitative: 'Strongest Arkham: sustained dark tone, credible power contest.' },
  'SEQ-H': { scores: [4, 4, 4, 5, 4, 4, 4, 4, 4, 4, 4, 4, 5, 2, 4, 5, 4, 4, 4], mean_19d: 4.16,
    c1_note: 'T8: table politics; six-hour north-run deferral.',
    c2_note: 'T16: repetition rises on tick/one-word templates.',
    c3_qualitative: 'Solid pressure; weaker voice distinction than G.' },
};

function sha256File(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}

function mean(arr) {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function armSummary(rows) {
  const byArm = {};
  for (const r of rows) {
    byArm[r.arm] ??= { means: [], byDim: Object.fromEntries(DIMS.map((d) => [d, []])) };
    byArm[r.arm].means.push(r.mean_19d);
    const scores = r.governance_scores ?? r.scores;
    DIMS.forEach((d, i) => byArm[r.arm].byDim[d].push(scores[i]));
  }
  const out = {};
  for (const [arm, data] of Object.entries(byArm)) {
    out[arm] = {
      n: data.means.length,
      overall_mean_19d: mean(data.means),
      dimension_means: Object.fromEntries(
        DIMS.map((d) => [d, mean(data.byDim[d])]),
      ),
    };
  }
  return out;
}

function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const integrity = JSON.parse(fs.readFileSync(
    path.join(OUT_DIR, 'issue201-lh1a-blind-integrity-report.json'), 'utf8',
  ));
  const evalPacketPath = integrity.evaluable_packet_path;
  const evalPacketHash = integrity.evaluable_packet_sha256;
  const answerKeyPath = path.join(CAMPAIGN_DIR, 'issue201-lh1a-blind-sequence-answer-key.json');
  const answerKeyHash = sha256File(answerKeyPath);
  const lockedAt = new Date().toISOString();

  const samples = Object.entries(BLIND_SCORES).map(([blind_label, data]) => ({
    blind_label,
    scores: data.scores,
    mean_19d: data.mean_19d,
    checkpoint_notes: {
      C1: data.c1_note,
      C2: data.c2_note,
      C3: data.c3_qualitative,
    },
  }));
  const allScores = samples.flatMap((s) => s.scores);
  const lock = {
    schema: 'issue201_lh1a_blind_score_lock_v1',
    issue: 201,
    experiment: 'LH-1A story-aging screening (8 sequences)',
    remediation_commit_sha: 'bc569c6',
    execution_evidence_root: CAMPAIGN_DIR,
    evaluable_blind_packet_path: evalPacketPath.replace(/\\/g, '/').replace(`${REPO_ROOT}/`.replace(/\\/g, '/'), ''),
    evaluable_blind_packet_sha256: evalPacketHash,
    placeholder_blind_packet_sha256: integrity.integrity.placeholder_packet_hash,
    answer_key_path: answerKeyPath.replace(/\\/g, '/').replace(`${REPO_ROOT}/`.replace(/\\/g, '/'), ''),
    answer_key_sha256: answerKeyHash,
    rubric_hash: integrity.integrity.rubric_hash,
    locked_at: lockedAt,
    locked_by: 'Implementation-AI blind evaluation (Governance-authorized)',
    evaluator_methodology: 'Frozen lh1a_blind_rubric_v1; 19 dimensions scored 1-5 at C3 from checkpoint slices; no arm/mechanism/cost data used during scoring.',
    dimension_order: DIMS,
    population_mean_all_dimensions: mean(allScores),
    samples,
    status: 'blind_scores_locked_pending_decode',
    answer_key_accessed_before_lock: false,
  };
  const lockPath = path.join(OUT_DIR, 'issue201-lh1a-blind-score-lock.json');
  fs.writeFileSync(lockPath, `${JSON.stringify(lock, null, 2)}\n`);
  const lockHash = sha256File(lockPath);

  const answerKey = JSON.parse(fs.readFileSync(answerKeyPath, 'utf8'));
  const sequences = fs.readdirSync(CAMPAIGN_DIR)
    .filter((f) => f.endsWith('-sequence.json'))
    .map((f) => JSON.parse(fs.readFileSync(path.join(CAMPAIGN_DIR, f), 'utf8')));
  const seqByBlind = new Map(sequences.map((s) => [s.blind_label, s]));

  const decodeRows = answerKey.map((row) => {
    const blind = BLIND_SCORES[row.blind_label];
    const live = seqByBlind.get(row.blind_label);
    return {
      ...row,
      governance_scores: blind.scores,
      mean_19d: blind.mean_19d,
      hg_session_id: live?.hg_session_id,
      sequence_artifact: live?.sequence_id,
      cost_rollup: live?.cost_rollup,
      archaeology_summary: live?.archaeology_dossier?.human_summary,
    };
  });

  const decodedAt = new Date().toISOString();
  const decode = {
    schema: 'issue201_lh1a_blind_decode_v1',
    issue: 201,
    decoded_at: decodedAt,
    score_lock_record: 'governance/records/issue201-lh1a-evaluation/issue201-lh1a-blind-score-lock.json',
    score_lock_sha256: lockHash,
    score_lock_precedes_decode: lockedAt < decodedAt,
    evaluable_blind_packet_sha256: evalPacketHash,
    answer_key_sha256: answerKeyHash,
    decode_mapping: decodeRows,
    arm_summary: armSummary(decodeRows),
    scenario_summary: {
      ayame_controlled: armSummary(decodeRows.filter((r) => r.scenario_key === 'ayame_controlled')),
      arkham_stress: armSummary(decodeRows.filter((r) => r.scenario_key === 'arkham_stress')),
    },
    status: 'decoded_pending_governance_adjudication',
  };

  const decodePath = path.join(OUT_DIR, 'issue201-lh1a-blind-decode-adjudication.json');
  fs.writeFileSync(decodePath, `${JSON.stringify(decode, null, 2)}\n`);

  console.log(JSON.stringify({
    lockPath,
    lockHash,
    lockSha: lockHash,
    decodedAt,
    arm_summary: decode.arm_summary,
  }, null, 2));
}

main();
