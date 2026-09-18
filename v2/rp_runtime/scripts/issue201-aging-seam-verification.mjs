#!/usr/bin/env node
/**
 * Issue #201 — information-aging qualification and live campaign.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT, gitSha } from './lib/issue201-lh0-lib.mjs';
import { runAgingApparatusQualification } from './lib/issue201-aging-qualification-lib.mjs';
import { executeAgingLiveCampaign } from './lib/issue201-aging-live-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = { qualify: false, executeCampaign: false, liveAuthorized: false, outputDir: null, skipPantry: false };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--qualify') args.qualify = true;
    if (argv[i] === '--execute-campaign') args.executeCampaign = true;
    if (argv[i] === '--live-authorized') args.liveAuthorized = true;
    if (argv[i] === '--skip-pantry-regression') args.skipPantry = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir(prefix) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 10);
  return path.join(REPO_ROOT, 'data/investigation_runs', `${prefix}-${stamp}`);
}

const args = parseArgs(process.argv);

if (args.executeCampaign) {
  if (!args.liveAuthorized) {
    console.error('Live campaign requires --live-authorized');
    process.exit(1);
  }
  const outputDir = args.outputDir ?? defaultOutputDir('issue201-aging-live-campaign');
  const report = await executeAgingLiveCampaign({ outputDir, liveAuthorized: true });
  console.log(JSON.stringify({ execution_sha: gitSha(), report }, null, 2));
  process.exit(report.fail_closed ? 1 : 0);
}

if (!args.qualify) {
  console.error('Usage: node issue201-aging-seam-verification.mjs --qualify [--skip-pantry-regression] | --execute-campaign --live-authorized [--output-dir PATH]');
  process.exit(1);
}

const report = await runAgingApparatusQualification({ skipPantryRegression: args.skipPantry });
console.log(JSON.stringify(report, null, 2));
process.exit(report.pass ? 0 : 1);
