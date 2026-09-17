#!/usr/bin/env node
/**
 * Issue #201 LH-1B — apparatus verification, runner qualification, live campaign entry.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT, gitSha } from './lib/issue201-lh0-lib.mjs';
import { runLh1bApparatusValidationSuite } from './lib/issue201-lh1b-validation-lib.mjs';
import { runLh1bLivePreflight } from './lib/issue201-lh1b-live-preflight-lib.mjs';
import { runLh1bRunnerMockQualification } from './lib/issue201-lh1b-runner-qualification-lib.mjs';
import { executeLh1bLiveCampaign } from './lib/issue201-lh1b-live-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {
    validateApparatus: false,
    qualifyRunner: false,
    preflight: false,
    executeCampaign: false,
    outputDir: null,
  };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--qualify-runner') args.qualifyRunner = true;
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
  if (!args.validateApparatus && !args.qualifyRunner && !args.preflight && !args.executeCampaign) {
    console.error('Usage: node issue201-lh1b-seam-verification.mjs (--validate-apparatus | --qualify-runner | --preflight | --execute-campaign) [--output-dir PATH]');
    process.exit(1);
  }

  if (args.validateApparatus) {
    const report = runLh1bApparatusValidationSuite();
    console.log(JSON.stringify(report, null, 2));
    process.exit(report.pass ? 0 : 1);
  }

  if (args.qualifyRunner) {
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh1b-runner-qualification');
    const qualification = await runLh1bRunnerMockQualification({ evidenceRoot: outputDir });
    const report = {
      execution_candidate_sha: gitSha(),
      qualification,
      apparatus: runLh1bApparatusValidationSuite(),
    };
    console.log(JSON.stringify(report, null, 2));
    process.exit(qualification.pass ? 0 : 1);
  }

  if (args.preflight) {
    const qualification = await runLh1bRunnerMockQualification();
    const report = runLh1bLivePreflight({
      requireRunnerQualification: true,
      runnerQualification: qualification,
    });
    console.log(JSON.stringify({ ...report, runner_qualification: qualification }, null, 2));
    process.exit(report.all_pass ? 0 : 1);
  }

  if (args.executeCampaign) {
    const preflight = runLh1bLivePreflight();
    if (!preflight.all_pass) {
      console.error(JSON.stringify({ error: 'preflight_failed', preflight }, null, 2));
      process.exit(1);
    }
    const outputDir = args.outputDir ?? defaultOutputDir('issue201-lh1b-live-campaign');
    const report = await executeLh1bLiveCampaign({
      outputDir,
      preflightReport: preflight,
      liveAuthorized: false,
    });
    console.log(JSON.stringify(report, null, 2));
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
