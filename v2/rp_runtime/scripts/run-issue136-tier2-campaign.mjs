#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { hasLiveApiKey } from '../src/scenario-harness/live-config.mjs';
import {
  deriveIssue136SafetyGuard,
  proveProductionInferenceUnchanged,
  runIssue136Tier2Campaign,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  const mode = process.argv.includes('--live') ? 'live' : 'mock';
  const reportPath = process.argv.find((arg) => !arg.startsWith('--') && arg.endsWith('.json'))
    ?? path.join(__dirname, '..', 'tmp', `issue136-tier2-${mode}-report.json`);

  if (mode === 'live' && !hasLiveApiKey()) {
    console.error('DEEPSEEK_API_KEY not set; cannot execute live Issue #136 Tier-2 campaign.');
    process.exit(2);
  }

  const guard = deriveIssue136SafetyGuard();
  const productionProof = proveProductionInferenceUnchanged();
  const report = await runIssue136Tier2Campaign({ mode });
  const envelope = {
    ...report,
    safety_guard_recorded: guard,
    production_inference_proof: productionProof,
  };

  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(envelope, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    report_path: reportPath,
    mode,
    campaign_data_dir: report.campaign_data_dir,
    runs: report.runs.length,
    safety_guard: guard,
    production_unchanged: productionProof.unchanged,
    limits: report.limits,
  }, null, 2));

  if (!productionProof.unchanged) {
    console.error('Production inference paths changed since implementation SHA.');
    process.exit(3);
  }
  if (report.limits.stopped) {
    process.exit(4);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
