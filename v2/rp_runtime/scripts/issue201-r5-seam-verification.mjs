#!/usr/bin/env node
/**
 * Issue #201 R5 — apparatus qualification (deterministic only).
 */
import { runR5ApparatusQualification } from './lib/issue201-r5-qualification-lib.mjs';
import { verifyR5FrozenHashes } from './lib/issue201-r5-frozen-hashes.mjs';

const args = process.argv.slice(2);
if (!args.includes('--qualify')) {
  console.error('Usage: node issue201-r5-seam-verification.mjs --qualify');
  process.exit(1);
}

const hashCheck = verifyR5FrozenHashes();
const report = runR5ApparatusQualification();
console.log(JSON.stringify({ frozen_hashes: hashCheck, qualification: report }, null, 2));
process.exit(report.pass && hashCheck.pass ? 0 : 1);
