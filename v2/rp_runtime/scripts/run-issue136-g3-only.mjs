/**
 * Issue #136 G3-only live gate: 136-T2-A-STABILITY ×1.
 * Does NOT run G2, other fixtures, or full Tier-2 campaign.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  runIssue136FixtureCampaign,
  ISSUE136_IMPLEMENTATION_SHA,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

function storytellerDetail(roundResult) {
  const st = roundResult?.storyteller ?? {};
  return {
    activation: st.bound ? 'active' : (st.skipped ? 'skipped' : 'degraded'),
    bound: st.bound ?? false,
    skipped: st.skipped ?? false,
    package_id: st.package_id ?? null,
    degradation_level: st.degradation_level ?? null,
    assessment_evidence_id: st.assessment_evidence_id ?? null,
    stage: st.stage ?? null,
    reason: st.reason ?? null,
  };
}

function extractCharacterForensics(roundResult) {
  const turns = roundResult?.character_turns ?? [];
  const turn = turns.find((t) => t.character_id === 'Mara') ?? turns[0] ?? null;
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
      raw_output_preview: String(a.raw_output ?? a.candidate_text ?? '').slice(0, 1200),
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
  const g3Dir = path.join(gateRoot, 'g3-a-stability-rep-1');
  fs.mkdirSync(g3Dir, { recursive: true });

  const g3 = await runIssue136FixtureCampaign({
    fixtureId: '136-T2-A-STABILITY',
    repetition: 1,
    mode: 'live',
    campaignDataDir: g3Dir,
  });
  const g3Round = g3.round_result ?? {};

  const report = {
    schema: 'issue136_g3_gate_report_v1',
    gate: 'G3',
    fixture_id: '136-T2-A-STABILITY',
    repetition: 1,
    candidate_sha: process.env.ISSUE136_CANDIDATE_SHA ?? ISSUE136_IMPLEMENTATION_SHA,
    execution_sha: process.env.ISSUE136_EXECUTION_SHA ?? null,
    gate_root: gateRoot,
    g3: {
      run_id: g3.run_id,
      report_path: g3.report_path,
      mode: g3.mode,
      forensic: g3.forensic,
      storyteller: storytellerDetail(g3Round),
      character: extractCharacterForensics(g3Round),
      limits: g3.limits,
      profiles: g3.forensic?.model_provider_config ?? null,
      evidence_anchors: {
        hg_session_id: g3.forensic?.evidence?.hg_session_id ?? g3Round.hg_session_id ?? null,
        hg_round_id: g3Round.hg_round_id ?? null,
      },
      round_result: g3Round,
    },
  };

  const outPath = path.join(gateRoot, 'g3-gate-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
