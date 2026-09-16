#!/usr/bin/env node
/**
 * Issue #201 LH-1A — long-horizon apparatus verification and live campaign.
 * --validate-apparatus: deterministic validation only (no live inference).
 * --preflight: mandatory pre-live gates.
 * --execute-campaign: run eight live sequences (requires passing preflight).
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT, runValidateLh1aApparatus } from './lib/issue201-lh1a-lib.mjs';
import { runLh1aLivePreflight, executeLh1aLiveCampaign } from './lib/issue201-lh1a-live-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {
    validateApparatus: false,
    preflight: false,
    executeCampaign: false,
    outputDir: null,
  };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--preflight') args.preflight = true;
    if (argv[i] === '--execute-campaign') args.executeCampaign = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir(prefix) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data/investigation_runs', `${prefix}-${stamp}`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.validateApparatus && !args.preflight && !args.executeCampaign) {
    console.error('Usage: node issue201-lh1a-seam-verification.mjs (--validate-apparatus | --preflight | --execute-campaign) [--output-dir PATH]');
    process.exit(1);
  }

  if (args.validateApparatus) {
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh1a-apparatus-validation');
    const report = runValidateLh1aApparatus({ outputDir });
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.validation.all_pass ? 0 : 1);
  }

  if (args.preflight) {
    const report = runLh1aLivePreflight();
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.all_pass ? 0 : 1);
  }

  if (args.executeCampaign) {
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh1a-live-campaign');
    const preflight = runLh1aLivePreflight();
    if (!preflight.all_pass) {
      console.error(JSON.stringify({ error: 'preflight_failed', preflight }, null, 2));
      process.exit(1);
    }
    const report = await executeLh1aLiveCampaign({ outputDir, preflightReport: preflight });
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.campaign_failed ? 1 : 0);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
