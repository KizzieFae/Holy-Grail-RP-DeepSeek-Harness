/**
 * Issue #136 G2 (Storyteller sentinel) + G3 (A-STABILITY ×1) gate runner.
 * Not a full Tier-2 campaign.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  runIssue136FixtureCampaign,
  runIssue136ProductionSentinel,
  ISSUE136_IMPLEMENTATION_SHA,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CANDIDATE_SHA = process.env.ISSUE136_CANDIDATE_SHA ?? ISSUE136_IMPLEMENTATION_SHA;

function storytellerDetail(roundResult) {
  const st = roundResult?.storyteller ?? {};
  return {
    activation: st.bound ? 'active' : (st.skipped ? 'skipped' : 'degraded'),
    bound: st.bound ?? false,
    skipped: st.skipped ?? false,
    package_id: st.package_id ?? null,
    degradation_level: st.degradation_level ?? null,
    assessment_evidence_id: st.assessment_evidence_id ?? null,
    mapped_preview: st.mapped_preview ?? null,
    invalidated: st.invalidated === true,
    invalidation_reason: st.invalidation_reason ?? null,
    stage: st.stage ?? null,
    reason: st.reason ?? null,
  };
}

function extractCharacterForensics(roundResult) {
  const turns = roundResult?.character_turns ?? [];
  const turn = turns[0] ?? null;
  const trace = turn?.character_inference_trace ?? turn?.characterInferenceTrace ?? {};
  const attempts = trace.attempts ?? trace.candidate_attempts ?? [];
  return {
    character_id: turn?.character_id ?? null,
    committed: turn?.committed ?? null,
    domain_commit_id: turn?.domain_commit_id ?? null,
    proposed_move: turn?.proposed_move ?? null,
    validated_move: turn?.validated_move ?? null,
    attempts: attempts.map((a, i) => ({
      attempt_index: a.attempt_index ?? i,
      accepted: a.accepted ?? null,
      outcome: a.outcome ?? null,
      raw_output_preview: String(a.raw_output ?? a.candidate_text ?? '').slice(0, 800),
    })),
  };
}

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const gateRoot = path.join(
    REPO_ROOT,
    'data',
    'issue136_g2_g3_gates',
    new Date().toISOString().replace(/[:.]/g, '-'),
  );
  fs.mkdirSync(gateRoot, { recursive: true });

  const report = {
    schema: 'issue136_g2_g3_gate_report_v1',
    candidate_sha: CANDIDATE_SHA,
    greptile_reviewed_sha: 'f679dc45e166eb93741335cab3dafc6307adac44',
    gate_root: gateRoot,
    g2: null,
    g3: null,
  };

  // G2 — Storyteller infrastructure sentinel
  const g2Dir = path.join(gateRoot, 'g2-sentinel');
  const g2 = await runIssue136ProductionSentinel({
    mode: 'live',
    campaignDataDir: g2Dir,
  });
  const g2Round = g2.round_result ?? {};
  const g2Text = JSON.stringify(g2).toLowerCase();
  report.g2 = {
    run_id: g2.run_id,
    report_path: g2.report_path,
    mode: g2.mode,
    profiles: g2.profiles,
    storyteller: storytellerDetail(g2Round),
    instrumentation: g2.instrumentation,
    limits: g2.limits,
    dict_string_http_400_observed: g2Text.includes('dict(string)') && g2Text.includes('400'),
    evidence_anchors: {
      hg_session_id: g2Round.hg_session_id ?? null,
      hg_round_id: g2Round.hg_round_id ?? null,
      assessment_evidence_id: g2Round.storyteller?.assessment_evidence_id ?? null,
    },
  };

  // G3 — Tier-2 A-STABILITY ×1
  const g3Dir = path.join(gateRoot, 'g3-a-stability-rep-1');
  const g3 = await runIssue136FixtureCampaign({
    fixtureId: '136-T2-A-STABILITY',
    repetition: 1,
    mode: 'live',
    campaignDataDir: g3Dir,
  });
  const g3Round = g3.round_result ?? {};
  report.g3 = {
    run_id: g3.run_id,
    report_path: g3.report_path,
    fixture_id: g3.fixture_id,
    repetition: g3.repetition,
    mode: g3.mode,
    forensic: g3.forensic,
    storyteller: storytellerDetail(g3Round),
    character: extractCharacterForensics(g3Round),
    limits: g3.limits,
    profiles: g3.forensic?.model_provider_config ?? null,
    evidence_anchors: {
      hg_session_id: g3.forensic?.evidence?.hg_session_id ?? g3Round.hg_session_id ?? null,
      hg_round_id: g3Round.hg_round_id ?? null,
      report_path: g3.report_path,
    },
  };

  const outPath = path.join(gateRoot, 'g2-g3-gate-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
