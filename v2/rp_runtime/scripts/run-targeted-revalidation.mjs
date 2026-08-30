#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { hasLiveApiKey } from '../src/scenario-harness/live-config.mjs';
import {
  runTargetedRevalidationCampaign,
  TARGETED_REVALIDATION_CEILING,
} from '../src/scenario-harness/tier1-tranche2.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const reportPath = process.argv[2]
  ?? path.join(__dirname, '..', 'tmp', 'targeted-revalidation-report.json');

async function main() {
  if (!hasLiveApiKey()) {
    console.error('DEEPSEEK_API_KEY not set; cannot execute targeted live revalidation.');
    process.exit(2);
  }
  const report = await runTargetedRevalidationCampaign();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    report_path: reportPath,
    campaign_data_dir: report.campaign_data_dir,
    scenario_runs: report.totals.scenario_runs,
    live_inference_calls: report.totals.live_inference_calls,
    call_ceiling: TARGETED_REVALIDATION_CEILING,
    hard_blockers: report.hard_blockers.length,
    stopped: report.limits.stopped,
    stop_reason: report.limits.stop_reason,
    tokens: report.totals.tokens,
  }, null, 2));
  if (report.hard_blockers.length > 0) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
