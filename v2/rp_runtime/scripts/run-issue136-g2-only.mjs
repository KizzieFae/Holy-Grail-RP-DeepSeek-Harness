/**
 * Issue #136 G2-only live sentinel (Storyteller-bound gate).
 * Does NOT run G3 or Tier-2 campaign.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  runIssue136ProductionSentinel,
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
    mapped_preview: st.mapped_preview ?? null,
    invalidated: st.invalidated === true,
    invalidation_reason: st.invalidation_reason ?? null,
    stage: st.stage ?? null,
    reason: st.reason ?? null,
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
  const g2Dir = path.join(gateRoot, 'g2-sentinel');
  fs.mkdirSync(g2Dir, { recursive: true });

  const g2 = await runIssue136ProductionSentinel({
    mode: 'live',
    campaignDataDir: g2Dir,
  });
  const g2Round = g2.round_result ?? {};
  const g2Text = JSON.stringify(g2).toLowerCase();

  const report = {
    schema: 'issue136_g2_gate_report_v1',
    gate: 'G2',
    candidate_sha: process.env.ISSUE136_CANDIDATE_SHA ?? ISSUE136_IMPLEMENTATION_SHA,
    execution_sha: process.env.ISSUE136_EXECUTION_SHA ?? null,
    gate_root: gateRoot,
    g2: {
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
      round_result: g2Round,
    },
  };

  const outPath = path.join(gateRoot, 'g2-gate-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
