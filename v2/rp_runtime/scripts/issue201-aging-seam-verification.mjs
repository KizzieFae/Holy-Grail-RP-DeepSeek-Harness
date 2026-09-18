#!/usr/bin/env node
/**
 * Issue #201 — information-aging apparatus qualification.
 */
import { runAgingApparatusQualification } from './lib/issue201-aging-qualification-lib.mjs';

const args = process.argv.slice(2);
if (!args.includes('--qualify')) {
  console.error('Usage: node issue201-aging-seam-verification.mjs --qualify');
  process.exit(1);
}

const report = await runAgingApparatusQualification();
console.log(JSON.stringify(report, null, 2));
process.exit(report.pass ? 0 : 1);
