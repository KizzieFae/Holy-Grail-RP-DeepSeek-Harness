#!/usr/bin/env node
/**
 * Issue #201 LH-1A — long-horizon apparatus verification.
 * --validate-apparatus: deterministic validation only (no live inference).
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { REPO_ROOT, runValidateLh1aApparatus } from './lib/issue201-lh1a-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = { validateApparatus: false, outputDir: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--validate-apparatus') args.validateApparatus = true;
    if (argv[i] === '--output-dir' && argv[i + 1]) {
      args.outputDir = argv[i + 1];
      i += 1;
    }
  }
  return args;
}

function defaultOutputDir() {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data/investigation_runs', `issue201-lh1a-apparatus-validation-${stamp}`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.validateApparatus) {
    console.error('Usage: node issue201-lh1a-seam-verification.mjs --validate-apparatus [--output-dir PATH]');
    process.exit(1);
  }
  const outputDir = args.outputDir ?? defaultOutputDir();
  const report = runValidateLh1aApparatus({ outputDir });
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.validation.all_pass ? 0 : 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
