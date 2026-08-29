import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { CampaignLimits } from '../src/scenario-harness/campaign-limits.mjs';
import { buildCampaignReport } from '../src/scenario-harness/campaign-report.mjs';
import { hasLiveApiKey } from '../src/scenario-harness/live-config.mjs';
import {
  campaignDataRoot,
  runC1_T1_01_live,
  runC2_T1_02_live,
} from '../src/scenario-harness/tier1-tranche2.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Live contract-conformance smoke (#65).
 * 4 scenarios, max 12 live calls (4 prod + up to 4 corrections + 4 cert evaluators).
 */
export const CONTRACT_SMOKE_CASES = [
  { case_id: 'S1', label: 'init', runner: runC1_T1_01_live },
  { case_id: 'S2', label: 'update', runner: runC2_T1_02_live },
];

// C4/C5 imported lazily to avoid circular deps — same module
async function runC4() {
  const { runC4_T1_05_live } = await import('../src/scenario-harness/tier1-tranche2.mjs');
  return runC4_T1_05_live;
}
async function runC5() {
  const { runC5_T1_06_unsafe_live } = await import('../src/scenario-harness/tier1-tranche2.mjs');
  return runC5_T1_06_unsafe_live;
}

export const CONTRACT_SMOKE_CALL_CEILING = 12;

export async function runContractSmokeCampaign() {
  const campaignDataDir = path.join(
    campaignDataRoot('contract_smoke'),
    `run-${crypto.randomUUID()}`,
  );
  const limits = new CampaignLimits({ maxRuns: 4, maxInferences: CONTRACT_SMOKE_CALL_CEILING });
  const results = [];
  const hardBlockers = [];

  const runners = [
    { case_id: 'S1', runner: runC1_T1_01_live },
    { case_id: 'S2', runner: runC2_T1_02_live },
    { case_id: 'S3', runner: await runC4() },
    { case_id: 'S4', runner: await runC5() },
  ];

  for (const entry of runners) {
    if (limits.stopped) break;
    limits.assertCanRun();
    const outcome = await entry.runner(limits, campaignDataDir);
    const blockerAnalysis = outcome.blockerAnalysis ?? outcome.result?.campaign?.hard_blockers ?? { has_blocker: false, blockers: [] };
    if (blockerAnalysis.has_blocker) {
      hardBlockers.push(...blockerAnalysis.blockers);
      limits.stop('hard_blocker');
    }
    results.push({ case_id: entry.case_id, ...outcome });
  }

  const report = buildCampaignReport({
    schema: 'hg_storyteller_contract_smoke_report_v1',
    tranche: 'contract_smoke',
    limits,
    results,
    hardBlockers,
  });
  report.campaign_data_dir = campaignDataDir;
  return report;
}

async function main() {
  if (!hasLiveApiKey()) {
    console.error('DEEPSEEK_API_KEY not set; cannot execute contract smoke.');
    process.exit(2);
  }
  const reportPath = process.argv[2]
    ?? path.join(__dirname, '..', 'tmp', 'contract-smoke-report.json');
  const report = await runContractSmokeCampaign();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    report_path: reportPath,
    scenario_runs: report.totals.scenario_runs,
    live_calls: report.totals.live_inference_calls,
    call_ceiling: CONTRACT_SMOKE_CALL_CEILING,
    hard_blockers: report.hard_blockers.length,
    tokens: report.totals.tokens,
  }, null, 2));
  if (report.hard_blockers.length > 0) process.exit(1);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
