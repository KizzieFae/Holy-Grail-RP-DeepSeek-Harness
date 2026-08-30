#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { hasLiveApiKey } from '../src/scenario-harness/live-config.mjs';
import {
  estimatePhaseDCallCeiling,
  PHASE_D_INFERENCE_CEILING,
  runPhaseDCampaign,
} from '../src/scenario-harness/tier2-characterization.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const reportPath = process.argv[2]
  ?? path.join(__dirname, '..', 'tmp', 'phase-d-report.json');

async function main() {
  const ceiling = estimatePhaseDCallCeiling();
  console.log(JSON.stringify({ phase_d_call_ceiling: ceiling }, null, 2));

  if (!hasLiveApiKey()) {
    console.error('DEEPSEEK_API_KEY not set; cannot execute Phase D live campaign.');
    process.exit(2);
  }

  const report = await runPhaseDCampaign();
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    report_path: reportPath,
    campaign_data_dir: report.campaign_data_dir,
    scenario_runs: report.totals.scenario_runs,
    live_inference_calls: report.totals.live_inference_calls,
    call_ceiling: PHASE_D_INFERENCE_CEILING,
    hard_blockers: report.hard_blockers.length,
    stopped: report.limits.stopped,
    stop_reason: report.limits.stop_reason,
    tokens: report.totals.tokens,
    phase_d_analysis: report.phase_d_analysis,
  }, null, 2));
  if (report.hard_blockers.length > 0) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
