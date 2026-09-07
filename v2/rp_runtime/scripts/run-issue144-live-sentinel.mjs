/**
 * Issue #144 bounded live Storyteller orientation sentinel (single attempt).
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { runIssue136ProductionSentinel } from '../src/scenario-harness/issue136-tier2-campaign.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from '../src/lib/live-inference-prompts.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CANDIDATE_SHA = process.env.ISSUE144_CANDIDATE_SHA ?? 'working-tree';

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const gateRoot = path.join(
    REPO_ROOT,
    'data',
    'issue144_live_sentinel',
    new Date().toISOString().replace(/[:.]/g, '-'),
  );
  fs.mkdirSync(gateRoot, { recursive: true });

  const g2 = await runIssue136ProductionSentinel({
    mode: 'live',
    campaignDataDir: gateRoot,
  });
  const st = g2.round_result?.storyteller ?? {};
  const report = {
    schema: 'issue144_live_sentinel_report_v1',
    candidate_sha: CANDIDATE_SHA,
    provider: 'deepseek-official',
    model: 'deepseek-v4-flash',
    reasoning: 'low',
    dsh_transport_prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
    storyteller: {
      bound: st.bound ?? false,
      skipped: st.skipped ?? false,
      stage: st.stage ?? null,
      reason: st.reason ?? null,
      package_id: st.package_id ?? null,
    },
    run_id: g2.run_id,
    report_path: g2.report_path,
    gate_root: gateRoot,
    profiles: g2.profiles,
    evidence_anchors: {
      hg_session_id: g2.round_result?.hg_session_id ?? null,
      hg_round_id: g2.round_result?.hg_round_id ?? null,
      assessment_evidence_id: st.assessment_evidence_id ?? null,
    },
  };
  const outPath = path.join(gateRoot, 'issue144-live-sentinel-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (!st.bound) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
