#!/usr/bin/env node
/** Export JS manifest policy for cross-runtime parity checks (#134). */

import {
  ALLOWED_SOURCE_KINDS,
  resolveInferenceKind,
} from '../src/lib/manifest-projection-policy.mjs';

const policy = {};
for (const [kind, allowed] of Object.entries(ALLOWED_SOURCE_KINDS)) {
  policy[kind] = [...allowed].sort();
}

const payload = {
  inference_kinds: Object.keys(ALLOWED_SOURCE_KINDS).sort(),
  allowed_source_kinds: policy,
  aliases: {
    director_decision: resolveInferenceKind('director_decision'),
    character_move: resolveInferenceKind('character_move'),
  },
};

process.stdout.write(`${JSON.stringify(payload)}\n`);
